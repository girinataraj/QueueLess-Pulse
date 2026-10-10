import os
import pytest
from app import create_app
from models import db
from conftest import join, post, login

@pytest.mark.parametrize('database', [None,'sqlite:///bad.db'])
def test_production_rejects_sqlite(monkeypatch,database):
    monkeypatch.setenv('SECRET_KEY','x'*64)
    with pytest.raises(RuntimeError,match='PostgreSQL'):
        create_app({'PRODUCTION':True,'SQLALCHEMY_DATABASE_URI':database or 'sqlite:///dev.db'})

def test_production_rejects_missing_secret(monkeypatch):
    monkeypatch.delenv('SECRET_KEY',raising=False)
    with pytest.raises(RuntimeError,match='SECRET_KEY'):
        create_app({'PRODUCTION':True})

def test_timezone_boundary(client,application,monkeypatch):
    from datetime import datetime,timezone
    import app as module
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            return datetime(2026,10,10,18,29,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(module,'datetime',Clock)
    join(client)
    class NextClock(datetime):
        @classmethod
        def now(cls,tz=None):
            return datetime(2026,10,10,18,31,tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(module,'datetime',NextClock)
    join(client)
    from models import Ticket
    with application.app_context():
        tickets=Ticket.query.order_by(Ticket.id).all()
        assert [str(t.business_date) for t in tickets] == ['2026-10-10','2026-10-11']
        assert [t.daily_number for t in tickets] == [1,1]

def test_called_cannot_cancel(client):
    ticket=join(client)
    login(client)
    post(client,'/staff/call/1')
    assert post(client,ticket.location+'/cancel').status_code == 409
def test_bootstrap_and_staff_provisioning(application):
    from models import Staff, Service
    runner=application.test_cli_runner()
    assert runner.invoke(args=['initdb']).exit_code==0
    result=runner.invoke(args=['create-staff','--username','new_staff','--password','strong-test-password'])
    assert result.exit_code==0
    with application.app_context():
        staff=Staff.query.filter_by(username='new_staff').one()
        assert staff.check_password('strong-test-password')
        assert staff.password_hash != 'strong-test-password'
        assert Service.query.count()==2
    assert runner.invoke(args=['create-staff','--username','bad','--password','short']).exit_code!=0
    assert runner.invoke(args=['migrate-legacy','--apply']).exit_code!=0
