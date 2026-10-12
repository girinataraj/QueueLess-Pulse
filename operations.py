"""Additive operational APIs. Every mutation uses existing service locks and RBAC."""
from datetime import date, datetime, timezone
import csv, io, uuid
from zoneinfo import ZoneInfo
from flask import Blueprint, abort, jsonify, request, session, Response
from access import current_user, require_service, reception_service, owner_business
from models import db, Staff, Service, Ticket, TicketEvent, Membership, ServiceAssignment, ReceptionGrant, DoctorDuty, OperationReceipt, AdminEvent, Branch
from queue_core import lock_service, issue_ticket
from universal import aware, business_day

operations = Blueprint('operations', __name__, url_prefix='/api/v1')

def duty_data(service_id, staff_id):
    duty=DoctorDuty.query.filter_by(service_id=service_id,staff_id=staff_id).first()
    return {'state':duty.state if duty else 'NOT_STARTED','started_at':aware(duty.started_at).isoformat() if duty else None,'updated_at':aware(duty.updated_at).isoformat() if duty else None}

def active_duties(service):
    # Revoked/inactive accounts and assignments cannot advertise availability.
    return DoctorDuty.query.join(Membership, (Membership.staff_id==DoctorDuty.staff_id) & (Membership.business_id==service.branch.business_id)).join(ServiceAssignment,ServiceAssignment.membership_id==Membership.id).join(Membership.staff).filter(DoctorDuty.service_id==service.id,ServiceAssignment.service_id==service.id,Membership.is_active.is_(True),Membership.staff.has(is_active=True),DoctorDuty.state!='OFF_DUTY').all()

def availability(service):
    if not service.is_active or not service.branch.is_active or not service.branch.business.is_active:return 'CLOSED'
    rows=active_duties(service)
    if any(d.state=='AVAILABLE' for d in rows):return 'AVAILABLE'
    if rows:return 'ON_BREAK'
    return 'NOT_RECORDED'

def receipt(service_id, action, ticket_id=None):
    if request.mimetype!='application/x-www-form-urlencoded':abort(415,'Send URL-encoded form fields.')
    try:key=str(uuid.UUID(request.form.get('request_key','')))
    except ValueError:abort(400,'Invalid submission key')
    old=OperationReceipt.query.filter_by(staff_id=current_user().id,request_key=key).first()
    if old and (old.service_id!=service_id or old.action!=action or old.ticket_id!=ticket_id):abort(409,'Submission key already used')
    return key,old

@operations.post('/staff/services/<int:service_id>/duty')
def set_duty(service_id):
    service=lock_service(service_id);require_service(service)
    action=request.form.get('action','')
    if action not in ('start','break','resume','end'):abort(400,'Choose a valid duty action')
    key,old=receipt(service_id,'DUTY_'+action)
    if old:return jsonify(duty_data(service_id,current_user().id))
    duty=DoctorDuty.query.filter_by(service_id=service_id,staff_id=current_user().id).first()
    state=duty.state if duty else 'NOT_STARTED'
    allowed={'start':('NOT_STARTED','OFF_DUTY'),'break':('AVAILABLE',),'resume':('ON_BREAK',),'end':('AVAILABLE','ON_BREAK')}
    if state not in allowed[action]:abort(409,'Availability changed. Refresh before retrying.')
    if action in ('break','end') and Ticket.query.filter_by(service_id=service_id,status='CALLED').first():abort(409,'Complete or skip the active ticket before changing duty.')
    if action in ('start','resume') and (not service.is_active or not service.branch.is_active or not service.branch.business.is_active):abort(409,'This service is closed.')
    now=datetime.now(timezone.utc)
    if duty is None:duty=DoctorDuty(service_id=service_id,staff_id=current_user().id,started_at=now);db.session.add(duty)
    if action=='start':duty.started_at=now
    duty.state={'start':'AVAILABLE','resume':'AVAILABLE','break':'ON_BREAK','end':'OFF_DUTY'}[action];duty.updated_at=now
    db.session.add(OperationReceipt(service_id=service_id,staff_id=current_user().id,request_key=key,action='DUTY_'+action))
    db.session.add(AdminEvent(business_id=service.branch.business_id,staff_id=current_user().id,action='DOCTOR_DUTY_'+action.upper(),details=f'service:{service_id}'))
    db.session.commit();return jsonify(duty_data(service_id,current_user().id))

