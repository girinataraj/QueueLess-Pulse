import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from jsonschema import Draft202012Validator
from models import db, Ticket, TicketEvent, Service
from test_universal import build_business
from test_postgres import pg_app

SCHEMA = json.loads((Path(__file__).parents[1] / 'contracts/api.schema.json').read_text())

def contract(response, name, status=200):
    assert response.status_code == status, response.text
    assert response.content_type == 'application/json'
    assert response.headers['Cache-Control'] == 'no-store'
    data = response.get_json()
    Draft202012Validator({'$ref': '#/$defs/' + name, '$defs': SCHEMA['$defs']}).validate(data)
    return data

def api_post(client, path, **data):
    data['csrf_token'] = client.get('/api/v1/session').get_json()['csrf_token']
    return client.post('/api/v1' + path, data=data)

def test_session_auth_rotation_and_json_errors(client):
    old = contract(client.get('/api/v1/session'), 'Session')
    assert old['user'] is None
    contract(client.post('/api/v1/auth/login', data={'username':'tester','password':'test-password-123'}), 'ApiError', 400)
    contract(api_post(client, '/auth/login', username='tester', password='wrong'), 'ApiError', 401)
    new = contract(api_post(client, '/auth/login', username='tester', password='test-password-123'), 'Session')
    assert new['csrf_token'] != old['csrf_token'] and new['user']['username'] == 'tester'
    contract(client.post('/api/v1/auth/logout', data={'csrf_token':old['csrf_token']}), 'ApiError', 400)
    assert contract(api_post(client, '/auth/logout'), 'Session')['user'] is None
    contract(client.get('/api/v1/staff/queues'), 'ApiError', 401)
    contract(client.get('/api/v1/not-real'), 'ApiError', 404)
    contract(client.post('/api/v1/auth/login', json={'username':'tester'}, headers={'X-CSRF-Token':client.get('/api/v1/session').json['csrf_token']}), 'ApiError', 415)

def test_api_customer_staff_and_public_contracts(client, application):
    contract(client.get('/api/v1/businesses'), 'BusinessList')
    contract(client.get('/api/v1/businesses/demo'), 'PublicBusiness')
    key = str(uuid.uuid4())
    ticket = contract(api_post(client, '/services/1/tickets', request_key=key), 'Ticket', 201)
    assert contract(api_post(client, '/services/1/tickets', request_key=key), 'Ticket', 201)['token'] == ticket['token']
    outsider = application.test_client()
    assert not contract(outsider.get('/api/v1/tickets/'+ticket['token']), 'Ticket')['can_cancel']
    contract(api_post(outsider, '/tickets/'+ticket['token']+'/cancel'), 'ApiError', 403)
    contract(client.get('/api/v1/my-tickets'), 'TicketList')
    contract(api_post(client, '/auth/login', username='tester', password='test-password-123'), 'Session')
    queues = contract(client.get('/api/v1/staff/queues'), 'QueueList')
    tid = queues[0]['waiting'][0]['id']
    contract(api_post(client, '/staff/services/1/call'), 'Action')
    public = contract(client.get('/api/v1/display/demo'), 'DisplayList')
    assert public[0]['currently_called'] == 'G001'
    assert ticket['token'] not in json.dumps(public) and 'owner_id' not in json.dumps(public)
    contract(api_post(client, '/staff/tickets/'+str(tid)+'/complete'), 'Action')
    assert contract(client.get('/api/v1/tickets/'+ticket['token']), 'Ticket')['status'] == 'COMPLETED'
    with application.app_context():
        assert [e.event_type for e in TicketEvent.query.order_by(TicketEvent.id)] == ['CREATED','CALLED','COMPLETED']

