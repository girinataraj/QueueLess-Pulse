import hashlib
import io
import re
import secrets
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import urlsplit
import qrcode
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from models import db, Staff, Business, Branch, Membership, Service, ServiceAssignment, StaffInvite, AdminEvent, Ticket
from access import current_user, login_required, owner_business, owned_businesses

universal = Blueprint('universal', __name__)

def audit(business_id, action, details=''):
    with db.session.no_autoflush:
        actor=current_user()
        db.session.add(AdminEvent(business_id=business_id,staff_id=actor.id,action=action,details=details))

def commit():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, 'That name, prefix, username or membership already exists. Choose another value.')

def value(name, maximum, required=True):
    result=request.form.get(name,'').strip()
    if (required and not result) or len(result)>maximum:
        abort(400, f'Invalid {name.replace("_"," ")}.')
    return result

def integer(name,minimum=1,maximum=2147483647):
    try:
        result=int(request.form.get(name,''))
    except ValueError:
        abort(400,f'Invalid {name}.')
    if not minimum<=result<=maximum:
        abort(400,f'Invalid {name}.')
    return result

def account_fields():
    username=value('username',64).lower()
    password=request.form.get('password','')
    if not re.fullmatch(r'[a-z0-9_.-]{3,64}',username) or not 12<=len(password)<=128:
        abort(400,'Use a username of 3–64 letters/numbers and a password of 12–128 characters.')
    email=value('email',254,False).lower() or None
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):
        abort(400,'Invalid email address.')
    return username,password,email

def establish(user):
    owner=session.get('owner_id')
    session.clear()
    session.update(staff_id=user.id,owner_id=owner or secrets.token_hex(16))

def business_fields(business):
    business.name=value('name',128)
    business.description=value('description',1000,False)
    business.category=value('category',40)
    timezone_name=value('timezone',64)
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError,ValueError):
        abort(400,'Unknown timezone; use an IANA name such as Asia/Kolkata.')
    if business.id and business.timezone != timezone_name and Ticket.query.join(Service).join(Branch).filter(Branch.business_id==business.id).first():
        abort(409,'Timezone cannot change after ticket history exists.')
    business.timezone=timezone_name

def branch_for(business_id,branch_id):
    return Branch.query.filter_by(business_id=business_id,id=branch_id).first_or_404()

def service_for(business_id,service_id):
    return Service.query.join(Branch).filter(Branch.business_id==business_id,Service.id==service_id).first_or_404()

def public_business(slug):
    return Business.query.filter_by(slug=slug,is_active=True).first_or_404()

def public_services(business,branch_id=None):
    query=Service.query.join(Branch).filter(Branch.business_id==business.id,Branch.is_active.is_(True),Service.is_active.is_(True))
    if branch_id:
        branch=branch_for(business.id,branch_id)
        if not branch.is_active:
            abort(404)
        query=query.filter(Service.branch_id==branch.id)
    return query.order_by(Service.id).all()

def reception_services(business,branch_id=None):
    query=Service.query.join(Branch).filter(Branch.business_id==business.id)
    if branch_id:
        branch_for(business.id,branch_id)
        query=query.filter(Service.branch_id==branch_id)
    outstanding=Ticket.query.filter(Ticket.service_id==Service.id,Ticket.status.in_(('WAITING','CALLED'))).exists()
    return query.filter(db.or_(db.and_(Service.is_active.is_(True),Branch.is_active.is_(True)),outstanding)).order_by(Service.id).all()

def display_rows(services):
    rows=[]
    for service in services:
        called=Ticket.query.filter_by(service_id=service.id,status='CALLED').first()
        rows.append({'service_id':service.id,'service_name':service.name,'branch_name':service.branch.name,'counter_label':service.counter_label,'currently_called':called.display_number if called else '---','waiting_count':Ticket.query.filter_by(service_id=service.id,status='WAITING').count()})
    return rows

