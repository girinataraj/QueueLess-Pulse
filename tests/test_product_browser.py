"""Integrated role acceptance uses disposable PostgreSQL, never the live service."""
from pathlib import Path
from threading import Thread
import io, os
import pytest
import zxingcpp
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from models import db, Business, Branch, Service, Membership, ReceptionGrant, Ticket, TicketEvent, Staff
from test_postgres import pg_app
from test_operations import users

ROOT=Path(__file__).parents[1]

@pytest.fixture
def product_server(pg_app):
    users(pg_app)
    with pg_app.app_context():
        b=db.session.get(Business,1);b.name='Erode Eye Clinic — DEMO';b.slug='erode-eye-clinic-demo'
        branch=db.session.get(Branch,1);branch.name='Main Reception'
        s=db.session.get(Service,1);s.name='Eye Consultation';s.prefix='E';s.counter_label='Consultation Room 1'
        m=Membership.query.join(Staff).filter(Staff.username=='operations_reception').one();db.session.add(ReceptionGrant(membership_id=m.id));db.session.commit()
    server=make_server('127.0.0.1',0,pg_app,threaded=True);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}',pg_app
    server.shutdown();server.server_close();thread.join(timeout=5)

def sign_in(page,origin,username,password,role):
    page.goto(origin+('/app/owner/login' if role=='owner' else '/app/staff/login'+('?experience=reception' if role=='reception' else '')))
    page.get_by_label('Username',exact=False).fill(username);page.get_by_label('Password',exact=False).fill(password)
    page.get_by_role('button',name='Sign in',exact=True).click()
    page.wait_for_url('**/app/'+('owner/business/*' if role=='owner' else 'staff/reception' if role=='reception' else 'staff/dashboard'))

def accessible(page):
    expect(page.locator('.skeleton:visible')).to_have_count(0)
    axe=next((ROOT/'frontend/node_modules/.pnpm').glob('axe-core@*/node_modules/axe-core/axe.min.js'))
    page.add_script_tag(path=str(axe))
    result=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})).violations")
    assert not result,[(v['id'],[n['target'] for n in v['nodes']]) for v in result]
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')


def owner_section(page,section):
    page.get_by_role('tab',name='Team & Services',exact=True).click()
    group=page.locator('#'+{'Services':'services','Team':'team','Branches':'branches'}[section])
    if group.get_attribute('open') is None:group.locator('summary').first.click()


def capture_state(page,name,width):
    folder=Path(os.environ.get('UX_SCREENSHOT_DIR',str(ROOT/'evidence/ux-after')));folder.mkdir(parents=True,exist_ok=True)
    expect(page.locator('h1').first).to_be_visible()
    expect(page.locator('.skeleton:visible')).to_have_count(0)
    page.screenshot(path=str(folder/f'{name}-{width}.png'),full_page=True)

