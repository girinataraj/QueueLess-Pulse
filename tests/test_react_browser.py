import io
import os
import re
import secrets
from pathlib import Path
from threading import Thread
import pytest
from PIL import Image
import zxingcpp
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from test_postgres import pg_app
from app import create_app

ROOT = Path(__file__).parents[1]

@pytest.fixture
def react_server(pg_app):
    assert (ROOT/'frontend/dist/index.html').exists(), 'Build frontend before running React browser tests'
    password=secrets.token_hex(32)
    demo=create_app({**pg_app.config,'DEMO_MODE':True,'DEMO_ACCESS_USER':'private-reviewer','DEMO_ACCESS_PASSWORD':password})
    server=make_server('127.0.0.1',0,demo,threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}',{'username':'private-reviewer','password':password}
    server.shutdown();server.server_close();thread.join(timeout=5)
    with demo.app_context():
        from models import db
        db.session.remove();db.engine.dispose()

def accessible(page):
    axe=next((ROOT/'frontend/node_modules/.pnpm').glob('axe-core@*/node_modules/axe-core/axe.min.js'))
    page.add_script_tag(path=str(axe))
    result=page.evaluate("async () => await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})")
    assert result['violations']==[], [(v['id'],[(n['target'],n.get('failureSummary')) for n in v['nodes']]) for v in result['violations']]

