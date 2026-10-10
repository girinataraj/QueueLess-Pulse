"""Isolated localhost-only PostgreSQL demo. Never uses inherited DATABASE_URL."""
import argparse
import base64
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.tmp'
PROFILE = PRIVATE / 'local-demo-private.json'
PG_BIN = Path(r'C:\Program Files\PostgreSQL\18\bin')
DATABASE = 'queueless_erode_demo'
SLUG = 'erode-eye-clinic-demo'
EXPECTED = {'waiting': 5, 'called': 1, 'completed': 7, 'skipped': 2}

def protect(path, directory=False):
    if os.name != 'nt':
        path.chmod(0o700 if directory else 0o600)
        return
    sid = subprocess.check_output(['whoami','/user','/fo','csv','/nh'],text=True).strip().split(',')[-1].strip('"')
    access = '(OI)(CI)(F)' if directory else '(F)'
    subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',f'*{sid}:{access}'],check=True,capture_output=True)

def load_profile():
    PRIVATE.mkdir(exist_ok=True)
    protect(PRIVATE, True)
    if PROFILE.exists():
        return json.loads(PROFILE.read_text())
    port = None
    for candidate in range(55433,55534):
        with socket.socket() as probe:
            try: probe.bind(('127.0.0.1',candidate))
            except OSError: continue
            port = candidate
            break
    if port is None: raise RuntimeError('No free local PostgreSQL demo port')
    data = {'database':DATABASE,'host':'127.0.0.1','port':port,'role':'queueless_demo',
            'database_password':secrets.token_urlsafe(36), 'admin_role':'queueless_demo_admin',
            'admin_password':secrets.token_urlsafe(36),'session_secret':secrets.token_hex(48),
            'gateway_user':'local-reviewer','gateway_password':secrets.token_urlsafe(36),
            'seed_customer_id':secrets.token_hex(16),'origin':'http://127.0.0.1:5000',
            'accounts':{role:{'username':f'erode_{role}_demo','password':secrets.token_urlsafe(28)} for role in ('owner','doctor','receptionist')}}
    PROFILE.write_text(json.dumps(data,indent=2),encoding='utf-8')
    protect(PROFILE)
    return data

def run_pg(name, *args, environment=None):
    # On Windows, the detached server can inherit pg_ctl's pipe handles. Avoid
    # waiting for server shutdown just to collect the startup command's output.
    output = {'stdout':subprocess.DEVNULL,'stderr':subprocess.DEVNULL} if name=='pg_ctl' else {'capture_output':True}
    completed = subprocess.run([str(PG_BIN/(name+'.exe')),*map(str,args)],env=environment,
                               text=True,**output)
    if completed.returncode:
        # Do not emit SQL, passwords, connection strings or inherited environment.
        raise RuntimeError(f'Local PostgreSQL {name} failed (exit {completed.returncode}); private logs in .tmp')
    return completed.stdout or ''

