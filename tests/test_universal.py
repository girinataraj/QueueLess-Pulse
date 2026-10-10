import re
from datetime import datetime,timezone,timedelta
import pytest
from sqlalchemy import select, text
from models import db,Staff,Business,Branch,Membership,Service,ServiceAssignment,StaffInvite,Ticket,TicketEvent,AdminEvent
from conftest import post,join,login
from test_postgres import pg_app


def build_business(app,username,slug):
    client=app.test_client()
    response=post(client,'/owner/register',username=username,password='secure-password-123',confirm_password='secure-password-123',email=f'{username}@example.com')
    assert response.status_code==303
    response=post(client,'/owner/business/create',name=slug.title(),slug=slug,category='Clinic',timezone='Asia/Kolkata',description=f'{slug} private workspace')
    assert response.status_code==303
    with app.app_context():
        business=Business.query.filter_by(slug=slug).one()
        bid=business.id
        uid=Staff.query.filter_by(username=username).one().id
    assert post(client,f'/owner/business/{bid}/branches/create',name='Central',address='Main street').status_code==303
    with app.app_context():
        branch=Branch.query.filter_by(business_id=bid).one()
        branch_id=branch.id
    assert post(client,f'/owner/business/{bid}/services/create',branch_id=branch_id,name='Consultation',prefix='C',average_minutes=7,counter_label='Desk 1',description='Service',is_active='on').status_code==303
    with app.app_context():
        service=Service.query.filter_by(branch_id=branch_id).one()
        sid=service.id
    return {'client':client,'business':bid,'branch':branch_id,'service':sid,'user':uid,'slug':slug}

@pytest.fixture
def tenants(application):
    return build_business(application,'owner_alpha','alpha'),build_business(application,'owner_beta','beta')


def test_owner_registration_login_and_duplicates(client,application):
    assert client.get('/owner').status_code==401
    assert post(client,'/owner/register',username='owner',password='short',confirm_password='short').status_code==400
    assert post(client,'/owner/register',username='owner',password='long-password-123',confirm_password='different').status_code==400
    assert post(client,'/owner/register',username='owner',password='long-password-123',confirm_password='long-password-123').status_code==303
    assert client.get('/owner').status_code==200
    with application.app_context():
        user=Staff.query.filter_by(username='owner').one()
        assert user.check_password('long-password-123')
        assert user.password_hash!='long-password-123'
    post(client,'/staff/logout')
    assert post(client,'/owner/login',username='owner',password='wrong').status_code==401
    assert post(client,'/owner/login',username='OWNER',password='long-password-123').status_code==303
    stranger=application.test_client()
    assert post(stranger,'/owner/register',username='owner',password='long-password-123',confirm_password='long-password-123').status_code==409


def test_management_and_configuration(tenants,application):
    a,b=tenants
    client=a['client']; bid=a['business']; sid=a['service']; branch=a['branch']
    assert client.get(f'/owner/business/{bid}').status_code==200
    assert post(client,f'/owner/business/{bid}/edit',name='Alpha Clinic',description='Updated',category='Salon',timezone='Asia/Tokyo').status_code==303
    assert post(client,f'/owner/business/{bid}/branches/{branch}/edit',name='Tokyo',address='Japan',is_active='on').status_code==303
    assert post(client,f'/owner/business/{bid}/services/{sid}/edit',name='Haircut',prefix='H',average_minutes=12,counter_label='Chair 2',description='New',is_active='on').status_code==303
    customer=application.test_client()
    issued=join(customer,sid)
    assert 'H001' in customer.get(issued.location).text
    assert customer.get(issued.location+'/status').json['counter_label']=='Chair 2'
    assert customer.get('/my-tickets').text.count('H001')==1
    assert 'H001' not in application.test_client().get('/my-tickets').text
    assert post(client,f'/owner/business/{bid}/edit',name='Alpha',description='',category='Clinic',timezone='UTC').status_code==409
    # Deactivated service rejects new joins but an assigned owner can drain its existing queue.
    assert post(client,f'/owner/business/{bid}/services/{sid}/edit',name='Haircut',prefix='H',average_minutes=12,counter_label='Chair 2',description='New').status_code==303
    assert join(customer,sid).status_code==409
    assert post(client,f'/staff/call/{sid}').status_code==303
    assert post(client,f'/staff/complete/3').status_code in (404,409)  # unrelated/nonexistent legacy ticket ID
    with application.app_context():
        tid=Ticket.query.filter_by(service_id=sid).one().id
    assert post(client,f'/staff/complete/{tid}').status_code==303

