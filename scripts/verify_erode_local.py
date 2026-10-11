"""Run the complete local gate without putting database credentials in commands."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import local_demo as demo

def main():
    os.chdir(demo.ROOT)
    profile=demo.load_profile()
    demo.start_postgres(profile);demo.make_app(profile);demo.verify_postgres(profile)
    from sqlalchemy.engine import URL
    from sqlalchemy import create_engine,text
    uri=URL.create('postgresql+psycopg2',username=profile['role'],password=profile['database_password'],
                   host='127.0.0.1',port=profile['port'],database='queueless_erode_integration_test')
    assert profile['database']=='queueless_erode_integration' and profile['port']==55434
    engine=create_engine(uri)
    with engine.connect() as connection:
        assert connection.execute(text('SELECT current_database(),host(inet_server_addr()),inet_server_port()')).one()==('queueless_erode_integration_test','127.0.0.1',55434)
    engine.dispose()
    env=dict(os.environ,TEST_DATABASE_URL=uri.render_as_string(hide_password=False),RUN_LOCAL_DEMO_ACCEPTANCE='1',
             PLAYWRIGHT_EXECUTABLE_PATH=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    for name in ('DATABASE_URL','DEMO_MODE','DEMO_ACCESS_USER','DEMO_ACCESS_PASSWORD','RENDER','PUBLIC_BASE_URL','TRUSTED_HOSTS','LOCAL_DEMO_LAN_TEST_ADDRESS','LOCAL_DEMO_LAN_TEST_HTTPS'):
        env.pop(name,None)
    node=Path(shutil.which('node'));npx=node.parent/'node_modules/npm/bin/npx-cli.js';assert npx.is_file()
    pnpm=[str(node),str(npx),'--yes','pnpm@11.25.0','--dir','frontend']
    commands=[
        [sys.executable,'scripts/generate_contracts.py','--check'],
        pnpm+['run','typecheck'],pnpm+['run','lint'],
        pnpm+['run','test','--reporter=default','--reporter=junit','--outputFile=../evidence/frontend.xml'],
        pnpm+['run','build'],pnpm+['audit','--audit-level=low'],
        [sys.executable,'-m','pytest','-q','tests','scripts/verify_local_demo_browser.py','--junitxml=evidence/complete.xml'],
        [sys.executable,'-m','pip_audit','--format','json','--output','evidence/python-advisories.json'],
        [sys.executable,'scripts/verify_secrets.py']]
    (demo.ROOT/'evidence').mkdir(exist_ok=True)
    for command in commands:
        if subprocess.run(command,env=env).returncode:
            raise SystemExit('Verification failed; inspect the test output. No tests or security checks were bypassed.')
    suite=ET.parse('evidence/complete.xml').getroot().find('testsuite')
    assert int(suite.attrib['tests'])>=116 and all(suite.attrib[name]=='0' for name in ('failures','errors','skipped'))
    frontend=list(ET.parse('evidence/frontend.xml').getroot().iter('testcase'))
    assert len(frontend)>=14 and not any(case.find(tag) is not None for case in frontend for tag in ('failure','error','skipped'))
    report={'python':{'passed':int(suite.attrib['tests']),'failed':0,'skipped':0},'frontend':{'passed':len(frontend),'failed':0,'skipped':0},
            'database':'queueless_erode_integration_test','host':'127.0.0.1','port':55434,'physical_android':'deferred by user',
            'typescript':'passed','eslint':'passed','production_build':'passed','dependency_audits':'passed','secret_scans':'passed'}
    Path('evidence/final-gate.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