@operations.post('/staff/tickets/<int:ticket_id>/recall')
def recall(ticket_id):
    ticket=db.get_or_404(Ticket,ticket_id);service=lock_service(ticket.service_id);require_service(service);db.session.refresh(ticket)
    key,old=receipt(service.id,'RECALL',ticket.id)
    if not old:
        if ticket.status!='CALLED':abort(409,'Only the currently called ticket can be recalled.')
        db.session.add(TicketEvent(ticket_id=ticket.id,event_type='RECALLED',staff_id=current_user().id))
        db.session.add(OperationReceipt(service_id=service.id,staff_id=current_user().id,request_key=key,action='RECALL',ticket_id=ticket.id));db.session.commit()
    return jsonify(resource_path='/staff/dashboard')

def doctor_details(service):
    today,start,end=business_day(service.branch.business)
    completed=Ticket.query.filter(Ticket.service_id==service.id,Ticket.status=='COMPLETED',Ticket.finished_at>=start,Ticket.finished_at<end,Ticket.called_at.is_not(None)).all()
    duration=[max(0,(aware(t.finished_at)-aware(t.called_at)).total_seconds()/60) for t in completed]
    activity=TicketEvent.query.join(Ticket).filter(Ticket.service_id==service.id,TicketEvent.staff_id==current_user().id,TicketEvent.timestamp>=start,TicketEvent.timestamp<end).order_by(TicketEvent.id.desc()).limit(30).all()
    called=Ticket.query.filter_by(service_id=service.id,status='CALLED').first()
    return {'duty':duty_data(service.id,current_user().id),'called_at':aware(called.called_at).isoformat() if called and called.called_at else None,'average_duration_today':round(sum(duration)/len(duration),1) if duration else None,'duration_samples_today':len(duration),'activity':[{'number':e.ticket.display_number,'action':e.event_type,'at':aware(e.timestamp).isoformat()} for e in activity]}

def can_walkin(service):
    user=current_user()
    if not user:return False
    member=Membership.query.filter_by(business_id=service.branch.business_id,staff_id=user.id,is_active=True,role='staff').first()
    return bool(member and db.session.get(ReceptionGrant,member.id))

def reception_details(service):
    rows=Ticket.query.filter_by(service_id=service.id,status='WAITING').order_by(Ticket.id).all()
    called=Ticket.query.filter_by(service_id=service.id,status='CALLED').first()
    today,start,end=business_day(service.branch.business)
    actions=AdminEvent.query.filter(AdminEvent.business_id==service.branch.business_id,AdminEvent.staff_id==current_user().id,AdminEvent.action=='RECEPTION_WALKIN',AdminEvent.timestamp>=start,AdminEvent.timestamp<end,AdminEvent.details.like(f'service:{service.id} token:%')).order_by(AdminEvent.id.desc()).limit(15).all()
    return {'availability':availability(service),'can_issue_walkins':can_walkin(service),'waiting':[{'number':t.display_number,'business_date':str(t.business_date)} for t in rows],'estimated_wait':(len(rows)+bool(called))*service.average_minutes,'average_minutes':service.average_minutes,'activity':[{'action':a.action,'details':a.details,'at':aware(a.timestamp).isoformat()} for a in actions]}

@operations.post('/reception/services/<int:service_id>/walkins')
def walkin(service_id):
    lock_service(service_id)
    service=reception_service(service_id)
    if not can_walkin(service):abort(403,'Walk-in issuance requires an explicit Owner grant.')
    key,old=receipt(service_id,'WALKIN')
    # Staff issuance never grants the receptionist the patient's private browser ownership.
    owner=str(uuid.uuid5(uuid.NAMESPACE_URL,f'queueless:walkin:{current_user().id}:{key}'))
    ticket,created=issue_ticket(service_id,key,owner,current_user().id)
    if not old:db.session.add(OperationReceipt(service_id=service_id,staff_id=current_user().id,request_key=key,action='WALKIN'))
    if created:db.session.add(AdminEvent(business_id=service.branch.business_id,staff_id=current_user().id,action='RECEPTION_WALKIN',details=f'service:{service_id} token:{ticket.display_number} date:{ticket.business_date}'))
    db.session.commit()
    return jsonify(number=ticket.display_number,business_date=str(ticket.business_date),service_name=service.name,created=created),201