@pytest.mark.parametrize('endpoint', ['','/stats','/history','/qr.png'])
def test_private_owner_url_isolation(tenants,endpoint):
    a,b=tenants
    assert a['client'].get(f"/owner/business/{b['business']}{endpoint}").status_code==404

@pytest.mark.parametrize('target', ['profile','branch','service','create_service','create_staff','invite'])
def test_private_mutation_isolation(tenants,target,application):
    a,b=tenants
    bid=b['business']; client=a['client']
    routes={
        'profile':(f'/owner/business/{bid}/edit',{'name':'Attacker','category':'Other','timezone':'UTC'}),
        'branch':(f"/owner/business/{bid}/branches/{b['branch']}/edit",{'name':'Attacker'}),
        'service':(f"/owner/business/{bid}/services/{b['service']}/edit",{'name':'Attacker','prefix':'X','average_minutes':5}),
        'create_service':(f'/owner/business/{bid}/services/create',{'branch_id':b['branch'],'name':'Attacker','prefix':'X','average_minutes':5}),
        'create_staff':(f'/owner/business/{bid}/staff/create',{'username':'attacker','password':'attack-password-123'}),
        'invite':(f'/owner/business/{bid}/staff/invite',{})}
    path,data=routes[target]
    assert post(client,path,**data).status_code==404
    with application.app_context():
        assert db.session.get(Business,bid).name=='Beta'
        assert db.session.get(Service,b['service']).name=='Consultation'
        assert not Staff.query.filter_by(username='attacker').first()


def test_payload_scope_staff_and_public_isolation(tenants,application):
    a,b=tenants
    client=a['client'];bid=a['business'];sid=b['service']
    assert post(client,f'/owner/business/{bid}/services/create',branch_id=b['branch'],name='Intrusion',prefix='X',average_minutes=5).status_code==404
    assert client.get(f'/owner/business/{bid}/qr.png?service_id={sid}').status_code==404
    assert client.get(f'/owner/business/{bid}/history?service_id={sid}').status_code==404
    assert client.get(f"/b/alpha/branch/{b['branch']}").status_code==404
    assert client.get(f'/b/alpha/service/{sid}').status_code==404
    assert client.get(f"/b/alpha/api/display?branch_id={b['branch']}").status_code==404
    customer=application.test_client()
    issued=join(customer,sid)
    with application.app_context():
        tid=Ticket.query.filter_by(service_id=sid).one().id
    for route in (f'/staff/call/{sid}',f'/staff/complete/{tid}',f'/staff/skip/{tid}'):
        assert post(client,route).status_code==404
    assert client.get('/staff/live').json[0]['id']==a['service']
    assert 'Beta' not in client.get('/staff/dashboard').text
    public=client.get('/b/alpha/api/display').json
    assert {r['service_id'] for r in public}=={a['service']}
    assert all(not {'token','owner_id','ticket_id'} & row.keys() for row in public)
    assert issued.location not in str(public)


def test_staff_assignment_revocation(tenants,application):
    a,b=tenants
    owner=a['client'];bid=a['business'];sid=a['service']
    assert post(owner,f'/owner/business/{bid}/staff/create',username='reception',password='staff-password-123').status_code==303
    staff=application.test_client()
    assert post(staff,'/staff/login',username='reception',password='staff-password-123').status_code==303
    assert staff.get('/staff/live').json==[]
    assert post(staff,f'/staff/call/{sid}').status_code==404
    with application.app_context():
        user=Staff.query.filter_by(username='reception').one()
        mid=Membership.query.filter_by(staff_id=user.id,business_id=bid).one().id
    path=f'/owner/business/{bid}/staff/{mid}/permissions'
    assert post(owner,path,is_active='on',service_ids=[b['service']]).status_code==404
    assert post(owner,path,is_active='on',service_ids=[sid]).status_code==303
    assert staff.get('/staff/live').json[0]['id']==sid
    ticket=join(application.test_client(),sid)
    assert post(staff,f'/staff/call/{sid}').status_code==303
    assert post(owner,path,service_ids=[]).status_code==303
    assert staff.get('/staff/live').json==[]
    with application.app_context():
        tid=Ticket.query.filter_by(service_id=sid).one().id
    assert post(staff,f'/staff/complete/{tid}').status_code==404
    assert post(owner,f'/staff/complete/{tid}').status_code==303
    # A non-owner cannot manage even their own business.
    assert staff.get(f'/owner/business/{bid}').status_code==404


