"""Exercise actual interpretation screens against the acceptance database in Chromium."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);out=Path(parser.parse_args().out).resolve()
out.mkdir(parents=True,exist_ok=False)
demo=out.parent/'demonstration';result=json.loads((demo/'result.json').read_text());identities=json.loads((demo/'local-identities.json').read_text())
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'.localresources/browser')
with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
with (out/'server.log').open('w') as log:
    proc=subprocess.Popen([sys.executable,'-m','legalmath.cli','serve','--data-dir',str(demo/'database'),'--identities',str(demo/'local-identities.json'),'--port',str(port)],stdout=log,stderr=subprocess.STDOUT)
    try:
        url=f'http://127.0.0.1:{port}'
        for _ in range(100):
            if proc.poll() is not None: raise RuntimeError('Server exited; see server.log')
            try: urllib.request.urlopen(url,timeout=1).close();break
            except OSError: time.sleep(.05)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1100})
            errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            response=page.goto(url+'/interpretations');assert response.status==200
            page.fill('#token',identities['meaning']['token']);page.fill('#run-id',result['real_circular_run_id']);page.click('#load')
            expect(page.locator('#outcome')).to_contain_text('BLOCKED_UNRESOLVED')
            expect(page.locator('#outcome')).to_contain_text('code.paragraph3.11')
            expect(page.locator('#sources')).to_contain_text('particular type')
            assert page.locator('#issues article').count()==7
            page.fill('#rationale','Browser rejection probe: unresolved source cannot be approved.');page.fill('#objection','Dependencies remain missing.');page.click('#review')
            expect(page.locator('#message')).to_have_text('E_RELEASE_BLOCKED')
            page.fill('#token','');page.screenshot(path=str(out/'real-circular.png'),full_page=False)
            page.fill('#token',identities['meaning']['token']);page.fill('#run-id',result['repair_run_id']);page.click('#load')
            expect(page.locator('#candidates')).to_contain_text('SHARED_RESOLUTION')
            assert page.locator('#candidates article').count()==5
            page.fill('#token','');page.screenshot(path=str(out/'alternatives-and-repair.png'),full_page=False)
            summary=page.locator('summary').last;summary.focus();page.keyboard.press('Enter');assert page.locator('details').last.get_attribute('open')==''
            page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(out/'mobile.png'),full_page=False)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors
            browser.close()
        (out/'result.json').write_text(json.dumps(dict(status='PASSED',actual_browser='Chromium via Playwright',blocked_meaning_review=True,retained_alternatives=5,unresolved_issues=7,keyboard_details=True,mobile_no_horizontal_overflow=True,js_errors=errors,human_usability_review='PENDING'),indent=2)+'\n')
        print('Interpretation browser, blocked approval, alternatives, keyboard and mobile checks passed.')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
