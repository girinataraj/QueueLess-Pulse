"""Linux CI production-build smoke with a throwaway PostgreSQL schema."""
import os
import secrets
import socket
import subprocess
import time
import uuid
import urllib.request
import re
import base64
from pathlib import Path
from sqlalchemy import create_engine, text, make_url

def main():
    uri = os.environ['TEST_DATABASE_URL']
    url = make_url(uri)
    assert url.get_backend_name() == 'postgresql' and url.database.endswith('_test')
    schema = 'gunicorn_test_' + uuid.uuid4().hex
    engine = create_engine(uri)
    with engine.begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    demo_password=secrets.token_hex(32)
    env = dict(os.environ, APP_ENV='production', SECRET_KEY=secrets.token_hex(32), DEMO_MODE='true', DEMO_ACCESS_USER='ci-reviewer', DEMO_ACCESS_PASSWORD=demo_password,
               DATABASE_URL=url.update_query_dict({'options': '-csearch_path=' + schema}).render_as_string(hide_password=False))
    process = None
    try:
        subprocess.run(['python', '-m', 'flask', '--app', 'app', 'initdb'], env=env, check=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(['gunicorn', '--workers', '2', '--threads', '4', '--bind', f'127.0.0.1:{port}', 'app:app'], env=env)
        base = f'http://127.0.0.1:{port}'
        for _ in range(80):
            if process.poll() is not None:
                raise RuntimeError('Gunicorn exited before readiness')
            try:
                with urllib.request.urlopen(base + '/health', timeout=2) as response:
                    assert response.status == 200
                break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError('Gunicorn readiness timeout')
        try:
            urllib.request.urlopen(base+'/app/',timeout=5)
            raise AssertionError('Restricted demo must reject unauthenticated navigation')
        except urllib.error.HTTPError as error:
            assert error.code==401
        auth={'Authorization':'Basic '+base64.b64encode(('ci-reviewer:'+demo_password).encode()).decode()}
        for path in ['/app/', '/app/owner', '/app/staff/dashboard', '/app/b/example/display', '/app/ticket/example']:
            with urllib.request.urlopen(urllib.request.Request(base + path,headers=auth), timeout=5) as response:
                html = response.read().decode()
                assert response.status == 200 and 'id="root"' in html
                assert 'no-store' in response.headers['Cache-Control']
        with urllib.request.urlopen(urllib.request.Request(base + re.search(r'src="([^"]+\.js)"', html).group(1),headers=auth), timeout=5) as response:
            assert response.status == 200 and len(response.read()) > 1000
        with urllib.request.urlopen(urllib.request.Request(base+'/api/v1/session',headers=auth),timeout=5) as response:
            cookie=response.headers['Set-Cookie']
            assert all(flag in cookie for flag in ('Secure','HttpOnly','SameSite=Lax'))
        Path('evidence').mkdir(exist_ok=True)
        Path('evidence/gunicorn-smoke.txt').write_text('PASS: production PostgreSQL config, Gunicorn 2 workers/4 threads, health, restricted demo access, secure session cookie flags, React deep links and built asset. No deployment.\n')
        print('Gunicorn production frontend smoke passed.')
    finally:
        if process is not None:
            process.terminate()
            process.wait(timeout=20)
        with engine.begin() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()

if __name__ == '__main__':
    main()