@pytest.mark.parametrize('width',[1440,1366,768,390,360])
def test_reception_patient_doctor_recall_break_reviews_display(product_server,width):
    origin,app=product_server
    with sync_playwright() as pw:
        browser=pw.chromium.launch();contexts=[browser.new_context(viewport={'width':width,'height':900}) for _ in range(5)]
        reception,patient,doctor,owner,display=[ctx.new_page() for ctx in contexts]
        sign_in(reception,origin,'operations_reception','isolated-test-password-123','reception')
        card=reception.locator('.reception-card').filter(has=reception.get_by_role('heading',name='Eye Consultation',exact=True))
        qr=card.get_by_alt_text('Eye Consultation service QR');expect(qr).to_be_visible();accessible(reception);capture_state(reception,'reception-desk',width)
        response=contexts[0].request.get(origin+qr.get_attribute('src'));entry=zxingcpp.read_barcode(Image.open(io.BytesIO(response.body()))).text
        assert entry==origin+'/app/b/erode-eye-clinic-demo/service/1'
        downloaded=contexts[0].request.get(origin+qr.get_attribute('src')+'?download=1')
        assert downloaded.status==200 and 'attachment' in downloaded.headers['content-disposition']
        card.get_by_role('button',name='Issue walk-in token').click();reception.get_by_role('button',name='Confirm registration').click();expect(card.get_by_text('Walk-in token E001',exact=True)).to_be_visible()
        reception.evaluate('window.print=()=>{window.__printed=true;}')
        card.get_by_role('button',name='Print QR',exact=True).click();reception.emulate_media(media='print')
        expect(qr).to_be_visible();expect(card.locator('.token-slip')).not_to_be_visible()
        reception.evaluate("window.dispatchEvent(new Event('afterprint'))");reception.emulate_media(media='screen')
        card.get_by_role('button',name='Print token slip',exact=True).click();reception.emulate_media(media='print')
        expect(card.locator('.token-slip')).to_be_visible();expect(qr).not_to_be_visible()
        assert reception.evaluate('window.__printed===true')
        reception.evaluate("window.dispatchEvent(new Event('afterprint'))");reception.emulate_media(media='screen')
        patient.goto(entry);expect(patient.get_by_role('button',name='Join Queue')).to_be_enabled();capture_state(patient,'patient-entry',width)
        held=[];patient.route('**/api/v1/services/1/tickets',lambda route:held.append(route));patient.get_by_role('button',name='Join Queue').click();expect(patient.get_by_role('button',name='Joining…')).to_be_visible();capture_state(patient,'patient-joining',width);assert len(held)==1;held[0].continue_();patient.unroute('**/api/v1/services/1/tickets');expect(patient.locator('.token-display')).to_have_text('E002');expect(patient.get_by_text('WAITING',exact=True)).to_be_visible();accessible(patient)
        capture_state(patient,'patient-waiting',width)
        private=patient.url;patient.reload();expect(patient.locator('.token-display')).to_have_text('E002')
        display.goto(origin+'/app/b/erode-eye-clinic-demo/display');expect(display.get_by_role('heading',name='Now serving',exact=True)).to_be_visible()
        sign_in(doctor,origin,'tester','test-password-123','doctor');queue=doctor.locator('.queue-card').filter(has=doctor.get_by_role('heading',name='Eye Consultation',exact=True))
        queue.get_by_role('button',name='Start duty').click();expect(queue.get_by_text('AVAILABLE',exact=True)).to_be_visible()
        queue.get_by_role('button',name='Call Next').click();expect(queue.locator('.token-display')).to_have_text('E001');expect(display.locator('.display-card').first.locator('.display-token')).to_have_text('E001',timeout=12000)
        assert queue.get_by_role('button',name='Start break').is_disabled();assert queue.get_by_role('button',name='End duty').is_disabled()
        capture_state(doctor,'doctor-active',width);capture_state(display,'display-serving',width)
        queue.get_by_role('button',name='Recall token').click();expect(queue.get_by_text('RECALLED',exact=True)).to_be_visible();accessible(doctor)
        queue.get_by_role('button',name='Skip',exact=True).click();doctor.get_by_role('button',name='Confirm skip').click();expect(queue.locator('.token-display')).to_have_text('—')
        queue.get_by_role('button',name='Start break').click();doctor.get_by_role('button',name='Confirm break').click();expect(queue.get_by_text('ON BREAK',exact=True)).to_be_visible()
        expect(patient.get_by_text('Doctor on break. Your place is retained; the wait may be longer.')).to_be_visible(timeout=12000)
        capture_state(doctor,'doctor-break',width)
        assert queue.get_by_role('button',name='Call Next').is_disabled()
        queue.get_by_role('button',name='Resume duty').click();expect(queue.get_by_text('AVAILABLE',exact=True)).to_be_visible();queue.get_by_role('button',name='Call Next').click();expect(patient.get_by_text('CALLED',exact=True)).to_be_visible(timeout=12000)
        capture_state(patient,'patient-called',width)
        queue.get_by_role('button',name='Mark Reviewed').click();expect(patient.get_by_text('COMPLETED',exact=True)).to_be_visible(timeout=12000)
        capture_state(patient,'patient-completed',width)
        expect(display.locator('.display-card').first.locator('.display-token')).to_have_text('---',timeout=12000);accessible(display)
        sign_in(owner,origin,'operations_owner','isolated-test-password-123','owner');owner.goto(origin+'/app/owner/business/1');accessible(owner);capture_state(owner,'owner-overview',width);owner_section(owner,'Services');capture_state(owner,'owner-services',width);owner_section(owner,'Team');capture_state(owner,'owner-team',width);owner.get_by_role('tab',name='Reviews',exact=True).click();expect(owner.locator('#reviews').get_by_role('cell',name='E002',exact=True)).to_be_visible();accessible(owner)
        owner.get_by_role('tab',name='Overview',exact=True).click()
        owner.get_by_role('link',name="Today's Reviews →").click()
        expect(owner.get_by_role('heading',name="Today's Reviews",exact=True)).to_be_visible()
        expect(owner.get_by_role('cell',name='E002',exact=True)).to_be_visible()
        expect(owner.get_by_role('cell',name='E001',exact=True)).not_to_be_visible();accessible(owner);capture_state(owner,'owner-reviews',width)
        owner.goto(origin+'/app/owner/business/1/reviews?date=2020-01-01&status=SKIPPED')
        expect(owner.get_by_role('cell',name='E002',exact=True)).to_be_visible()
        expect(owner.get_by_role('cell',name='E001',exact=True)).not_to_be_visible()
        owner.get_by_role('link',name='Back to dashboard',exact=True).click()
        expect(card.get_by_test_id('waiting-count')).to_have_text('0',timeout=12000)
        assert private.rsplit('/',1)[-1] not in display.locator('body').inner_text()
        for page,role in [(reception,'reception'),(patient,'patient'),(doctor,'doctor'),(owner,'owner'),(display,'display')]:
            folder=ROOT/'evidence/product-browser';folder.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(folder/f'{role}-{width}.png'),full_page=True)
        for ctx in contexts:ctx.close()
        browser.close()
    with app.app_context():
        assert Ticket.query.count()==2
        assert [t.status for t in Ticket.query.order_by(Ticket.id)]==['SKIPPED','COMPLETED']
        assert TicketEvent.query.filter_by(event_type='RECALLED').count()==1
