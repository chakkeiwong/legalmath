"""Correct retained navigation locally; keep all original failed source receipts."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
from html import unescape
import json
import re
import sys
import time
from urllib.parse import urljoin, urlsplit

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts import prospectus_ordinance_sources as source
from scripts.prospectus_publication_source_correction import Links

PREP = AUTH / 'reviews/ordinance-navigation-375'
HERE = AUTH / 'attempts/basf-references/attempt-108'
PRIOR = AUTH / 'attempts/basf-references/attempt-107'
PLAN = 'docs/plans/prospectus-ordinance-navigation-repair-2026-10-20.md'
METHOD = 'scripts/prospectus_ordinance_navigation.py'


def costs(extra=0):
    initial = read(PREP / 'accounting-start.json')
    requests = 40 * len(list(HERE.glob('requests/*/started.json')))
    local = extra + sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    local += sum(read(p).get('wall_seconds', 0) for p in PREP.glob('*-execution.json'))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (PLAN, METHOD)); paths.add(AUTH / 'revisions/0375.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in initial['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - initial['program_bytes'])
    total, combined = initial['prior_seconds'] + requests + local + 120, initial['prior_bytes'] + size
    assert requests <= 200 and local < 90 and size < 60 * 1024**2
    assert total < 31000 and combined < 4540 * 1024**2
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_conservative_request_seconds': requests, 'new_measured_local_seconds': local,
        'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 374 and not PREP.exists() and not HERE.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] in ('RECORD', 'REJECT') and e.get('attempt') == rel(PRIOR) for e in events)
    for name, checksum in read(PRIOR / 'outputs.json').items(): assert sha(PRIOR / name) == checksum, name
    previous = source.costs(); assert previous['combined_accounted_seconds'] + 410 < 31000
    assert previous['combined_bytes'] + 64 * 1024**2 < 4544 * 1024**2
    folder = PRIOR / 'requests/directory'; receipt = read(folder / 'receipt.json')
    assert receipt['curl_exit_code'] == 0 and receipt['http_status'] == 200
    raw = (folder / 'body').read_bytes(); headers = (folder / 'headers').read_text()
    assert len(raw) == int(re.findall(r'(?im)^content-length:\s*(\d+)\s*$', headers)[-1])
    assert re.search(r'(?im)^content-encoding:\s*gzip\s*$', headers)
    import zlib
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS); body = decoder.decompress(raw, 2 * 1024**2 + 1)
    assert decoder.eof and not decoder.unused_data and len(body) <= 2 * 1024**2
    charset = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', body[:8192], re.I); assert charset
    html = body.decode(charset[1].decode('ascii'), errors='strict')
    assert html.rstrip().lower().endswith('</html>')
    title = unescape(re.search(r'<title>(.*?)</title>', html, re.S | re.I)[1])
    assert title == 'Gesetze im Internet - Gesetze / Verordnungen - Teilliste'
    assert re.search(r'<h1[^>]*>Gesetze / Verordnungen - Teilliste W</h1>', html)
    links = Links(); links.feed(html); links.close()
    candidates = [r for r in links.rows if r['text'].strip() == 'WpAV']
    assert len(candidates) == 1 and candidates[0]['href'] == './wpaiv/index.html'
    assert 'Verordnung zur Konkretisierung von Anzeige-, Mitteilungs- und Veröffentlichungspflichten nach dem Wertpapierhandelsgesetz' in html
    url = urljoin(receipt['url'], candidates[0]['href'])
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    save(PREP / 'corrected-navigation.json', {'status': 'PASS', 'source': rel(folder / 'body'),
        'encoded_body_sha256': sha(folder / 'body'), 'decoded_bytes': len(body),
        'actual_title': title, 'heading': 'Gesetze / Verordnungen - Teilliste W',
        'literal_href': candidates[0]['href'], 'label': 'WpAV', 'index_url': url,
        'retained_invalid_result': rel(PRIOR / 'local/directory/result.json'),
        'operative_law_established': False, 'historical_application_established': False})
    save(PREP / 'preparation-execution.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began})
    bindings = dict(read(AUTH / 'reviews/ordinance-linked-sources-374/freeze.json')['bindings'])
    bindings.update({n: sha(ROOT / n) for n in (PLAN, METHOD)})
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(PRIOR / n): sha(PRIOR / n) for n in read(PRIOR / 'outputs.json')})
    bindings[rel(PRIOR / 'outputs.json')] = sha(PRIOR / 'outputs.json')
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_change': False})
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 107
    new = deepcopy(program); new['revision'] = 375
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Correct observed official directory parsing locally and read exact linked publication ordinance',
        ordinance_navigation_repair={'review': rel(PREP), 'new_GETs': 5, 'new_local_seconds': 90,
            'new_request_seconds': 200, 'new_other_seconds': 120, 'new_bytes': 64 * 1024**2,
            'cumulative_seconds': 31000, 'cumulative_bytes': 4544 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 108
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 375
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Use corrected literal directory link; inspect full ordinance index and selected publication sections',
                stop_condition='108admissions;5GETs;200request+90local+120other seconds/64MiB;31000s/4544MiB cumulative')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Observed title/heading and WpAV abbreviation correction; reuse complete107 response without another GET'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Correct source binding and operative provision review',
            'promotion_veto': ['Partial/wrong text', 'Lost exception', 'Unproved temporal inference'],
            'continuation_veto': ['Invalid authority', 'Corrupt evidence', 'Exhausted limits'],
            'explanatory_only': ['HTTP status', 'Counts', 'Runtime'],
            'not_concluded': ['Integration', 'Actual compliance', 'Historical law', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 107, 'new_maximum': 108,
            'retained_attempts': attempts, 'reason': 'Two demonstrated local parser assumptions blocked a complete official response',
            'next_discriminating_check': 'Locally corrected navigation then exact index/section texts',
            'stop_condition': '5GETs;200+90+120s/64MiB;unchanged31000s/4544MiB cumulative',
            'same_scope_authorization': 'Continue authorized source build; no directory retry or external messages',
            'all_prior_costs_retained': True},
        'acquisition_revision': {'additional_official_GETs': 5, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 375, 'index_url': url, 'resources': costs()}


def start(key, selected=None):
    assert key != 'directory' and len(list(HERE.glob('requests/*/started.json'))) < 5
    if key != 'index': return source.start(key, selected)
    source.frozen(); url = read(PREP / 'corrected-navigation.json')['index_url']
    assert selected is None or selected == url
    folder = HERE / 'requests/index'; assert not folder.exists()
    command = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', '2097152', '--header', 'Accept-Encoding: gzip',
        '--dump-header', str(folder / 'headers'), '--output', str(folder / 'body'),
        '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code} %{time_total}', url]
    save(folder / 'started.json', {'command': command, 'url': url, 'timeout_seconds': 20,
        'started_at': datetime.now(timezone.utc).isoformat(), 'redirects': False, 'automatic_retries': 0,
        'navigation': rel(PREP / 'corrected-navigation.json')})
    costs(); return {'status': 'READY_FOR_EXACT_GET', 'command': command}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': result = prepare()
    else:
        source.PREP, source.HERE, source.PLAN, source.METHOD, source.costs = PREP, HERE, PLAN, METHOD, costs
        if action == 'start': result = start(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        elif action == 'finish': result = source.finish(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
        elif action == 'extract': result = source.extract(sys.argv[2])
        elif action == 'seal': result = source.seal()
        else: raise SystemExit('Unsupported navigation action')
    print(json.dumps(result))
