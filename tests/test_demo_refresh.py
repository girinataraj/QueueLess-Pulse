"""Refresh is explicit, backed up, idempotent and preserves prior ticket/audit history."""
from datetime import datetime, timezone, date
from pathlib import Path
import secrets
import sys
import pytest
from models import db, Ticket, TicketEvent, AdminEvent
from test_postgres import pg_app
from test_reception_reviews import clock

sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import local_demo as demo
import refresh_erode_demo as refresh_module

@pytest.fixture(params=['application','pg_app'])
def hospital(request,monkeypatch):
    app=request.getfixturevalue(request.param)
    # Both fixtures are disposable: memory SQLite or random schema in *_test DB.
    with app.app_context():
        assert app.testing
        if db.engine.dialect.name=='postgresql':
            from sqlalchemy import text
            assert db.engine.url.database.endswith('_test')
            assert db.session.execute(text('SELECT current_schema()')).scalar().startswith('test_')
        db.drop_all();db.create_all()
    profile={'gateway_user':'test-gateway','gateway_password':secrets.token_urlsafe(32),'seed_customer_id':secrets.token_hex(16),
             'accounts':{role:{'username':f'{role}_refresh','password':secrets.token_urlsafe(28)} for role in ('owner','doctor','receptionist')}}
    saturday=datetime(2026,10,10,4,tzinfo=timezone.utc)
    clock(monkeypatch,saturday)
    class SeedClock(datetime):
        @classmethod
        def now(cls,tz=None):return saturday.astimezone(tz) if tz else saturday.replace(tzinfo=None)
    monkeypatch.setattr(demo,'datetime',SeedClock)
    demo.seed(app,profile)
    clock(monkeypatch,datetime(2026,10,12,4,tzinfo=timezone.utc))
    return app,profile

@pytest.mark.postgres
def test_monday_refresh_keeps_history_and_is_repeatable(hospital,tmp_path):
    app,profile=hospital
    with app.app_context():
        old={t.id:(t.token,t.business_date,t.created_at,t.request_key) for t in Ticket.query.all()}
        events={e.id:(e.ticket_id,e.event_type,e.timestamp) for e in TicketEvent.query.all()}
    dry=refresh_module.refresh(app,profile,date(2026,10,12))
    assert dry['dry_run'] and dry['carryover_tickets']==6 and dry['existing_tickets']==15
    with pytest.raises(RuntimeError,match='Finish the prior-day'):
        refresh_module.refresh(app,profile,date(2026,10,12),dry_run=False)
    backups=[]
    def backup(_):
        with app.app_context():assert Ticket.query.count()==15 and TicketEvent.query.count()==34
        path=tmp_path/'verified-test-backup.dump';path.write_bytes(b'test backup stand-in');backups.append(path);return path
    result=refresh_module.refresh(app,profile,date(2026,10,12),dry_run=False,resolve_carryover=True,backup=backup)
    assert len(backups)==1 and result['fixture_counts']==demo.EXPECTED and result['total_tickets']==30
    assert result['metrics']['completed_today']==13 and result['metrics']['skipped_today']==2
    with app.app_context():
        for tid,values in old.items():
            ticket=db.session.get(Ticket,tid)
            assert (ticket.token,ticket.business_date,ticket.created_at,ticket.request_key)==values
        for eid,values in events.items():
            event=db.session.get(TicketEvent,eid)
            assert (event.ticket_id,event.event_type,event.timestamp)==values
        before=(Ticket.query.count(),TicketEvent.query.count(),AdminEvent.query.count())
    again=refresh_module.refresh(app,profile,date(2026,10,12),dry_run=False,resolve_carryover=True,backup=lambda _:pytest.fail('Idempotent refresh must not back up or reseed'))
    assert again['already_refreshed']
    with app.app_context():assert before==(Ticket.query.count(),TicketEvent.query.count(),AdminEvent.query.count())

@pytest.mark.postgres
def test_refresh_backup_failure_and_future_date_change_nothing(hospital):
    app,profile=hospital
    with pytest.raises(AssertionError,match='actual business-local date'):
        refresh_module.refresh(app,profile,date(2026,10,13),dry_run=False,resolve_carryover=True)
    def failure(_):raise RuntimeError('Backup unavailable')
    with pytest.raises(RuntimeError,match='Backup unavailable'):
        refresh_module.refresh(app,profile,date(2026,10,12),dry_run=False,resolve_carryover=True,backup=failure)
    with app.app_context():
        assert Ticket.query.count()==15 and TicketEvent.query.count()==34
        assert not AdminEvent.query.filter(AdminEvent.action.like('ERODE_DEMO_REFRESH_%')).count()
        assert Ticket.query.filter_by(status='CALLED').one().display_number=='E010'
