"""Fail-closed staging configuration and additive initialization of its own DB."""
import ipaddress
import re
from urllib.parse import urlsplit

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url


def validate_configuration(config):
    if not config['PRODUCTION'] or config['DEBUG']:
        raise RuntimeError('Staging requires production mode with debug disabled')
    if len(config['SECRET_KEY']) < 32 or not config['DEMO_MODE']:
        raise RuntimeError('Staging requires strong secrets and the restricted evaluator gateway')
    origin = config['PUBLIC_BASE_URL']
    parsed = urlsplit(origin)
    host = parsed.hostname or ''
    try:
        ipaddress.ip_address(host)
        is_address = True
    except ValueError:
        is_address = False
    try:
        port = parsed.port
    except ValueError:
        raise RuntimeError('Staging requires a public HTTPS origin') from None
    if (parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}', host)
            or is_address or host.endswith(('.local', '.localhost', '.internal'))
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment or port not in (None, 443)):
        raise RuntimeError('Staging requires a public HTTPS origin without credentials, path, query or fragment')
    if config['TRUSTED_HOSTS'] != [host]:
        raise RuntimeError('Staging TRUSTED_HOSTS must contain only its HTTPS hostname')
    if host == 'queueless-pulse-demo.onrender.com':
        raise RuntimeError('Staging must not use the protected hosted demo origin')
    uri = make_url(config['SQLALCHEMY_DATABASE_URI'])
    expected = config['STAGING_DATABASE_NAME']
    if uri.get_backend_name() != 'postgresql' or not expected or uri.database != expected:
        raise RuntimeError('Staging requires its explicitly named separate PostgreSQL database')
    if expected in ('queueless_erode_demo', 'queueless_erode_integration', 'queueless_pulse_demo_db'):
        raise RuntimeError('Staging must not reuse a protected demo database')


def bootstrap_schema(app, expected_database):
    """Create missing tables under an advisory lock; never reset or migrate blindly."""
    from models import db
    with app.app_context():
        with db.engine.connect() as connection:
            actual, schema = connection.execute(text('SELECT current_database(),current_schema()')).one()
            if actual != expected_database or not expected_database:
                raise RuntimeError('Staging database identity mismatch; no schema was changed')
            if schema != 'public' and not (app.testing and schema.startswith('test_')):
                raise RuntimeError('Unexpected staging schema; no schema was changed')
            connection.execute(text("SELECT pg_advisory_lock(hashtext('queueless-staging-bootstrap'))"))
            try:
                inspector = inspect(connection)
                if inspector.has_table('services', schema=schema):
                    columns = {c['name'] for c in inspector.get_columns('services', schema=schema)}
                    if 'branch_id' not in columns:
                        raise RuntimeError('Legacy schema requires an explicit backed-up migration')
                if inspector.has_table('tickets', schema=schema):
                    columns = {c['name'] for c in inspector.get_columns('tickets', schema=schema)}
                    if 'business_date' not in columns:
                        raise RuntimeError('Legacy numbering requires an explicit backed-up migration')
                db.metadata.create_all(connection)
                connection.commit()
            finally:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(hashtext('queueless-staging-bootstrap'))"))
                connection.commit()


def main():
    from app import create_app
    app = create_app()
    if app.config['APP_STAGE'] != 'staging':
        raise RuntimeError('This initializer is restricted to APP_STAGE=staging')
    validate_configuration(app.config)
    bootstrap_schema(app, app.config['STAGING_DATABASE_NAME'])
    print('Separate staging schema is ready. No tickets, accounts or seed data were inserted.')


if __name__ == '__main__':
    main()
