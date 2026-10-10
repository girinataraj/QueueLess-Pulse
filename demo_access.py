"""Outer access gate for the invited-reviewer demo; application RBAC stays intact."""
import secrets
from flask import jsonify, request

def configure(app):
    enabled=app.config['DEMO_MODE']
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
            response=jsonify(error={'code':'demo_access_required','message':'Restricted evaluator demonstration. Access is by private invitation only.'})
            response.status_code=401
            response.headers['WWW-Authenticate']='Basic realm="QueueLess Pulse restricted demo", charset="UTF-8"'
            return response
    app.before_request(gate)