def test_invite_one_time_and_expiry(tenants,application):
    a,b=tenants
    response=post(a['client'],f"/owner/business/{a['business']}/staff/invite")
    link=re.search(r'id="invite-link" value="([^"]+)"',response.text).group(1)
    path='/invite/'+link.rsplit('/',1)[-1]
    invitee=application.test_client()
    assert invitee.get(path).status_code==200
    assert post(invitee,path,username='invited',password='invited-password-123',confirm_password='invited-password-123').status_code==303
    assert invitee.get('/staff/live').json==[]
    assert invitee.get(path).status_code==410
    assert post(invitee,path).status_code==410
    response=post(a['client'],f"/owner/business/{a['business']}/staff/invite")
    token=re.search(r'id="invite-link" value="([^"]+)"',response.text).group(1).rsplit('/',1)[-1]
    with application.app_context():
        import hashlib
        invite=StaffInvite.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).one()
        assert invite.token_hash!=token
        invite.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
        db.session.commit()
    assert invitee.get('/invite/'+token).status_code==410


def test_actual_metrics_history_and_audit(tenants,application):
    a,b=tenants; owner=a['client'];sid=a['service'];bid=a['business']
    issued=join(application.test_client(),sid)
    with application.app_context():
        t=Ticket.query.filter_by(service_id=sid).one();tid=t.id
    post(owner,f'/staff/call/{sid}');post(owner,f'/staff/complete/{tid}')
    with application.app_context():
        t=db.session.get(Ticket,tid)
        t.created_at=datetime.now(timezone.utc)-timedelta(minutes=32)
        t.called_at=t.created_at+timedelta(minutes=20)
        t.finished_at=t.called_at+timedelta(minutes=12)
        db.session.commit()
    stats=owner.get(f'/owner/business/{bid}/stats').json
    assert stats['average_wait']==20 and stats['average_duration']==12
    assert stats['completed']==1 and stats['duration_samples']==1
    assert stats['throughput'][0]['completed']==1
    history=owner.get(f'/owner/business/{bid}/history')
    assert 'C001' in history.text and 'CREATED' in history.text and 'CALLED' in history.text and 'COMPLETED' in history.text
    assert b['client'].get(f"/owner/business/{b['business']}/stats").json['completed']==0
    with application.app_context():
        assert AdminEvent.query.filter_by(business_id=bid,action='BUSINESS_CREATED').count()==1
        assert TicketEvent.query.filter_by(ticket_id=tid).count()==3

@pytest.mark.parametrize('field,value', [('prefix','<script>'),('average_minutes','0'),('average_minutes','121'),('name',''),('counter_label','x'*41)])
def test_invalid_service_configuration(tenants,field,value):
    a,b=tenants
    data=dict(branch_id=a['branch'],name='New',prefix='N',average_minutes='5',counter_label='',is_active='on')
    data[field]=value
    assert post(a['client'],f"/owner/business/{a['business']}/services/create",**data).status_code==400


def test_scoped_names_prefixes_and_qr(tenants,application):
    a,b=tenants
    assert post(a['client'],f"/owner/business/{a['business']}/services/create",branch_id=a['branch'],name='Duplicate',prefix='C',average_minutes=5).status_code==409
    for args in ('',f"?service_id={a['service']}",f"?branch_id={a['branch']}&download=1"):
        response=a['client'].get(f"/owner/business/{a['business']}/qr.png"+args)
        assert response.status_code==200 and response.mimetype=='image/png'
        assert response.data.startswith(b'\x89PNG\r\n\x1a\n')
        assert response.headers['Cache-Control']=='no-store'
    c=application.test_client()
    assert join(c,a['service']).status_code==303 and join(c,b['service']).status_code==303
    with application.app_context():
        assert Ticket.query.filter(Ticket.service_id.in_((a['service'],b['service']))).count()==2
        assert {t.daily_number for t in Ticket.query}=={1}

@pytest.mark.parametrize('path',['/owner/register','/owner/login','/owner/business/create','/owner/business/1/edit','/owner/business/1/branches/create','/owner/business/1/services/create','/owner/business/1/staff/create','/owner/business/1/staff/invite','/invite/invalid'])
def test_universal_csrf(client,path):
    assert client.post(path).status_code==400

