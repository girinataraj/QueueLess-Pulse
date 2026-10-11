"""Fresh browser/public entry and normal role logins; isolated fixture data only."""
import os
from threading import Thread
import pytest
from werkzeug.serving import make_server
from models import db,Staff,Membership

@pytest.mark.parametrize('width',[1366,390],ids=['desktop','mobile'])
def test_fresh_patient_display_reception_doctor_owner_without_basic(browser_application,width):
    from playwright.sync_api import sync_playwright,expect
    browser_application.config['OWNER_REGISTRATION_ENABLED']=False
    with browser_application.app_context():
        for name,role in [('browser_owner','owner'),('browser_reception','staff')]:
            user=Staff(username=name);user.set_password('test-only-browser-password')
            db.session.add(user);db.session.flush();db.session.add(Membership(business_id=1,staff_id=user.id,role=role))
        db.session.commit()
    server=make_server('127.0.0.1',0,browser_application,threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start();origin=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.getenv('PLAYWRIGHT_EXECUTABLE_PATH'),headless=True)
            contexts=[]
            def page():
                c=browser.new_context(viewport={'width':width,'height':900});contexts.append(c);return c.new_page()
            patient=page();display=page();doctor=page();reception=page();owner=page()
            for p in (patient,display):
                response=p.goto(origin+'/app/');assert response.status==200 and 'www-authenticate' not in response.headers
                s=p.request.get(origin+'/api/v1/session');assert s.json()['user'] is None and not s.json()['gateway_required']
                denied=p.request.get(origin+'/api/v1/owner/businesses');assert denied.status==401 and 'www-authenticate' not in denied.headers
            patient.goto(origin+'/app/b/demo/service/1');patient.get_by_role('button',name='Join Queue',exact=True).click()
            expect(patient.get_by_role('heading',name='Your ticket')).to_be_visible();expect(patient.locator('.token-display')).to_have_text('G001')
            private_token=patient.url.rsplit('/',1)[-1]
            display.goto(origin+'/app/b/demo/display');expect(display.get_by_role('heading',name='Now serving')).to_be_visible()
            assert private_token not in display.content()
            def login(p,path,username,password):
                p.goto(origin+path);p.get_by_label('Username',exact=False).fill(username);p.get_by_label('Password',exact=False).fill(password)
                p.get_by_role('button',name='Sign in',exact=True).click()
                target='/app/owner' if username=='browser_owner' else '/app/staff/reception' if username=='browser_reception' else '/app/staff/dashboard'
                p.wait_for_url(origin+target)
            login(reception,'/app/staff/login?experience=reception','browser_reception','test-only-browser-password')
            expect(reception.get_by_role('heading',name='Reception desk')).to_be_visible();expect(reception.get_by_alt_text('General service QR')).to_be_visible()
            assert 'browser gateway is required' not in reception.content()
            login(doctor,'/app/staff/login','tester','test-password-123')
            card=doctor.locator('.queue-card').filter(has=doctor.get_by_role('heading',name='General',exact=True))
            card.get_by_role('button',name='Call Next',exact=True).click()
            expect(card.locator('.token-display')).to_have_text('G001')
            expect(patient.get_by_text('CALLED',exact=True)).to_be_visible(timeout=12000)
            card.get_by_role('button',name='Mark Reviewed',exact=True).click()
            expect(patient.get_by_text('COMPLETED',exact=True)).to_be_visible(timeout=12000)
            login(owner,'/app/owner/login','browser_owner','test-only-browser-password')
            owner.goto(origin+'/app/owner/business/1/history?date_basis=finished&status=COMPLETED')
            expect(owner.get_by_role('cell',name='G001',exact=True)).to_be_visible()
            owner.goto(origin+'/app/owner/register');expect(owner.get_by_role('heading',name='Owner registration is closed')).to_be_visible()
            assert owner.get_by_role('button',name='Create account').count()==0
            for c in contexts:c.close()
            browser.close()
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
