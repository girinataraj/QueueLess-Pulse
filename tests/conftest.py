import re
import uuid
import pytest
from app import create_app
from models import db, Service, Staff, Business, Branch, Membership, ServiceAssignment

@pytest.fixture
def application():
    yield from seeded_application('sqlite:///:memory:')

@pytest.fixture
def browser_application(tmp_path):
    # The threaded browser server needs separate pooled DBAPI connections.
    # In-memory SQLite uses StaticPool and shares one connection concurrently.
    uri = 'sqlite:///' + (tmp_path / 'browser.sqlite3').as_posix()
    yield from seeded_application(uri)

def seeded_application(uri):
    app = create_app({'TESTING': True, 'PRODUCTION': False, 'SECRET_KEY': 'test-only', 'SQLALCHEMY_DATABASE_URI': uri})
    with app.app_context():
        db.create_all()
        seed_foundation()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

@pytest.fixture
def client(application):
    return application.test_client()

def csrf(client, path='/'):
    response = client.get(path)
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)

def post(client, path, **data):
    data.setdefault('csrf_token', csrf(client))
    return client.post(path, data=data)

def join(client, service=1, key=None):
    return post(client, f'/service/{service}/join', request_key=key or str(uuid.uuid4()))

def login(client):
    return post(client, '/staff/login', username='tester', password='test-password-123')


def seed_foundation():
    business=Business(name='Demo Clinic',slug='demo',timezone='Asia/Kolkata')
    db.session.add(business)
    db.session.flush()
    branch=Branch(name='Main Branch',business_id=business.id)
    db.session.add(branch)
    db.session.flush()
    staff=Staff(username='tester')
    staff.set_password('test-password-123')
    services=[Service(name='General',prefix='G',branch_id=branch.id),Service(name='Tech',prefix='T',branch_id=branch.id)]
    db.session.add_all([staff,*services])
    db.session.flush()
    member=Membership(business_id=business.id,staff_id=staff.id,role='staff')
    db.session.add(member)
    db.session.flush()
    db.session.add_all([ServiceAssignment(membership_id=member.id,service_id=s.id) for s in services])
    db.session.commit()
