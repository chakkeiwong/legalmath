"""Two linked official source requests; no production or source-history rewrite."""
from copy import deepcopy
from datetime import datetime, timezone
from html import unescape
import json
import re
import sys
import time
from urllib.parse import urljoin, urldefrag, urlsplit
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts.prospectus_statutory_sources_accounted import SourceHTML

PREP = AUTH / 'reviews/election-sources-368'
HERE = AUTH / 'attempts/basf-references/attempt-101'
PRIOR = AUTH / 'attempts/basf-references/attempt-100'
BASE = AUTH / 'attempts/basf-office/attempt-006'
SOURCE = AUTH / 'attempts/basf-references/attempt-098'
PLAN = 'docs/plans/prospectus-election-source-route-2026-10-20.md'
METHOD = 'scripts/prospectus_election_sources.py'


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    requests = 40 * len(list(HERE.glob('requests/*/started.json')))
    local = extra + sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    local += sum(read(p).get('wall_seconds', 0) for p in PREP.glob('preparation-result.json'))
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in (PLAN, METHOD)); files.add(AUTH / 'revisions/0368.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['prior_seconds'] + requests + local + 120
    combined = start['prior_bytes'] + size
    assert local < 90 and requests <= 80 and size < 60 * 1024**2, 'Source increment bounds'
    assert total < 28000 and combined < 4348 * 1024**2, 'Original reference cumulative bounds'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_conservative_request_seconds': requests, 'new_local_seconds': local,
        'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    started = time.monotonic(); program = read(AUTH / 'program.json'); assert program['revision'] == 367
    events = Authority(ROOT).events()
    assert any(e['kind'] == 'RECORD' and e.get('attempt') == rel(BASE) for e in events)
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 100
    for folder in (PRIOR, BASE, SOURCE):
        for name, checksum in read(folder / 'outputs.json').items(): assert sha(folder / name) == checksum, name
    links = read(SOURCE / 'local/issuer-definition/links.json')
    candidates = {urldefrag(urljoin('https://www.gesetze-im-internet.de/wphg/__2.html', h))[0]
        for h in links if h.startswith('index.html#')}
    assert candidates == {'https://www.gesetze-im-internet.de/wphg/index.html'}
    from scripts.prospectus_issuer_qualification import costs as prior_costs
    previous = prior_costs()
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resource_record': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    save(PREP / 'config.json', {'index': candidates.pop(),
        'source_navigation': rel(SOURCE / 'local/issuer-definition/links.json'),
        'current_answer': rel(BASE / 'ordinary-answer.json.gz')})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - started,
        'actual_navigation_validated': True, 'earlier_transport_failures_retained': True})
    bindings = {n: sha(ROOT / n) for n in (PLAN, METHOD, 'scripts/prospectus_default_holder.py',
        'scripts/prospectus_statutory_sources_accounted.py', 'scripts/prospectus_issuer_qualification.py')}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')})
    for folder, names in ((BASE, ('ordinary-answer.json.gz', 'outputs.json', 'result.json')),
            (SOURCE, ('local/issuer-definition/links.json', 'requests/issuer-definition/body', 'outputs.json')),
            (PRIOR, ('outputs.json', 'result.json'))):
        bindings.update({rel(folder / n): sha(folder / n) for n in names})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_change': False})
    new = deepcopy(program); new['revision'] = 368
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Inspect missing home-state election provisions through actual linked official statute index',
        election_sources={'review': rel(PREP), 'maximum_new_GETs': 2, 'production_change': False,
            'original_task_complete': False, 'new_local_seconds': 90, 'new_request_charge': 80,
            'new_other_charge': 120, 'new_bytes': 64 * 1024**2,
            'cumulative_seconds': 28000, 'cumulative_bytes': 4352 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 101
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 368
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Inspect linked complete WpHG election law or retain exact transport failure; no guessed ordinance route',
                stop_condition='101 admissions;2 logical GETs;90local+80request+120other seconds;64MiB increment;28000s/4352MiB cumulative')
        elif row['task'] == 'finance-conventions':
            row['remaining'] = '012 implements scheduled principal and all ten coupons with exact ordinary/installed equality. Floating/reset/call/FX/tax and broader settlement remain unsupported; actual holdings follow the build.'
            row['next_action'] = 'Preserve012; reconcile supported financial-domain acceptance and distinct original source requirements without repeating fixed-fraction checks'
        elif row['task'] == 'basf-office':
            row['remaining'] = '006 records conditional designated-office/country/notice composition. Actual office designation, historical applicability and whole-source acceptance remain unresolved.'
            row['next_action'] = 'Preserve006 and unknown B54; acquire exact role-specific designation if available or continue distinct source requirements'
        elif row['task'] == 'basf-meanings':
            row['remaining'] = '023 records explicit holder-authority composition; original three default(f) readings remain unselected and nonexhaustive.'
            row['next_action'] = 'Preserve023; inspect distinct original wording/applicability gaps and full-scope acceptance, with no external-opinion prerequisite'
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Actual source navigation in current shell environment; preserve previous transport failures',
            'Refresh stale finance/office/meaning continuation descriptions from retained results'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Complete official statute with inspected operative election provisions and exceptions',
            'promotion_veto': ['Incomplete source', 'Wrong identity', 'Invented historical application'],
            'continuation_veto': ['Invalid authority', 'Corrupt evidence', 'Exhausted cumulative bounds'],
            'explanatory_only': ['HTTP status', 'Counts', 'Runtime'],
            'not_concluded': ['Consumer integration', 'Actual election', 'Historical law', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 100, 'new_maximum': 101,
            'retained_attempts': attempts, 'reason': 'Missing textual dependencies; changed actual tool environment and linked whole-statute route',
            'next_discriminating_check': 'Complete actually linked official index then full statute',
            'stop_condition': '2 logical GETs;90+80+120s/64MiB new;28000s/4352MiB cumulative;no unchanged retry',
            'same_scope_authorization': 'User authorized continued original source research; no external message or branch action'},
        'acquisition_revision': {'additional_official_GETs': 2, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 368, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name
    costs()


def start(key):
    frozen(); assert key in ('index', 'full')
    if key == 'index': url = read(PREP / 'config.json')['index']
    else:
        source = read(HERE / 'local/index/result.json'); assert source['status'] == 'PASS'
        url = source['complete_text_url']
    parsed = urlsplit(url)
    assert parsed.scheme == 'https' and parsed.netloc == 'www.gesetze-im-internet.de'
    assert parsed.path.startswith('/wphg/') and not parsed.query and not parsed.fragment
    assert len(list(HERE.glob('requests/*/started.json'))) < 2
    folder = HERE / 'requests' / key
    argv = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', str((2 if key == 'index' else 8) * 1024**2),
        '--dump-header', str(folder / 'headers'), '--output', str(folder / 'body'),
        '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code} %{time_total}', url]
    save(folder / 'started.json', {'command': argv, 'url': url, 'started_at': datetime.now(timezone.utc).isoformat(),
        'logical_request': key, 'automatic_retries': 0, 'redirects': False})
    return {'status': 'READY_FOR_EXACT_GET', 'command': argv}


