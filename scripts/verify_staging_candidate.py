"""Run all regression and Erode acceptance tests in disposable PostgreSQL schemas.

Requires TEST_DATABASE_URL for an isolated database ending _test; never starts a
cluster or uses the localhost demo's public schema. Credentials stay in memory.
"""
import json
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
from threading import Thread
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]


def main():
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from werkzeug.serving import make_server, WSGIRequestHandler
    import local_demo as demo
    import pytest
    os.chdir(ROOT)
    parser = argparse.ArgumentParser()
    parser.add_argument('--connection-profile', type=Path, help='Private integrated-demo profile; selects ONLY its separate _test database')
    args = parser.parse_args()
    if args.connection_profile:
        from sqlalchemy.engine import URL
        private = json.loads(args.connection_profile.read_text())
        if (private['host'],private['port'],private['database']) != ('127.0.0.1',55434,'queueless_erode_integration'):
            raise SystemExit('Unrecognized private local test connection profile')
        os.environ['TEST_DATABASE_URL'] = URL.create('postgresql+psycopg2', username=private['role'],
            password=private['database_password'],host='127.0.0.1',port=55434,
            database='queueless_erode_integration_test').render_as_string(hide_password=False)
    url = make_url(os.environ['TEST_DATABASE_URL'])
    if url.get_backend_name() != 'postgresql' or not url.database.endswith('_test'):
        raise SystemExit('Requires an explicitly isolated PostgreSQL database ending _test')
    if url.host != '127.0.0.1':
        raise SystemExit('Local Erode acceptance requires the isolated loopback test database')
    for name in ('DATABASE_URL','RENDER','APP_ENV','APP_STAGE','DEMO_MODE','PUBLIC_BASE_URL','TRUSTED_HOSTS',
                 'LOCAL_DEMO_LAN_TEST_ADDRESS','LOCAL_DEMO_LAN_TEST_HTTPS'):
        os.environ.pop(name, None)
    os.environ['RUN_LOCAL_DEMO_ACCEPTANCE'] = '1'
    # Capture clean default configuration before local_demo.make_app sets its
    # private environment. Regression fixtures do not inherit the outer gate.
    from app import create_app
    os.environ.setdefault('PLAYWRIGHT_EXECUTABLE_PATH', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    schema = 'local_demo_check_candidate_'+uuid.uuid4().hex
    engine = create_engine(url)
    with engine.begin() as connection:
        assert connection.execute(text('SELECT current_database(),host(inet_server_addr())')).one() == (url.database, '127.0.0.1')
        connection.execute(text('CREATE SCHEMA "'+schema+'"'))
        initial_schemas = set(connection.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'local_demo_check_%'")).scalars())
    profile = dict(database=url.database, host=url.host, port=url.port, role=url.username,
                   database_password=url.password, session_secret=secrets.token_hex(48),
                   gateway_user='candidate-evaluator', gateway_password=secrets.token_urlsafe(36),
                   seed_customer_id=secrets.token_hex(16), origin='http://127.0.0.1:5002',
                   accounts={role:dict(username='candidate_'+role, password=secrets.token_urlsafe(28))
                             for role in ('owner','doctor','receptionist')})
    demo.DATABASE = url.database
    demo.load_profile = lambda: profile
    original_make_app = demo.make_app
    def make_app(profile, origin=None, schema='public'):
        return original_make_app(profile, origin, schema if schema != 'public' else fixture_schema)
    fixture_schema = schema
    demo.make_app = make_app
    app = demo.make_app(profile)
    demo.seed(app,profile)
    from models import Business
    with app.app_context(): business_id = Business.query.one().id
    profile['urls'] = {'reception':profile['origin']+'/app/staff/reception',
                       'history':profile['origin']+f'/app/owner/business/{business_id}/history?status=COMPLETED'}
    class QuietHandler(WSGIRequestHandler):
        def log_request(self,*args,**kwargs): pass
    server = make_server('127.0.0.1',5002,app,threaded=True,request_handler=QuietHandler)
    thread = Thread(target=server.serve_forever,daemon=True)
    thread.start()
    node = Path(shutil.which('node'))
    npx = node.parent/'node_modules/npm/bin/npx-cli.js'
    pnpm = [str(node),str(npx),'--yes','pnpm@11.25.0']
    (ROOT/'evidence').mkdir(exist_ok=True)
    try:
        for command in ([sys.executable,'scripts/generate_contracts.py','--check'],
                        pnpm+['--dir','frontend','run','typecheck'],pnpm+['--dir','frontend','run','lint'],
                        pnpm+['--dir','frontend','run','test','--reporter=default','--reporter=junit','--outputFile=../evidence/frontend.xml'],
                        pnpm+['--dir','frontend','run','build'],pnpm+['--dir','frontend','audit','--audit-level=low'],
                        pnpm+['--dir','mobile','test'],pnpm+['--dir','mobile','audit','--audit-level=low']):
            if subprocess.run(command).returncode: raise SystemExit('Candidate check failed; no check was bypassed')
        result = pytest.main(['-q','tests','scripts/verify_local_demo_browser.py','--junitxml=evidence/candidate.xml'])
        if result: raise SystemExit(int(result))
        suite = ET.parse('evidence/candidate.xml').getroot().find('testsuite')
        assert all(suite.attrib[k]=='0' for k in ('failures','errors','skipped'))
        report = dict(python_passed=int(suite.attrib['tests']), python_failed=0, python_skipped=0,
                      frontend_passed=len(list(ET.parse('evidence/frontend.xml').getroot().iter('testcase'))),
                      database=url.database, acceptance_fixture_schema=fixture_schema, physical_android='deferred',
                      staging_deployment='awaiting explicit approval')
        (ROOT/'evidence/candidate-gate.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
        from models import db
        with app.app_context(): db.session.remove(); db.engine.dispose()
        with engine.begin() as connection:
            current_schemas = set(connection.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'local_demo_check_%'")).scalars())
            for owned_schema in (current_schemas-initial_schemas)|{fixture_schema}:
                assert owned_schema.startswith('local_demo_check_') and all(c.isalnum() or c=='_' for c in owned_schema)
                connection.execute(text('DROP SCHEMA "'+owned_schema+'" CASCADE'))
        engine.dispose()


if __name__=='__main__': main()
