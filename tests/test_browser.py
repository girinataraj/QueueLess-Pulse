import os
from pathlib import Path
from threading import Thread
import pytest
from werkzeug.serving import make_server

@pytest.fixture
def live_server(browser_application):
    server = make_server('127.0.0.1', 0, browser_application, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

@pytest.mark.browser
def test_browser_database_connections_are_independent(browser_application):
    from models import db
    from sqlalchemy import text
    with browser_application.app_context():
        with db.engine.connect() as first, db.engine.connect() as second:
            # Polling requests must not concurrently share a SQLite connection
            # or let one request roll back another request's transaction.
            assert first.connection.driver_connection is not second.connection.driver_connection
            first.execute(text("INSERT INTO staff (username, password_hash, is_active) VALUES ('uncommitted', 'test-only', 1)"))
            assert second.scalar(text("SELECT count(*) FROM staff WHERE username = 'uncommitted'")) == 0
            second.rollback()
            first.commit()
            assert second.scalar(text("SELECT count(*) FROM staff WHERE username = 'uncommitted'")) == 1

@pytest.mark.browser
@pytest.mark.parametrize('viewport', [{'width':1280,'height':900},{'width':390,'height':844}],ids=['desktop','mobile'])
def test_complete_workflow(live_server, viewport):
    from playwright.sync_api import sync_playwright, expect
    with sync_playwright() as pw:
        executable = os.getenv('PLAYWRIGHT_EXECUTABLE_PATH')
        browser = pw.chromium.launch(executable_path=executable, headless=True)
        customer_context = browser.new_context(viewport=viewport)
        customer = customer_context.new_page()
        errors = []
        customer.on('pageerror',lambda error: errors.append(str(error)))
        customer.goto(live_server)
        customer.get_by_role('button',name='Join Queue').first.click()
        expect(customer.locator('.token-display')).to_have_text('G001')
        expect(customer.locator('.status-badge')).to_have_text('WAITING')
        staff_context = browser.new_context(viewport=viewport)
        staff = staff_context.new_page()
        staff.goto(live_server+'/staff/login')
        staff.get_by_label('Username').fill('tester')
        staff.get_by_label('Password').fill('test-password-123')
        staff.get_by_role('button',name='Login',exact=True).click()
        expect(staff.get_by_role('heading',name='Queue Dashboard')).to_be_visible()
        assert staff.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        display = staff_context.new_page()
        display.goto(live_server+'/display')
        staff.get_by_role('button',name='Call Next').first.click()
        expect(customer.locator('.status-badge')).to_have_text('CALLED',timeout=10000)
        expect(display.locator('.display-token').first).to_have_text('G001',timeout=10000)
        staff.get_by_role('button',name='Complete',exact=True).click()
        expect(customer.locator('.status-badge')).to_have_text('COMPLETED',timeout=10000)
        expect(display.locator('.display-token').first).to_have_text('---',timeout=10000)
        assert customer.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        # Exercise failure and reconnection states on actual polling requests.
        customer.route('**/ticket/*/status',lambda route: route.abort())
        expect(customer.locator('#connection-status')).to_contain_text('Connection lost',timeout=10000)
        customer.unroute('**/ticket/*/status')
        expect(customer.locator('#connection-status')).to_contain_text('Connected',timeout=10000)
        customer.evaluate('async () => { await navigator.serviceWorker.ready; }')
        customer.wait_for_function('async () => (await caches.keys()).includes("queueless-static-v3")')
        cached = customer.evaluate('async () => { const keys = await caches.keys(); const urls = []; for(const key of keys){const cache=await caches.open(key); for(const req of await cache.keys()) urls.push(new URL(req.url).pathname);} return urls; }')
        assert len(cached) == 3
        assert all(path.startswith('/static/') for path in cached)
        display.route('**/api/display_data',lambda route:route.abort())
        expect(display.locator('#last-update')).to_contain_text('Connection lost',timeout=10000)
        display.unroute('**/api/display_data')
        expect(display.locator('#last-update')).to_contain_text('Connected',timeout=10000)
        assert errors == []
        Path('evidence').mkdir(exist_ok=True)
        customer.screenshot(path=f"evidence/workflow-{viewport['width']}.png",full_page=True)
        browser.close()