@pytest.mark.browser
@pytest.mark.postgres
@pytest.mark.parametrize('viewport',[{'width':1366,'height':900},{'width':390,'height':844}],ids=['desktop','mobile'])
def test_react_four_experiences_postgres(react_server,viewport):
    react_server,credentials=react_server
    Path('evidence').mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.getenv('PLAYWRIGHT_EXECUTABLE_PATH'),headless=True)
        outsider=browser.new_context()
        assert outsider.request.get(react_server+'/app/owner/register').status==401
        assert outsider.request.get(react_server+'/api/v1/businesses').status==401
        outsider.close()
        owner_context=browser.new_context(viewport=viewport,http_credentials=credentials);owner=owner_context.new_page();errors=[]
        owner.on('pageerror',lambda e:errors.append(str(e)))
        owner.goto(react_server+'/app/owner/register')
        owner.get_by_label('Username',exact=False).fill('react_owner')
        owner.get_by_label('Password *',exact=True).fill('react-owner-password-123')
        owner.get_by_label('Confirm password',exact=False).fill('react-owner-password-123')
        owner.get_by_role('button',name='Create account',exact=True).click()
        expect(owner.get_by_role('heading',name='Your businesses')).to_be_visible()
        expect(owner.get_by_role('status').filter(has_text='Restricted evaluator demo')).to_be_visible()
        owner.get_by_label('Business name',exact=False).fill('Meridian Clinic')
        owner.get_by_label('Business URL',exact=False).fill('meridian-clinic')
        owner.get_by_role('button',name='Create business',exact=True).click()
        expect(owner.get_by_role('heading',name='Meridian Clinic',exact=True)).to_be_visible()
        bid=int(owner.url.rsplit('/',1)[-1])
        branch_form=owner.locator('section.card').filter(has=owner.get_by_role('heading',name='Add a branch',exact=True))
        branch_form.get_by_label('Branch name',exact=False).fill('Central Branch')
        branch_form.get_by_label('Address',exact=True).fill('Main Street')
        branch_form.get_by_role('button',name='Add branch',exact=True).click()
        service_form=owner.locator('section.card').filter(has=owner.get_by_role('heading',name='Create a service',exact=True))
        service_form.get_by_label('Service name',exact=False).fill('Consultation')
        service_form.get_by_label('Token prefix',exact=False).fill('MC')
        service_form.get_by_label('Fallback duration',exact=False).fill('8')
        service_form.get_by_label('Counter label',exact=False).fill('Desk 1')
        service_form.get_by_role('button',name='Create service',exact=True).click()
        expect(owner.locator('#services').get_by_role('heading',name='Consultation',exact=True)).to_be_visible()
        staff_form=owner.locator('section.card').filter(has=owner.get_by_role('heading',name='Create staff securely',exact=True))
        staff_form.get_by_label('Username',exact=False).fill('react_staff')
        staff_form.get_by_label('Password',exact=False).fill('react-staff-password-123')
        staff_form.get_by_role('button',name='Create staff',exact=True).click()
        member=owner.locator('article.card').filter(has=owner.get_by_role('heading',name='react_staff',exact=True))
        member.get_by_label('Central Branch · Consultation',exact=True).check()
        member.get_by_role('button',name='Save permissions',exact=True).click()
        expect(owner.get_by_role('status').filter(has_text='Changes saved.')).to_be_visible()
        # Radix focus trapping and keyboard close; configuration remains unchanged.
        owner.locator('#branches').get_by_role('button',name='Edit branch',exact=True).click()
        dialog=owner.get_by_role('dialog');expect(dialog).to_be_visible();accessible(owner)
        owner.keyboard.press('Escape');expect(dialog).not_to_be_visible()
        accessible(owner)
        owner.evaluate('window.scrollTo(0,0)');owner.screenshot(path=f'evidence/react-owner-{viewport["width"]}.png',full_page=False)
        qr=owner_context.request.get(react_server+f'/owner/business/{bid}/qr.png?ui=react&download=1')
        decoded=zxingcpp.read_barcode(Image.open(io.BytesIO(qr.body()))).text
        assert decoded==react_server+'/app/b/meridian-clinic'
        customer_context=browser.new_context(viewport=viewport,http_credentials=credentials);customer=customer_context.new_page();customer.on('pageerror',lambda e:errors.append(str(e)))
        customer.goto(decoded);customer.get_by_role('link',name=re.compile('Central Branch')).click()
        customer.get_by_role('button',name='Join Queue',exact=True).click()
        expect(customer.locator('.token-display')).to_have_text('MC001')
        expect(customer.locator('.status-badge')).to_have_text('WAITING')
        private_url=customer.url
        customer.reload();expect(customer.locator('.token-display')).to_have_text('MC001')
        accessible(customer);customer.screenshot(path=f'evidence/react-customer-{viewport["width"]}.png',full_page=True)
        staff_context=browser.new_context(viewport=viewport,http_credentials=credentials);staff=staff_context.new_page();staff.on('pageerror',lambda e:errors.append(str(e)))
        staff.goto(react_server+'/app/staff/login')
        staff.get_by_label('Username',exact=False).fill('react_staff')
        staff.get_by_label('Password',exact=False).fill('react-staff-password-123')
        staff.get_by_role('button',name='Sign in',exact=True).click()
        expect(staff.get_by_role('heading',name='Staff console',exact=True)).to_be_visible()
        expect(staff.locator('.waiting-list')).to_contain_text('MC001')
        assert 'Demo Clinic' not in staff.locator('main').inner_text()
        display_context=browser.new_context(viewport=viewport,http_credentials=credentials);display=display_context.new_page();display.on('pageerror',lambda e:errors.append(str(e)))
        display.goto(react_server+'/app/b/meridian-clinic/display?branch_id='+str(owner_context.request.get(react_server+'/api/v1/owner/businesses/'+str(bid)).json()['branches'][0]['id']))
        staff.get_by_role('button',name='Call Next',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('CALLED',timeout=12000)
        expect(display.locator('.display-token')).to_have_text('MC001',timeout=12000)
        expect(display.locator('.display-card')).to_contain_text('Desk 1')
        accessible(staff);accessible(display)
        staff.screenshot(path=f'evidence/react-staff-{viewport["width"]}.png',full_page=True)
        display.screenshot(path=f'evidence/react-display-{viewport["width"]}.png',full_page=True)
        staff.get_by_role('button',name='Mark Reviewed',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('COMPLETED',timeout=12000)
        expect(owner.locator('.metric').filter(has_text='Completed').locator('strong')).to_have_text('1',timeout=12000)
        owner.get_by_role('link',name='Ticket history',exact=True).click()
        expect(owner.get_by_role('cell',name='MC001',exact=True)).to_be_visible()
        # A recovery link is viewable elsewhere but does not grant cancellation.
        recovery=display_context.new_page();recovery.goto(private_url)
        expect(recovery.locator('.status-badge')).to_have_text('COMPLETED')
        expect(recovery.get_by_role('button',name='Cancel ticket',exact=True)).to_have_count(0)
        # Exercise SKIPPED and CANCELLED, not just the happy completion path.
        customer.goto(decoded);customer.get_by_role('link',name=re.compile('Central Branch')).click();customer.get_by_role('button',name='Join Queue',exact=True).click()
        expect(customer.locator('.token-display')).to_have_text('MC002');staff.get_by_role('button',name='Call Next',exact=True).click()
        expect(staff.get_by_role('button',name='Skip',exact=True)).to_be_visible();staff.get_by_role('button',name='Skip',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('SKIPPED',timeout=12000)
        customer.goto(decoded);customer.get_by_role('link',name=re.compile('Central Branch')).click();customer.get_by_role('button',name='Join Queue',exact=True).click()
        expect(customer.locator('.token-display')).to_have_text('MC003');customer.get_by_role('button',name='Cancel ticket',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('CANCELLED',timeout=12000)
        display.route('**/api/v1/display/*',lambda route:route.abort())
        expect(display.get_by_role('status').filter(has_text='Connection lost')).to_be_visible(timeout=15000)
        display.unroute('**/api/v1/display/*');expect(display.get_by_role('status').filter(has_text='Connected')).to_be_visible(timeout=15000)
        display.bring_to_front()
        display.get_by_role('button',name='Full screen',exact=True).click()
        display.wait_for_function('document.fullscreenElement !== null')
        display.get_by_role('button',name='Full screen',exact=True).click()
        display.wait_for_function('document.fullscreenElement === null')
        # Editing, service activation, invitations and revocation are exercised through React.
        owner.get_by_role('link',name='Back to dashboard',exact=True).click()
        owner.locator('#branches').get_by_role('button',name='Edit branch',exact=True).click()
        dialog=owner.get_by_role('dialog');dialog.get_by_label('Address',exact=True).fill('Updated Main Street')
        dialog.get_by_role('button',name='Save branch',exact=True).click()
        expect(owner.locator('#branches')).to_contain_text('Updated Main Street');owner.keyboard.press('Escape')
        owner.locator('#services').get_by_role('button',name='Edit service',exact=True).click()
        dialog=owner.get_by_role('dialog');dialog.get_by_label('Accept new customers',exact=True).uncheck()
        dialog.get_by_role('button',name='Save service',exact=True).click()
        expect(owner.locator('#services').locator('.badge')).to_have_text('Inactive');owner.keyboard.press('Escape')
        customer.goto(decoded);customer.get_by_role('link',name=re.compile('Central Branch')).click()
        expect(customer.get_by_role('button',name='Join Queue',exact=True)).to_have_count(0)
        owner.locator('#services').get_by_role('button',name='Edit service',exact=True).click()
        dialog=owner.get_by_role('dialog');dialog.get_by_label('Accept new customers',exact=True).check()
        dialog.get_by_role('button',name='Save service',exact=True).click()
        expect(owner.locator('#services').locator('.badge')).to_have_text('Active');owner.keyboard.press('Escape')
        owner.get_by_role('button',name='Create invitation',exact=True).click()
        invitation=owner.get_by_label('Private invitation link',exact=True)
        expect(invitation).to_be_visible()
        invited_context=browser.new_context(viewport=viewport,http_credentials=credentials);invited=invited_context.new_page();invited.on('pageerror',lambda e:errors.append(str(e)))
        invited.goto(invitation.input_value())
        invited.get_by_label('Username',exact=False).fill('react_invited')
        invited.get_by_label('Password *',exact=True).fill('react-invited-password-123')
        invited.get_by_label('Confirm password',exact=False).fill('react-invited-password-123')
        invited.get_by_role('button',name='Accept invitation',exact=True).click()
        expect(invited.get_by_role('heading',name='No assigned queues',exact=True)).to_be_visible()
        invited.goto(invitation.input_value());expect(invited.get_by_role('alert')).to_contain_text('Invitation expired or already used')
        member=owner.locator('article.card').filter(has=owner.get_by_role('heading',name='react_staff',exact=True))
        member.get_by_label('Membership active',exact=True).uncheck()
        member.get_by_role('button',name='Save permissions',exact=True).click()
        expect(staff.get_by_role('heading',name='No assigned queues',exact=True)).to_be_visible(timeout=12000)
        expect(staff.locator('.queue-card')).to_have_count(0)
        for page in (owner,customer,staff,display):
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), page.evaluate('JSON.stringify({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll("*")].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,15).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right}))})')
        manifest=staff.evaluate("async () => (await fetch('/app.webmanifest')).json()")
        assert manifest['start_url']=='/app/' and manifest['scope']=='/app/'
        staff.evaluate('async () => await navigator.serviceWorker.ready')
        cached=staff.evaluate('async () => {const paths=[];for(const key of await caches.keys()){for(const r of await (await caches.open(key)).keys())paths.push(new URL(r.url).pathname);}return paths;}')
        assert len(cached)==3 and all(p.startswith('/static/') for p in cached)
        assert errors==[]
        browser.close()
