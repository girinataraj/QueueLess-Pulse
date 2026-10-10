from datetime import datetime, timedelta
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from models import db, Ticket, TicketEvent, Service
from conftest import post, join, login, csrf

def test_pages_and_health(client):
    for path in ('/', '/staff/login', '/display', '/health', '/sw.js', '/static/icon-192.png', '/static/icon-512.png'):
        assert client.get(path).status_code == 200
    assert client.get('/ticket/missing').status_code == 404

def test_issue_duplicate_and_independent_queues(client, application):
    key = str(uuid.uuid4())
    first = join(client, key=key)
    assert first.status_code == 303
    assert join(client, key=key).location == first.location
    join(client)
    join(client, 2)
    with application.app_context():
        assert [(t.service_id,t.daily_number) for t in Ticket.query.order_by(Ticket.id)] == [(1,1),(1,2),(2,1)]
        assert TicketEvent.query.count() == 3
        assert len({t.token for t in Ticket.query}) == 3

@pytest.mark.parametrize('path', ['/service/1/join','/staff/login','/staff/logout','/staff/call/1','/staff/complete/1','/staff/skip/1','/ticket/none/cancel'])
def test_csrf_rejects(client, path):
    assert client.post(path).status_code == 400

def test_login_logout_and_authorization(client, application):
    assert client.get('/staff/dashboard').status_code == 401
    assert post(client, '/staff/call/1').status_code == 401
    assert post(client, '/staff/login', username='tester', password='wrong').status_code == 401
    assert login(client).status_code == 303
    assert client.get('/staff/dashboard').status_code == 200
    assert client.get('/staff/logout').status_code == 405
    assert post(client, '/staff/logout').status_code == 303
    assert client.get('/staff/dashboard').status_code == 401
    with client.session_transaction() as session:
        session['staff_id'] = 999
    assert client.get('/staff/dashboard').status_code == 401

def test_fifo_eta_transitions_audit(client, application):
    first, second = join(client), join(client)
    login(client)
    assert post(client,'/staff/complete/1').status_code == 409
    assert post(client,'/staff/call/1').status_code == 303
    assert post(client,'/staff/call/1').status_code == 409
    state = client.get(second.location + '/status').json
    assert state['people_ahead'] == 1 and state['estimated_time'] == 5
    assert client.get('/api/display_data').json[0]['currently_called'] == 'G001'
    assert post(client,'/staff/complete/1').status_code == 303
    assert post(client,'/staff/complete/1').status_code == 303
    assert post(client,'/staff/skip/1').status_code == 409
    assert client.get(first.location + '/status').json['estimated_time'] == 0
    assert post(client,'/staff/call/1').status_code == 303
    assert post(client,'/staff/skip/2').status_code == 303
    assert post(client,'/staff/call/1').status_code == 303
    with application.app_context():
        assert [e.event_type for e in TicketEvent.query.filter_by(ticket_id=1).order_by(TicketEvent.id)] == ['CREATED','CALLED','COMPLETED']
        assert db.session.get(Ticket,2).status == 'SKIPPED'

def test_cancel_ownership_and_repetition(client, application):
    ticket = join(client)
    stranger = application.test_client()
    assert post(stranger,ticket.location + '/cancel').status_code == 403
    assert post(client,ticket.location + '/cancel').status_code == 303
    assert post(client,ticket.location + '/cancel').status_code == 303
    login(client)
    post(client,'/staff/call/1')
    with application.app_context():
        assert Ticket.query.first().status == 'CANCELLED'
        assert TicketEvent.query.count() == 2

def test_daily_reset_and_historical_fifo(client, application):
    first = join(client)
    with application.app_context():
        ticket = Ticket.query.first()
        ticket.business_date -= timedelta(days=1)
        service = db.session.get(Service,1)
        service.seq_date = ticket.business_date
        db.session.commit()
    second = join(client)
    login(client)
    post(client,'/staff/call/1')
    with application.app_context():
        tickets = Ticket.query.order_by(Ticket.id).all()
        assert [t.daily_number for t in tickets] == [1,1]
        assert tickets[0].status == 'CALLED'
    assert client.get(second.location + '/status').json['people_ahead'] == 1

def test_invalid_input_and_inactive(client, application):
    assert post(client,'/service/1/join',request_key='invalid').status_code == 400
    assert join(client,999).status_code == 404
    with application.app_context():
        db.session.get(Service,1).is_active = False
        db.session.commit()
    assert join(client).status_code == 409

def test_no_private_caching(client):
    ticket = join(client)
    for path in ('/', ticket.location, ticket.location+'/status','/staff/login','/api/display_data'):
        assert client.get(path).headers['Cache-Control'] == 'no-store'
    assert client.get(ticket.location).headers['Referrer-Policy'] == 'no-referrer'

def test_db_constraints(client, application):
    join(client)
    join(client)
    with application.app_context():
        tickets = Ticket.query.order_by(Ticket.id).all()
        tickets[1].daily_number = 1
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        for t in Ticket.query:
            t.status = 'CALLED'
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