@universal.route('/owner/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username,password,email=account_fields()
        if request.form.get('confirm_password') != password:
            abort(400,'Passwords must match.')
        user=Staff(username=username,email=email)
        user.set_password(password)
        db.session.add(user)
        commit()
        establish(user)
        flash('Account created. Create your business to get started.','success')
        return redirect(url_for('universal.owner_home'),303)
    return render_template('owner/auth.html',mode='register')

@universal.route('/owner/login',methods=['GET','POST'])
def owner_login():
    if request.method=='POST':
        user=Staff.query.filter_by(username=request.form.get('username','').strip().lower(),is_active=True).first()
        if user and user.check_password(request.form.get('password','')):
            establish(user)
            return redirect(url_for('universal.owner_home'),303)
        return render_template('owner/auth.html',mode='login',error='Invalid credentials'),401
    return render_template('owner/auth.html',mode='login')

@universal.get('/owner')
@login_required
def owner_home():
    return render_template('owner/home.html',businesses=owned_businesses())

@universal.post('/owner/business/create')
@login_required
def create_business():
    slug=value('slug',80).lower()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):
        abort(400,'Business URL must contain lowercase letters, numbers and hyphens.')
    business=Business(slug=slug)
    business_fields(business)
    db.session.add(business)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(409,'That business URL already exists.')
    db.session.add(Membership(business_id=business.id,staff_id=current_user().id,role='owner'))
    audit(business.id,'BUSINESS_CREATED',business.name)
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business.id),303)

@universal.post('/owner/business/<int:business_id>/edit')
@login_required
def edit_business(business_id):
    business=owner_business(business_id,lock=True)
    db.session.scalars(select(Service).join(Branch).where(Branch.business_id==business.id).order_by(Service.id).with_for_update(of=Service)).all()
    business_fields(business)
    audit(business.id,'BUSINESS_UPDATED')
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.route('/owner/business/<int:business_id>/branches/create',methods=['POST'])
@login_required
def create_branch(business_id):
    owner_business(business_id,lock=True)
    branch=Branch(business_id=business_id,name=value('name',128),address=value('address',300,False))
    db.session.add(branch)
    audit(business_id,'BRANCH_CREATED',branch.name)
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.post('/owner/business/<int:business_id>/branches/<int:branch_id>/edit')
@login_required
def edit_branch(business_id,branch_id):
    owner_business(business_id,lock=True)
    branch=branch_for(business_id,branch_id)
    # Serialize with joins/calls while changing availability.
    db.session.scalars(select(Service).where(Service.branch_id==branch.id).order_by(Service.id).with_for_update()).all()
    branch.name=value('name',128)
    branch.address=value('address',300,False)
    branch.is_active=request.form.get('is_active')=='on'
    audit(business_id,'BRANCH_UPDATED',str(branch.id))
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)


def service_fields(service):
    service.name=value('name',128)
    service.description=value('description',256,False)
    prefix=value('prefix',6).upper()
    if not re.fullmatch('[A-Z0-9]{1,6}',prefix):
        abort(400,'Prefix must contain 1–6 letters or digits.')
    service.prefix=prefix
    service.average_minutes=integer('average_minutes',1,120)
    service.counter_label=value('counter_label',40,False)
    service.is_active=request.form.get('is_active')=='on'

@universal.post('/owner/business/<int:business_id>/services/create')
@login_required
def create_service(business_id):
    owner_business(business_id,lock=True)
    branch=branch_for(business_id,integer('branch_id'))
    service=Service(branch_id=branch.id)
    service_fields(service)
    db.session.add(service)
    audit(business_id,'SERVICE_CREATED',service.name)
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.post('/owner/business/<int:business_id>/services/<int:service_id>/edit')
@login_required
def edit_service(business_id,service_id):
    owner_business(business_id,lock=True)
    service=service_for(business_id,service_id)
    db.session.execute(select(Service.id).where(Service.id==service.id).with_for_update())
    db.session.refresh(service)
    service_fields(service)
    audit(business_id,'SERVICE_UPDATED',str(service.id))
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.post('/owner/business/<int:business_id>/staff/create')
@login_required
def create_staff(business_id):
    owner_business(business_id,lock=True)
    username,password,email=account_fields()
    user=Staff(username=username,email=email)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(409,'Account already exists. Use an invitation to add an existing user.')
    db.session.add(Membership(business_id=business_id,staff_id=user.id,role='staff'))
    audit(business_id,'STAFF_CREATED',username)
    commit()
    flash('Staff created. Assign service permissions below.','success')
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.post('/owner/business/<int:business_id>/staff/<int:membership_id>/permissions')
@login_required
def permissions(business_id,membership_id):
    owner_business(business_id,lock=True)
    membership=Membership.query.filter_by(id=membership_id,business_id=business_id,role='staff').first_or_404()
    services=Service.query.join(Branch).filter(Branch.business_id==business_id).order_by(Service.id).with_for_update(of=Service).all()
    try:
        selected={int(v) for v in request.form.getlist('service_ids')}
    except ValueError:
        abort(400,'Invalid service assignment.')
    if not selected <= {s.id for s in services}:
        abort(404,'Service is outside this business.')
    membership.is_active=request.form.get('is_active')=='on'
    ServiceAssignment.query.filter_by(membership_id=membership.id).delete()
    db.session.add_all([ServiceAssignment(membership_id=membership.id,service_id=sid) for sid in selected])
    audit(business_id,'STAFF_PERMISSIONS_UPDATED',str(membership.id))
    commit()
    return redirect(url_for('universal.owner_dashboard',business_id=business_id),303)

