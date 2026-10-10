"""Read-only screenshots of the running persisted demo; never log private access."""
import io
import json
from pathlib import Path
import sys
from PIL import Image
import zxingcpp
from playwright.sync_api import sync_playwright,expect
import local_demo as demo
from verify_local_demo_browser import login,accessible,public_snapshot

def main():
    profile=demo.load_profile();app=demo.make_app(profile)
    before=public_snapshot(app);origin=profile['origin']
    assert origin=='http://127.0.0.1:5001' and profile['port']==55434
    evidence=demo.ROOT/'evidence';evidence.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
        for width,height in ((1366,900),(390,844)):
            def page():
                context=browser.new_context(viewport={'width':width,'height':height},
                    http_credentials={'username':profile['gateway_user'],'password':profile['gateway_password']})
                return context.new_page()
            reception=page();login(reception,origin,'receptionist',profile)
            expect(reception.locator('.token-display')).to_have_text('E010')
            expect(reception.get_by_test_id('waiting-count')).to_have_text('5')
            image=reception.context.request.get(origin+'/api/v1/staff/services/1/qr.png')
            assert image.status==200
            assert zxingcpp.read_barcode(Image.open(io.BytesIO(image.body()))).text==profile['urls']['patient']
            doctor=page();login(doctor,origin,'doctor',profile)
            expect(doctor.locator('.current-ticket .token-display')).to_have_text('E010')
            expect(doctor.get_by_role('button',name='Mark Reviewed',exact=True)).to_be_visible()
            owner=page();login(owner,origin,'owner',profile)
            owner.goto(origin+'/app/owner/business/1')
            expect(owner.locator('.today-reviews')).to_contain_text('13 completed consultations today')
            patient=page();patient.goto(profile['urls']['patient'])
            expect(patient.get_by_role('button',name='Join Queue',exact=True)).to_be_visible()
            display=page();display.goto(profile['urls']['display'])
            expect(display.locator('.display-token')).to_have_text('E010')
            for name,view in (('reception',reception),('doctor',doctor),('owner-reviews',owner),('patient-entry',patient),('public-display',display)):
                accessible(view)
                assert view.evaluate('document.documentElement.scrollWidth<=innerWidth')
                view.screenshot(path=str(evidence/f'live-{name}-{width}.png'),full_page=True)
            reception.emulate_media(media='print')
            expect(reception.get_by_alt_text('Eye Consultation service QR')).to_be_visible()
            expect(reception.get_by_role('button',name='Print QR',exact=True)).not_to_be_visible()
            reception.screenshot(path=str(evidence/f'live-qr-print-{width}.png'),full_page=True)
            for context in list(browser.contexts):context.close()
        browser.close()
    assert public_snapshot(app)==before
    result={'desktop_and_mobile_views':10,'print_layouts':2,'axe_violations':0,'horizontal_overflow':False,
            'qr_decodes_to':profile['urls']['patient'],'tickets_and_audit_unchanged':True}
    (evidence/'live-preview-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
