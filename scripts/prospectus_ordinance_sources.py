"""Bounded complete-source discovery with retained encoded transfer evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
from html import unescape
import json
import re
import sys
import time
from urllib.parse import urljoin, urlsplit
import zlib

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts.prospectus_statutory_sources_accounted import SourceHTML
from scripts.prospectus_publication_source_correction import Links

PREP = AUTH / 'reviews/ordinance-linked-sources-374'
HERE = AUTH / 'attempts/basf-references/attempt-107'
PRIOR = AUTH / 'attempts/basf-references/attempt-106'
PLAN = 'docs/plans/prospectus-ordinance-linked-sources-2026-10-20.md'
METHOD = 'scripts/prospectus_ordinance_sources.py'
HOST = 'https://www.gesetze-im-internet.de'
MAX_BYTES = 2 * 1024**2


def costs(extra=0):
    initial = read(PREP / 'accounting-start.json')
    requests = sum(2 * read(p)['timeout_seconds'] for p in HERE.glob('requests/*/started.json'))
    local = extra + sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    local += sum(read(p).get('wall_seconds', 0) for p in PREP.glob('*-execution.json'))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (PLAN, METHOD)); paths.add(AUTH / 'revisions/0374.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in initial['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - initial['program_bytes'])
    total, combined = initial['prior_seconds'] + requests + local + 120, initial['prior_bytes'] + size
    assert requests <= 260 and local < 90 and size < 60 * 1024**2, 'Source increment exhausted'
    assert total < 31000 and combined < 4540 * 1024**2, 'Cumulative source bounds exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_conservative_request_seconds': requests, 'new_measured_local_seconds': local,
        'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 373 and not HERE.exists() and not PREP.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] in ('RECORD', 'REJECT') and e.get('attempt') == rel(PRIOR) for e in events)
    for name, checksum in read(PRIOR / 'outputs.json').items(): assert sha(PRIOR / name) == checksum, name
    from scripts.prospectus_reference_validation import costs as prior_costs
    previous = prior_costs()
    assert previous['combined_accounted_seconds'] + 470 < 31000
    assert previous['combined_bytes'] + 64 * 1024**2 < 4544 * 1024**2
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 106
    save(PREP / 'preparation-execution.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began,
        'changed_method': 'Accept gzip, retain original encoded bytes, directory30s; small literal linked sections',
        'last_integration_status': read(PRIOR / 'result.json')['status'], 'production_change': False})
    names = (PLAN, METHOD, 'scripts/prospectus_default_holder.py',
        'scripts/prospectus_statutory_sources_accounted.py', 'scripts/prospectus_publication_source_correction.py')
    bindings = {n: sha(ROOT / n) for n in names}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')})
    for folder, files in ((PRIOR, ('outputs.json', 'result.json', 'RESULT.md')),
        (AUTH / 'attempts/basf-references/attempt-099', ('outputs.json', 'RESULT.md',
         'requests/directory/body', 'requests/directory/receipt.json'))):
        bindings.update({rel(folder / name): sha(folder / name) for name in files})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_change': False})
    new = deepcopy(program); new['revision'] = 374
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Resolve missing publication implementing provisions through complete official directory and literal small sections',
        ordinance_linked_sources={'review': rel(PREP), 'maximum_new_GETs': 6,
            'new_local_seconds': 90, 'new_request_seconds': 260, 'new_other_seconds': 120,
            'new_bytes': 64 * 1024**2, 'cumulative_seconds': 31000,
            'cumulative_bytes': 4544 * 1024**2, 'production_change': False}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 107
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 374
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Acquire complete ordinance navigation and selected operative provisions; review applicability and consumer consequences',
                stop_condition='107admissions;6logicalGETs;260request+90local+120other seconds;64MiB;31000s/4544MiB cumulative')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Bounded encoded transfer after retained truncation; literal section links; no production change'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Complete identified official source and substantive publication-rule reading',
            'promotion_veto': ['Partial or wrong response', 'Lost qualifier', 'Unproved historical inference'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted limits'],
            'explanatory_only': ['HTTP status', 'Counts', 'Runtime'],
            'not_concluded': ['Integration', 'Actual compliance', 'Historical law', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 106, 'new_maximum': 107,
            'retained_attempts': attempts, 'reason': 'Unresolved implementing-law premise; changed bounded transport after prior truncated directory',
            'next_discriminating_check': 'Complete directory and exact identified ordinance sections',
            'stop_condition': '6logicalGETs;260+90+120s/64MiB increment;unchanged31000s/4544MiB cumulative',
            'same_scope_authorization': 'Continued source research for authorized general build; no messages or branch actions',
            'all_prior_costs_retained': True, 'cumulative_limits_unchanged': True},
        'acquisition_revision': {'additional_official_GETs': 6, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 374, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name
    costs()


def start(key, selected=None):
    frozen()
    if key == 'directory': url = HOST + '/Teilliste_W.html'
    elif key == 'index':
        prior = read(HERE / 'local/directory/result.json'); assert prior['status'] == 'PASS'
        assert selected in [row['url'] for row in prior['ordinance_candidates']]
        url = selected
    else:
        assert re.fullmatch(r'section-[1-4]', key)
        prior = read(HERE / 'local/index/result.json'); assert prior['status'] == 'PASS'
        selection = read(HERE / 'section-selection.json')
        assert selected == selection[key]['url'] and selection[key]['reason'].strip()
        assert selected in [row['url'] for row in prior['sections']]
        url = selected
    parsed = urlsplit(url)
    assert parsed.scheme == 'https' and parsed.netloc == 'www.gesetze-im-internet.de'
    assert not parsed.query and not parsed.fragment
    if key != 'directory': assert parsed.path != '/Teilliste_W.html'
    folder = HERE / 'requests' / key; assert not folder.exists(), 'No redispatch'
    assert len(list(HERE.glob('requests/*/started.json'))) < 6
    seconds = 30 if key == 'directory' else 20
    command = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', str(seconds),
        '--connect-timeout', '8', '--max-filesize', str(MAX_BYTES), '--header', 'Accept-Encoding: gzip',
        '--dump-header', str(folder / 'headers'), '--output', str(folder / 'body'),
        '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code} %{time_total}', url]
    save(folder / 'started.json', {'command': command, 'url': url,
        'timeout_seconds': seconds, 'started_at': datetime.now(timezone.utc).isoformat(),
        'context': 'trusted after retained same-host sandbox DNS failures', 'redirects': False,
        'automatic_retries': 0, 'decoded_by_curl': False})
    costs(); return {'status': 'READY_FOR_EXACT_GET', 'command': command}


def finish(key, code, elapsed):
    frozen(); folder = HERE / 'requests' / key
    headers = (folder / 'headers').read_text() if (folder / 'headers').exists() else ''
    statuses = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers)
    status = int(statuses[-1]) if statuses else None
    save(folder / 'receipt.json', {'status': 'RETAINED' if code == 0 and status == 200 else 'UNAVAILABLE',
        'curl_exit_code': code, 'http_status': status, 'actual_transfer_seconds': elapsed,
        'execution_context': 'trusted', 'url': read(folder / 'started.json')['url'],
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'receipt.json'}})
    return {'status': 'RECORDED', 'http_status': status, 'resources': costs()}


def extract(key):
    frozen(); began = time.monotonic(); folder = HERE / 'requests' / key
    output = HERE / 'local' / key; receipt = read(folder / 'receipt.json')
    for name, checksum in receipt['files'].items(): assert sha(folder / name) == checksum, name
    result = {'status': 'UNAVAILABLE', 'key': key, 'url': receipt['url']}
    if receipt['status'] == 'RETAINED':
        try:
            raw = (folder / 'body').read_bytes(); assert 0 < len(raw) <= MAX_BYTES
            headers = (folder / 'headers').read_text()
            lengths = re.findall(r'(?im)^content-length:\s*(\d+)\s*$', headers)
            assert not lengths or len(raw) == int(lengths[-1]), 'Truncated declared encoded body'
            encodings = re.findall(r'(?im)^content-encoding:\s*([^\r\n]+)', headers)
            encoding = encodings[-1].strip().lower() if encodings else 'identity'
            assert encoding in ('identity', 'gzip'), 'Unsupported transfer representation'
            body = raw
            if encoding == 'gzip':
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                body = decoder.decompress(raw, MAX_BYTES + 1)
                assert len(body) <= MAX_BYTES and decoder.eof and not decoder.unused_data, 'Incomplete or excessive gzip'
            charset = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', body[:8192], re.I)
            assert charset, 'Declared character encoding required'
            html = body.decode(charset[1].decode('ascii'), errors='strict')
            assert html.rstrip().lower().endswith('</html>'), 'Complete closing HTML required'
            title = re.search(r'<title>(.*?)</title>', html, re.I | re.S); assert title
            title = unescape(title[1]); links = Links(); links.feed(html); links.close()
            parser = SourceHTML(); parser.feed(html); parser.close()
            text = '\n'.join(line for line in (' '.join(s.split()) for s in ''.join(parser.text).splitlines()) if line) + '\n'
            assert '\ufffd' not in text
            rows = [{'text': ' '.join(r['text'].split()), 'url': urljoin(receipt['url'], r['href'])} for r in links.rows]
            result.update(status='PASS', title=title, encoded_body_sha256=sha(folder / 'body'),
                encoded_bytes=len(raw), decoded_bytes=len(body), content_encoding=encoding,
                historical_application_established=False, operative_review_required=True)
            if key == 'directory':
                assert 'Gesetze' in title and 'W' in title
                candidates = [r for r in rows if 'Wertpapierhandelsanzeige' in r['text'] or r['text'] == 'WpAIV']
                assert candidates, 'Complete directory does not identify candidate ordinance'
                result['ordinance_candidates'] = candidates
            else:
                assert 'WpAIV' in title or 'WpAV' in title, 'Exact ordinance title required'
                if key == 'index':
                    sections = [r for r in rows if re.search(r'/__\d+[a-z]?\.html$', r['url'])
                                and urlsplit(r['url']).netloc == 'www.gesetze-im-internet.de']
                    assert sections, 'Literal operative section links required'
                    result['sections'] = sections
                else:
                    expected = read(HERE / 'section-selection.json')[key]
                    assert expected['title_fragment'] in text and '§' in title, 'Selected section differs'
            output.mkdir(parents=True, exist_ok=True)
            with (output / 'text.txt').open('x') as stream: stream.write(text)
            save(output / 'links.json', rows)
        except Exception as error:
            result.update(status='INVALID_SOURCE', kind=type(error).__name__, error=str(error))
    result['wall_seconds'] = time.monotonic() - began
    save(output / 'result.json', result); costs(); return result


def seal():
    frozen(); assert (HERE / 'SOURCE-REVIEW.md').is_file() and (HERE / 'RESULT.md').is_file()
    requests = {p.parent.name for p in HERE.glob('requests/*/started.json')}
    results = {p.parent.name: read(p)['status'] for p in HERE.glob('local/*/result.json')}
    assert requests == set(results) and requests
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'ORDINANCE_SOURCE_REVIEW', 'source_results': results,
        'consumer_integration_established': False, 'resources': costs(),
        'next_action': 'Follow inspected implementing provisions or retain exact source blockers; no automatic legal promotion'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted(HERE.glob('requests/*/started.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A source reading', 'data_version': {p.parent.name: sha(p) for p in HERE.glob('requests/*/body')},
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in ('outputs.json', 'admission.json')})
    return result


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'start': result = start(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif action == 'finish': result = finish(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    elif action == 'extract': result = extract(sys.argv[2])
    elif action in ('prepare', 'seal'): result = globals()[action]()
    else: raise SystemExit('Unsupported source action')
    print(json.dumps(result))