@pytest.mark.postgres
def test_postgres_tenant_isolation(pg_app):
    a=build_business(pg_app,'pg_owner_a','postgres-alpha');b=build_business(pg_app,'pg_owner_b','postgres-beta')
    assert a['client'].get(f"/owner/business/{b['business']}/history").status_code==404
    assert post(a['client'],f"/staff/call/{b['service']}").status_code==404
    assert post(a['client'],f"/owner/business/{a['business']}/services/create",branch_id=b['branch'],name='Intruder',prefix='X',average_minutes=5).status_code==404
    with pg_app.app_context():
        assert db.session.get(Service,b['service']).name=='Consultation'
        assert not Service.query.filter_by(name='Intruder').first()
@pytest.mark.postgres
def test_pg_assignment_constraint_and_revoke_lock(pg_app):
    from concurrent.futures import ThreadPoolExecutor,TimeoutError
    from threading import Event
    from sqlalchemy.exc import IntegrityError
    a=build_business(pg_app,'constraint_owner_a','constraint-alpha')
    b=build_business(pg_app,'constraint_owner_b','constraint-beta')
    owner=a['client'];bid=a['business'];sid=a['service']
    post(owner,f'/owner/business/{bid}/staff/create',username='pg_reception',password='strong-staff-password')
    with pg_app.app_context():
        user=Staff.query.filter_by(username='pg_reception').one()
        mid=Membership.query.filter_by(staff_id=user.id,business_id=bid).one().id
        db.session.add(ServiceAssignment(membership_id=mid,service_id=b['service']))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
    post(owner,f'/owner/business/{bid}/staff/{mid}/permissions',is_active='on',service_ids=[sid])
    staff=pg_app.test_client()
    post(staff,'/staff/login',username='pg_reception',password='strong-staff-password')
    ticket=join(pg_app.test_client(),sid)
    ready=Event()
    # Save signed owner session for a separate request/connection.
    with owner.session_transaction() as sess:
        copied=dict(sess)
    def revoke():
        client=pg_app.test_client()
        with client.session_transaction() as sess:
            sess.update(copied)
        ready.set()
        return post(client,f'/owner/business/{bid}/staff/{mid}/permissions')
    with pg_app.app_context():
        db.session.execute(select(Service.id).where(Service.id==sid).with_for_update())
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(revoke)
            assert ready.wait(timeout=10)
            try:
                with pytest.raises(TimeoutError):
                    future.result(timeout=.3)
            finally:
                db.session.commit()
            assert future.result(timeout=10).status_code==303
    assert post(staff,f'/staff/call/{sid}').status_code==404
    with pg_app.app_context():
        assert Ticket.query.filter_by(service_id=sid).one().status=='WAITING'
        assert ServiceAssignment.query.filter_by(membership_id=mid).count()==0

@pytest.mark.postgres
def test_pg_upgrade_audited_schema_preserves_scope(pg_app):
    from pathlib import Path
    with pg_app.app_context():
        # Build the audited pre-Universal schema, isolated inside this test's random schema.
        db.drop_all()
        with db.engine.begin() as connection:
            connection.execute(text('''
CREATE TABLE staff(id serial PRIMARY KEY,username varchar(64) UNIQUE NOT NULL,password_hash varchar(256) NOT NULL);
CREATE TABLE services(id serial PRIMARY KEY,name varchar(128) UNIQUE NOT NULL,description varchar(256),prefix varchar(10) UNIQUE NOT NULL,is_active boolean);
CREATE TABLE tickets(id serial PRIMARY KEY,token varchar(36) UNIQUE NOT NULL,service_id integer REFERENCES services(id) NOT NULL,daily_number integer NOT NULL,display_number varchar(20) NOT NULL,status varchar(20) NOT NULL,created_at timestamp NOT NULL);
CREATE TABLE ticket_events(id serial PRIMARY KEY,ticket_id integer REFERENCES tickets(id) NOT NULL,event_type varchar(50) NOT NULL,timestamp timestamp NOT NULL,staff_id integer REFERENCES staff(id));
INSERT INTO services(name,prefix,is_active) VALUES('Audited Service','A',true);
INSERT INTO tickets(token,service_id,daily_number,display_number,status,created_at) VALUES('00000000-0000-0000-0000-000000000001',1,1,'A001','COMPLETED','2026-10-10 08:00:00');
INSERT INTO ticket_events(ticket_id,event_type,timestamp) VALUES(1,'CREATED','2026-10-10 08:00:00'),(1,'CALLED','2026-10-10 08:10:00'),(1,'COMPLETED','2026-10-10 08:15:00');
'''))
            connection.execute(text(Path('migrations/001_queue_integrity.sql').read_text(encoding='utf-8')))
            from werkzeug.security import generate_password_hash
            connection.execute(text("INSERT INTO staff(username,password_hash) VALUES('legacy_staff',:pw)"),{'pw':generate_password_hash('legacy-secure-password')})
        runner=pg_app.test_cli_runner()
        result=runner.invoke(args=['upgrade-db','--apply'])
        assert result.exit_code==0,result.output
        t=db.session.get(Ticket,1)
        assert t.service.branch.business.slug=='legacy' and len(t.events)==3
        assert (t.called_at-t.created_at).total_seconds()==600
        assert (t.finished_at-t.called_at).total_seconds()==300
        assert Membership.query.filter_by(role='owner').count()==0
        assert ServiceAssignment.query.count()==1
        customer=pg_app.test_client()
        assert post(customer,'/staff/login',username='legacy_staff',password='legacy-secure-password').status_code==303
        assert customer.get('/staff/live').json[0]['name']=='Audited Service'
        assert customer.get('/owner/business/1').status_code==404
        claimed=runner.invoke(args=['create-owner','--business-id','1','--username','legacy_staff','--password','legacy-secure-password'])
        assert claimed.exit_code==0,claimed.output
        assert customer.get('/owner/business/1').status_code==200
        assert runner.invoke(args=['upgrade-db','--apply']).exit_code==0
