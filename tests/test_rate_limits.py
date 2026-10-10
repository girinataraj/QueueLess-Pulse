import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from sqlalchemy import text
from models import db, RateLimitBucket, Ticket
from test_api import api_post, contract
from test_postgres import pg_app

def test_auth_limit_shared_by_legacy_and_api(client, application, monkeypatch):
    import rate_limit
    monkeypatch.setattr(rate_limit.time, 'time', lambda: 1800)
    application.config['RATE_LIMIT_AUTH']=2
    assert api_post(client,'/auth/login',username='tester',password='wrong').status_code==401
    token=client.get('/api/v1/session').json['csrf_token']
    assert client.post('/staff/login',data={'csrf_token':token,'username':'tester','password':'wrong'}).status_code==401
    denied=api_post(client,'/auth/login',username='tester',password='wrong')
    contract(denied,'ApiError',429)
    assert denied.headers['Retry-After']=='300'
    assert client.post('/staff/login',data={'csrf_token':token}).status_code==429
    assert client.get('/health').status_code==200
    with application.app_context():
        rows=RateLimitBucket.query.all()
        assert len(rows)==1 and rows[0].hits==2
        assert '127.0.0.1' not in rows[0].key_hash and len(rows[0].key_hash)==64
    monkeypatch.setattr(rate_limit.time,'time',lambda:2100)
    assert api_post(client,'/auth/login',username='tester',password='wrong').status_code==401

def test_queue_limit_forwarding_spoof_and_expired_cleanup(client,application,monkeypatch):
    import rate_limit
    monkeypatch.setattr(rate_limit.time,'time',lambda:7200)
    application.config['RATE_LIMIT_QUEUE']=1
    with application.app_context():
        db.session.add(RateLimitBucket(key_hash='a'*64,window_start=3000,hits=1));db.session.commit()
    token=client.get('/api/v1/session').json['csrf_token']
    first=client.post('/api/v1/services/1/tickets',data={'csrf_token':token,'request_key':str(uuid.uuid4())},headers={'X-Forwarded-For':'1.2.3.4'})
    assert first.status_code==201
    second=client.post('/service/1/join',data={'csrf_token':token,'request_key':str(uuid.uuid4())},headers={'X-Forwarded-For':'5.6.7.8'})
    assert second.status_code==429 and second.headers['Retry-After']=='60'
    with application.app_context():
        assert Ticket.query.count()==1
        assert RateLimitBucket.query.filter_by(key_hash='a'*64).count()==0
    # A trusted edge's appended address is used, never an attacker-controlled first entry.
    application.config['RATE_LIMIT_TRUSTED_PROXY_HOPS']=1
    def from_proxy(header):
        return client.post('/api/v1/services/1/tickets',data={'csrf_token':token,'request_key':str(uuid.uuid4())},headers={'X-Forwarded-For':header})
    assert from_proxy('9.9.9.9, 203.0.113.2').status_code==201
    assert from_proxy('8.8.8.8, 203.0.113.2').status_code==429
    assert from_proxy('203.0.113.3').status_code==201

def test_render_three_hop_chain_ignores_spoofs_and_changing_proxies(client,application):
    application.config['RATE_LIMIT_QUEUE']=1
    application.config['RATE_LIMIT_TRUSTED_PROXY_HOPS']=3
    token=client.get('/api/v1/session').json['csrf_token']
    def issue(chain):
        return client.post('/api/v1/services/1/tickets',
            data={'csrf_token':token,'request_key':str(uuid.uuid4())},
            headers={'X-Forwarded-For':chain})
    assert issue('203.0.113.2, 198.51.100.100, 10.0.0.1').status_code==201
    # The edge appends three addresses. Neither a forged prefix nor changing
    # intermediary proxy addresses may create another bucket for this client.
    assert issue('192.0.2.50, 192.0.2.51, 203.0.113.2, 198.51.100.101, 10.0.0.2').status_code==429
    assert issue('203.0.113.3, 198.51.100.101, 10.0.0.2').status_code==201
    with application.app_context():
        assert Ticket.query.count()==2
        assert RateLimitBucket.query.count()==2


@pytest.mark.postgres
def test_postgres_rate_limit_atomic_across_connections(pg_app):
    pg_app.config['RATE_LIMIT_QUEUE']=2
    clients=[pg_app.test_client() for _ in range(8)]
    tokens=[c.get('/api/v1/session').json['csrf_token'] for c in clients]
    barrier=Barrier(8)
    def issue(pair):
        client,token=pair;barrier.wait(timeout=15)
        return client.post('/api/v1/services/1/tickets',data={'csrf_token':token,'request_key':str(uuid.uuid4())})
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(issue,zip(clients,tokens)))
    assert sorted(r.status_code for r in results)==[201,201,429,429,429,429,429,429]
    with pg_app.app_context():
        assert Ticket.query.count()==2 and RateLimitBucket.query.one().hits==2

@pytest.mark.postgres
def test_additive_rate_limit_migration_preserves_existing_history(pg_app):
    client=pg_app.test_client()
    ticket=api_post(client,'/services/1/tickets',request_key=str(uuid.uuid4())).json
    with pg_app.app_context():
        with db.engine.begin() as c:c.execute(text('DROP TABLE rate_limit_buckets'))
        result=pg_app.test_cli_runner().invoke(args=['upgrade-db','--apply'])
        assert result.exit_code==0,result.output
        assert Ticket.query.one().token==ticket['token']
        assert len(Ticket.query.one().events)==1
        assert RateLimitBucket.query.count()==0
        assert pg_app.test_cli_runner().invoke(args=['upgrade-db','--apply']).exit_code==0
    assert client.get('/health').status_code==200
