"""Compare separately retrieved publications; never change campaign inputs."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent

def reference(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha256(path.read_bytes()).hexdigest())

def headers(path):
    lines = path.read_text().splitlines()
    fields = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            if key.lower() in ('date', 'content-type', 'last-modified', 'etag', 'age'):
                fields[key.lower()] = value.strip()
    return dict(status_lines=[line for line in lines if line.startswith('HTTP/')], fields=fields)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = dict(attrs)
            self.current['text'] = ''
    def handle_data(self, data):
        if self.current is not None:
            self.current['text'] += data
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None

def main():
    started = time.monotonic()
    output = WORK / 'source-check-result.json'
    if output.exists():
        raise RuntimeError('The retained comparison already exists; do not overwrite it')
    pairs = {
        '26EC22': 'docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json',
        '26EC23': '.localresources/sfc/26EC23.json',
    }
    rows = []
    for name, prior in pairs.items():
        fresh, old = WORK / ('fresh-' + name + '.content'), ROOT / prior
        new_value, old_value = json.loads(fresh.read_text()), json.loads(old.read_text())
        if new_value.get('refNo') != name or new_value.get('lang') != 'EN' or not new_value.get('html'):
            raise RuntimeError('Unqualified circular identity: ' + name)
        h = WORK / ('fresh-' + name + '.headers')
        rows.append(dict(name=name, url='https://apps.sfc.hk/edistributionWeb/api/circular/content?refNo=' + name + '&lang=EN',
            current=reference(fresh), baseline=reference(old), headers=reference(h), response=headers(h),
            exact_bytes_equal=fresh.read_bytes() == old.read_bytes(), parsed_equal=new_value == old_value,
            html_equal=new_value['html'] == old_value['html'],
            changed_fields=sorted(k for k in set(new_value) | set(old_value) if new_value.get(k) != old_value.get(k)),
            title=new_value['title'], released_date=new_value['releasedDate']))
    for name, new, prior, url in (
        ('handbook', 'fresh-handbook.pdf', 'ut-handbook-current.pdf', 'https://www.sfc.hk/-/media/EN/assets/components/codes/files-current/web/codes/sfc-handbook-for-unit-trusts-and-mutual-funds/sfc-handbook-for-unit-trusts-and-mutual-funds.pdf'),
        ('codes', 'fresh-codes.html', 'sfc-codes.html', 'https://www.sfc.hk/en/Rules-and-standards/Codes-and-guidelines/Codes'),
    ):
        fresh = WORK / new
        old = ROOT / 'artifacts/legal-mission-control/2026-10-13/master/corpus-work' / prior
        h = WORK / ('fresh-' + name + '.headers')
        if name == 'handbook' and not fresh.read_bytes().startswith(b'%PDF-'):
            raise RuntimeError('Handbook response is not a PDF')
        row = dict(name=name, url=url, current=reference(fresh), baseline=reference(old),
            headers=reference(h), response=headers(h), exact_bytes_equal=fresh.read_bytes() == old.read_bytes())
        if name == 'codes':
            parser = Links()
            parser.feed(fresh.read_text())
            row['current_handbook_links'] = [link for link in parser.links
                if 'files-current/' in link.get('href', '')
                and 'sfc-handbook-for-unit-trusts-and-mutual-funds.pdf' in link.get('href', '')]
            if len(row['current_handbook_links']) != 1:
                raise RuntimeError('Ambiguous current Handbook publication link')
        rows.append(row)
    result = dict(profile='independent-publication-identity-check.v1', at_utc=datetime.now(timezone.utc).isoformat(),
        command='.venv/bin/python ' + str(Path(__file__).resolve().relative_to(ROOT)),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=dict(interpreter=sys.executable, python=sys.version, computation='stdlib CPU-only; no GPU framework imported'),
        seeds='N/A: deterministic source comparison', plan=reference(WORK / 'continuation-source-check.md'),
        implementation=reference(Path(__file__).resolve()), rows=rows,
        all_identity_comparisons_equal=all(row.get('parsed_equal', row['exact_bytes_equal']) for row in rows),
        provider_calls=0, campaign_inputs_changed=False, acquisition_attempts_added=0,
        legal_acceptance=False, actual_answer_citation_use_qualified=False,
        later_treatment_search_refreshed=False,
        conclusion='Fresh official responses preserve the retained publications; no new source standard or legal closure follows.',
        limitations=['Publication identity does not establish client/date applicability.',
            'This is not an exhaustive amendment or later-treatment search.',
            'Original answers and matched tool effects remain incomplete.',
            'No active input, binding, owner or allowance was changed.'],
        wall_seconds=round(time.monotonic() - started, 3))
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in ('at_utc', 'all_identity_comparisons_equal',
        'provider_calls', 'campaign_inputs_changed', 'legal_acceptance', 'conclusion')}, indent=2))

if __name__ == '__main__':
    main()
