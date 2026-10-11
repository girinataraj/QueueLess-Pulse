"""Reception read permissions and business-local review dates on SQLite/PostgreSQL."""
import io
from datetime import datetime, date, timezone
import uuid
import pytest
from PIL import Image
import zxingcpp
from models import db, Staff, Business, Membership, Ticket, TicketEvent
from test_api import api_post, contract
from test_universal import build_business
from test_postgres import pg_app
import universal
import app as app_module

@pytest.fixture(params=['application','pg_app'])
def store(request):
    return request.getfixturevalue(request.param)

def receptionist(application, business):
    with application.app_context():
        user=Staff(username='reception_test');user.set_password('reception-test-password-123')
        db.session.add(user);db.session.flush()
        db.session.add(Membership(business_id=business['business'],staff_id=user.id,role='staff'))
        db.session.commit()
    client=application.test_client()
    assert api_post(client,'/auth/login',username='reception_test',password='reception-test-password-123').status_code==200
    return client

@pytest.mark.postgres
def test_reception_reads_without_owner_or_doctor_privileges(store):
    a=build_business(store,'reception_owner','reception-clinic')
    b=build_business(store,'other_owner','other-clinic')
    c=receptionist(store,a)
    rows=contract(c.get('/api/v1/reception/queues'),'ReceptionList')
    assert [r['service_id'] for r in rows]==[a['service']]
    assert contract(c.get('/api/v1/staff/queues'),'QueueList')==[]
    for suffix in ('','/stats','/history'):
        assert c.get(f"/api/v1/owner/businesses/{a['business']}{suffix}").status_code==404
    assert api_post(c,f"/staff/services/{a['service']}/call").status_code==404
    assert api_post(c,f"/owner/businesses/{a['business']}",name='Unauthorized').status_code==404
    assert c.get(f"/api/v1/staff/services/{b['service']}/qr.png").status_code==404
    png=c.get(f"/api/v1/staff/services/{a['service']}/qr.png?download=1")
    assert png.status_code==200 and png.mimetype=='image/png'
    assert 'attachment' in png.headers['Content-Disposition']
    assert zxingcpp.read_barcode(Image.open(io.BytesIO(png.data))).text==rows[0]['patient_url']
    # A read-only membership must also be unable to finish another person's visit.
    t=api_post(a['client'],f"/services/{a['service']}/tickets",request_key=str(uuid.uuid4())).json
    assert api_post(a['client'],f"/staff/services/{a['service']}/call").status_code==200
    with store.app_context(): tid=Ticket.query.filter_by(token=t['token']).one().id
    for target in ('complete','skip'):
        assert api_post(c,f'/staff/tickets/{tid}/{target}').status_code==404
    with store.app_context():
        membership=Membership.query.join(Staff).filter(Staff.username=='reception_test').one()
        membership.is_active=False;db.session.commit()
    assert c.get(f"/api/v1/staff/services/{a['service']}/qr.png").status_code==404
    assert contract(c.get('/api/v1/reception/queues'),'ReceptionList')==[]
    assert store.test_client().get('/api/v1/reception/queues').status_code==401

def clock(monkeypatch, moment):
    class Frozen(datetime):
        @classmethod
        def now(cls,tz=None):
            return moment.astimezone(tz) if tz else moment.replace(tzinfo=None)
    monkeypatch.setattr(universal,'datetime',Frozen)
    monkeypatch.setattr(app_module,'datetime',Frozen)

@pytest.mark.postgres
def test_carried_over_ticket_review_counts_on_completion_day(store,monkeypatch):
    a=build_business(store,'review_owner','reviews')
    c=a['client'];sid=a['service']
    clock(monkeypatch,datetime(2026,10,11,18,29,tzinfo=timezone.utc)) # Sunday 23:59 IST
    t=api_post(c,f'/services/{sid}/tickets',request_key=str(uuid.uuid4())).json
    assert t['business_date']=='2026-10-11'
    assert api_post(c,f'/staff/services/{sid}/call').status_code==200
    second=api_post(c,f'/services/{sid}/tickets',request_key=str(uuid.uuid4())).json
    clock(monkeypatch,datetime(2026,10,11,18,31,tzinfo=timezone.utc)) # Monday 00:01 IST
    assert api_post(c,f'/staff/services/{sid}/call').status_code==409
    with store.app_context(): tid=Ticket.query.filter_by(token=t['token']).one().id
    assert api_post(c,f'/staff/tickets/{tid}/complete').status_code==200
    assert api_post(c,f'/staff/services/{sid}/call').status_code==200
    with store.app_context(): tid2=Ticket.query.filter_by(token=second['token']).one().id
    assert api_post(c,f'/staff/tickets/{tid2}/skip').status_code==200
    metrics=contract(c.get(f"/api/v1/owner/businesses/{a['business']}/stats"),'Metrics')
    assert (metrics['business_date'],metrics['completed_today'],metrics['skipped_today'])==('2026-10-12',1,1)
    rows=contract(c.get('/api/v1/reception/queues'),'ReceptionList')
    assert (rows[0]['completed_today'],rows[0]['skipped_today'])==(1,1)
    base=f"/api/v1/owner/businesses/{a['business']}/history"
    result=contract(c.get(base+'?date=2026-10-12&date_basis=finished&status=COMPLETED'),'History')
    assert result['total']==1 and result['items'][0]['date']=='2026-10-11'
    assert contract(c.get(base+'?date=2026-10-12&date_basis=issued'),'History')['total']==0
    assert contract(c.get(base+'?date=2026-10-11'),'History')['total']==2
    new=api_post(c,f'/services/{sid}/tickets',request_key=str(uuid.uuid4())).json
    assert new['display_number']==t['display_number'] and new['business_date']=='2026-10-12'
    with store.app_context():
        assert Ticket.query.count()==3
        assert [e.event_type for e in TicketEvent.query.filter_by(ticket_id=tid).order_by(TicketEvent.id)]==['CREATED','CALLED','COMPLETED']

@pytest.mark.parametrize('query',['date=invalid','date=2026-02-30','date=2026-1-1','date=2026-10-12T00:00:00','date_basis=unknown'])
def test_history_invalid_dates_are_client_errors(application,query):
    a=build_business(application,'date_owner','dates')
    contract(a['client'].get(f"/api/v1/owner/businesses/{a['business']}/history?{query}"),'ApiError',400)

@pytest.mark.parametrize('day,hours',[(date(2026,3,8),23),(date(2026,11,1),25)])
def test_business_day_uses_calendar_boundaries_across_dst(day,hours):
    business=Business(timezone='America/New_York')
    actual,start,end=universal.business_day(business,day)
    assert actual==day and (end-start).total_seconds()==hours*3600
