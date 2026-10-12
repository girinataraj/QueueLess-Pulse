"""Atomic database-backed fixed-window limits for both legacy and React routes."""
import hashlib
import hmac
import ipaddress
import time

from flask import current_app, request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from werkzeug.exceptions import TooManyRequests
from models import db, RateLimitBucket

AUTH_ENDPOINTS = frozenset(('staff_login', 'universal.owner_login', 'universal.register',
                          'universal.accept_invite', 'api.login', 'api.register', 'api.accept'))
QUEUE_ENDPOINTS = frozenset(('join_queue', 'api.issue', 'operations.walkin'))

def client_address():
    # Never trust client-supplied forwarding headers without an explicit proxy count.
    hops = current_app.config['RATE_LIMIT_TRUSTED_PROXY_HOPS']
    values = [v.strip() for v in request.headers.get('X-Forwarded-For', '').split(',') if v.strip()]
    value = values[-hops] if hops and len(values) >= hops else request.remote_addr or 'unknown'
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return request.remote_addr or 'unknown'

def consume(group, seconds, limit):
    """Share atomic protection across workers without retaining addresses/secrets."""
    now = int(time.time())
    start = now - now % seconds
    key = hmac.new(str(current_app.config['SECRET_KEY']).encode(), (group + ':' + client_address()).encode(), hashlib.sha256).hexdigest()
    table = RateLimitBucket.__table__
    insert = pg_insert if db.engine.dialect.name == 'postgresql' else sqlite_insert
    stmt = insert(table).values(key_hash=key, window_start=start, hits=1)
    stmt = stmt.on_conflict_do_update(index_elements=['key_hash', 'window_start'],
        set_={'hits': table.c.hits + 1}, where=table.c.hits < limit).returning(table.c.hits)
    # A separate short transaction ends before queue locks/handler transactions start.
    # A database failure propagates as 503 instead of silently disabling protection.
    with db.engine.begin() as connection:
        connection.execute(delete(table).where(table.c.window_start < now - 3600))
        allowed = connection.scalar(stmt) is not None
    if not allowed:
        raise TooManyRequests('Too many requests. Wait and retry.', retry_after=start + seconds - now)

def enforce():
    if request.method != 'POST':
        return
    if request.endpoint in AUTH_ENDPOINTS:
        consume('auth', 300, current_app.config['RATE_LIMIT_AUTH'])
    elif request.endpoint in QUEUE_ENDPOINTS:
        consume('queue', 60, current_app.config['RATE_LIMIT_QUEUE'])

def failed_gateway_attempt():
    # Called by the outer gate: a rejected request never reaches before_request
    # callbacks registered after it. Valid gateway polling is not rate limited.
    consume('gateway', 300, current_app.config['RATE_LIMIT_GATEWAY'])

def configure(app):
    if any(app.config[k] <= 0 for k in ('RATE_LIMIT_AUTH', 'RATE_LIMIT_QUEUE', 'RATE_LIMIT_GATEWAY')) or app.config['RATE_LIMIT_TRUSTED_PROXY_HOPS'] < 0:
        raise RuntimeError('Rate limits must be positive and trusted proxy count nonnegative')
    app.before_request(enforce)
