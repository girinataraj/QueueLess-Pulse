"""Opt-in local PostgreSQL demo acceptance; public demo fixtures stay unchanged."""
import io
import os
import sys
import uuid
from pathlib import Path
from threading import Thread

import pytest
from PIL import Image
import zxingcpp
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, text
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import local_demo as demo

class PrivateProfile(dict):
    def __repr__(self):return '<private local-demo profile>'

@pytest.fixture
def local_profile():
    if os.getenv('RUN_LOCAL_DEMO_ACCEPTANCE')!='1':
        pytest.skip('Opt-in acceptance requires an initialized isolated local demo')
    profile=demo.load_profile()
    assert profile['database']==demo.DATABASE and profile['host']=='127.0.0.1'
    return PrivateProfile(profile)

def public_snapshot(app):
    from models import Ticket,TicketEvent
    with app.app_context():
        return ([tuple(getattr(t,c.name) for c in Ticket.__table__.columns) for t in Ticket.query.order_by(Ticket.id)],
                [tuple(getattr(t,c.name) for c in TicketEvent.__table__.columns) for t in TicketEvent.query.order_by(TicketEvent.id)])

def accessible(page):
    axe=next((ROOT/'frontend/node_modules/.pnpm').glob('axe-core@*/node_modules/axe-core/axe.min.js'))
    page.add_script_tag(path=str(axe))
    result=page.evaluate("async () => await axe.run(document, {runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})")
    assert result['violations']==[], [(item['id'],[node['target'] for node in item['nodes']]) for item in result['violations']]

class QuietHandler(WSGIRequestHandler):
    def log_request(self,*args,**kwargs):pass

def login(page,origin,role,profile):
    page.goto(origin+('/app/owner/login' if role=='owner' else '/app/staff/login?experience=reception' if role=='receptionist' else '/app/staff/login'))
    account=profile['accounts'][role]
    page.get_by_label('Username',exact=False).fill(account['username'])
    page.get_by_label('Password',exact=False).fill(account['password'])
    page.get_by_role('button',name='Sign in',exact=True).click()
    target='/app/owner' if role=='owner' else '/app/staff/reception' if role=='receptionist' else '/app/staff/dashboard'
    page.wait_for_url(origin+target,timeout=15000)

