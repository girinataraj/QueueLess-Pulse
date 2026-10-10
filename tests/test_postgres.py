import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid
import pytest
from sqlalchemy import create_engine, text, make_url
from app import create_app
from models import db, Staff, Service, Ticket, TicketEvent
from conftest import join, login, post, seed_foundation

@pytest.fixture
def pg_app():
    uri = os.getenv('TEST_DATABASE_URL')
    if not uri:
        pytest.skip('TEST_DATABASE_URL unset; PostgreSQL correctness not established by SQLite')
    uri = uri.replace('postgresql://', 'postgresql+psycopg2://', 1)
    url = make_url(uri)
    if url.get_backend_name() != 'postgresql' or not url.database.endswith('_test'):
        pytest.fail('Integration database must be PostgreSQL with name ending _test')
    schema = 'test_' + uuid.uuid4().hex
    admin = create_engine(uri)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    app = create_app({'TESTING': True, 'PRODUCTION': False, 'SECRET_KEY': 'postgres-test-only',
                      'SQLALCHEMY_DATABASE_URI': uri,
                      'SQLALCHEMY_ENGINE_OPTIONS': {'connect_args': {'options': f'-csearch_path={schema}'}, 'pool_size': 16}})
    with app.app_context():
        db.create_all()
        seed_foundation()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


def parallel(app, operations, staff=False):
    clients = [app.test_client() for _ in operations]
    for client in clients:
        client.get('/')
        if staff:
            login(client)
        client.get('/')
    barrier = Barrier(len(operations))
    def run(pair):
        client, operation = pair
        barrier.wait(timeout=15)
        return operation(client)
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(run, zip(clients, operations)))

@pytest.mark.postgres
def test_concurrent_first_and_later_issuance(pg_app):
    for batch in range(2):
        responses = parallel(pg_app, [lambda c: join(c) for _ in range(8)])
        assert all(r.status_code == 303 for r in responses)
    with pg_app.app_context():
        assert sorted(t.daily_number for t in Ticket.query) == list(range(1,17))
        assert len({t.token for t in Ticket.query}) == 16
        assert TicketEvent.query.count() == 16
        assert db.session.get(Service,1).last_number == 16

@pytest.mark.postgres
def test_simultaneous_call_next(pg_app):
    client = pg_app.test_client()
    for _ in range(4):
        join(client)
    responses = parallel(pg_app,[lambda c: post(c,'/staff/call/1') for _ in range(4)],staff=True)
    assert sorted(r.status_code for r in responses) == [303,409,409,409]
    with pg_app.app_context():
        assert [t.id for t in Ticket.query.filter_by(status='CALLED')] == [1]
        assert Ticket.query.filter_by(status='WAITING').count() == 3
        assert TicketEvent.query.filter_by(event_type='CALLED').count() == 1

@pytest.mark.postgres
def test_complete_vs_skip(pg_app):
    client = pg_app.test_client()
    join(client)
    login(client)
    post(client,'/staff/call/1')
    results = parallel(pg_app,[lambda c: post(c,'/staff/complete/1'),lambda c: post(c,'/staff/skip/1')],staff=True)
    assert sorted(r.status_code for r in results) == [303,409]
    with pg_app.app_context():
        assert db.session.get(Ticket,1).status in ('COMPLETED','SKIPPED')
        assert TicketEvent.query.filter(TicketEvent.event_type.in_(('COMPLETED','SKIPPED'))).count() == 1

@pytest.mark.postgres
def test_independent_service_calls(pg_app):
    client = pg_app.test_client()
    join(client,1)
    join(client,2)
    results = parallel(pg_app,[lambda c: post(c,'/staff/call/1'),lambda c: post(c,'/staff/call/2')],staff=True)
    assert [r.status_code for r in results] == [303,303]
    with pg_app.app_context():
        assert Ticket.query.filter_by(status='CALLED').count() == 2

@pytest.mark.postgres
def test_duplicate_request_concurrently(pg_app):
    client = pg_app.test_client()
    client.get('/')
    with client.session_transaction() as session:
        token, owner = session['csrf_token'], session['owner_id']
    key = str(uuid.uuid4())
    barrier = Barrier(2)
    def run(_):
        c = pg_app.test_client()
        with c.session_transaction() as session:
            session.update(csrf_token=token,owner_id=owner)
        barrier.wait(timeout=15)
        return c.post('/service/1/join',data={'csrf_token':token,'request_key':key})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(run,range(2)))
    assert all(r.status_code == 303 for r in responses)
    assert responses[0].location == responses[1].location
    with pg_app.app_context():
        assert Ticket.query.count() == 1
        assert TicketEvent.query.count() == 1
@pytest.mark.postgres
def test_held_service_lock_blocks_issuance(pg_app):
    from concurrent.futures import TimeoutError
    from threading import Event
    from sqlalchemy import select
    started = Event()
    def issue():
        client = pg_app.test_client()
        client.get('/')
        started.set()
        return join(client)
    with pg_app.app_context():
        service = db.session.scalar(select(Service).where(Service.id==1).with_for_update())
        service.seq_date = __import__('datetime').datetime.now(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).date()
        service.last_number = 10
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(issue)
            assert started.wait(timeout=5)
            try:
                with pytest.raises(TimeoutError):
                    future.result(timeout=0.3)
            finally:
                db.session.commit()
            assert future.result(timeout=10).status_code == 303
        assert Ticket.query.first().daily_number == 11

