"""Outer access gate for the invited-reviewer demo; application RBAC stays intact."""
import secrets
from flask import jsonify, request

def configure(app):
    mode=app.config['STAGING_AUTH_MODE']
    if mode not in ('basic', 'application'):
        raise RuntimeError('Unknown staging authentication mode')
    if mode == 'application' and app.config['APP_STAGE'] != 'staging':
        raise RuntimeError('Application-only demo access is limited to explicitly isolated staging')
    enabled=app.config['DEMO_MODE'] and mode == 'basic'
    app.config['DEMO_GATEWAY_ENABLED']=enabled
    user=app.config['DEMO_ACCESS_USER']
    password=app.config['DEMO_ACCESS_PASSWORD']
    if enabled and (not user or len(password)<32):
        raise RuntimeError('Restricted demo requires an environment username and password of at least 32 characters')
    def gate():
        if not enabled or (request.path == '/health' and request.method in ('GET','HEAD')):
            return
        auth=request.authorization
        valid=bool(auth and auth.type=='basic')
        valid=valid and secrets.compare_digest((auth.username or '').encode(),user.encode()) and secrets.compare_digest((auth.password or '').encode(),password.encode())
        if not valid:
            # Basic authentication starts with a credential-free challenge;
            # parallel asset requests can each need one. Count failed supplied
            # credentials, never punish that mandatory browser negotiation.
            if 'Authorization' in request.headers:
                from rate_limit import failed_gateway_attempt
                failed_gateway_attempt()
            response=jsonify(error={'code':'demo_access_required','message':'Restricted evaluator demonstration. Access is by private invitation only.'})
            response.status_code=401
            response.headers['WWW-Authenticate']='Basic realm="QueueLess Pulse restricted demo", charset="UTF-8"'
            return response
    app.before_request(gate)
