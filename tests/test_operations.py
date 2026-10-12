from datetime import datetime, timedelta, timezone
import json, uuid
import pytest
from sqlalchemy import text
from models import db, Staff, Membership, ReceptionGrant, DoctorDuty, OperationReceipt, Ticket, TicketEvent, AdminEvent, Service
from conftest import join, login, post
from test_api import api_post, contract
from test_postgres import pg_app, parallel

def op(client, path, **values):
    values.setdefault('request_key',str(uuid.uuid4()))
    return api_post(client,path,**values)

def users(app):
    with app.app_context():
        for name,role in [('operations_owner','owner'),('operations_reception','staff')]:
            user=Staff(username=name);user.set_password('isolated-test-password-123');db.session.add(user);db.session.flush()
            db.session.add(Membership(business_id=1,staff_id=user.id,role=role))
        db.session.commit()

def signin(app,name):
    c=app.test_client();api_post(c,'/auth/login',username=name,password='isolated-test-password-123');return c

def grant(owner,app,enabled=True,marker=True):
    with app.app_context():
        mid=Membership.query.join(Staff).filter(Staff.username=='operations_reception').one().id
    values={'is_active':'on'}
    if marker:values['walkin_permission_set']='on'
    if enabled:values['can_issue_walkins']='on'
    return api_post(owner,f'/owner/businesses/1/staff/{mid}/permissions',**values)

@pytest.mark.parametrize('fixture',['application','pg_app'])
def test_duty_transitions_preserve_active_ticket(request,fixture):
    app=request.getfixturevalue(fixture);c=app.test_client();login(c)
    assert op(c,'/staff/services/1/duty',action='break').status_code==409
    contract(op(c,'/staff/services/1/duty',action='start'),'Duty')
    assert op(c,'/staff/services/1/duty',action='start').status_code==409
    join(c);post(c,'/staff/call/1')
    for action in ('break','end'):assert op(c,'/staff/services/1/duty',action=action).status_code==409
    with app.app_context():assert Ticket.query.one().status=='CALLED'
    post(c,'/staff/complete/1')
    key=str(uuid.uuid4());assert op(c,'/staff/services/1/duty',action='break',request_key=key).json['state']=='ON_BREAK'
    assert op(c,'/staff/services/1/duty',action='break',request_key=key).status_code==200
    join(c);assert post(c,'/staff/call/1').status_code==409
    assert op(c,'/staff/services/1/duty',action='resume').json['state']=='AVAILABLE'
    assert post(c,'/staff/call/1').status_code==303
    post(c,'/staff/skip/2')
    assert op(c,'/staff/services/1/duty',action='end').json['state']=='OFF_DUTY'
    assert post(c,'/staff/call/1').status_code==409
    assert op(c,'/staff/services/1/duty',action='start').json['state']=='AVAILABLE'
    with app.app_context():
        assert Ticket.query.count()==2
        assert AdminEvent.query.filter_by(action='DOCTOR_DUTY_break'.upper()).count()==1

@pytest.mark.parametrize('fixture',['application','pg_app'])
def test_recall_is_same_token_audited_and_idempotent(request,fixture):
    app=request.getfixturevalue(fixture);c=app.test_client();join(c);login(c);post(c,'/staff/call/1')
    before=c.get('/api/v1/display/demo').json[0]['announcement_id']
    key=str(uuid.uuid4())
    for _ in range(2):contract(op(c,'/staff/tickets/1/recall',request_key=key),'Action')
    public=c.get('/api/v1/display/demo').json[0]
    assert public['currently_called']=='G001' and public['announcement_id']!=before
    with app.app_context():
        t=Ticket.query.one();assert t.status=='CALLED' and t.daily_number==1
        assert TicketEvent.query.filter_by(event_type='RECALLED').count()==1
        assert t.token not in json.dumps(public)
    post(c,'/staff/complete/1')
    assert op(c,'/staff/tickets/1/recall').status_code==409
    assert op(c,'/staff/tickets/1/recall',request_key=key).status_code==200