@pytest.mark.postgres
def test_completion_races_call_next(pg_app):
    client=pg_app.test_client()
    join(client)
    join(client)
    login(client)
    post(client,'/staff/call/1')
    responses=parallel(pg_app,[lambda c:post(c,'/staff/complete/1'),lambda c:post(c,'/staff/call/1')],staff=True)
    assert responses[0].status_code==303
    assert responses[1].status_code in (303,409)
    with pg_app.app_context():
        assert db.session.get(Ticket,1).status=='COMPLETED'
        assert db.session.get(Ticket,2).status in ('WAITING','CALLED')
        assert Ticket.query.filter_by(status='CALLED').count() <= 1
        assert TicketEvent.query.filter_by(ticket_id=1,event_type='COMPLETED').count()==1

@pytest.mark.postgres
@pytest.mark.parametrize('conflict',[False,True],ids=['valid-history','duplicate-history'])
def test_legacy_migration_preserves_history(pg_app,conflict):
    from pathlib import Path
    with pg_app.app_context():
        db.drop_all()  # Only random test schema inside the explicitly isolated test DB.
        with db.engine.begin() as connection:
            connection.execute(text('''
CREATE TABLE staff(id serial PRIMARY KEY,username varchar(64) UNIQUE NOT NULL,password_hash varchar(256) NOT NULL);
CREATE TABLE services(id serial PRIMARY KEY,name varchar(128) UNIQUE NOT NULL,description varchar(256),prefix varchar(10) UNIQUE NOT NULL,is_active boolean);
CREATE TABLE tickets(id serial PRIMARY KEY,token varchar(36) UNIQUE NOT NULL,service_id integer REFERENCES services(id) NOT NULL,daily_number integer NOT NULL,display_number varchar(20) NOT NULL,status varchar(20) NOT NULL,created_at timestamp NOT NULL);
CREATE TABLE ticket_events(id serial PRIMARY KEY,ticket_id integer REFERENCES tickets(id) NOT NULL,event_type varchar(50) NOT NULL,timestamp timestamp NOT NULL,staff_id integer REFERENCES staff(id));
INSERT INTO services(name,prefix,is_active) VALUES('Legacy','L',true);
INSERT INTO tickets(token,service_id,daily_number,display_number,status,created_at) VALUES('00000000-0000-0000-0000-000000000001',1,1,'L001','COMPLETED','2026-10-10 18:31:00');
INSERT INTO ticket_events(ticket_id,event_type,timestamp) VALUES(1,'CREATED','2026-10-10 18:31:00');
'''))
        if conflict:
            with db.engine.begin() as connection:
                connection.execute(text("INSERT INTO tickets(token,service_id,daily_number,display_number,status,created_at) VALUES('00000000-0000-0000-0000-000000000002',1,1,'L001','COMPLETED','2026-10-10 18:32:00')"))
        result=pg_app.test_cli_runner().invoke(args=['migrate-legacy','--apply'])
        if conflict:
            from sqlalchemy import inspect
            assert result.exit_code != 0
            assert 'rolled back' in result.output
            assert 'business_date' not in {c['name'] for c in inspect(db.engine).get_columns('tickets')}
            with db.engine.connect() as connection:
                assert connection.scalar(text('SELECT count(*) FROM tickets')) == 2
                assert connection.scalar(text('SELECT count(*) FROM ticket_events')) == 1
            return
        assert result.exit_code == 0, result.output
        ticket=db.session.get(Ticket,1)
        assert str(ticket.business_date)=='2026-10-11'
        assert ticket.status=='COMPLETED'
        assert len(ticket.events)==1
        from datetime import datetime, timezone
        assert ticket.created_at.astimezone(timezone.utc) == datetime(2026,10,10,18,31,tzinfo=timezone.utc)
        assert db.session.get(Service,1).last_number==1
        assert pg_app.test_client().get('/health').status_code==200
@pytest.mark.postgres
def test_production_factory_smoke(pg_app,monkeypatch):
    monkeypatch.setenv('SECRET_KEY','p'*64)
    production=create_app({'PRODUCTION':True,'SECRET_KEY':'p'*64,
        'SQLALCHEMY_DATABASE_URI':pg_app.config['SQLALCHEMY_DATABASE_URI'],
        'SQLALCHEMY_ENGINE_OPTIONS':pg_app.config['SQLALCHEMY_ENGINE_OPTIONS']})
    client=production.test_client()
    assert client.get('/health').json == {'status':'ok'}
    response=client.get('/')
    assert response.status_code==200
    assert 'Secure;' in response.headers['Set-Cookie']
    assert 'HttpOnly;' in response.headers['Set-Cookie']
    assert 'SameSite=Lax' in response.headers['Set-Cookie']
