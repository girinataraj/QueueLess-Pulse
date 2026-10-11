import base64
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from models import db, Service, Ticket
from staging import bootstrap_schema, validate_configuration
from test_postgres import pg_app


def configuration(**overrides):
    return dict(PRODUCTION=True, DEBUG=False, SECRET_KEY=secrets.token_hex(32), DEMO_MODE=True, OWNER_REGISTRATION_ENABLED=False,
                PUBLIC_BASE_URL='https://queueless-staging.onrender.com',
                TRUSTED_HOSTS=['queueless-staging.onrender.com'],
                SQLALCHEMY_DATABASE_URI='postgresql://test@127.0.0.1/staging_test',
                STAGING_DATABASE_NAME='staging_test', **overrides)


def test_staging_accepts_explicit_isolated_database_and_https():
    validate_configuration(configuration())


@pytest.mark.parametrize('field,value', [
    ('PRODUCTION', False), ('DEBUG', True), ('SECRET_KEY', 'short'), ('DEMO_MODE', False),
    ('PUBLIC_BASE_URL', 'http://queueless-staging.onrender.com'),
    ('PUBLIC_BASE_URL', 'https://127.0.0.1'), ('PUBLIC_BASE_URL', 'https://demo.local'),
    ('PUBLIC_BASE_URL', 'https://user:password@queueless-staging.onrender.com'),
    ('PUBLIC_BASE_URL', 'https://queueless-staging.onrender.com/app/'),
    ('PUBLIC_BASE_URL', 'https://queueless-staging.onrender.com?secret=x'),
    ('PUBLIC_BASE_URL', 'https://queueless-staging.onrender.com#fragment'),
    ('PUBLIC_BASE_URL', 'https://queueless-staging.onrender.com:bad'),
    ('PUBLIC_BASE_URL', 'https://queueless-staging.onrender.com:5001'),
    ('TRUSTED_HOSTS', ['*']), ('TRUSTED_HOSTS', ['other.onrender.com']),
    ('STAGING_DATABASE_NAME', ''), ('STAGING_DATABASE_NAME', 'different'),
    ('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')])
def test_staging_rejects_unsafe_configuration(field, value):
    config = configuration()
    config[field] = value
    with pytest.raises(RuntimeError):
        validate_configuration(config)


@pytest.mark.parametrize('name', ['queueless_erode_demo', 'queueless_erode_integration', 'queueless_pulse_demo_db'])
def test_staging_cannot_reuse_protected_demo_database(name):
    config = configuration()
    config.update(STAGING_DATABASE_NAME=name, SQLALCHEMY_DATABASE_URI='postgresql://test@127.0.0.1/'+name)
    with pytest.raises(RuntimeError, match='protected'):
        validate_configuration(config)


def test_staging_cannot_use_existing_hosted_demo_origin():
    config = configuration()
    config.update(PUBLIC_BASE_URL='https://queueless-pulse-demo.onrender.com',
                  TRUSTED_HOSTS=['queueless-pulse-demo.onrender.com'])
    with pytest.raises(RuntimeError, match='protected hosted demo'):
        validate_configuration(config)


