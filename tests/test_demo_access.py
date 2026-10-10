import base64
import secrets
import pytest
from app import create_app
from models import db

def auth(user,password):
    return {'Authorization':'Basic '+base64.b64encode((user+':'+password).encode()).decode()}

def test_restricted_demo_gate_blocks_every_experience_but_health(application):
    # A new in-memory database contains no accounts or production data.
    password=secrets.token_hex(32)
    app=create_app({**application.config,'DEMO_MODE':True,'DEMO_ACCESS_USER':'reviewer','DEMO_ACCESS_PASSWORD':password})
    with app.app_context():
        db.create_all()
    client=app.test_client()
    assert client.get('/health').status_code==200
    for path in ('/app/','/app/owner/register','/app/staff/login','/app/display','/','/owner/register','/api/v1/session','/sw.js'):
        response=client.get(path)
        assert response.status_code==401 and 'Basic realm=' in response.headers['WWW-Authenticate']
        assert response.headers['Cache-Control']=='no-store'
        assert password not in response.text
    assert client.get('/app/',headers=auth('reviewer','wrong')).status_code==401
    session=client.get('/api/v1/session',headers=auth('reviewer',password))
    assert session.status_code==200 and session.json['user'] is None
    # The outer invitation does not grant a business role or bypass CSRF.
    assert client.get('/api/v1/owner/businesses',headers=auth('reviewer',password)).status_code==401
    assert client.post('/api/v1/auth/register',headers=auth('reviewer',password),data={}).status_code==400

@pytest.mark.parametrize('config',[{'DEMO_ACCESS_USER':''},{'DEMO_ACCESS_PASSWORD':'short'}])
def test_demo_requires_private_strong_environment_configuration(config):
    with pytest.raises(RuntimeError,match='Restricted demo requires'):
        create_app({'PRODUCTION':False,'DEMO_MODE':True,'DEMO_ACCESS_USER':'reviewer','DEMO_ACCESS_PASSWORD':secrets.token_hex(32),**config})