def test_reception_walkin_requires_explicit_grant_and_is_private(application):
    users(application);owner=signin(application,'operations_owner');reception=signin(application,'operations_reception')
    assert op(reception,'/reception/services/1/walkins').status_code==403
    assert op(owner,'/reception/services/1/walkins').status_code==403
    assert grant(owner,application).status_code==200
    key=str(uuid.uuid4());first=contract(op(reception,'/reception/services/1/walkins',request_key=key),'Walkin',201)
    replay=contract(op(reception,'/reception/services/1/walkins',request_key=key),'Walkin',201)
    assert first['number']=='G001' and first['created'] and not replay['created']
    assert not any(name in first for name in ('token','owner_id','request_key','id','recovery_link'))
    assert reception.get('/api/v1/my-tickets').json==[]
    assert api_post(reception,'/staff/services/1/call').status_code==404
    assert reception.get('/api/v1/owner/businesses/1').status_code==404
    with application.app_context():
        t=Ticket.query.one();assert TicketEvent.query.one().staff_id is not None
        assert AdminEvent.query.filter_by(action='RECEPTION_WALKIN').count()==1
        private=t.token;day=str(t.business_date)
    assert api_post(reception,'/tickets/'+private+'/cancel').status_code==403
    located=contract(reception.get(f'/api/v1/reception/services/1/tokens?number=G001&date={day}'),'LocatedToken')
    assert located['number']=='G001' and private not in json.dumps(located)
    assert grant(owner,application,marker=False).status_code==200
    assert reception.get('/api/v1/reception/queues').json[0]['can_issue_walkins']
    assert grant(owner,application,enabled=False).status_code==200
    assert op(reception,'/reception/services/1/walkins').status_code==403

def test_new_mutations_keep_csrf_assignment_and_tenant_guards(application):
    users(application);r=signin(application,'operations_reception');anon=application.test_client()
    for path in ('/staff/services/1/duty','/staff/tickets/1/recall','/reception/services/1/walkins'):
        assert r.post('/api/v1'+path,data={'action':'start','request_key':str(uuid.uuid4())}).status_code==400
    assert op(anon,'/staff/services/1/duty',action='start').status_code==401
    assert op(r,'/staff/services/1/duty',action='start').status_code==404
    from test_universal import build_business
    other=build_business(application,'operations_other','other-operations')
    sid=other['service']
    assert r.get(f'/api/v1/reception/services/{sid}/tokens?number=G001&date=2026-10-12').status_code==404
    assert op(r,f'/reception/services/{sid}/walkins').status_code==404
    assert op(r,f'/staff/services/{sid}/duty',action='start').status_code==404
    assert r.get('/api/v1/owner/businesses/2/operations').status_code==404

def test_walkin_rate_limit_and_invalid_request(application):
    users(application);o=signin(application,'operations_owner');r=signin(application,'operations_reception');grant(o,application)
    application.config['RATE_LIMIT_QUEUE']=1
    assert op(r,'/reception/services/1/walkins').status_code==201
    assert op(r,'/reception/services/1/walkins').status_code==429
    with application.app_context():assert Ticket.query.count()==1

def test_receipt_cannot_be_reused_for_other_operation(client):
    login(client);key=str(uuid.uuid4())
    assert op(client,'/staff/services/1/duty',action='start',request_key=key).status_code==200
    assert op(client,'/staff/services/1/duty',action='break',request_key=key).status_code==409
    assert op(client,'/staff/services/2/duty',action='start',request_key=key).status_code==409

def test_today_metrics_include_review_of_previous_day_without_private_links(application):
    users(application);o=signin(application,'operations_owner');c=application.test_client();join(c);login(c);post(c,'/staff/call/1');post(c,'/staff/complete/1')
    from universal import business_day
    with application.app_context():
        b=Service.query.first().branch.business;day,start,end=business_day(b);t=Ticket.query.one()
        t.business_date=day-timedelta(days=1);t.created_at=start-timedelta(minutes=10);t.called_at=start-timedelta(minutes=5);t.finished_at=start+timedelta(minutes=2)
        for e in t.events:e.timestamp=t.finished_at if e.event_type=='COMPLETED' else t.created_at
        db.session.commit()
    result=contract(o.get('/api/v1/owner/businesses/1/operations'),'OperationsMetrics')
    assert result['issued_today']==0 and result['average_duration_today']==7 and result['duration_samples']==1
    assert sum(h['completed'] for h in result['hourly'])==1
    assert result['workload'][0]['reviewed']==1
    export=api_post(o,'/owner/businesses/1/export',date=str(day))
    assert export.status_code==200 and 'G001' in export.text and 'owner_id' not in export.text
    with application.app_context():
        assert Ticket.query.one().token not in export.text
        assert AdminEvent.query.filter_by(action='REPORT_EXPORTED').count()==1