@operations.get('/reception/services/<int:service_id>/tokens')
def locate(service_id):
    reception_service(service_id)
    try:day=date.fromisoformat(request.args.get('date',''))
    except ValueError:abort(400,'Choose a business-local date.')
    number=request.args.get('number','').strip().upper()
    if not number or len(number)>20:abort(400,'Enter a public token number.')
    t=Ticket.query.filter_by(service_id=service_id,business_date=day,display_number=number).first_or_404()
    return jsonify(number=t.display_number,business_date=str(t.business_date),status=t.status)

def public_announcement(service):
    called=Ticket.query.filter_by(service_id=service.id,status='CALLED').first()
    e=TicketEvent.query.filter(TicketEvent.ticket_id==called.id,TicketEvent.event_type.in_(('CALLED','RECALLED'))).order_by(TicketEvent.id.desc()).first() if called else None
    return str(e.id) if e else ''

@operations.get('/owner/businesses/<int:business_id>/operations')
def owner_operations(business_id):
    b=owner_business(business_id);today,start,end=business_day(b)
    tickets=Ticket.query.join(Service).join(Branch).filter(Branch.business_id==b.id).all()
    issued=[t for t in tickets if start<=aware(t.created_at)<end]
    completed=[t for t in tickets if t.status=='COMPLETED' and t.finished_at and start<=aware(t.finished_at)<end]
    called=[t for t in tickets if t.called_at and start<=aware(t.called_at)<end]
    waits=[max(0,(aware(t.called_at)-aware(t.created_at)).total_seconds()/60) for t in called]
    durations=[max(0,(aware(t.finished_at)-aware(t.called_at)).total_seconds()/60) for t in completed if t.called_at]
    hourly=[{'hour':f'{h:02d}:00','arrivals':sum(aware(t.created_at).astimezone(ZoneInfo(b.timezone)).hour==h for t in issued),'completed':sum(aware(t.finished_at).astimezone(ZoneInfo(b.timezone)).hour==h for t in completed)} for h in range(24)]
    services=Service.query.join(Branch).filter(Branch.business_id==b.id).order_by(Service.id).all()
    activity=AdminEvent.query.filter(AdminEvent.business_id==b.id,AdminEvent.timestamp>=start,AdminEvent.timestamp<end).order_by(AdminEvent.id.desc()).limit(30).all()
    workload=TicketEvent.query.join(Ticket).join(Service).join(Branch).filter(Branch.business_id==b.id,TicketEvent.timestamp>=start,TicketEvent.timestamp<end,TicketEvent.event_type.in_(('COMPLETED','SKIPPED'))).all()
    doctors={e.staff_id:e.staff.username for e in workload if e.staff_id and e.staff}
    return jsonify(business_date=str(today),issued_today=len(issued),average_wait_today=round(sum(waits)/len(waits),1) if waits else None,wait_samples=len(waits),average_duration_today=round(sum(durations)/len(durations),1) if durations else None,duration_samples=len(durations),hourly=hourly,
        services=[{'id':s.id,'name':s.name,'availability':availability(s),'completed_today':sum(t.service_id==s.id for t in completed),'duties':[{'username':db.session.get(Staff,d.staff_id).username,'state':d.state} for d in active_duties(s)]} for s in services],
        workload=[{'username':name,'reviewed':sum(e.staff_id==sid and e.event_type=='COMPLETED' for e in workload),'skipped':sum(e.staff_id==sid and e.event_type=='SKIPPED' for e in workload)} for sid,name in doctors.items()],activity=[{'action':a.action,'details':a.details,'at':aware(a.timestamp).isoformat()} for a in activity])

@operations.post('/owner/businesses/<int:business_id>/export')
def export_report(business_id):
    b=owner_business(business_id)
    try:day=date.fromisoformat(request.form.get('date',''))
    except ValueError:abort(400,'Choose a business-local date.')
    _,start,end=business_day(b,day)
    rows=Ticket.query.join(Service).join(Branch).filter(Branch.business_id==b.id,Ticket.finished_at>=start,Ticket.finished_at<end,Ticket.status.in_(('COMPLETED','SKIPPED'))).order_by(Ticket.id).all()
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['Token','Issue date','Finish date (UTC)','Service ID','Status'])
    # Export public token data only. Prefix user-controlled values against spreadsheet formulas.
    for t in rows:writer.writerow(["'"+t.display_number,str(t.business_date),aware(t.finished_at).isoformat(),t.service_id,t.status])
    db.session.add(AdminEvent(business_id=b.id,staff_id=current_user().id,action='REPORT_EXPORTED',details=f'date:{day} rows:{len(rows)}'));db.session.commit()
    return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename="queue-report-{day}.csv"'})