@universal.post('/owner/business/<int:business_id>/staff/invite')
@login_required
def invite_staff(business_id):
    business=owner_business(business_id)
    token=secrets.token_urlsafe(32)
    invite=StaffInvite(business_id=business_id,token_hash=hashlib.sha256(token.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=24),created_by=current_user().id)
    db.session.add(invite)
    audit(business_id,'STAFF_INVITED')
    commit()
    invite_path=url_for('universal.accept_invite',token=token)
    base=current_app.config.get('PUBLIC_BASE_URL') or request.url_root.rstrip('/')
    return render_template('owner/invite_created.html',business=business,invite_url=base.rstrip('/')+invite_path)

@universal.route('/invite/<token>',methods=['GET','POST'])
def accept_invite(token):
    statement=select(StaffInvite).where(StaffInvite.token_hash==hashlib.sha256(token.encode()).hexdigest())
    if request.method=='POST':
        statement=statement.with_for_update()
    invite=db.session.scalar(statement)
    if not invite or invite.used_at or aware(invite.expires_at)<datetime.now(timezone.utc):
        abort(410,'Invitation expired or already used.')
    business=db.session.get(Business,invite.business_id)
    if request.method=='POST':
        user=current_user()
        if not user:
            username,password,email=account_fields()
            if request.form.get('confirm_password')!=password:
                abort(400,'Passwords must match.')
            user=Staff(username=username,email=email)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                abort(409,'Account exists. Sign in first, then reopen the invitation.')
        member=Membership.query.filter_by(business_id=business.id,staff_id=user.id).first()
        if member:
            if not member.is_active:
                abort(403,'Membership was revoked. Ask the owner to restore it directly.')
        else:
            db.session.add(Membership(business_id=business.id,staff_id=user.id,role='staff'))
        invite.used_at=datetime.now(timezone.utc)
        db.session.add(AdminEvent(business_id=business.id,staff_id=user.id,action='INVITE_ACCEPTED'))
        commit()
        establish(user)
        flash('Invitation accepted. Your owner can now assign services.','success')
        return redirect(url_for('staff_dashboard'),303)
    return render_template('owner/accept_invite.html',business=business,user=current_user())


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value

def statistics(business_id):
    query=Ticket.query.join(Service).join(Branch).filter(Branch.business_id==business_id)
    counts=dict(query.with_entities(Ticket.status,func.count(Ticket.id)).group_by(Ticket.status).all())
    # Mean computed from actual persisted timestamps; no fabricated AI metric.
    called=query.filter(Ticket.called_at.is_not(None)).all()
    waits=[max(0,(aware(t.called_at)-aware(t.created_at)).total_seconds()/60) for t in called]
    completed=query.filter(Ticket.status=='COMPLETED',Ticket.called_at.is_not(None),Ticket.finished_at.is_not(None)).all()
    durations=[max(0,(aware(t.finished_at)-aware(t.called_at)).total_seconds()/60) for t in completed]
    business=db.session.get(Business,business_id)
    today=datetime.now(ZoneInfo(business.timezone)).date()
    throughput=query.filter(Ticket.business_date>=today-timedelta(days=6),Ticket.status=='COMPLETED').with_entities(Ticket.business_date,func.count(Ticket.id)).group_by(Ticket.business_date).order_by(Ticket.business_date).all()
    return {'waiting':counts.get('WAITING',0),'called':counts.get('CALLED',0),'completed':counts.get('COMPLETED',0),'skipped':counts.get('SKIPPED',0),'cancelled':counts.get('CANCELLED',0),'average_wait':round(sum(waits)/len(waits),1) if waits else None,'average_duration':round(sum(durations)/len(durations),1) if durations else None,'wait_samples':len(waits),'duration_samples':len(durations),'throughput':[{'date':str(d),'completed':n} for d,n in throughput]}

