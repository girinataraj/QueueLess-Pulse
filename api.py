"""Versioned transport adapters; mutations execute the existing queue/owner handlers."""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, jsonify, make_response, request, session
from access import current_user, login_required, owner_business, owned_businesses, readable_services, reception_service
from models import db, Business, Branch, Service, Membership, ServiceAssignment, Ticket, StaffInvite, ReceptionGrant
from universal import public_business, public_services, reception_services, display_rows, statistics, service_for, aware, make_invitation, history_filters, qr_response

api = Blueprint('api', __name__, url_prefix='/api/v1')

def csrf():
    session.setdefault('csrf_token', secrets.token_urlsafe(32))
    session.setdefault('owner_id', str(uuid.uuid4()))
    return session['csrf_token']

def business_data(b):
    return {k: getattr(b, k) for k in ('id', 'slug', 'name', 'category', 'description', 'timezone', 'is_active')}

def branch_data(b):
    return {k: getattr(b, k) for k in ('id', 'business_id', 'name', 'address', 'is_active')}

def service_data(s):
    return {**{k: getattr(s, k) for k in ('id', 'branch_id', 'name', 'prefix', 'average_minutes', 'counter_label', 'is_active')}, 'description': s.description or ''}

def ticket_data(t):
    from operations import availability, public_announcement
    return {**current_app.extensions['queue_state'](t), 'token': t.token,
            'business_date': str(t.business_date), 'can_cancel': t.owner_id == session.get('owner_id') and t.status == 'WAITING', 'created_at':aware(t.created_at).isoformat(), 'called_at':aware(t.called_at).isoformat() if t.called_at else None, 'finished_at':aware(t.finished_at).isoformat() if t.finished_at else None, 'service_availability':availability(t.service), 'entry_path':f'/app/b/{t.service.branch.business.slug}/service/{t.service_id}', 'announcement_id':public_announcement(t.service)}

def invoke(endpoint, **kwargs):
    """Reuse audited form validation, role checks, locks and transaction commits."""
    if request.mimetype != 'application/x-www-form-urlencoded':
        abort(415, 'Send URL-encoded form fields.')
    response = make_response(current_app.view_functions[endpoint](**kwargs))
    if response.status_code >= 400:
        abort(response.status_code, 'Invalid credentials.' if response.status_code == 401 else 'Request rejected.')
    return response

@api.get('/session')
def bootstrap():
    user = current_user()
    memberships = Membership.query.filter_by(staff_id=user.id, is_active=True).all() if user else []
    return jsonify(csrf_token=csrf(), demo_mode=current_app.config['DEMO_MODE'], gateway_required=current_app.config['DEMO_GATEWAY_ENABLED'],
                   owner_registration_enabled=current_app.config['OWNER_REGISTRATION_ENABLED'], user={'id': user.id, 'username': user.username, 'email': user.email} if user else None,
                   memberships=[{'business_id': m.business_id, 'role': m.role} for m in memberships])

@api.post('/auth/register')
def register():
    invoke('universal.register')
    return bootstrap(), 201

@api.post('/auth/login')
def login():
    invoke('universal.owner_login')
    return bootstrap()

@api.post('/auth/logout')
def logout():
    invoke('staff_logout')
    return bootstrap()

@api.get('/businesses')
def businesses():
    return jsonify([business_data(b) for b in Business.query.filter_by(is_active=True).order_by(Business.id)])

@api.get('/businesses/<slug>')
def business(slug):
    b = public_business(slug)
    return jsonify(business=business_data(b), branches=[branch_data(v) for v in Branch.query.filter_by(business_id=b.id, is_active=True).order_by(Branch.id)], services=[service_data(v) for v in public_services(b)])

@api.post('/services/<int:service_id>/tickets')
def issue(service_id):
    response = invoke('join_queue', service_id=service_id)
    token = urlsplit(response.headers['Location']).path.rsplit('/', 1)[-1]
    return jsonify(ticket_data(Ticket.query.filter_by(token=token).first_or_404())), 201

@api.get('/tickets/<token>')
def ticket(token):
    return jsonify(ticket_data(Ticket.query.filter_by(token=token).first_or_404()))

@api.post('/tickets/<token>/cancel')
def cancel(token):
    invoke('cancel_ticket', token=token)
    return ticket(token)

@api.get('/my-tickets')
def my_tickets():
    rows = Ticket.query.filter_by(owner_id=session['owner_id']).order_by(Ticket.id.desc()).limit(30).all() if session.get('owner_id') else []
    return jsonify([ticket_data(t) for t in rows])

@api.get('/staff/queues')
def staff_queues():
    return current_app.view_functions['staff_live']()

@api.get('/reception/queues')
def reception_queues():
    from operations import reception_details
    rows=display_rows(readable_services())
    base=(current_app.config.get('PUBLIC_BASE_URL') or request.url_root.rstrip('/')).rstrip('/')
    for row in rows:
        row.update(reception_details(db.session.get(Service,row['service_id'])))
        row['patient_url']=f"{base}/app/b/{row['business_slug']}/service/{row['service_id']}"
    return jsonify(rows)

@api.get('/staff/services/<int:service_id>/qr.png')
def service_qr(service_id):
    service=reception_service(service_id)
    base=(current_app.config.get('PUBLIC_BASE_URL') or request.url_root.rstrip('/')).rstrip('/')
    return qr_response(f'{base}/app/b/{service.branch.business.slug}/service/{service.id}',
                       f'{service.branch.business.slug}-service-{service.id}.png')