def test_invite_existing_account_cannot_restore_revoked_access(tenants,application):
    a,b=tenants
    owner=a['client'];bid=a['business']
    post(owner,f'/owner/business/{bid}/staff/create',username='shared_staff',password='shared-secure-password')
    staff=application.test_client()
    post(staff,'/staff/login',username='shared_staff',password='shared-secure-password')
    with application.app_context():
        uid=Staff.query.filter_by(username='shared_staff').one().id
        mid=Membership.query.filter_by(business_id=bid,staff_id=uid).one().id
    response=post(b['client'],f"/owner/business/{b['business']}/staff/invite")
    token=re.search(r'id="invite-link" value="([^"]+)"',response.text).group(1).rsplit('/',1)[-1]
    assert post(staff,'/invite/'+token).status_code==303
    assert staff.get('/staff/live').json==[]
    response=post(owner,f'/owner/business/{bid}/staff/invite')
    token=re.search(r'id="invite-link" value="([^"]+)"',response.text).group(1).rsplit('/',1)[-1]
    post(owner,f'/owner/business/{bid}/staff/{mid}/permissions')
    assert post(staff,'/invite/'+token).status_code==403
    assert post(b['client'],f"/owner/business/{b['business']}/staff/{mid}/permissions",is_active='on',service_ids=[b['service']]).status_code==404
    assert post(owner,f'/owner/business/{bid}/staff/create',username='shared_staff',password='replaced-password-123').status_code==409
    with application.app_context():
        assert db.session.get(Staff,uid).check_password('shared-secure-password')
        assert db.session.get(Membership,mid).is_active is False


def test_inactive_branch_drains_and_invalid_scope(tenants,application):
    a,b=tenants;owner=a['client'];bid=a['business'];sid=a['service']
    customer=application.test_client()
    issued=join(customer,sid)
    assert post(owner,f"/owner/business/{bid}/branches/{a['branch']}/edit",name='Closed',address='').status_code==303
    assert customer.get(f"/b/alpha/branch/{a['branch']}").status_code==404
    assert join(customer,sid).status_code==409
    assert post(owner,f'/staff/call/{sid}').status_code==303
    rows=customer.get(f"/b/alpha/api/display?branch_id={a['branch']}").json
    assert rows[0]['currently_called']=='C001'
    assert customer.get('/b/alpha/api/display?branch_id=not-a-number').status_code==400
    assert owner.get(f'/owner/business/{bid}/history?page=-1').status_code==400
    assert owner.get(f'/owner/business/{bid}/history?status=WAITING').status_code==400


def test_fresh_schema_has_no_default_credentials():
    from app import create_app
    application=create_app({'TESTING':True,'PRODUCTION':False,'SECRET_KEY':'fresh-schema-only','SQLALCHEMY_DATABASE_URI':'sqlite:///:memory:'})
    result=application.test_cli_runner().invoke(args=['initdb'])
    assert result.exit_code==0,result.output
    with application.app_context():
        assert Staff.query.count()==0 and Business.query.count()==0 and Service.query.count()==0
    assert application.test_client().get('/health').status_code==200
