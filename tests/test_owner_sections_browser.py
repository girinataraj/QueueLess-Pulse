"""Owner consolidation acceptance using an owned disposable PostgreSQL schema."""
from test_postgres import pg_app
from test_product_browser import product_server,sign_in,accessible
import pytest
from playwright.sync_api import sync_playwright,expect

@pytest.mark.parametrize('width',[1366,390])
def test_owner_four_sections_preserve_administration_and_unsaved_forms(product_server,width):
    origin,_=product_server
    with sync_playwright() as pw:
        browser=pw.chromium.launch();context=browser.new_context(viewport={'width':width,'height':900});page=context.new_page()
        sign_in(page,origin,'operations_owner','isolated-test-password-123','owner')
        tabs=page.get_by_role('tablist',name='Business sections')
        expect(tabs.get_by_role('tab')).to_have_count(4)
        expect(tabs.get_by_role('tab')).to_have_text(['Overview','Team & Services','Reviews','Settings'])
        page.get_by_role('tab',name='Team & Services',exact=True).click()
        expect(page.locator('#services')).to_be_visible()
        team=page.locator('#team');team.locator('summary').first.click()
        team.get_by_text('Create staff securely',exact=True).click()
        draft=team.get_by_label('Username',exact=False);draft.fill('unfinished_draft')
        page.get_by_role('tab',name='Reviews',exact=True).click()
        expect(page.get_by_role('heading',name="Today's Reviews",exact=True)).to_be_visible()
        expect(draft).not_to_be_visible()
        page.get_by_role('tab',name='Team & Services',exact=True).click()
        expect(draft).to_have_value('unfinished_draft')
        page.get_by_role('tab',name='Overview',exact=True).focus();page.keyboard.press('ArrowRight')
        expect(page.get_by_role('tab',name='Team & Services',exact=True)).to_be_focused()
        page.keyboard.press('End');expect(page.get_by_role('tab',name='Settings',exact=True)).to_be_focused()
        expect(page.get_by_role('heading',name='Business profile')).to_be_visible()
        page.keyboard.press('Home');expect(page.get_by_role('tab',name='Overview',exact=True)).to_be_focused()
        for section in ('services','team','branches','profile'):
            page.goto(origin+'/app/owner/business/1?section='+section)
            selected='Settings' if section=='profile' else 'Team & Services'
            expect(page.get_by_role('tab',name=selected,exact=True)).to_have_attribute('aria-selected','true')
            expect(page.locator('#'+section)).to_be_visible()
            accessible(page)
        context.close();browser.close()
