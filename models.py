from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import uuid

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class RateLimitBucket(db.Model):
    """Short-lived HMAC identifiers; shared by all production workers."""
    __tablename__ = 'rate_limit_buckets'
    key_hash = db.Column(db.String(64), primary_key=True)
    window_start = db.Column(db.BigInteger, primary_key=True, index=True)
    hits = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.CheckConstraint('hits > 0', name='ck_rate_limit_hits'),)

class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Business(db.Model):
    __tablename__ = 'businesses'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(40), nullable=False, default='Service center')
    description = db.Column(db.String(1000), nullable=False, default='')
    timezone = db.Column(db.String(64), nullable=False, default='Asia/Kolkata')
    is_active = db.Column(db.Boolean, nullable=False, default=True)

class Branch(db.Model):
    __tablename__ = 'branches'
    __table_args__ = (db.UniqueConstraint('business_id','name',name='uq_branch_name'),)
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    address = db.Column(db.String(300), nullable=False, default='')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    business = db.relationship('Business', backref='branches')

class Membership(db.Model):
    __tablename__ = 'memberships'
    __table_args__ = (db.UniqueConstraint('business_id','staff_id',name='uq_membership'), db.CheckConstraint("role IN ('owner','staff')",name='ck_membership_role'))
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False, index=True)
    role = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    business = db.relationship('Business')
    staff = db.relationship('Staff')

class Service(db.Model):
    __tablename__ = 'services'
    __table_args__ = (db.UniqueConstraint('branch_id','name',name='uq_service_name'), db.UniqueConstraint('branch_id','prefix',name='uq_service_prefix'), db.CheckConstraint('average_minutes BETWEEN 1 AND 120',name='ck_service_duration'))
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256))
    prefix = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    seq_date = db.Column(db.Date)
    last_number = db.Column(db.Integer, nullable=False, default=0)
    average_minutes = db.Column(db.Integer, nullable=False, default=5)
    counter_label = db.Column(db.String(40), nullable=False, default='')
    branch = db.relationship('Branch', backref='services')

class ServiceAssignment(db.Model):
    __tablename__ = 'service_assignments'
    __table_args__ = (db.UniqueConstraint('membership_id','service_id',name='uq_service_assignment'),)
    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(db.Integer, db.ForeignKey('memberships.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    membership = db.relationship('Membership')
    service = db.relationship('Service')

class StaffInvite(db.Model):
    __tablename__ = 'staff_invites'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    created_by = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)

class AdminEvent(db.Model):
    __tablename__ = 'admin_events'
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False, index=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    action = db.Column(db.String(64), nullable=False)
    details = db.Column(db.String(300), nullable=False, default='')
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

class Ticket(db.Model):
    __tablename__ = 'tickets'
    __table_args__ = (
        db.UniqueConstraint('service_id', 'business_date', 'daily_number', name='uq_ticket_daily'),
        db.CheckConstraint('daily_number > 0', name='ck_ticket_number'),
        db.CheckConstraint("status IN ('WAITING','CALLED','COMPLETED','SKIPPED','CANCELLED')", name='ck_ticket_status'),
        db.Index('uq_one_called_service', 'service_id', unique=True, postgresql_where=db.text("status = 'CALLED'"), sqlite_where=db.text("status = 'CALLED'")),
        db.Index('ix_ticket_queue', 'service_id', 'status', 'id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    daily_number = db.Column(db.Integer, nullable=False)
    business_date = db.Column(db.Date, nullable=False)
    request_key = db.Column(db.String(36), nullable=False, unique=True)
    owner_id = db.Column(db.String(36), nullable=False)
    display_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='WAITING', nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    called_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    service = db.relationship('Service', backref=db.backref('tickets', lazy=True))

class TicketEvent(db.Model):
    __tablename__ = 'ticket_events'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    ticket = db.relationship('Ticket', backref=db.backref('events', lazy=True, order_by='TicketEvent.timestamp'))
    staff = db.relationship('Staff', backref=db.backref('actions', lazy=True))


# Enforce assignment scope on PostgreSQL, including databases initialized from metadata.
from sqlalchemy import DDL, event
_assignment_guard = ( __import__('pathlib').Path(__file__).parent / 'migrations/003_assignment_guard.sql').read_text(encoding='utf-8')
event.listen(ServiceAssignment.__table__, 'after_create', DDL(_assignment_guard).execute_if(dialect='postgresql'))