@pytest.mark.postgres
def test_additive_upgrade_preserves_tickets_and_does_not_grant_privileges(pg_app):
    c=pg_app.test_client();join(c)
    with pg_app.app_context():
        original=[(t.id,t.token,t.status,t.request_key) for t in Ticket.query]
        db.session.remove()
        with db.engine.begin() as con:
            for name in ('operation_receipts','doctor_duties','reception_grants'):con.execute(text(f'DROP TABLE {name}'))
    runner=pg_app.test_cli_runner()
    for _ in range(2):
        r=runner.invoke(args=['upgrade-db','--apply']);assert r.exit_code==0,r.output
    with pg_app.app_context():
        assert [(t.id,t.token,t.status,t.request_key) for t in Ticket.query]==original
        assert ReceptionGrant.query.count()==0 and DoctorDuty.query.count()==0

@pytest.mark.postgres
def test_concurrent_recall_duplicate_writes_one_event(pg_app):
    c=pg_app.test_client();join(c);login(c);post(c,'/staff/call/1');key=str(uuid.uuid4())
    results=parallel(pg_app,[lambda c:op(c,'/staff/tickets/1/recall',request_key=key) for _ in range(4)],staff=True)
    assert [r.status_code for r in results]==[200]*4
    with pg_app.app_context():
        assert Ticket.query.count()==1 and TicketEvent.query.filter_by(event_type='RECALLED').count()==1

@pytest.mark.postgres
def test_concurrent_call_and_break_have_serial_outcomes(pg_app):
    c=pg_app.test_client();join(c);login(c);op(c,'/staff/services/1/duty',action='start')
    results=parallel(pg_app,[lambda c:post(c,'/staff/call/1'),lambda c:op(c,'/staff/services/1/duty',action='break')],staff=True)
    assert sorted(r.status_code for r in results) in ([200,409],[303,409])
    with pg_app.app_context():
        duty=DoctorDuty.query.one();t=Ticket.query.one()
        assert (duty.state,t.status) in [('ON_BREAK','WAITING'),('AVAILABLE','CALLED')]

@pytest.mark.postgres
def test_patient_and_walkin_share_one_concurrent_numbering_engine(pg_app):
    users(pg_app)
    with pg_app.app_context():
        mid=Membership.query.join(Staff).filter(Staff.username=='tester').one().id
        db.session.add(ReceptionGrant(membership_id=mid));db.session.commit()
    calls=[lambda c:join(c),lambda c:op(c,'/reception/services/1/walkins')]*4
    results=parallel(pg_app,calls,staff=True)
    assert sorted(r.status_code for r in results)==[201]*4+[303]*4
    with pg_app.app_context():
        assert sorted(t.daily_number for t in Ticket.query)==list(range(1,9))
        assert TicketEvent.query.filter_by(event_type='CREATED').count()==8
        assert Ticket.query.filter_by(status='WAITING').count()==8

def test_walkin_midnight_rollover_retains_unresolved_previous_day(application,monkeypatch):
    import queue_core
    from datetime import datetime
    users(application);o=signin(application,'operations_owner');r=signin(application,'operations_reception');grant(o,application)
    class Sunday(datetime):
        @classmethod
        def now(cls,tz=None):return datetime(2026,10,11,18,29,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(queue_core,'datetime',Sunday)
    first=op(r,'/reception/services/1/walkins').json
    c=application.test_client();login(c);post(c,'/staff/call/1')
    class Monday(datetime):
        @classmethod
        def now(cls,tz=None):return datetime(2026,10,11,18,31,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(queue_core,'datetime',Monday)
    second=op(r,'/reception/services/1/walkins').json
    assert first['number']==second['number']=='G001'
    assert first['business_date']=='2026-10-11' and second['business_date']=='2026-10-12'
    with application.app_context():
        assert Ticket.query.filter_by(status='CALLED').one().business_date.isoformat()=='2026-10-11'
        assert Ticket.query.filter_by(status='WAITING').one().business_date.isoformat()=='2026-10-12'