def start_postgres(profile):
    assert profile['host']=='127.0.0.1' and profile['database']==DATABASE
    assert 55433<=profile['port']<=55533
    directory = PRIVATE/'postgres18-data'
    if not (directory/'PG_VERSION').exists():
        pwfile = PRIVATE/'bootstrap-postgres-password.txt'
        pwfile.write_text(profile['admin_password'],encoding='utf-8');protect(pwfile)
        run_pg('initdb','-D',directory,'-U',profile['admin_role'],'--auth-host=scram-sha-256',
               '--auth-local=scram-sha-256','--pwfile',pwfile,'--encoding=UTF8','--locale=C')
        pwfile.unlink()
    assert (directory/'PG_VERSION').read_text().strip()=='18'
    settings=directory/'queueless-local.conf'
    settings.write_text("listen_addresses = '127.0.0.1'\nport = "+str(profile['port'])+"\npassword_encryption = 'scram-sha-256'\n",encoding='utf-8')
    config=directory/'postgresql.conf'
    include="include_if_exists = 'queueless-local.conf'"
    if include not in config.read_text(encoding='utf-8'):
        with config.open('a',encoding='utf-8') as target:target.write('\n'+include+'\n')
    status = subprocess.run([str(PG_BIN/'pg_ctl.exe'),'-D',str(directory),'status'],capture_output=True)
    if status.returncode:
        run_pg('pg_ctl','-D',directory,'-l',PRIVATE/'postgres18-server.log','-o',
               f'-h 127.0.0.1 -p {profile["port"]} -c password_encryption=scram-sha-256','start','-w')
    import psycopg2
    from psycopg2 import sql
    admin = psycopg2.connect(host='127.0.0.1',port=profile['port'],dbname='postgres',
                            user=profile['admin_role'],password=profile['admin_password'])
    try:
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute('SHOW data_directory')
            assert Path(cursor.fetchone()[0]).resolve()==directory.resolve(), 'Unrecognized PostgreSQL cluster'
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(profile['role'],))
            if not cursor.fetchone():
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD %s').format(sql.Identifier(profile['role'])),(profile['database_password'],))
            cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DATABASE,))
            if not cursor.fetchone():
                cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(DATABASE),sql.Identifier(profile['role'])))
                cursor.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(DATABASE)))
    finally:
        admin.close()
    environment = dict(os.environ,PGPASSWORD=profile['database_password'])
    proof = run_pg('psql','-h','127.0.0.1','-p',profile['port'],'-U',profile['role'],'-d',DATABASE,
                   '-X','-A','-t','-c','SELECT current_database(),inet_server_addr(),inet_server_port(),current_user;',environment=environment).strip()
    assert proof==f'{DATABASE}|127.0.0.1|{profile["port"]}|{profile["role"]}'
    return directory