def action(endpoint, **kwargs):
    response = invoke(endpoint, **kwargs)
    return jsonify(resource_path=response.headers.get('Location', ''))

@api.post('/staff/services/<int:service_id>/call')
def call(service_id):
    return action('staff_call', service_id=service_id)

@api.post('/staff/tickets/<int:ticket_id>/complete')
def complete(ticket_id):
    return action('staff_complete', ticket_id=ticket_id)

@api.post('/staff/tickets/<int:ticket_id>/skip')
def skip(ticket_id):
    return action('staff_skip', ticket_id=ticket_id)

@api.get('/owner/businesses')
@login_required
def owned():
    return jsonify([business_data(b) for b in owned_businesses()])

@api.get('/owner/businesses/<int:business_id>')
def owner_bundle(business_id):
    b = owner_business(business_id)
    members = Membership.query.filter_by(business_id=b.id).order_by(Membership.id).all()
    return jsonify(business=business_data(b), branches=[branch_data(v) for v in Branch.query.filter_by(business_id=b.id).order_by(Branch.id)],
                   services=[service_data(v) for v in Service.query.join(Branch).filter(Branch.business_id == b.id).order_by(Service.id)],
                   members=[{'id': m.id, 'username': m.staff.username, 'role': m.role, 'is_active': m.is_active,
                             'can_issue_walkins':bool(db.session.get(ReceptionGrant,m.id)), 'service_ids': [a.service_id for a in ServiceAssignment.query.filter_by(membership_id=m.id)]} for m in members], stats=statistics(b.id))

@api.get('/owner/businesses/<int:business_id>/stats')
def stats(business_id):
    owner_business(business_id)
    return jsonify(statistics(business_id))

# Explicit routes and methods keep the adapter surface closed to arbitrary views.
def register_owner_action(path, endpoint, target, created=False):
    def adapter(**kwargs):
        result = action(target, **kwargs)
        return (result, 201) if created else result
    api.add_url_rule(path, endpoint, adapter, methods=['POST'])

register_owner_action('/owner/businesses', 'create_business', 'universal.create_business', True)
register_owner_action('/owner/businesses/<int:business_id>', 'edit_business', 'universal.edit_business')
register_owner_action('/owner/businesses/<int:business_id>/branches', 'create_branch', 'universal.create_branch', True)
register_owner_action('/owner/businesses/<int:business_id>/branches/<int:branch_id>', 'edit_branch', 'universal.edit_branch')
register_owner_action('/owner/businesses/<int:business_id>/services', 'create_service', 'universal.create_service', True)
register_owner_action('/owner/businesses/<int:business_id>/services/<int:service_id>', 'edit_service', 'universal.edit_service')
register_owner_action('/owner/businesses/<int:business_id>/staff', 'create_staff', 'universal.create_staff', True)
register_owner_action('/owner/businesses/<int:business_id>/staff/<int:membership_id>/permissions', 'permissions', 'universal.permissions')

@api.post('/owner/businesses/<int:business_id>/invitations')
def invite(business_id):
    if request.mimetype != 'application/x-www-form-urlencoded':
        abort(415)
    b, url = make_invitation(business_id, react=True)
    return jsonify(invite_url=url, business_name=b.name), 201

@api.get('/invitations/<token>')
def invitation(token):
    invite = StaffInvite.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    if not invite or invite.used_at or aware(invite.expires_at) < datetime.now(timezone.utc):
        abort(410, 'Invitation expired or already used.')
    return jsonify(business_name=db.session.get(Business, invite.business_id).name)

@api.post('/invitations/<token>')
def accept(token):
    invoke('universal.accept_invite', token=token)
    return bootstrap()

@api.get('/owner/businesses/<int:business_id>/history')
def history(business_id):
    business=owner_business(business_id)
    query = Ticket.query.join(Service).join(Branch).filter(Branch.business_id == business_id, Ticket.status.in_(('COMPLETED', 'SKIPPED')))
    status = request.args.get('status')
    if status:
        if status not in ('COMPLETED', 'SKIPPED'):
            abort(400, 'Invalid history status.')
        query = query.filter(Ticket.status == status)
    if request.args.get('service_id'):
        sid = request.args.get('service_id', type=int)
        service_for(business_id, sid)
        query = query.filter(Ticket.service_id == sid)
    query=history_filters(query,business)
    page = request.args.get('page', 1, type=int)
    if page is None or page < 1:
        abort(400, 'Invalid page.')
    result = db.paginate(query.order_by(Ticket.id.desc()).statement, page=page, per_page=25, error_out=False)
    return jsonify(page=result.page, pages=result.pages, total=result.total,
                   items=[{'number': t.display_number, 'date': str(t.business_date), 'finished_at': aware(t.finished_at).isoformat() if t.finished_at else None, 'service': t.service.name, 'branch': t.service.branch.name, 'status': t.status,
                           'events': [{'action': e.event_type, 'at': aware(e.timestamp).isoformat()} for e in t.events]} for t in result.items])

@api.get('/display/<slug>')
def display(slug):
    b = public_business(slug)
    bid = request.args.get('branch_id', type=int)
    if request.args.get('branch_id') and not bid:
        abort(400)
    return jsonify(display_rows(reception_services(b, bid)))
