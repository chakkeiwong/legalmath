"""Bounded official discovery and election-source continuation of reference098."""
from copy import deepcopy
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import json
import re
import sys
import time
from urllib.parse import urljoin, urlsplit

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel
from scripts.prospectus_statutory_sources_accounted import SourceHTML
from legalmath.prospectus.execution_authority import Authority, digest

PREP = AUTH / 'reviews/publication-source-correction-364'
HERE = AUTH / 'attempts/basf-references/attempt-099'
PRIOR = AUTH / 'attempts/basf-references/attempt-098'
PLAN = 'docs/plans/prospectus-publication-source-correction-2026-10-20.md'
METHOD = 'scripts/prospectus_publication_source_correction.py'
HOST = 'https://www.gesetze-im-internet.de'
URLS = {'directory': HOST + '/Teilliste_W.html',
        'election': HOST + '/wphg/__4.html', 'election-publication': HOST + '/wphg/__5.html'}


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.active = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a': self.active = {'href': dict(attrs).get('href', ''), 'text': ''}

    def handle_data(self, data):
        if self.active is not None: self.active['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.active is not None:
            self.rows.append(self.active); self.active = None


def costs():
    start = read(PREP / 'accounting-start.json')
    request_charges = 20 * len(list(HERE.glob('requests/*/receipt.json')))
    local = sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in (PLAN, METHOD))
    files.add(AUTH / 'revisions/0364.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['prior_accounted_seconds'] + request_charges + local + 120
    combined = start['prior_bytes'] + size
    assert request_charges + local <= 150 and size < 44 * 1024**2
    assert total < 27000 and combined < 4092 * 1024**2
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_local_seconds': local, 'new_conservative_request_seconds': request_charges,
        'new_conservative_other_seconds': 120, 'new_bytes': size,
        'prior_accounted_seconds': start['prior_accounted_seconds'],
        'new_logical_GETs_started': len(list(HERE.glob('requests/*/started.json'))),
        'earlier_manual_time': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    program = read(AUTH / 'program.json'); assert program['revision'] == 363
    events = Authority(ROOT).events()
    assert any(e['kind'] == 'RECORD' and e.get('attempt', '').endswith('basf-references/attempt-098') for e in events)
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 98
    for name, checksum in read(PRIOR / 'outputs.json').items(): assert sha(PRIOR / name) == checksum
    from scripts.prospectus_publication_prerequisites import costs as prior_costs
    carried = prior_costs()
    save(PREP / 'accounting-start.json', {
        'prior_accounted_seconds': read(PRIOR / 'ACCOUNTING-ADDENDUM.json')['carry_forward_accounted_seconds'],
        'prior_bytes': carried['combined_bytes'], 'prior_sealed_resources': read(PRIOR / 'result.json')['resources'],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    names = [PLAN, METHOD, 'scripts/prospectus_default_holder.py',
        'scripts/prospectus_statutory_sources_accounted.py', 'scripts/prospectus_publication_prerequisites.py',
        rel(PRIOR / 'outputs.json'), rel(PRIOR / 'result.json'), rel(PRIOR / 'ACCOUNTING-ADDENDUM.json'),
        rel(PREP / 'accounting-start.json')]
    bindings = {n: sha(ROOT / n) for n in names}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_changes': False})
    new = deepcopy(program); new['revision'] = 364
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Correct failed ordinance route through official directory and inspect WpHG4/5 dependencies',
        publication_source_correction={'review': rel(PREP), 'maximum_new_GETs': 5,
            'original_task_complete': False, 'production_changes': False,
            'new_execution_seconds': 150, 'new_other_charge_seconds': 120,
            'new_bytes': 48 * 1024**2, 'cumulative_seconds': 27000, 'cumulative_bytes': 4096 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 99
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 364
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Discover exact official ordinance; independently inspect home-state election sources; review all results',
                stop_condition='99 admissions;5 GETs;150+120s/48MiB new;27000s/4096MiB cumulative;no production changes')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Official discovery replaces guessed ordinance URL; elections sources are independent',
                    'One original-task admission; retained five-second accounting correction and all historical costs'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Complete identified official sources with operative-section and exception review',
            'promotion_veto': ['Incorrect identity', 'Incomplete source', 'Lost qualifier', 'Invented historical applicability'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Cumulative exhaustion'],
            'explanatory_only': ['HTTP status', 'Counts', 'Time'],
            'not_concluded': ['Consumer integration', 'Actual issuer qualification', 'Historical law', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 98, 'new_maximum': 99,
            'retained_attempts': attempts, 'reason': 'Source098 established wrong candidate route and uninspected textual dependencies',
            'next_discriminating_check': 'Official directory and exact operative ordinance/election provisions',
            'stop_condition': '5 GETs;150+120s/48MiB new;27000s/4096MiB cumulative',
            'same_scope_authorization': 'User authorized source research and continued general build after restart'},
        'acquisition_revision': {'additional_official_GETs': 5, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 364, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name
    costs()


def start(key, selected=None):
    frozen()
    if key == 'ordinance-index':
        source = read(HERE / 'local/directory/result.json'); assert source['status'] == 'PASS'
        assert selected in [r['url'] for r in source['ordinance_candidates']]
        url = selected
    elif key == 'ordinance-full':
        source = read(HERE / 'local/ordinance-index/result.json'); assert source['status'] == 'PASS'
        url = source['complete_text_url']
        assert urlsplit(url).path.rsplit('/', 1)[0] == urlsplit(source['url']).path.rstrip('/').removesuffix('/index.html')
    else: url = URLS[key]
    parsed = urlsplit(url)
    assert parsed.scheme == 'https' and parsed.netloc == 'www.gesetze-im-internet.de'
    assert not parsed.query and not parsed.fragment
    folder = HERE / 'requests' / key
    assert len(list(HERE.glob('requests/*/started.json'))) < 5
    command = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', '2097152', '--dump-header', str(folder / 'headers'),
        '--output', str(folder / 'body'), '--stderr', str(folder / 'stderr'),
        '--write-out', '%{http_code} %{time_total}', url]
    save(folder / 'started.json', {'command': command, 'url': url,
        'started_at': datetime.now(timezone.utc).isoformat(), 'redirects': False, 'retries': 0})
    return {'status': 'READY_FOR_EXACT_GET', 'key': key, 'command': command}


def finish(key, code, transfer):
    frozen(); folder = HERE / 'requests' / key
    headers = (folder / 'headers').read_text() if (folder / 'headers').exists() else ''
    matches = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers); status = int(matches[-1]) if matches else None
    save(folder / 'receipt.json', {'status': 'RETAINED' if code == 0 and status == 200 else 'UNAVAILABLE',
        'curl_exit_code': code, 'http_status': status, 'url': read(folder / 'started.json')['url'],
        'curl_reported_transfer_seconds': transfer, 'conservative_charge_seconds': 20,
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'receipt.json'}})
    return {'status': 'RECORDED', 'key': key, 'http_status': status}


def extract(key):
    frozen(); started = time.monotonic(); folder = HERE / 'requests' / key
    receipt = read(folder / 'receipt.json'); output = HERE / 'local' / key
    if receipt['status'] != 'RETAINED':
        save(output / 'result.json', {'status': 'UNAVAILABLE', 'key': key, 'wall_seconds': time.monotonic() - started})
        return {'status': 'UNAVAILABLE', 'key': key}
    for name, checksum in receipt['files'].items(): assert sha(folder / name) == checksum
    raw = (folder / 'body').read_bytes(); assert 0 < len(raw) <= 2097152
    charset = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', raw[:8192], re.I)
    assert charset, 'Explicit charset required'
    html = raw.decode(charset[1].decode('ascii'), errors='strict')
    title = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    assert title and html.rstrip().lower().endswith('</html>'), 'Complete HTML required'
    title = unescape(title[1]); parser = SourceHTML(); parser.feed(html); parser.close()
    text = '\n'.join(line for line in (' '.join(x.split()) for x in ''.join(parser.text).splitlines()) if line) + '\n'
    assert '\ufffd' not in text
    result = {'status': 'PASS', 'key': key, 'url': receipt['url'], 'title': title,
        'source_sha256': sha(folder / 'body'), 'historical_edition_established': False}
    if key == 'directory':
        links = Links(); links.feed(html); links.close()
        candidates = [{'text': r['text'], 'url': urljoin(receipt['url'], r['href'])} for r in links.rows
            if 'Wertpapierhandelsanzeige' in r['text']]
        assert candidates and 'Gesetze' in title
        result['ordinance_candidates'] = candidates
    elif key in ('ordinance-index', 'ordinance-full'):
        assert 'WpAV' in title or 'WpAIV' in title, 'Ordinance title identity required'
        if key == 'ordinance-index':
            links = {urljoin(receipt['url'], h) for h in parser.links if re.search(r'BJNR\d+\.html$', h)}
            assert len(links) == 1, 'One explicitly linked complete HTML required'
            result['complete_text_url'] = links.pop()
    else: assert ('§ 4 WpHG' if key == 'election' else '§ 5 WpHG') in title
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'text.txt').open('x') as stream: stream.write(text)
    save(output / 'links.json', parser.links)
    result['wall_seconds'] = time.monotonic() - started; save(output / 'result.json', result)
    return result


def seal():
    frozen()
    assert (HERE / 'SOURCE-REVIEW.md').is_file() and (HERE / 'RESULT.md').is_file()
    results = {key: read(HERE / 'local' / key / 'result.json')['status'] for key in URLS}
    for key in ('ordinance-index', 'ordinance-full'):
        if (HERE / 'requests' / key / 'started.json').exists():
            results[key] = read(HERE / 'local' / key / 'result.json')['status']
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'PUBLICATION_SOURCE_CORRECTION_REVIEW', 'source_results': results,
        'consumer_integration_established': False, 'resources': costs(),
        'next_action': 'Review source-bound publication prerequisite integration; keep facts and historical applicability open'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in HERE.glob('requests/*/started.json')],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU hidden; no GPU imports',
        'seeds': 'N/A source reading', 'data_version': {p.parent.name: sha(p) for p in HERE.glob('requests/*/body')},
        'resource_accounting': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in ('admission.json', 'outputs.json')})
    return result


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': result = prepare()
    elif action == 'start': result = start(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif action == 'finish': result = finish(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    elif action == 'extract': result = extract(sys.argv[2])
    elif action == 'seal': result = seal()
    else: raise SystemExit('Unknown source correction action')
    print(json.dumps(result))