def finish(key, code, transfer):
    frozen(); folder = HERE / 'requests' / key
    headers = (folder / 'headers').read_text() if (folder / 'headers').exists() else ''
    matches = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers)
    status = int(matches[-1]) if matches else None
    save(folder / 'receipt.json', {'status': 'RETAINED' if code == 0 and status == 200 else 'UNAVAILABLE',
        'curl_exit_code': code, 'http_status': status, 'actual_transfer_seconds': transfer,
        'conservative_charge_seconds': 40, 'url': read(folder / 'started.json')['url'],
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'receipt.json'}})
    return {'status': 'RECORDED', 'key': key, 'http_status': status, 'resources': costs()}


def extract(key):
    frozen(); began = time.monotonic(); folder = HERE / 'requests' / key; output = HERE / 'local' / key
    receipt = read(folder / 'receipt.json')
    for name, checksum in receipt['files'].items(): assert sha(folder / name) == checksum, name
    result = {'status': 'UNAVAILABLE', 'key': key}
    if receipt['status'] == 'RETAINED':
        try:
            raw = (folder / 'body').read_bytes(); assert 0 < len(raw) <= (2 if key == 'index' else 8) * 1024**2
            charset = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', raw[:8192], re.I); assert charset
            html = raw.decode(charset[1].decode('ascii'), errors='strict')
            title = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
            assert title and html.rstrip().lower().endswith('</html>'), 'Complete HTML required'
            title = unescape(title[1]); assert 'WpHG' in title, 'Correct statute identity required'
            parser = SourceHTML(); parser.feed(html); parser.close()
            text = '\n'.join(line for line in (' '.join(x.split()) for x in ''.join(parser.text).splitlines()) if line) + '\n'
            assert '\ufffd' not in text
            result = {'status': 'PASS', 'key': key, 'title': title, 'url': receipt['url'],
                'source_sha256': sha(folder / 'body'), 'historical_application_established': False}
            if key == 'index':
                links = {urldefrag(urljoin(receipt['url'], h))[0] for h in parser.links if re.search(r'BJNR\d+\.html$', h)}
                assert len(links) == 1, 'One actually linked complete HTML required'
                result['complete_text_url'] = links.pop()
            else:
                assert all('§ ' + str(n) in text for n in (2, 4, 5, 50)), 'Required sections absent'
            output.mkdir(parents=True, exist_ok=True)
            with (output / 'text.txt').open('x') as stream: stream.write(text)
            save(output / 'links.json', parser.links)
        except Exception as error:
            result = {'status': 'INVALID_SOURCE', 'key': key, 'kind': type(error).__name__, 'error': str(error)}
    result['wall_seconds'] = time.monotonic() - began
    save(output / 'result.json', result); costs()
    return result


def seal():
    frozen(); assert (HERE / 'SOURCE-REVIEW.md').is_file() and (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'ELECTION_SOURCE_REVIEW', 'production_changed': False,
        'sources': {p.parent.name: read(p)['status'] for p in HERE.glob('local/*/result.json')},
        'resources': costs(), 'next_action': 'Use reviewed sources for a distinct conditional extension; retain unavailable source branches'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p)['command'] for p in HERE.glob('requests/*/started.json')],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'No numerical/GPU execution',
        'seeds': 'N/A source research', 'data_version': sha(PREP / 'freeze.json'),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in ('admission.json', 'outputs.json')})
    return result


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'finish': result = finish(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    elif action in ('start', 'extract'): result = globals()[action](sys.argv[2])
    elif action in ('prepare', 'seal'): result = globals()[action]()
    else: raise ValueError('Unknown source action')
    print(json.dumps(result))