def verify_postgres(profile):
    """Save connection/authentication evidence without connection secrets."""
    import psycopg2
    connection=psycopg2.connect(host=profile['host'],port=profile['port'],dbname=DATABASE,
                              user=profile['admin_role'],password=profile['admin_password'],connect_timeout=5)
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(),host(inet_server_addr()),inet_server_port(),version()')
            database,host,port,version=cursor.fetchone()
            cursor.execute('SHOW listen_addresses');listen=cursor.fetchone()[0]
            cursor.execute('SHOW password_encryption');encryption=cursor.fetchone()[0]
            cursor.execute("SELECT auth_method FROM pg_hba_file_rules WHERE type LIKE 'host%' AND error IS NULL")
            methods=[r[0] for r in cursor.fetchall()]
            cursor.execute("SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolpassword LIKE 'SCRAM-SHA-256$%%' FROM pg_authid WHERE rolname=%s",(profile['role'],))
            superuser,createdb,createrole,replication,scram=cursor.fetchone()
            assert listen=='127.0.0.1' and encryption=='scram-sha-256' and methods and set(methods)=={'scram-sha-256'}
            assert not any((superuser,createdb,createrole,replication)) and scram
            evidence={'database':database,'host':host,'port':port,'application_role':profile['role'],
                      'server_version':version,'listen_addresses':listen,'host_authentication':methods,
                      'stored_application_password_is_scram':scram,'application_role_is_superuser':superuser,
                      'psql_verified':True,'sqlalchemy_verified':True,'data_directory':str(PRIVATE/'postgres18-data')}
            folder=ROOT/'evidence';folder.mkdir(exist_ok=True)
            (folder/'local-postgres-verification.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    finally:connection.close()

def database_url(profile):
    from sqlalchemy.engine import URL
    assert profile['database']==DATABASE and profile['host']=='127.0.0.1'
    return URL.create('postgresql+psycopg2',username=profile['role'],password=profile['database_password'],
                      host='127.0.0.1',port=profile['port'],database=DATABASE)

def make_app(profile, origin=None, schema='public'):
    from sqlalchemy import create_engine, text
    uri = database_url(profile)
    options = {'pool_pre_ping':True,'connect_args':{'options':'-csearch_path='+schema}}
    assert schema=='public' or (schema.startswith('local_demo_check_') and all(c.isalnum() or c=='_' for c in schema))
    engine = create_engine(uri,**options)
    with engine.connect() as connection:
        dbname,host,port,role = connection.execute(text('SELECT current_database(),host(inet_server_addr()),inet_server_port(),current_user')).one()
        assert (dbname,host,port,role)==(DATABASE,'127.0.0.1',profile['port'],profile['role'])
        assert connection.execute(text("SELECT current_setting('server_version_num')::int")).scalar()>=180000
    engine.dispose()
    # Override inherited Render/preview settings BEFORE importing the application.
    origin = origin or profile['origin']
    host = origin.split('://',1)[1].split(':',1)[0]
    os.environ.pop('RENDER',None)
    os.environ.update(APP_ENV='development',DATABASE_URL=uri.render_as_string(hide_password=False),
                      SECRET_KEY=profile['session_secret'],DEMO_MODE='true',
                      DEMO_ACCESS_USER=profile['gateway_user'],DEMO_ACCESS_PASSWORD=profile['gateway_password'],
                      PUBLIC_BASE_URL=origin,TRUSTED_HOSTS=f'127.0.0.1,localhost,{host}')
    sys.path.insert(0,str(ROOT))
    from app import create_app
    app = create_app({'PRODUCTION':False,'DEBUG':False,'TESTING':False,
                      'SQLALCHEMY_DATABASE_URI':uri.render_as_string(hide_password=False),
                      'SQLALCHEMY_ENGINE_OPTIONS':options,'SECRET_KEY':profile['session_secret'],
                      'SESSION_COOKIE_SECURE':False,'DEMO_MODE':True,
                      'DEMO_ACCESS_USER':profile['gateway_user'],'DEMO_ACCESS_PASSWORD':profile['gateway_password'],
                      'PUBLIC_BASE_URL':origin,'TRUSTED_HOSTS':['127.0.0.1','localhost',host],
                      'BUSINESS_TIMEZONE':'Asia/Kolkata','RATE_LIMIT_TRUSTED_PROXY_HOPS':0})
    return app

def configure_lan_http(app):
    """Keep the built SPA usable on temporary LAN HTTP without changing auth."""
    assets=ROOT/'static/local-demo';assets.mkdir(parents=True,exist_ok=True)
    shim=assets/'lan-request-key.js'
    shim.write_text("""// Local HTTP compatibility only; preserve native secure-context implementation.
if (typeof crypto.randomUUID !== 'function') {
  crypto.randomUUID = function () {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    return hex.slice(0,8)+'-'+hex.slice(8,12)+'-'+hex.slice(12,16)+'-'+hex.slice(16,20)+'-'+hex.slice(20);
  };
}
""",encoding='utf-8')
    @app.after_request
    def lan_request_key(response):
        from flask import request
        if request.path.startswith('/app/') and response.status_code==200 and response.mimetype=='text/html':
            response.direct_passthrough=False
            body=response.get_data(as_text=True)
            body=body.replace('<head>','<head><script src="/static/local-demo/lan-request-key.js"></script>',1)
            response.set_data(body)
        return response

def hotspot_tls(address):
    """Short-lived private CA and IP-specific certificate for this local demo."""
    import shutil
    directory=PRIVATE/'hotspot-tls';directory.mkdir(exist_ok=True);protect(directory,True)
    openssl=Path(r'C:\Program Files\Git\usr\bin\openssl.exe')
    ca=directory/'queueless-local-ca.crt';key=directory/'queueless-local-ca.key'
    cert=directory/'hotspot-server.crt';server_key=directory/'hotspot-server.key'
    def execute(*args):
        result=subprocess.run([str(openssl),*map(str,args)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Local certificate generation failed')
    if not ca.exists():
        execute('req','-x509','-newkey','rsa:3072','-nodes','-keyout',key,'-out',ca,
                '-days','2','-sha256','-subj','/CN=QueueLess Pulse Local Demo CA',
                '-addext','basicConstraints=critical,CA:true',
                '-addext','keyUsage=critical,keyCertSign,cRLSign')
        protect(key);protect(ca)
    address_file=directory/'server-address.txt'
    if not cert.exists() or not address_file.exists() or address_file.read_text()!=address:
        csr=directory/'hotspot-server.csr'
        extensions=directory/'server-extensions.cnf'
        extensions.write_text('basicConstraints=critical,CA:false\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=IP:'+address+'\n',encoding='utf-8')
        execute('req','-new','-newkey','rsa:3072','-nodes','-keyout',server_key,'-out',csr,'-subj','/CN='+address)
        execute('x509','-req','-in',csr,'-CA',ca,'-CAkey',key,'-CAcreateserial','-out',cert,
                '-days','2','-sha256','-extfile',extensions)
        address_file.write_text(address,encoding='utf-8')
        protect(server_key);protect(cert)
    assets=ROOT/'static/local-demo';assets.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ca,assets/'QueueLess-Pulse-Hotspot-CA.crt')
    return cert,server_key,ca

class LocalClient:
    def __init__(self, app, profile):
        self.client = app.test_client()
        value = profile['gateway_user']+':'+profile['gateway_password']
        self.headers = {'Authorization':'Basic '+base64.b64encode(value.encode()).decode()}
    def get(self,path):
        return self.client.get(path,headers=self.headers)
    def post(self,path,**fields):
        fields['csrf_token']=self.get('/api/v1/session').get_json()['csrf_token']
        return self.client.post(path,data=fields,headers=self.headers)

def counts(app):
    from models import db,Ticket
    from sqlalchemy import func
    with app.app_context():
        rows=dict(db.session.query(Ticket.status,func.count(Ticket.id)).group_by(Ticket.status).all())
        return {key:rows.get(key.upper(),0) for key in EXPECTED}

def seed(app,profile):
    from models import db,Business,Branch,Service,Staff,Membership,ServiceAssignment,AdminEvent,Ticket,TicketEvent
    from sqlalchemy import inspect, text
    with app.app_context():
        # Database identity was checked in make_app before any schema write.
        db.create_all()
        prior=AdminEvent.query.filter_by(action='LOCAL_DEMO_SEEDED_V1').first()
        if prior:
            assert Business.query.count()==Branch.query.count()==Service.query.count()==1
            doctor=Staff.query.filter_by(username=profile['accounts']['doctor']['username']).one()
            membership=Membership.query.filter_by(staff_id=doctor.id,is_active=True).one()
            assert ServiceAssignment.query.filter_by(membership_id=membership.id).count()==1
            return {'already_seeded':True,'counts':counts(app)}
    owner=LocalClient(app,profile)
    account=profile['accounts']['owner']
    login=owner.post('/api/v1/auth/login',**account)
    if login.status_code==401:
        registered=owner.post('/api/v1/auth/register',**account,confirm_password=account['password'])
        assert registered.status_code==201, 'Owner registration failed'
    else: assert login.status_code==200
    businesses=owner.get('/api/v1/owner/businesses').get_json()
    if not businesses:
        created=owner.post('/api/v1/owner/businesses',name='Erode Eye Clinic — DEMO',slug=SLUG,
                           category='Clinic',timezone='Asia/Kolkata',
                           description='Fictional single-location demonstration. Synthetic queue data only; no hospital affiliation.')
        assert created.status_code==201
        businesses=owner.get('/api/v1/owner/businesses').get_json()
    assert len(businesses)==1 and businesses[0]['slug']==SLUG
    bid=businesses[0]['id'];base=f'/api/v1/owner/businesses/{bid}'
    bundle=owner.get(base).get_json()
    if not bundle['branches']:
        assert owner.post(base+'/branches',name='Main Reception',address='Erode — fictional demo location').status_code==201
    bundle=owner.get(base).get_json();assert len(bundle['branches'])==1
    branch=bundle['branches'][0]['id']
    if not bundle['services']:
        assert owner.post(base+'/services',branch_id=str(branch),name='Eye Consultation',prefix='E',
                          average_minutes='5',counter_label='Doctor 1',is_active='on').status_code==201
    bundle=owner.get(base).get_json();assert len(bundle['services'])==1
    sid=bundle['services'][0]['id']
    for role in ('doctor','receptionist'):
        account=profile['accounts'][role]
        if not any(m['username']==account['username'] for m in bundle['members']):
            assert owner.post(base+'/staff',**account).status_code==201
            bundle=owner.get(base).get_json()
        member=next(m for m in bundle['members'] if m['username']==account['username'])
        fields={'role':'staff','is_active':'on'}
        if role=='doctor': fields['service_ids']=str(sid)
        assert owner.post(base+f'/staff/{member["id"]}/permissions',**fields).status_code==200
    doctor=LocalClient(app,profile)
    assert doctor.post('/api/v1/auth/login',**profile['accounts']['doctor']).status_code==200
    queues=doctor.get('/api/v1/staff/queues').get_json()
    assert len(queues)==1 and queues[0]['id']==sid, 'Doctor has no active assigned queue'
    patient=LocalClient(app,profile)
    with patient.client.session_transaction() as session:
        session['owner_id']=profile['seed_customer_id']
    day=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    for number in range(1,16):
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,f'{DATABASE}:{day}:seed:{number}'))
        issued=patient.post(f'/api/v1/services/{sid}/tickets',request_key=key)
        assert issued.status_code==201
        ticket=issued.get_json()
        with app.app_context():
            tid=Ticket.query.filter_by(token=ticket['token']).one().id
        target='COMPLETED' if number<=7 else 'SKIPPED' if number<=9 else 'CALLED' if number==10 else 'WAITING'
        if ticket['status']==target:continue
        assert ticket['status']=='WAITING'
        if target!='WAITING':
            assert doctor.post(f'/api/v1/staff/services/{sid}/call').status_code==200
            live=doctor.get('/api/v1/staff/queues').get_json()[0]
            assert live['called']['id']==tid
            if target in ('COMPLETED','SKIPPED'):
                action='complete' if target=='COMPLETED' else 'skip'
                assert doctor.post(f'/api/v1/staff/tickets/{tid}/{action}').status_code==200
    assert counts(app)==EXPECTED
    with app.app_context():
        assert all(str(t.business_date)==day for t in Ticket.query.all())
        assert TicketEvent.query.count()==34  # 15 created + 10 called + 9 terminal events.
        user=Staff.query.filter_by(username=profile['accounts']['owner']['username']).one()
        db.session.add(AdminEvent(business_id=bid,staff_id=user.id,action='LOCAL_DEMO_SEEDED_V1',details='Synthetic fixture '+day))
        db.session.commit()
    return {'already_seeded':False,'counts':counts(app)}

