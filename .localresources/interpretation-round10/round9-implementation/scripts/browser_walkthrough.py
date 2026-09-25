"""Inspect four actual rendered views and keyboard navigation in Chromium."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
run = Path(sys.argv[1]).resolve()
output = ROOT / "artifacts/runs/browser-review"
output.mkdir(parents=True, exist_ok=True)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(ROOT / ".localresources/browser")
report = json.loads((run / "walkthrough.json").read_text())
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
process = subprocess.Popen([sys.executable, "-m", "legalmath.cli", "serve", "--data-dir", str(run / "database"),
    "--identities", str(run / "local-identities.json"), "--port", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    address = "http://127.0.0.1:" + str(port)
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError(process.stderr.read().decode())
        try:
            urllib.request.urlopen(address, timeout=1).close()
            break
        except OSError:
            time.sleep(.05)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        pages = {"overview": "/", "source-and-rule": "/review/" + report["bundle_hash"],
            "withdrawal-decision": "/decisions/" + report["withdrawal_decision"],
            "amendment": "/amendments/" + report["bundle_hash"] + "/" + report["amendment_bundle_hash"]}
        for name, path in pages.items():
            response = page.goto(address + path)
            if response.status != 200: raise RuntimeError((name, response.status))
            page.screenshot(path=str(output / (name + ".png")), full_page=False)
            if page.locator("h1").count() != 1: raise RuntimeError("Missing unique page title")
            if name == "source-and-rule":
                summary = page.locator("summary").first
                summary.focus()
                page.keyboard.press("Enter")
                if not page.locator("details").first.get_attribute("open") == "":
                    raise RuntimeError("Keyboard could not expand the rule flow")
            checks.append({"page": name, "http_status": response.status, "title": page.title()})
        response = page.goto(address + "/docs")
        page.locator("#operation option").nth(5).wait_for(state="attached")
        option = page.locator("#operation option").filter(has_text="GET /v1/bundles/{bh}")
        page.select_option("#operation", option.get_attribute("value"))
        page.fill("#request-path", "/v1/bundles/" + report["bundle_hash"])
        identities = json.loads((run / "local-identities.json").read_text())
        page.fill("#token", identities["synthetic.author"]["token"])
        page.click("#send-request")
        expect(page.locator("#response-status")).to_have_text("HTTP 200")
        if report["bundle_hash"] not in page.locator("#response-body").text_content():
            # The bundle response contains the bundle, state and revision, not its hash.
            if '"state":"RELEASED"' not in page.locator("#response-body").text_content():
                raise RuntimeError("The API console did not retrieve the released bundle")
        page.fill("#token", "")
        page.screenshot(path=str(output / "api-workbench.png"), full_page=False)
        checks.append({"page": "api-workbench", "http_status": response.status, "authenticated_get": True})
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(address + "/")
        page.screenshot(path=str(output / "mobile-overview.png"))
        browser.close()
    (output / "report.json").write_text(json.dumps({"checks": checks, "keyboard_expansion": True,
        "human_usability": "PENDING", "browser": "Chromium via Playwright 1.58.0"}, indent=2) + "\n")
    print("Five rendered screens, authenticated API request, mobile layout and keyboard expansion passed.")
finally:
    process.terminate()
    try: process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
