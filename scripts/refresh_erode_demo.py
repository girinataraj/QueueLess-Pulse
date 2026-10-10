"""Explicit synthetic-only date refresh. No deletion, timestamp rewriting or hosted DB."""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys
import uuid

import local_demo as demo

def backup_database(profile):
    """Verify the cluster identity again immediately before making a private backup."""
    import psycopg2
    assert profile['host']=='127.0.0.1' and profile['database']==demo.DATABASE
    assert 55433<=profile['port']<=55533
    connection=psycopg2.connect(host=profile['host'],port=profile['port'],dbname=profile['database'],
                              user=profile['admin_role'],password=profile['admin_password'])
    try:
        with connection.cursor() as cursor:
            cursor.execute('SHOW data_directory')
            assert Path(cursor.fetchone()[0]).resolve()==(demo.PRIVATE/'postgres18-data').resolve()
            cursor.execute('SELECT current_database(),host(inet_server_addr()),inet_server_port()')
            assert cursor.fetchone()==(demo.DATABASE,'127.0.0.1',profile['port'])
    finally:connection.close()
    from datetime import datetime, timezone
    folder=demo.PRIVATE/'backups';folder.mkdir(exist_ok=True);demo.protect(folder,True)
    path=folder/('erode-before-refresh-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.dump')
    demo.run_pg('pg_dump','-h',profile['host'],'-p',profile['port'],'-U',profile['role'],'-d',profile['database'],
                '--format=custom','--schema=public','--file',path,
                environment=dict(os.environ,PGPASSWORD=profile['database_password']))
    demo.protect(path)
    listing=demo.run_pg('pg_restore','--list',path)
    assert path.stat().st_size>0 and ' TABLE DATA public tickets ' in listing and ' TABLE DATA public ticket_events ' in listing
    return path