def test_staging_requires_encrypted_database_transport_and_distinct_secure_cookie(pg_app, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', secrets.token_hex(32))
    config = {**pg_app.config, **configuration(), 'APP_STAGE':'staging',
              'SQLALCHEMY_DATABASE_URI':pg_app.config['SQLALCHEMY_DATABASE_URI'],
              'STAGING_DATABASE_NAME':make_url(pg_app.config['SQLALCHEMY_DATABASE_URI']).database,
              'DEMO_ACCESS_USER':'evaluator', 'DEMO_ACCESS_PASSWORD':secrets.token_hex(32)}
    app = create_app(config)
    assert app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args']['sslmode']=='require'
    assert app.config['SESSION_COOKIE_NAME']=='queueless_staging'
    assert app.config['SESSION_COOKIE_SECURE'] and app.config['SESSION_COOKIE_HTTPONLY']
    assert app.config['SESSION_COOKIE_SAMESITE']=='Lax'
    with app.app_context(): db.engine.dispose()


@pytest.mark.parametrize('backend', ['sqlite', 'postgres'])
def test_gateway_failures_throttled_without_blocking_authorized_polling(request, backend):
    foundation = request.getfixturevalue('application' if backend == 'sqlite' else 'pg_app')
    password = secrets.token_hex(32)
    app = create_app({**foundation.config, 'DEMO_MODE': True, 'DEMO_ACCESS_USER': 'evaluator',
                      'DEMO_ACCESS_PASSWORD': password, 'RATE_LIMIT_GATEWAY': 3})
    with app.app_context():
        db.create_all()
    client = app.test_client()
    headers = {'Authorization': 'Basic '+base64.b64encode(('evaluator:'+password).encode()).decode()}
    bad = {'Authorization':'Basic '+base64.b64encode(b'evaluator:wrong').decode()}
    assert all(client.get('/api/v1/session').status_code==401 for _ in range(50))
    assert [client.get('/api/v1/session',headers=bad).status_code for _ in range(4)] == [401,401,401,429]
    limited = client.get('/api/v1/session',headers=bad)
    assert limited.status_code == 429 and 0 < int(limited.headers['Retry-After']) <= 300
    assert client.get('/health').status_code == 200
    assert all(client.get('/api/v1/session', headers=headers).status_code == 200 for _ in range(6))
    # A caller cannot evade the gateway budget by inventing forwarding headers.
    assert client.get('/api/v1/session', headers={**bad,'X-Forwarded-For': '198.51.100.2'}).status_code == 429
    assert client.get('/api/v1/owner/businesses', headers=headers).status_code == 401
    assert client.post('/api/v1/auth/login', headers=headers, json={}).status_code == 400


def test_gateway_limit_is_atomic_across_postgres_workers(pg_app):
    app = create_app({**pg_app.config, 'DEMO_MODE': True, 'DEMO_ACCESS_USER': 'evaluator',
                      'DEMO_ACCESS_PASSWORD': secrets.token_hex(32), 'RATE_LIMIT_GATEWAY': 3})
    with ThreadPoolExecutor(max_workers=8) as pool:
        bad = {'Authorization':'Basic '+base64.b64encode(b'evaluator:wrong').decode()}
        statuses = list(pool.map(lambda _: app.test_client().get('/app/',headers=bad).status_code, range(8)))
    assert sorted(statuses) == [401]*3+[429]*5


def test_production_headers_and_legacy_nonce(pg_app, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', secrets.token_hex(32))
    app = create_app({**pg_app.config, 'PRODUCTION': True, 'SECRET_KEY': secrets.token_hex(32)})
    first = app.test_client().get('/')
    second = app.test_client().get('/')
    assert first.status_code == 200
    assert first.headers['Strict-Transport-Security'] == 'max-age=31536000'
    csp = first.headers['Content-Security-Policy']
    assert "frame-ancestors 'none'" in csp and "script-src 'self' 'nonce-" in csp
    nonce = csp.split("'nonce-",1)[1].split("'",1)[0]
    assert 'nonce="'+nonce+'"' in first.text
    assert nonce not in second.headers['Content-Security-Policy']
    assert "'unsafe-inline'" not in csp.split('script-src',1)[1]
    assert 'camera=()' in first.headers['Permissions-Policy']


def test_staging_bootstrap_repeatedly_preserves_records(pg_app):
    name = make_url(pg_app.config['SQLALCHEMY_DATABASE_URI']).database
    with pg_app.app_context():
        before = [(s.id,s.name) for s in Service.query.order_by(Service.id)]
    bootstrap_schema(pg_app, name)
    bootstrap_schema(pg_app, name)
    with pg_app.app_context():
        assert [(s.id,s.name) for s in Service.query.order_by(Service.id)] == before
        assert Ticket.query.count() == 0


def test_staging_bootstrap_refuses_identity_mismatch(pg_app):
    with pytest.raises(RuntimeError, match='identity mismatch'):
        bootstrap_schema(pg_app, 'never_use_the_demo')
    with pg_app.app_context():
        assert Service.query.count() == 2


def test_staging_bootstrap_refuses_legacy_without_destructive_migration(pg_app):
    name = make_url(pg_app.config['SQLALCHEMY_DATABASE_URI']).database
    with pg_app.app_context():
        # Disposable fixture schema only. Preserve the legacy table to prove refusal.
        db.session.remove()
        db.drop_all()
        with db.engine.begin() as connection:
            connection.execute(text('CREATE TABLE services (id integer PRIMARY KEY, name text)'))
            connection.execute(text("INSERT INTO services VALUES (1,'legacy preserved')"))
    with pytest.raises(RuntimeError, match='explicit backed-up migration'):
        bootstrap_schema(pg_app, name)
    with pg_app.app_context(), db.engine.connect() as connection:
        assert connection.execute(text('SELECT name FROM services')).scalar() == 'legacy preserved'