@universal.get('/owner/business/<int:business_id>')
@login_required
def owner_dashboard(business_id):
    business=owner_business(business_id)
    services=Service.query.join(Branch).filter(Branch.business_id==business_id).order_by(Service.id).all()
    members=Membership.query.filter_by(business_id=business_id).order_by(Membership.id).all()
    assignments={m.id:{a.service_id for a in ServiceAssignment.query.filter_by(membership_id=m.id)} for m in members}
    return render_template('owner/dashboard.html',business=business,branches=Branch.query.filter_by(business_id=business_id).order_by(Branch.id).all(),services=services,members=members,assignments=assignments,stats=statistics(business_id))

@universal.get('/owner/business/<int:business_id>/stats')
@login_required
def stats_api(business_id):
    owner_business(business_id)
    return jsonify(statistics(business_id))

@universal.get('/owner/business/<int:business_id>/history')
@login_required
def history(business_id):
    business=owner_business(business_id)
    query=Ticket.query.join(Service).join(Branch).filter(Branch.business_id==business_id,Ticket.status.in_(('COMPLETED','SKIPPED')))
    status=request.args.get('status')
    if status:
        if status not in ('COMPLETED','SKIPPED'):
            abort(400)
        query=query.filter(Ticket.status==status)
    if request.args.get('service_id'):
        sid=request.args.get('service_id',type=int)
        service_for(business_id,sid)
        query=query.filter(Ticket.service_id==sid)
    page=request.args.get('page',1,type=int)
    if page is None or page<1:
        abort(400)
    result=db.paginate(query.order_by(Ticket.id.desc()).statement,page=page,per_page=25,error_out=False)
    return render_template('owner/history.html',business=business,history=result,services=Service.query.join(Branch).filter(Branch.business_id==business_id).all(),status=status)

@universal.get('/b/<slug>')
def landing(slug):
    business=public_business(slug)
    return render_template('customer/business.html',business=business,branches=Branch.query.filter_by(business_id=business.id,is_active=True).order_by(Branch.id).all())

@universal.get('/b/<slug>/branch/<int:branch_id>')
def branch_landing(slug,branch_id):
    business=public_business(slug)
    branch=branch_for(business.id,branch_id)
    services=public_services(business,branch_id)
    return render_template('customer/select_service.html',business=business,branch=branch,services=services)

@universal.get('/b/<slug>/service/<int:service_id>')
def service_entry(slug,service_id):
    business=public_business(slug)
    service=service_for(business.id,service_id)
    if not service.is_active or not service.branch.is_active:
        abort(404)
    return render_template('customer/select_service.html',business=business,branch=service.branch,services=[service])

@universal.get('/b/<slug>/display')
def business_display(slug):
    business=public_business(slug)
    branch_id=request.args.get('branch_id',type=int)
    if request.args.get('branch_id') and not branch_id:
        abort(400)
    reception_services(business,branch_id)
    return render_template('public/display.html',business=business,display_url=url_for('universal.business_display_api',slug=slug,branch_id=branch_id))

@universal.get('/b/<slug>/api/display')
def business_display_api(slug):
    business=public_business(slug)
    branch_id=request.args.get('branch_id',type=int)
    if request.args.get('branch_id') and not branch_id:
        abort(400)
    return jsonify(display_rows(reception_services(business,branch_id)))

@universal.get('/owner/business/<int:business_id>/qr.png')
@login_required
def qr(business_id):
    business=owner_business(business_id)
    endpoint='universal.landing'
    kwargs={'slug':business.slug}
    sid=request.args.get('service_id',type=int)
    bid=request.args.get('branch_id',type=int)
    if request.args.get('service_id') and not sid or request.args.get('branch_id') and not bid:
        abort(400)
    if sid:
        service_for(business_id,sid)
        endpoint='universal.service_entry'
        kwargs['service_id']=sid
    elif bid:
        branch_for(business_id,bid)
        endpoint='universal.branch_landing'
        kwargs['branch_id']=bid
    path=url_for(endpoint,**kwargs)
    base=current_app.config.get('PUBLIC_BASE_URL') or request.url_root.rstrip('/')
    image=qrcode.make(base.rstrip('/')+path)
    buffer=io.BytesIO()
    image.save(buffer,format='PNG')
    buffer.seek(0)
    return send_file(buffer,mimetype='image/png',as_attachment=request.args.get('download')=='1',download_name=f'{business.slug}-queue.png',max_age=0)
