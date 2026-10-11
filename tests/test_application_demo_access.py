"""Staging session-auth behavior over actual isolated PostgreSQL/TLS."""
import secrets
import uuid
import pytest
from sqlalchemy.engine import make_url
from app import create_app
from models import db,Staff,Membership,Ticket
from staging import validate_configuration
from test_postgres import pg_app

ORIGIN='https://queueless-staging.onrender.com'

@pytest.fixture
def session_app(pg_app,monkeypatch):
    monkeypatch.setenv('SECRET_KEY',secrets.token_hex(32))
    with pg_app.app_context():
        owner=Staff(username='owner_auth');owner.set_password('test-only-owner-password')
        reception=Staff(username='reception_auth');reception.set_password('test-only-reception-password')
        db.session.add_all([owner,reception]);db.session.flush()
        db.session.add_all([Membership(business_id=1,staff_id=owner.id,role='owner'),Membership(business_id=1,staff_id=reception.id,role='staff')]);db.session.commit()
    app=create_app({**pg_app.config,'APP_STAGE':'staging','PRODUCTION':True,'DEBUG':False,
        'SECRET_KEY':secrets.token_hex(32),'DEMO_MODE':True,'STAGING_AUTH_MODE':'application',
        'OWNER_REGISTRATION_ENABLED':False,'DEMO_ACCESS_USER':'','DEMO_ACCESS_PASSWORD':'',
        'PUBLIC_BASE_URL':ORIGIN,'TRUSTED_HOSTS':['queueless-staging.onrender.com'],
        'STAGING_DATABASE_NAME':make_url(pg_app.config['SQLALCHEMY_DATABASE_URI']).database})
    yield app
    with app.app_context():db.session.remove();db.engine.dispose()

def get(c,path):
    r=c.get(path,base_url=ORIGIN);assert 'WWW-Authenticate' not in r.headers;return r

def post(c,path,**fields):
    fields['csrf_token']=get(c,'/api/v1/session').json['csrf_token']
    r=c.post(path,base_url=ORIGIN,data=fields);assert 'WWW-Authenticate' not in r.headers;return r

def test_anonymous_qr_issuance_display_and_ticket_privacy(session_app):
    c=session_app.test_client()
    bootstrap=get(c,'/api/v1/session');assert bootstrap.status_code==200
    assert bootstrap.json['user'] is None and bootstrap.json['demo_mode']
    assert not bootstrap.json['gateway_required'] and not bootstrap.json['owner_registration_enabled']
    assert all(flag in bootstrap.headers['Set-Cookie'] for flag in ('Secure','HttpOnly','SameSite=Lax'))
    assert get(c,'/api/v1/businesses/demo').status_code==200
    key=str(uuid.uuid4());a=post(c,'/api/v1/services/1/tickets',request_key=key)
    assert a.status_code==201 and a.json['display_number']=='G001'
    b=post(c,'/api/v1/services/1/tickets',request_key=key);assert b.json['token']==a.json['token']
    display=get(c,'/api/v1/display/demo');assert display.status_code==200
    assert a.json['token'] not in display.text and '/ticket/' not in display.text
    assert get(c,'/api/v1/tickets/'+a.json['token']).status_code==200
    outsider=session_app.test_client()
    assert get(outsider,'/api/v1/my-tickets').json==[]
    assert post(outsider,'/api/v1/tickets/'+a.json['token']+'/cancel').status_code==403
    with session_app.app_context():assert Ticket.query.count()==1

@pytest.mark.parametrize('path',['/api/v1/staff/queues','/api/v1/reception/queues','/api/v1/staff/services/1/qr.png','/api/v1/owner/businesses','/api/v1/owner/businesses/1/history','/api/v1/owner/businesses/1/stats'])
def test_anonymous_privileged_reads_are_denied_without_basic_challenge(session_app,path):
    assert get(session_app.test_client(),path).status_code==401

@pytest.mark.parametrize('path',['/api/v1/staff/services/1/call','/api/v1/staff/tickets/1/complete','/api/v1/owner/businesses'])
def test_anonymous_privileged_mutations_are_denied_with_valid_csrf(session_app,path):
    assert post(session_app.test_client(),path).status_code==401

def test_csrf_and_queue_login_rate_limits_remain(session_app):
    c=session_app.test_client();get(c,'/api/v1/session')
    assert c.post('/api/v1/services/1/tickets',base_url=ORIGIN,data={'request_key':str(uuid.uuid4())}).status_code==400
    # The missing-CSRF attempt already consumed one queue slot; it cannot evade limiting.
    session_app.config['RATE_LIMIT_QUEUE']=2
    assert [post(c,'/api/v1/services/1/tickets',request_key=str(uuid.uuid4())).status_code for _ in range(3)]==[201,429,429]
    session_app.config['RATE_LIMIT_AUTH']=2
    assert [post(c,'/api/v1/auth/login',username='tester',password='wrong').status_code for _ in range(3)]==[401,401,429]

def test_roles_use_sessions_and_reception_cannot_act_as_doctor_or_owner(session_app):
    rec=session_app.test_client()
    assert post(rec,'/api/v1/auth/login',username='reception_auth',password='test-only-reception-password').status_code==200
    assert get(rec,'/api/v1/staff/queues').json==[]
    assert len(get(rec,'/api/v1/reception/queues').json)==2
    assert get(rec,'/api/v1/staff/services/1/qr.png?download=1').mimetype=='image/png'
    assert post(rec,'/api/v1/staff/services/1/call').status_code==404
    assert get(rec,'/api/v1/owner/businesses/1').status_code==404
    patient=session_app.test_client();issued=post(patient,'/api/v1/services/1/tickets',request_key=str(uuid.uuid4())).json
    doctor=session_app.test_client();assert post(doctor,'/api/v1/auth/login',username='tester',password='test-password-123').status_code==200
    assert post(doctor,'/api/v1/staff/services/1/call').status_code==200
    called=get(doctor,'/api/v1/staff/queues').json[0]['called']
    assert called['number']==issued['display_number']
    assert post(doctor,f'/api/v1/staff/tickets/{called["id"]}/complete').status_code==200
    assert get(doctor,'/api/v1/owner/businesses/1').status_code==404
    owner=session_app.test_client();assert post(owner,'/api/v1/auth/login',username='owner_auth',password='test-only-owner-password').status_code==200
    assert get(owner,'/api/v1/owner/businesses/1/stats').json['completed_today']==1
    assert get(owner,'/api/v1/owner/businesses/1/history?date_basis=finished&status=COMPLETED').json['total']==1

def test_registration_disabled_in_api_and_legacy_ui_without_creating_accounts(session_app):
    c=session_app.test_client()
    with session_app.app_context():before=Staff.query.count()
    assert get(c,'/owner/register').status_code==403
    assert post(c,'/api/v1/auth/register',username='unauthorized',password='test-only-new-password',confirm_password='test-only-new-password').status_code==403
    assert 'Create an account' not in get(c,'/owner/login').text
    with session_app.app_context():assert Staff.query.count()==before

def test_application_mode_does_not_bypass_nonstaging_demo_gateway(application):
    with pytest.raises(RuntimeError,match='isolated staging'):
        create_app({**application.config,'DEMO_MODE':True,'STAGING_AUTH_MODE':'application','APP_STAGE':''})

def test_staging_rejects_unrestricted_registration_and_unknown_mode():
    from test_staging_security import configuration
    for field,value in [('OWNER_REGISTRATION_ENABLED',True),('STAGING_AUTH_MODE','unknown')]:
        config=configuration();config[field]=value
        with pytest.raises(RuntimeError):validate_configuration(config)