@pytest.mark.parametrize('width,height',[(1366,900),(390,844)],ids=['desktop','mobile'])
def test_seeded_reception_patient_doctor_owner(local_profile,width,height):
    profile=local_profile
    public=demo.make_app(profile)
    before=public_snapshot(public)
    schema='local_demo_check_'+uuid.uuid4().hex
    engine=create_engine(demo.database_url(profile))
    with engine.begin() as connection:
        assert connection.execute(text('SELECT current_database()')).scalar()==demo.DATABASE
        connection.execute(text('CREATE SCHEMA "'+schema+'"'))
    app=demo.make_app(profile,schema=schema)
    assert demo.seed(app,profile)['counts']==demo.EXPECTED
    assert demo.seed(app,profile)['already_seeded'] is True
    address=os.getenv('LOCAL_DEMO_LAN_TEST_ADDRESS','127.0.0.1')
    https=os.getenv('LOCAL_DEMO_LAN_TEST_HTTPS')=='1'
    tls=None
    if address!='127.0.0.1':
        import ipaddress
        assert ipaddress.ip_address(address).is_private
        if https:
            cert,key,_=demo.hotspot_tls(address)
            tls=(str(cert),str(key));app.config['SESSION_COOKIE_SECURE']=True
        else:demo.configure_lan_http(app)
        app.config['TRUSTED_HOSTS']=['127.0.0.1','localhost',address]
    server=make_server(address,5000 if address!='127.0.0.1' else 0,app,threaded=True,request_handler=QuietHandler,ssl_context=tls)
    origin=f'{"https" if https else "http"}://{address}:{server.server_port}'
    app.config['PUBLIC_BASE_URL']=origin
    urls,qr=demo.create_reception_assets(app,profile,origin,prefix='check-'+schema.removeprefix('local_demo_check_')+'-')
    decoded=zxingcpp.read_barcode(Image.open(io.BytesIO(qr.read_bytes()))).text
    assert decoded==urls['patient']
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    credentials={'username':profile['gateway_user'],'password':profile['gateway_password']}
    (ROOT/'evidence').mkdir(exist_ok=True)
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
            denied=browser.new_context()
            assert denied.request.get(origin+'/app/').status==401
            assert denied.request.get(origin+'/api/v1/businesses').status==401
            denied.close()
            def page():
                context=browser.new_context(viewport={'width':width,'height':height},http_credentials=credentials)
                result=context.new_page();result.on('pageerror',lambda e:errors.append(str(e)))
                return result
            reception=page();login(reception,origin,'receptionist',profile)
            expect(reception.get_by_role('heading',name='Reception desk',exact=True)).to_be_visible()
            expect(reception.get_by_alt_text('Eye Consultation service QR')).to_be_visible()
            live=reception
            expect(live.locator('.token-display')).to_have_text('E010')
            expect(live.get_by_test_id('waiting-count')).to_have_text('5')
            display=page();display.goto(urls['display'])
            expect(display.locator('.display-token')).to_have_text('E010')
            expect(display.locator('.display-card')).to_contain_text('5 waiting')
            reception.screenshot(path=str(ROOT/f'evidence/local-reception-{width}.png'),full_page=True)
            owner=page();login(owner,origin,'owner',profile)
            expect(owner.get_by_role('heading',name='Your businesses',exact=True)).to_be_visible()
            owner.locator('a.card').filter(has=owner.get_by_role('heading',name='Erode Eye Clinic — DEMO',exact=True)).click()
            expect(owner.locator('.metric').filter(has_text='Completed').locator('strong')).to_have_text('7')
            bid=int(owner.url.rsplit('/',1)[-1])
            doctor=page();login(doctor,origin,'doctor',profile)
            expect(doctor.get_by_role('heading',name='Staff console',exact=True)).to_be_visible()
            expect(doctor.locator('.queue-card')).to_have_count(1)
            expect(doctor.locator('.queue-card')).to_contain_text('Eye Consultation')
            expect(doctor.get_by_role('heading',name='No assigned queues',exact=True)).to_have_count(0)
            receptor=page();login(receptor,origin,'receptionist',profile)
            expect(receptor.get_by_role('heading',name='Reception desk',exact=True)).to_be_visible()
            assert receptor.context.request.get(origin+f'/api/v1/owner/businesses/{bid}').status==404
            assert receptor.context.request.get(origin+'/api/v1/staff/queues').json()==[]
            expect(receptor.get_by_role('button',name='Call Next',exact=True)).to_have_count(0)
            expect(receptor.get_by_role('button',name='Mark Reviewed',exact=True)).to_have_count(0)
            expect(receptor.locator('.token-display')).to_have_text('E010')
            service=receptor.context.request.get(origin+'/api/v1/reception/queues').json()[0]['service_id']
            image=receptor.context.request.get(origin+f'/api/v1/staff/services/{service}/qr.png?download=1')
            assert image.status==200 and 'attachment' in image.headers['content-disposition']
            assert zxingcpp.read_barcode(Image.open(io.BytesIO(image.body()))).text==decoded
            receptor.evaluate('window.print = () => { window.printWasRequested=true; }')
            receptor.get_by_role('button',name='Print QR',exact=True).click()
            assert receptor.evaluate('window.printWasRequested === true')
            receptor.emulate_media(media='print')
            expect(receptor.get_by_alt_text('Eye Consultation service QR')).to_be_visible()
            expect(receptor.get_by_role('button',name='Print QR',exact=True)).not_to_be_visible()
            receptor.emulate_media(media='screen')
            accessible(receptor)
            receptor.route('**/api/v1/reception/queues',lambda route:route.abort())
            expect(receptor.get_by_role('status').filter(has_text='Connection lost')).to_be_visible(timeout=15000)
            receptor.unroute('**/api/v1/reception/queues')
            expect(receptor.get_by_role('status').filter(has_text='Connected')).to_be_visible(timeout=15000)
            patient=page();patient.goto(decoded)
            if address!='127.0.0.1':
                assert patient.evaluate('window.isSecureContext') is https
                assert patient.evaluate("typeof crypto.randomUUID === 'function'")
            patient.get_by_role('button',name='Join Queue',exact=True).click()
            expect(patient.locator('.token-display')).to_have_text('E016')
            expect(patient.locator('.status-badge')).to_have_text('WAITING')
            expect(patient.locator('.metric-grid')).to_contain_text('30')
            accessible(patient)
            patient.screenshot(path=str(ROOT/f'evidence/local-patient-{width}.png'),full_page=True,mask=[patient.get_by_label('Your private recovery link',exact=True)])
            patient.reload();expect(patient.locator('.token-display')).to_have_text('E016')
            # Maintain FIFO: finish the existing called ticket, skip E011,
            # complete E012-E015, then call and complete the new patient E016.
            doctor.get_by_role('button',name='Mark Reviewed',exact=True).click()
            expect(doctor.locator('.current-ticket .token-display')).to_have_text('—')
            for number in range(11,17):
                doctor.get_by_role('button',name='Call Next',exact=True).click()
                expect(doctor.locator('.current-ticket .token-display')).to_have_text(f'E{number:03d}')
                expect(live.locator('.token-display')).to_have_text(f'E{number:03d}',timeout=12000)
                if number==16:
                    expect(patient.locator('.status-badge')).to_have_text('CALLED',timeout=12000)
                    expect(display.locator('.display-token')).to_have_text('E016',timeout=12000)
                    doctor.screenshot(path=str(ROOT/f'evidence/local-doctor-{width}.png'),full_page=True)
                action='Skip' if number==11 else 'Mark Reviewed'
                doctor.get_by_role('button',name=action,exact=True).click()
                expect(doctor.locator('.current-ticket .token-display')).to_have_text('—')
            expect(patient.locator('.status-badge')).to_have_text('COMPLETED',timeout=12000)
            expect(live.locator('.token-display')).to_have_text('---',timeout=12000)
            expect(live.get_by_test_id('waiting-count')).to_have_text('0')
            expect(display.locator('.display-token')).to_have_text('---',timeout=12000)
            expect(display.locator('.display-card')).to_contain_text('0 waiting')
            owner.goto(origin+f'/app/owner/business/{bid}/history?status=COMPLETED')
            expect(owner.get_by_role('cell',name='E016',exact=True)).to_be_visible()
            row=owner.get_by_role('row').filter(has=owner.get_by_role('cell',name='E016',exact=True))
            expect(row).to_contain_text('COMPLETED')
            expect(row).to_contain_text('CREATED')
            expect(row).to_contain_text('CALLED')
            from datetime import datetime
            from zoneinfo import ZoneInfo
            expect(row).to_contain_text(datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat())
            owner.get_by_label('Date',exact=True).fill(datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat())
            owner.get_by_label('Date basis',exact=True).select_option('finished')
            owner.get_by_role('button',name='Filter history',exact=True).click()
            owner.wait_for_url('**date_basis=finished**',timeout=15000)
            expect(owner.get_by_role('cell',name='E016',exact=True)).to_be_visible()
            assert 'date_basis=finished' in owner.url
            owner.screenshot(path=str(ROOT/f'evidence/local-owner-history-{width}.png'),full_page=True)
            owner.goto(origin+f'/app/owner/business/{bid}')
            expect(owner.locator('.today-reviews').get_by_role('cell',name='E016',exact=True)).to_be_visible()
            expect(owner.locator('.today-reviews')).to_contain_text('13 completed consultations today')
            owner.screenshot(path=str(ROOT/f'evidence/local-owner-reviews-{width}.png'),full_page=True)
            display.screenshot(path=str(ROOT/f'evidence/local-public-display-{width}.png'),full_page=True)
            assert demo.counts(app)=={'waiting':0,'called':0,'completed':13,'skipped':3}
            for active in (doctor,patient,owner,reception,display):
                assert active.evaluate('document.documentElement.scrollWidth<=innerWidth')
                accessible(active)
            assert errors==[]
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
        from models import db
        with app.app_context():db.session.remove();db.engine.dispose()
        engine.dispose()
    # Test records live in a unique test schema, never in the user's public demo.
    assert public_snapshot(public)==before

def test_running_local_demo_initial_views(local_profile):
    profile=local_profile
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
        context=browser.new_context(http_credentials={'username':profile['gateway_user'],'password':profile['gateway_password']})
        page=context.new_page();login(page,profile['origin'],'receptionist',profile);response=page.goto(profile['urls']['reception'])
        assert response.status==200, page.url
        expect(page.locator('.token-display')).to_have_text('E010')
        expect(page.get_by_test_id('waiting-count')).to_have_text('5')
        login(page,profile['origin'],'doctor',profile)
        expect(page.locator('.queue-card')).to_contain_text('Eye Consultation')
        expect(page.locator('.current-ticket .token-display')).to_have_text('E010')
        page.context.clear_cookies()
        login(page,profile['origin'],'owner',profile)
        expect(page.get_by_role('heading',name='Your businesses',exact=True)).to_be_visible()
        with demo.make_app(profile).app_context():
            from models import Ticket
            day=str(Ticket.query.filter_by(status='CALLED').one().business_date)
        page.goto(profile['urls']['history']+'&date='+day+'&date_basis=issued')
        expect(page.get_by_role('cell',name='E001',exact=True)).to_be_visible()
        expect(page.get_by_role('cell',name='E007',exact=True)).to_be_visible()
        browser.close()
