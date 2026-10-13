"""Real route/recovery acceptance; only existing disposable PostgreSQL fixtures."""
import pytest
from urllib.parse import parse_qs
from playwright.sync_api import sync_playwright, expect
from models import db, Business, Branch, Service, Ticket, TicketEvent
from test_postgres import pg_app
from test_product_browser import product_server, sign_in, accessible

@pytest.mark.parametrize('width',[1440,390])
def test_focused_entry_redirects_recovery_back_and_protected_roles(product_server,width):
    origin,app=product_server
    with app.app_context():
        # This dedicated test needs exactly one public service before exercising multi-service selection.
        for s in Service.query.filter(Service.id!=1):s.is_active=False
        db.session.commit()
    with sync_playwright() as pw:
        browser=pw.chromium.launch();context=browser.new_context(viewport={'width':width,'height':900});page=context.new_page()
        page.goto(origin+'/app/');page.wait_for_url('**/app/b/erode-eye-clinic-demo/service/1')
        expect(page.get_by_role('button',name='Join Queue',exact=True)).to_be_enabled()
        assert page.locator('a[href*="/staff"],a[href*="/owner"]').count()==0
        assert page.locator('.sidebar').count()==0
        accessible(page)
        page.goto(origin+'/app/b/erode-eye-clinic-demo/branch/1');page.wait_for_url('**/service/1')
        page.goto(origin+'/app/b/erode-eye-clinic-demo/branch/999')
        expect(page.get_by_role('heading',name='This service link is unavailable')).to_be_visible()
        assert page.get_by_role('button',name='Join Queue',exact=True).count()==0
        page.goto(origin+'/app/display');page.wait_for_url('**/b/erode-eye-clinic-demo/display')
        expect(page.get_by_role('heading',name='Now serving')).to_be_visible()
        assert page.locator('.workspace-header').count()==0
        accessible(page)
        page.goto(origin+'/app/b/erode-eye-clinic-demo/service/1');page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E001');private=page.url
        page.go_back();expect(page.get_by_role('button',name='View my token',exact=True)).to_be_enabled()
        page.get_by_role('button',name='View my token',exact=True).click();expect(page.locator('.token-display')).to_have_text('E001')
        page.goto(origin+'/app/my-tickets');expect(page.get_by_role('dialog',name='Your tickets')).to_be_visible()
        expect(page.get_by_role('dialog').get_by_role('link').filter(has_text='E001')).to_be_visible();accessible(page)
        page.keyboard.press('Escape');expect(page.get_by_role('dialog')).not_to_be_visible()
        page.get_by_role('button',name='Your tickets',exact=True).click()
        page.get_by_label('Saved ticket link',exact=True).fill('https://untrusted.example/app/ticket/synthetic_saved_123456')
        page.get_by_role('button',name='Recover ticket',exact=True).click()
        expect(page.get_by_role('alert').filter(has_text='Paste a saved')).to_be_visible()
        page.get_by_label('Saved ticket link',exact=True).fill(private);page.get_by_role('button',name='Recover ticket',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E001')
        expect(page.get_by_role('dialog')).not_to_be_visible()
        for endpoint in ('/staff/queues','/reception/queues','/owner/businesses/1'):
            response=context.request.get(origin+'/api/v1'+endpoint)
            assert response.status==401
            assert not response.headers.get('www-authenticate')
        page.goto(origin+'/app/owner/business/1/reviews');expect(page.get_by_role('alert').filter(has_text='Sign in to continue')).to_be_visible()
        assert page.get_by_role('cell',name='E001',exact=True).count()==0
        sign_in(page,origin,'operations_owner','isolated-test-password-123','owner')
        page.goto(origin+'/app/owner/business/1/history?date=2026-10-12&status=SKIPPED&service_id=1')
        expect(page.get_by_role('heading',name='Ticket history',exact=True)).to_be_visible()
        assert 'section=reviews' in page.url and 'review=history' in page.url
        expect(page.get_by_label('Date',exact=True)).to_have_value('2026-10-12')
        expect(page.get_by_label('Status',exact=True)).to_have_value('SKIPPED')
        expect(page.get_by_label('Service',exact=True)).to_have_value('1')
        page.get_by_role('tab',name='Overview',exact=True).focus();page.keyboard.press('ArrowRight')
        expect(page.get_by_role('tab',name='Team & Services',exact=True)).to_be_focused()
        accessible(page)
        with app.app_context():
            assert Ticket.query.count()==1
            other=Business(name='Second Synthetic Clinic',slug='second-synthetic-clinic',timezone='Asia/Kolkata',is_active=True);db.session.add(other);db.session.flush()
            branch=Branch(business_id=1,name='Second synthetic reception',is_active=True);db.session.add(branch);db.session.flush()
            service=Service(branch_id=branch.id,name='Optical Consultation',prefix='O',average_minutes=5,is_active=True);db.session.add(service);db.session.commit()
        public=browser.new_context(viewport={'width':width,'height':900});visitor=public.new_page()
        visitor.goto(origin+'/app/');expect(visitor.get_by_role('heading',name='Where are you visiting?')).to_be_visible()
        assert visitor.locator('.entry-option').count()==2
        visitor.goto(origin+'/app/b/erode-eye-clinic-demo');expect(visitor.get_by_role('heading',name='Choose your service')).to_be_visible()
        assert visitor.get_by_role('button',name='Join Queue',exact=True).count()==2
        assert visitor.get_by_role('link',name='View branches').count()==0
        accessible(visitor)
        visitor.goto(origin+'/app/?view=display');expect(visitor.get_by_role('heading',name='Choose a waiting-room display')).to_be_visible();accessible(visitor)
        public.close();context.close();browser.close()


@pytest.mark.parametrize('width',[1440,390])
def test_repeat_patient_preserves_unresolved_issuance_across_reload(product_server,width):
    origin,app=product_server
    entry=origin+'/app/b/erode-eye-clinic-demo/service/1'
    with sync_playwright() as pw:
        browser=pw.chromium.launch();patient=browser.new_context(viewport={'width':width,'height':900});page=patient.new_page()
        page.goto(entry);page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E001')
        doctor=browser.new_context()
        csrf=doctor.request.get(origin+'/api/v1/session').json()['csrf_token']
        login=doctor.request.post(origin+'/api/v1/auth/login',form={'username':'tester','password':'test-password-123','csrf_token':csrf})
        assert login.status==200
        def post(path,**fields):
            fields['csrf_token']=doctor.request.get(origin+'/api/v1/session').json()['csrf_token']
            result=doctor.request.post(origin+'/api/v1'+path,form=fields)
            assert result.status==200
            return result
        post('/staff/services/1/call');post('/staff/tickets/1/complete')
        page.goto(entry);expect(page.get_by_role('button',name='Join Queue',exact=True)).to_be_enabled()
        held=[]
        page.route('**/api/v1/services/1/tickets',lambda route:held.append(route))
        page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.get_by_role('button',name='Joining…',exact=True)).to_be_visible()
        assert len(held)==1
        fields={name:values[0] for name,values in parse_qs(held[0].request.post_data).items()}
        pending_key=fields['request_key']
        # Reload before the original POST reaches the database. Its outcome is unknown.
        page.reload();expect(page.get_by_role('button',name='Recover interrupted join',exact=True)).to_be_enabled()
        assert page.evaluate("sessionStorage.getItem('queueless-pending-join:1')")==pending_key
        page.get_by_role('button',name='Recover interrupted join',exact=True).click()
        expect(page.get_by_role('button',name='Joining…',exact=True)).to_be_visible()
        assert len(held)==2
        assert parse_qs(held[1].request.post_data)['request_key']==[pending_key]
        # The original request commits late; the retry must resolve that exact ticket.
        late=patient.request.post(origin+'/api/v1/services/1/tickets',form=fields)
        assert late.status==201 and late.json()['display_number']=='E002'
        held[1].continue_();page.unroute('**/api/v1/services/1/tickets')
        expect(page.locator('.token-display')).to_have_text('E002')
        assert page.evaluate("sessionStorage.getItem('queueless-pending-join:1')") is None
        with app.app_context():
            assert Ticket.query.count()==2
            assert TicketEvent.query.filter_by(event_type='CREATED').count()==2
        # A confirmed successful issuance may be followed by a genuinely new visit.
        post('/staff/services/1/call');post('/staff/tickets/2/complete')
        page.goto(entry);page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E003')
        with app.app_context():assert Ticket.query.count()==3
        post('/staff/services/1/call');post('/staff/tickets/3/complete')
        def lose_response(route):
            response=route.fetch()
            assert response.status==201
            route.abort()
        page.route('**/api/v1/services/1/tickets',lose_response)
        page.goto(entry);page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.get_by_role('button',name='View my token',exact=True)).to_be_enabled(timeout=12000)
        page.unroute('**/api/v1/services/1/tickets')
        page.get_by_role('button',name='View my token',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E004')
        post('/staff/services/1/call');post('/staff/tickets/4/complete')
        page.goto(entry);page.get_by_role('button',name='Recover interrupted join',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E004')
        expect(page.get_by_text('COMPLETED',exact=True)).to_be_visible()
        page.goto(entry);page.get_by_role('button',name='Join Queue',exact=True).click()
        expect(page.locator('.token-display')).to_have_text('E005')
        with app.app_context():
            assert Ticket.query.count()==5
            assert TicketEvent.query.filter_by(event_type='CREATED').count()==5
        patient.close();doctor.close();browser.close()
