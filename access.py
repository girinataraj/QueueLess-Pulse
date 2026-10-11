from functools import wraps
from flask import abort, session
from sqlalchemy import select, or_
from models import db, Staff, Business, Branch, Membership, Service, ServiceAssignment

def current_user():
    user = db.session.get(Staff, session.get('staff_id')) if session.get('staff_id') else None
    return user if user and user.is_active else None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            abort(401, 'Sign in to continue.')
        return fn(*args, **kwargs)
    return wrapped

def owner_business(business_id, lock=False):
    user = current_user()
    if not user:
        abort(401)
    statement = select(Business).join(Membership).where(Business.id == business_id, Membership.staff_id == user.id, Membership.role == 'owner', Membership.is_active.is_(True))
    if lock:
        statement = statement.with_for_update(of=Business)
    business = db.session.scalar(statement)
    if not business:
        abort(404, 'Business unavailable or access denied.')
    return business

def owned_businesses():
    user = current_user()
    if not user:
        return []
    return db.session.scalars(select(Business).join(Membership).where(Membership.staff_id==user.id,Membership.role=='owner',Membership.is_active.is_(True)).order_by(Business.id)).all()

def allowed_services():
    user = current_user()
    if not user:
        return []
    # Assignments can never grant access outside the membership's own business.
    return db.session.scalars(select(Service).join(Branch).join(Membership, Membership.business_id==Branch.business_id).outerjoin(ServiceAssignment, (ServiceAssignment.membership_id==Membership.id) & (ServiceAssignment.service_id==Service.id)).where(Membership.staff_id==user.id, Membership.is_active.is_(True), or_(Membership.role=='owner',ServiceAssignment.id.is_not(None))).distinct().order_by(Service.id)).all()

def require_service(service):
    user = current_user()
    if not user:
        abort(401)
    membership = Membership.query.filter_by(staff_id=user.id,business_id=service.branch.business_id,is_active=True).first()
    if not membership or (membership.role != 'owner' and not ServiceAssignment.query.filter_by(membership_id=membership.id,service_id=service.id).first()):
        abort(404, 'Queue unavailable or access denied.')
    return membership

def readable_services():
    """Active business membership permits reception reads, never queue actions."""
    user = current_user()
    if not user:
        abort(401)
    return db.session.scalars(select(Service).join(Branch).join(Business).join(
        Membership, Membership.business_id == Business.id).where(
        Membership.staff_id == user.id, Membership.is_active.is_(True),
        Business.is_active.is_(True), Branch.is_active.is_(True),
        Service.is_active.is_(True)).distinct().order_by(Service.id)).all()

def reception_service(service_id):
    service = next((s for s in readable_services() if s.id == service_id), None)
    if service is None:
        abort(404, 'Queue unavailable or access denied.')
    return service
