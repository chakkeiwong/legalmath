#!/usr/bin/env python3
"""Render immutable Catala HTML evidence with print-only pagination repairs."""
import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

STYLE = """
@media print {
  body { margin: 0 !important; max-width: none !important; }
  article, .code-wrapper { break-inside: avoid; }
  h1, h2, h3, .law-heading { break-after: avoid; }
  .highlighttable { width: 100%; table-layout: fixed; }
  .highlighttable .linenos { width: 2em; }
  pre { white-space: pre-wrap !important; overflow-wrap: anywhere; }
  .filename { overflow-wrap: anywhere; }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(args.browser), headless=True,
                                             args=["--no-sandbox", "--disable-gpu"])
        page = browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=1)
        page.route("**/*", lambda route: route.continue_() if route.request.url.startswith("file:") else route.abort())
        for name in ("reviewer-packet", "pilot"):
            source = (args.run / (name + ".html")).resolve()
            page.goto(source.as_uri(), wait_until="load")
            page.add_style_tag(content=STYLE)
            page.screenshot(path=str(args.out / (name + ".png")), full_page=True)
            page.pdf(path=str(args.out / (name + ".pdf")), format="A4", print_background=True,
                     margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"})
            records.append({"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "document": name, "title": page.title(),
                "headings": page.locator("h1,h2,h3").all_text_contents(),
                "scroll_width": page.evaluate("document.documentElement.scrollWidth"), "viewport_width": 1100})
        browser.close()
    (args.out / "layout.json").write_text(json.dumps({"print_css": STYLE, "documents": records,
        "human_acceptance": "pending", "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
