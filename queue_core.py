"""The shared transactional issuance engine for patients and authorized walk-ins."""
from datetime import datetime
import uuid
from zoneinfo import ZoneInfo
from flask import abort
from sqlalchemy import select
from models import db, Service, Ticket, TicketEvent

def lock_service(service_id):
    service = db.session.scalar(select(Service).where(Service.id == service_id).with_for_update().execution_options(populate_existing=True))
    if service is None: abort(404)
    return service

def issue_ticket(service_id, request_key, owner_id, staff_id=None, clock=None):
    try: key = str(uuid.UUID(request_key))
    except (ValueError, TypeError, AttributeError): abort(400, 'Invalid submission key')
    service = lock_service(service_id)
    db.session.refresh(service.branch)
    db.session.refresh(service.branch.business)
    if not service.is_active or not service.branch.is_active or not service.branch.business.is_active:
        abort(409, 'Service unavailable')
    existing = Ticket.query.filter_by(request_key=key).first()
    if existing:
        if existing.owner_id != owner_id or existing.service_id != service_id:
            abort(409, 'Submission key already used')
        return existing, False
    day = (clock or datetime).now(ZoneInfo(service.branch.business.timezone)).date()
    if service.seq_date != day: service.seq_date, service.last_number = day, 0
    service.last_number += 1
    ticket = Ticket(service_id=service.id, business_date=day, daily_number=service.last_number,
                    display_number=f'{service.prefix}{service.last_number:03d}', request_key=key, owner_id=owner_id)
    db.session.add(ticket); db.session.flush()
    db.session.add(TicketEvent(ticket_id=ticket.id, event_type='CREATED', staff_id=staff_id))
    return ticket, True