def create_reception_assets(app,profile,origin=None,prefix=''):
    owner=LocalClient(app,profile)
    assert owner.post('/api/v1/auth/login',**profile['accounts']['owner']).status_code==200
    business=owner.get('/api/v1/owner/businesses').get_json()[0]
    bundle=owner.get(f'/api/v1/owner/businesses/{business["id"]}').get_json()
    sid=bundle['services'][0]['id'];bid=business['id']
    assets=ROOT/'static/local-demo';assets.mkdir(parents=True,exist_ok=True)
    qr=owner.get(f'/owner/business/{bid}/qr.png?ui=react&service_id={sid}&download=1')
    assert qr.status_code==200
    assert not prefix or (prefix.startswith('check-') and all(c.isalnum() or c=='-' for c in prefix))
    qr_path=assets/(prefix+'eye-consultation-qr.png')
    qr_path.write_bytes(qr.data)
    origin=origin or profile['origin'];patient=f'{origin}/app/b/{SLUG}/service/{sid}'
    reception=f'{origin}/static/local-demo/{prefix}reception.html';display=f'{origin}/app/b/{SLUG}/display'
    (assets/(prefix+'reception.js')).write_text("""async function refresh() {
  try {
    const response=await fetch('/api/v1/display/erode-eye-clinic-demo',{cache:'no-store'});
    if(!response.ok) throw new Error('Display unavailable');
    const rows=await response.json();
    if(rows.length!==1) throw new Error('Unexpected service configuration');
    document.querySelector('.display-token').textContent=rows[0].currently_called;
    document.querySelector('#waiting').textContent=rows[0].waiting_count+' waiting';
    document.querySelector('[role=status]').textContent='Connected · live database counts';
  } catch(error) {
    document.querySelector('[role=status]').textContent='Connection lost — displayed values may be stale';
  }
}
refresh();setInterval(refresh,3000);
""",encoding='utf-8')
    (assets/(prefix+'reception.html')).write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Erode Eye Clinic — DEMO Reception</title><link rel="stylesheet" href="/static/css/style.css"><script src="{prefix}reception.js" defer></script></head><body><main class="container main-content"><h1>Erode Eye Clinic — DEMO</h1><p>Erode · Main Reception · Eye Consultation. Fictional data only.</p><p>Scan the service QR. The private local demo gateway is required on the phone.</p><img alt="Eye Consultation service QR" src="{html.escape(qr_path.name)}" width="260" height="260"><p><a href="{html.escape(patient)}">Open patient queue</a> · <a href="{html.escape(display)}">Open full display</a></p><section class="card display-card" aria-label="Live reception queue"><h2>Eye Consultation</h2><p>Main Reception · Doctor 1</p><div class="display-token">Loading…</div><p id="waiting">Loading queue count…</p><p role="status" aria-live="polite">Connecting…</p></section></main></body></html>''',encoding='utf-8')
    urls={'reception':reception,'patient':patient,'display':display,'owner':origin+'/app/owner/login',
          'doctor':origin+'/app/staff/login','history':origin+f'/app/owner/business/{bid}/history?status=COMPLETED'}
    return urls,qr_path

def write_access(app,profile):
    urls,qr_path=create_reception_assets(app,profile)
    reception=urls['reception'];display=urls['display'];patient=urls['patient']
    profile['urls']=urls;PROFILE.write_text(json.dumps(profile,indent=2),encoding='utf-8');protect(PROFILE)
    lines=['# PRIVATE — Local Erode Eye Clinic demo access','',
           'LOCAL only. Generated secrets are separate from the hosted demo. Fictional records only.',
           '', '## Browser gateway', '', 'Username: '+profile['gateway_user'],'Password: '+profile['gateway_password'],'']
    for role in ('owner','doctor','receptionist'):
        account=profile['accounts'][role]
        lines += ['## '+role.title(),'', 'Username: '+account['username'],'Password: '+account['password'],'']
    lines += ['Receptionist has an ACTIVE Staff membership with no clinical service assignment and no Owner rights. Use the Reception link and printed Owner-generated QR; application sign-in is optional for that read-only view.',
              'Doctor has an ACTIVE membership and the Eye Consultation assignment.', '', '## Interface URLs','']
    lines += [name+': '+url for name,url in urls.items()]
    lines += ['', 'QR image: '+str(qr_path),'',
              'Use separate browser profiles for Owner and Doctor, or log out before switching.',
              'Initial called E010 must be completed/skipped before Call Next. Waiting E011–E015 precede a newly joined E016 in FIFO order.',
              '', '## pgAdmin 4 — new separate local server', '',
              'Name: QueueLess Pulse — LOCAL PostgreSQL 18','Host: 127.0.0.1','Port: '+str(profile['port']),
              'Maintenance database: '+DATABASE,'Username: '+profile['role'],
              'Password: '+profile['database_password'],'SSL mode: disable (loopback-only local instance)',
              'Data directory: '+str(PRIVATE/'postgres18-data'),
              'Do not edit or connect this demo to the older Digital ocean server.']
    access=PRIVATE/'PRIVATE_LOCAL_DEMO_ACCESS.md';access.write_text('\n'.join(lines)+'\n',encoding='utf-8');protect(access)
    receptor=PRIVATE/'PRIVATE_RECEPTION_ACCESS.md'
    receptor.write_text('# PRIVATE — Local Reception\n\nGateway username: '+profile['gateway_user']+'\nGateway password: '+profile['gateway_password']+'\n\nReception: '+reception+'\nDisplay: '+display+'\nPatient: '+patient+'\n\nShow the generated QR; do not distribute Owner or Doctor credentials.\n',encoding='utf-8');protect(receptor)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['setup','start','info','stop-postgres'])
    parser.add_argument('--lan-address')
    parser.add_argument('--https',action='store_true')
    args=parser.parse_args()
    profile=load_profile()
    if args.action=='stop-postgres':
        run_pg('pg_ctl','-D',PRIVATE/'postgres18-data','stop','-m','fast');print('Stopped only the isolated local-demo PostgreSQL cluster.');return
    profile['origin']='http://127.0.0.1:5000'
    if args.lan_address:
        address=ipaddress.ip_address(args.lan_address)
        assert address.version==4 and address.is_private and not address.is_loopback
        with socket.socket() as probe:probe.bind((str(address),0))
        profile['origin']=f'{"https" if args.https else "http"}://{address}:5000'
    assert not args.https or args.lan_address, 'HTTPS mode requires a specific LAN address'
    start_postgres(profile)
    app=make_app(profile)
    tls=None
    if args.https:
        cert,key,ca=hotspot_tls(args.lan_address)
        tls=(str(cert),str(key))
        app.config['SESSION_COOKIE_SECURE']=True
    elif args.lan_address:configure_lan_http(app)
    verify_postgres(profile)
    seeded=seed(app,profile)
    write_access(app,profile)
    if args.action!='start':
        print(json.dumps({'database':DATABASE,'host':'127.0.0.1','port':profile['port'],'role':profile['role'],
                          'psql_verified':True,'sqlalchemy_verified':True,'scram':True,**seeded,
                          'url':profile['origin']+'/app/','private_access_file':str(PRIVATE/'PRIVATE_LOCAL_DEMO_ACCESS.md')}));return
    assert (ROOT/'frontend/dist/index.html').exists(),'Build the approved React assets first'
    from werkzeug.serving import make_server, WSGIRequestHandler
    class PrivateHandler(WSGIRequestHandler):
        def log_request(self,*args,**kwargs): pass  # Never log ticket recovery URLs or credentials.
    bind=args.lan_address or '127.0.0.1'
    print('Local demo ready: '+profile['origin']+'/app/ . Private access file: '+str(PRIVATE/'PRIVATE_LOCAL_DEMO_ACCESS.md'),flush=True)
    make_server(bind,5000,app,threaded=True,request_handler=PrivateHandler,ssl_context=tls).serve_forever()

if __name__=='__main__':
    try:main()
    except Exception as error:
        import traceback
        PRIVATE.mkdir(exist_ok=True)
        diagnostic=PRIVATE/'local-demo-error.txt'
        diagnostic.write_text(traceback.format_exc(),encoding='utf-8');protect(diagnostic)
        print('Local demo operation failed: '+type(error).__name__+'. No credentials emitted.',file=sys.stderr)
        sys.exit(1)
