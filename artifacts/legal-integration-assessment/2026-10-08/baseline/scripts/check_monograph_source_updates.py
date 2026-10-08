"""Capture publisher-index update metadata; absence is not a clean bill of health."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.localresources/monograph-revision/source-updates'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    papers = json.loads((ROOT / 'docs/papers/manifest.json').read_text())['papers']
    papers += [
        {'id':'legalfictions2024', 'doi':'10.1093/jla/laae003'},
        {'id':'legalrag2024', 'doi':'10.48550/arXiv.2405.20362'}]
    def capture(paper):
        doi = paper.get('doi')
        row = {'key': paper['id'], 'doi': doi, 'status': 'no_registered_doi_in_manifest'}
        if not doi:
            return row
        path = OUT / (paper['id'] + '.json')
        datacite = doi.lower().startswith('10.48550/')
        url = ('https://api.datacite.org/dois/' if datacite else 'https://api.crossref.org/works/') + quote(doi, safe='')
        result = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                                 '--max-time', '30', url, '--output', str(path)], capture_output=True, text=True)
        row.update(url=url, exit_code=result.returncode)
        if result.returncode:
            row.update(status='retrieval_failed', error=result.stderr)
            return row
        try:
            payload = json.loads(path.read_text())
            message = payload['data']['attributes'] if datacite else payload['message']
            row.update(status='metadata_captured_not_exhaustive_retraction_search',
                       agency='DataCite' if datacite else 'Crossref',
                       title=message.get('titles') if datacite else message.get('title'),
                       relation=message.get('relatedIdentifiers') if datacite else message.get('relation'),
                       update_to=message.get('update-to'), updated_by=message.get('updated-by'),
                       path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except (KeyError, ValueError) as exc:
            row.update(status='invalid_metadata', error=str(exc))
        return row
    with ThreadPoolExecutor(max_workers=2) as executor:
        rows = list(executor.map(capture, papers))
    report = {'scope': 'DOIs recorded for the 50 historical editions and two added legal-reliability papers',
              'limitation': 'Registration-agency update fields are incomplete. Missing metadata and no update relation do not establish no correction or retraction.',
              'records': rows}
    (ROOT / 'docs/monograph/review/revision/source-update-check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})}))


if __name__ == '__main__':
    main()
