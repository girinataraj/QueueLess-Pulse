import os
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_browser import live_server

@pytest.mark.browser
@pytest.mark.parametrize('viewport',[{'width':1366,'height':900},{'width':390,'height':844}],ids=['desktop','mobile'])
def test_owner_to_staff_to_customer_platform(live_server,viewport):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv('PLAYWRIGHT_EXECUTABLE_PATH'),headless=True)
        owner_context=browser.new_context(viewport=viewport)
        owner=owner_context.new_page()
        errors=[]
        owner.on('pageerror',lambda error:errors.append(str(error)))
        owner.goto(live_server+'/owner/register')
        owner.get_by_label('Username',exact=True).fill('sakura_owner')
        owner.get_by_label('Email (optional)').fill('owner@example.com')
        owner.get_by_label('Password',exact=True).fill('owner-secure-password-123')
        owner.get_by_label('Confirm password').fill('owner-secure-password-123')
        owner.get_by_role('button',name='Create account',exact=True).click()
        expect(owner.get_by_role('heading',name='Your businesses')).to_be_visible()
        owner.get_by_label('Business name',exact=True).fill('Sakura Clinic')
        owner.get_by_label('Business URL',exact=True).fill('sakura-clinic')
        owner.get_by_label('About the business',exact=True).fill('Care without the waiting room.')
        owner.get_by_role('button',name='Create business',exact=True).click()
        expect(owner.get_by_role('heading',name='Sakura Clinic',exact=True)).to_be_visible()
        branch_form=owner.locator('form[action$="/branches/create"]')
        branch_form.get_by_label('Branch name').fill('Central Branch')
        branch_form.get_by_label('Address').fill('Main Street')
        branch_form.get_by_role('button',name='Add branch',exact=True).click()
        service_form=owner.locator('form[action$="/services/create"]')
        service_form.get_by_label('Service name').fill('Consultation')
        service_form.get_by_label('Token prefix').fill('SC')
        service_form.get_by_label('Fallback duration (minutes)').fill('8')
        service_form.get_by_label('Counter label (optional)').fill('Desk 1')
        service_form.get_by_label('Description',exact=True).fill('A comfortable consultation.')
        service_form.get_by_role('button',name='Create service',exact=True).click()
        staff_form=owner.locator('form[action$="/staff/create"]')
        staff_form.get_by_label('Staff username').fill('sakura_staff')
        staff_form.get_by_label('Initial password').fill('staff-secure-password-123')
        staff_form.get_by_role('button',name='Create staff',exact=True).click()
        permissions=owner.locator('form[action$="/permissions"]')
        permissions.get_by_label('Central Branch · Consultation',exact=True).check()
        permissions.get_by_role('button',name='Save permissions',exact=True).click()
        expect(owner.locator('#owner-connection')).to_contain_text('Connected',timeout=10000)
        assert owner.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        with owner.expect_download() as downloaded:
            owner.get_by_role('link',name='Download service QR',exact=True).click()
        download=downloaded.value
        Path('evidence').mkdir(exist_ok=True)
        qr_path=f'evidence/service-qr-{viewport["width"]}.png'
        download.save_as(qr_path)
        # Decode the actual downloaded QR; navigate to its encoded URL.
        import zxingcpp
        from PIL import Image
        decoded=zxingcpp.read_barcode(Image.open(qr_path))
        assert decoded and '/b/sakura-clinic/service/' in decoded.text
        customer_context=browser.new_context(viewport=viewport)
        customer=customer_context.new_page()
        customer.on('pageerror',lambda error:errors.append(str(error)))
        customer.goto(decoded.text)
        expect(customer.get_by_role('heading',name='Central Branch',exact=True)).to_be_visible()
        customer.get_by_role('button',name='Join Queue').click()
        expect(customer.locator('.token-display')).to_have_text('SC001')
        expect(customer.locator('#recovery-link')).to_have_value(customer.url)
        staff_context=browser.new_context(viewport=viewport)
        staff=staff_context.new_page()
        staff.goto(live_server+'/staff/login')
        staff.get_by_label('Username').fill('sakura_staff')
        staff.get_by_label('Password').fill('staff-secure-password-123')
        staff.get_by_role('button',name='Login',exact=True).click()
        expect(staff.locator('.waiting-list')).to_contain_text('SC001')
        assert 'Demo Clinic' not in staff.locator('#staff-queues').inner_text()
        display=customer_context.new_page()
        display.goto(live_server+'/b/sakura-clinic/display')
        staff.get_by_role('button',name='Call Next',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('CALLED',timeout=10000)
        expect(customer.locator('#now-serving')).to_have_text('SC001',timeout=10000)
        expect(display.locator('.display-token')).to_have_text('SC001',timeout=10000)
        expect(display.locator('.display-counter')).to_have_text('Desk 1')
        expect(owner.locator('#stat-called')).to_have_text('1',timeout=12000)
        staff.get_by_role('button',name='Complete',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('COMPLETED',timeout=10000)
        expect(owner.locator('#stat-completed')).to_have_text('1',timeout=12000)
        owner.evaluate('window.scrollTo(0,0)')
        owner.screenshot(path=f'evidence/universal-owner-{viewport["width"]}.png',full_page=False)
        customer.screenshot(path=f'evidence/universal-customer-{viewport["width"]}.png',full_page=True)
        staff.screenshot(path=f'evidence/universal-staff-{viewport["width"]}.png',full_page=True)
        display.screenshot(path=f'evidence/universal-display-{viewport["width"]}.png',full_page=True)
        owner.get_by_role('link',name='Ticket history',exact=True).click()
        expect(owner.get_by_role('cell',name='SC001',exact=True)).to_be_visible()
        expect(owner.get_by_role('cell',name='COMPLETED',exact=True)).to_be_visible()
        for page in (owner,customer,staff,display):
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        manifest=staff.evaluate("async () => (await fetch('/staff/manifest.webmanifest')).json()")
        assert manifest['start_url']=='/staff/dashboard' and manifest['scope']=='/'
        staff.evaluate('async () => await navigator.serviceWorker.ready')
        cached=staff.evaluate('async () => { const urls=[]; for(const name of await caches.keys()){const cache=await caches.open(name);for(const req of await cache.keys()) urls.push(new URL(req.url).pathname);}return urls; }')
        assert len(cached)==3 and all(path.startswith('/static/') for path in cached)
        assert errors==[]
        browser.close()