def refresh(app,profile,requested_day,dry_run=True,resolve_carryover=False,backup=backup_database):
    """Use ordinary queue transitions; fail closed on unrelated or current-day data."""
    from models import db, Business, Branch, Service, Staff, Membership, ServiceAssignment, Ticket, AdminEvent
    from universal import business_day, statistics
    with app.app_context():
        assert Business.query.count()==Branch.query.count()==Service.query.count()==1, 'Expected exactly one fictional demo tenant'
        business=Business.query.one();branch=Branch.query.one();service=Service.query.one()
        assert (business.slug,business.name,branch.name,service.name,service.prefix)==(
            demo.SLUG,'Erode Eye Clinic — DEMO','Main Reception','Eye Consultation','E')
        today,_,_=business_day(business)
        assert requested_day==today, 'Refresh only the actual business-local date; future/backdated records are forbidden'
        bid,sid=business.id,service.id
        marker='ERODE_DEMO_REFRESH_'+str(today)
        done=AdminEvent.query.filter_by(business_id=bid,action=marker).first()
        if done:return {'already_refreshed':True,'business_date':str(today),'metrics':statistics(bid)}
        started=AdminEvent.query.filter_by(business_id=bid,action=marker+'_START').first()
        current=Ticket.query.filter_by(service_id=sid,business_date=today).all()
        if current and not started:
            raise RuntimeError('Current-day tickets already exist. Preserve the active demonstration; do not reseed it.')
        for role in ('owner','doctor','receptionist'):
            user=Staff.query.filter_by(username=profile['accounts'][role]['username'],is_active=True).one()
            membership=Membership.query.filter_by(staff_id=user.id,business_id=bid,is_active=True).one()
            assert membership.role==('owner' if role=='owner' else 'staff')
            assignments=[a.service_id for a in ServiceAssignment.query.filter_by(membership_id=membership.id)]
            if role=='doctor':assert assignments==[sid]
            if role=='receptionist':assert assignments==[]
            if role=='owner':owner_id=user.id
        old=Ticket.query.filter(Ticket.service_id==sid,Ticket.business_date<today,Ticket.status.in_(('WAITING','CALLED'))).order_by(Ticket.id).all()
        plan={'business_date':str(today),'carryover_tickets':len(old),'new_fixture':demo.EXPECTED,
              'existing_tickets':Ticket.query.count(),'dry_run':dry_run,
              'note':'Carry-over completion uses the real current timestamp and increases today\'s reviewed total.'}
        if dry_run:return plan
        if old and not resolve_carryover:
            raise RuntimeError('Finish the prior-day called/waiting tickets first, or explicitly pass --resolve-carryover to review them through the Doctor workflow.')
        # Verify that any interrupted refresh contains only its own idempotent requests.
        keys={str(uuid.uuid5(uuid.NAMESPACE_URL,f'{demo.DATABASE}:{today}:refresh:{n}')) for n in range(1,16)}
        assert all(t.request_key in keys for t in current), 'Unexpected current-day patient data: preserve it and stop'
        path=backup(profile) # Mandatory, verified backup before even a refresh marker is inserted.
        assert path and Path(path).is_file(), 'Backup missing; no records changed'
        if not started:
            db.session.add(AdminEvent(business_id=bid,staff_id=owner_id,action=marker+'_START',details=json.dumps({'date':str(today),'backup':Path(path).name})))
            db.session.commit()
    doctor=demo.LocalClient(app,profile)
    assert doctor.post('/api/v1/auth/login',**profile['accounts']['doctor']).status_code==200
    # Finish older tickets in FIFO order, including an already-CALLED ticket.
    while True:
        with app.app_context():
            carried=Ticket.query.filter(Ticket.service_id==sid,Ticket.business_date<today,Ticket.status.in_(('WAITING','CALLED'))).order_by(Ticket.id).first()
            if not carried:break
            tid,status=carried.id,carried.status
        if status=='WAITING':
            assert doctor.post(f'/api/v1/staff/services/{sid}/call').status_code==200
            assert doctor.get('/api/v1/staff/queues').json[0]['called']['id']==tid
        assert doctor.post(f'/api/v1/staff/tickets/{tid}/complete').status_code==200
    patient=demo.LocalClient(app,profile)
    with patient.client.session_transaction() as session:session['owner_id']=profile['seed_customer_id']
    for number in range(1,16):
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'{demo.DATABASE}:{today}:refresh:{number}'))
        issued=patient.post(f'/api/v1/services/{sid}/tickets',request_key=key)
        assert issued.status_code==201
        with app.app_context():ticket=Ticket.query.filter_by(token=issued.json['token']).one();tid,status=ticket.id,ticket.status
        target='COMPLETED' if number<=7 else 'SKIPPED' if number<=9 else 'CALLED' if number==10 else 'WAITING'
        if status==target:continue
        assert status in ('WAITING','CALLED'), 'Demonstration actions already changed a seed ticket; preserve it and stop'
        if status=='WAITING' and target!='WAITING':
            assert doctor.post(f'/api/v1/staff/services/{sid}/call').status_code==200
            assert doctor.get('/api/v1/staff/queues').json[0]['called']['id']==tid
        if target in ('COMPLETED','SKIPPED'):
            action='complete' if target=='COMPLETED' else 'skip'
            assert doctor.post(f'/api/v1/staff/tickets/{tid}/{action}').status_code==200
    with app.app_context():
        fixture=Ticket.query.filter(Ticket.service_id==sid,Ticket.business_date==today,Ticket.request_key.in_(keys)).all()
        assert len(fixture)==15
        actual={key:sum(t.status==key.upper() for t in fixture) for key in demo.EXPECTED}
        assert actual==demo.EXPECTED
        db.session.add(AdminEvent(business_id=bid,staff_id=owner_id,action=marker,details=json.dumps({'date':str(today),'backup':Path(path).name,'seed_count':15})))
        db.session.commit()
        return {'business_date':str(today),'fixture_counts':actual,'total_tickets':Ticket.query.count(),'metrics':statistics(bid),'backup':str(path),'already_refreshed':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',required=True,type=date.fromisoformat)
    parser.add_argument('--apply',action='store_true',help='Make the explicitly reviewed refresh; default is read-only.')
    parser.add_argument('--resolve-carryover',action='store_true',help='Complete older outstanding synthetic tickets through normal Doctor transitions.')
    args=parser.parse_args()
    profile=demo.load_profile();demo.start_postgres(profile);app=demo.make_app(profile)
    lock=demo.PRIVATE/'refresh-in-progress.lock'
    if args.apply:
        # An interrupted process leaves an explicit lock for inspection, never an automatic bypass.
        with lock.open('x',encoding='utf-8') as target:target.write(str(os.getpid()))
        demo.protect(lock)
    try:result=refresh(app,profile,args.date,dry_run=not args.apply,resolve_carryover=args.resolve_carryover)
    finally:
        if args.apply:lock.unlink()
    demo.write_access(app,profile)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as error:
        demo.PRIVATE.mkdir(exist_ok=True)
        import traceback
        path=demo.PRIVATE/'refresh-error.txt';path.write_text(traceback.format_exc(),encoding='utf-8');demo.protect(path)
        print('Refresh stopped safely: '+type(error).__name__+'. Details are in the ignored private file.',file=sys.stderr)
        sys.exit(1)