def test_registration_management_invites_and_history(application):
    owner = application.test_client()
    contract(api_post(owner, '/auth/register', username='api_owner', password='secure-password-123', confirm_password='secure-password-123'), 'Session', 201)
    result = contract(api_post(owner, '/owner/businesses', name='API Clinic', slug='api-clinic', category='Clinic', timezone='Asia/Kolkata'), 'Action', 201)
    bid = int(result['resource_path'].rsplit('/',1)[-1]);base='/owner/businesses/'+str(bid)
    contract(api_post(owner, base+'/branches', name='Central', address='Street'), 'Action', 201)
    bundle = contract(owner.get('/api/v1'+base), 'OwnerBusiness');branch=bundle['branches'][0]['id']
    contract(api_post(owner, base+'/services', branch_id=branch, name='Consult', prefix='C', average_minutes=8, counter_label='Desk 1', is_active='on'), 'Action', 201)
    contract(api_post(owner, base+'/staff', username='api_staff',password='staff-password-123'), 'Action', 201)
    bundle = contract(owner.get('/api/v1'+base), 'OwnerBusiness');member=next(m for m in bundle['members'] if m['role']=='staff')
    contract(api_post(owner, base+'/staff/'+str(member['id'])+'/permissions', service_ids=str(bundle['services'][0]['id']), is_active='on'), 'Action')
    contract(owner.get('/api/v1/owner/businesses'), 'BusinessList')
    contract(owner.get('/api/v1'+base+'/stats'), 'Metrics')
    contract(owner.get('/api/v1'+base+'/history'), 'History')
    invite = contract(api_post(owner, base+'/invitations'), 'InviteCreated', 201)
    token=invite['invite_url'].rsplit('/',1)[-1]
    assert '/app/invite/' in invite['invite_url']
    recipient=application.test_client()
    contract(recipient.get('/api/v1/invitations/'+token), 'Invitation')
    contract(api_post(recipient, '/invitations/'+token,username='api_invited',password='invited-password-123',confirm_password='invited-password-123'), 'Session')
    contract(recipient.get('/api/v1/invitations/'+token), 'ApiError', 410)
    image=owner.get(f'/owner/business/{bid}/qr.png?ui=react&service_id={bundle["services"][0]["id"]}')
    assert image.status_code==200
    import zxingcpp
    from PIL import Image
    import io
    assert '/app/b/api-clinic/service/' in zxingcpp.read_barcode(Image.open(io.BytesIO(image.data))).text

@pytest.mark.parametrize('suffix',['','/stats','/history'])
def test_api_foreign_owner_reads(application, suffix):
    a=build_business(application,'api_alpha','alpha');b=build_business(application,'api_beta','beta')
    contract(a['client'].get('/api/v1/owner/businesses/'+str(b['business'])+suffix), 'ApiError',404)

@pytest.mark.parametrize('action',['profile','branch','service','staff','invite','payload'])
def test_api_foreign_mutations(application,action):
    a=build_business(application,'api_alpha','alpha');b=build_business(application,'api_beta','beta')
    base='/owner/businesses/'+str(b['business'])
    paths={'profile':base,'branch':base+'/branches/'+str(b['branch']),'service':base+'/services/'+str(b['service']),'staff':base+'/staff','invite':base+'/invitations','payload':'/owner/businesses/'+str(a['business'])+'/services'}
    contract(api_post(a['client'],paths[action],name='Forbidden',branch_id=b['branch'],prefix='X',average_minutes=5), 'ApiError',404)
    with application.app_context(): assert db.session.get(Service,b['service']).name=='Consultation'

def test_api_validation_cancel_history_and_inactive(client,application):
    contract(api_post(client,'/services/1/tickets',request_key='bad'), 'ApiError',400)
    t=contract(api_post(client,'/services/1/tickets',request_key=str(uuid.uuid4())), 'Ticket',201)
    assert contract(api_post(client,'/tickets/'+t['token']+'/cancel'), 'Ticket')['status']=='CANCELLED'
    contract(api_post(client,'/tickets/'+t['token']+'/cancel'), 'Ticket')
    contract(client.get('/api/v1/display/demo?branch_id=9999'), 'ApiError',404)
    contract(client.get('/api/v1/display/demo?branch_id=no'), 'ApiError',400)
    with application.app_context():db.session.get(Service,1).is_active=False;db.session.commit()
    contract(api_post(client,'/services/1/tickets',request_key=str(uuid.uuid4())), 'ApiError',409)

@pytest.mark.postgres
def test_postgres_api_duplicate_serialization(pg_app):
    first=pg_app.test_client();first.get('/api/v1/session')
    with first.session_transaction() as s:saved=dict(s)
    clients=[pg_app.test_client() for _ in range(4)]
    for c in clients:
        with c.session_transaction() as s:s.update(saved)
    barrier=Barrier(4);key=str(uuid.uuid4())
    def issue(c):
        barrier.wait(timeout=10)
        return c.post('/api/v1/services/1/tickets',data={'csrf_token':saved['csrf_token'],'request_key':key})
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(issue,clients))
    assert len({contract(r,'Ticket',201)['token'] for r in results})==1
    with pg_app.app_context():assert Ticket.query.count()==1 and TicketEvent.query.count()==1
