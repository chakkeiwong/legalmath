"""Acquire the small election sections linked by the complete retained index."""
from copy import deepcopy
from datetime import datetime, timezone
from html import unescape
import json
import re
import sys
import time
from urllib.parse import urljoin, urlsplit

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts.prospectus_statutory_sources_accounted import SourceHTML

PREP = AUTH / 'reviews/election-sections-369'
HERE = AUTH / 'attempts/basf-references/attempt-102'
PRIOR = AUTH / 'attempts/basf-references/attempt-101'
BASE = AUTH / 'attempts/basf-office/attempt-006'
PLAN = 'docs/plans/prospectus-election-linked-sections-2026-10-20.md'
METHOD = 'scripts/prospectus_election_sections.py'
SECTIONS = {'section4': (4, 'Wahl des Herkunftsstaates'),
            'section5': (5, 'Veröffentlichung des Herkunftsstaates')}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    requests = 40 * len(list(HERE.glob('requests/*/started.json')))
    local = extra + sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    local += sum(read(p).get('wall_seconds', 0) for p in PREP.glob('preparation-result.json'))
    files = {p for d in (PREP, HERE) for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in (PLAN, METHOD)); files.add(AUTH / 'revisions/0369.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['prior_seconds'] + requests + local + 120
    combined = start['prior_bytes'] + size
    assert local < 90 and requests <= 80 and size < 60 * 1024**2, 'New source bounds exhausted'
    assert total < 28000 and combined < 4348 * 1024**2, 'Original cumulative bounds exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
            'new_conservative_request_seconds': requests, 'new_local_seconds': local,
            'new_conservative_other_seconds': 120, 'new_bytes': size,
            'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 368 and not HERE.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] == 'RECORD' and e.get('attempt') == rel(PRIOR) for e in events)
    attempts = [e['attempt'] for e in events
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 101
    for folder in (PRIOR, BASE):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, name
    index = read(PRIOR / 'local/index/result.json'); assert index['status'] == 'PASS'
    assert read(PRIOR / 'local/full/result.json')['status'] == 'UNAVAILABLE'
    links = read(PRIOR / 'local/index/links.json')
    urls = {}
    for key, (number, _) in SECTIONS.items():
        href = f'__{number}.html'; assert href in links
        urls[key] = urljoin(index['url'], href)
    from scripts.prospectus_election_sources import costs as prior_costs
    previous = prior_costs()
    assert previous['combined_accounted_seconds'] + 290 < 28000
    assert previous['combined_bytes'] + 64 * 1024**2 < 4352 * 1024**2
    save(PREP / 'accounting-start.json', {
        'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resource_record': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    save(PREP / 'config.json', {'urls': urls,
        'navigation': rel(PRIOR / 'local/index/links.json'),
        'changed_evidence': 'Complete index and successful trusted HTTP; smaller documents after truncated full statute'})
    save(PREP / 'preparation-result.json', {'status': 'PASS',
        'wall_seconds': time.monotonic() - began, 'literal_links_checked': True,
        'full_budget_reserved': True, 'production_change': False})
    bindings = {n: sha(ROOT / n) for n in (PLAN, METHOD,
        'scripts/prospectus_default_holder.py', 'scripts/prospectus_statutory_sources_accounted.py')}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')})
    bindings.update({rel(PRIOR / n): sha(PRIOR / n) for n in
        ('outputs.json', 'result.json', 'requests/index/body', 'requests/index/receipt.json',
         'local/index/links.json', 'local/index/result.json', 'SOURCE-REVIEW.md')})
    bindings.update({rel(BASE / n): sha(BASE / n) for n in ('ordinary-answer.json.gz', 'outputs.json')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_change': False})
    new = deepcopy(program); new['revision'] = 369
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Acquire operative election law from verified small section links after complete-index success',
        election_sections={'review': rel(PREP), 'original_task_complete': False,
            'maximum_new_GETs': 2, 'new_local_seconds': 90, 'new_request_charge': 80,
            'new_other_charge': 120, 'new_bytes': 64 * 1024**2,
            'cumulative_seconds': 28000, 'cumulative_bytes': 4352 * 1024**2},
        build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 102
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 369
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Inspect exact linked WpHG4/5 operative provisions and onward dependencies, or retain each independent failure',
                stop_condition='102admissions;2logicalGETs;90local+80request+120other seconds;64MiB increment;28000s/4352MiB cumulative')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Use verified literal small-section links, preserving all earlier source failures'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Complete correct official election provisions and inspected exceptions',
            'promotion_veto': ['Incomplete source', 'Wrong section identity', 'Lost exception', 'Historical inference'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted original bounds'],
            'explanatory_only': ['HTTP status', 'Counts', 'Timings'],
            'not_concluded': ['Consumer integration', 'Actual election', 'Historical law', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 101, 'new_maximum': 102,
            'retained_attempts': attempts,
            'reason': 'New complete navigation and demonstrated trusted HTTP; smaller linked documents discriminate transfer-size failure',
            'next_discriminating_check': 'Complete literal section4 and5 links; no full-statute retry',
            'stop_condition': '2logicalGETs;90+80+120seconds/64MiB increment;original28000seconds/4352MiB unchanged',
            'same_scope_authorization': 'Continue original source research; no external messages or new product claim'},
        'acquisition_revision': {'additional_official_GETs': 2, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 369, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name
    costs()


def start(key):
    frozen(); assert key in SECTIONS
    url = read(PREP / 'config.json')['urls'][key]; parsed = urlsplit(url)
    assert parsed.scheme == 'https' and parsed.netloc == 'www.gesetze-im-internet.de'
    assert parsed.path == f'/wphg/__{SECTIONS[key][0]}.html' and not parsed.query and not parsed.fragment
    assert len(list(HERE.glob('requests/*/started.json'))) < 2
    folder = HERE / 'requests' / key
    assert not folder.exists(), 'No redispatch'
    argv = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', str(2 * 1024**2),
        '--dump-header', str(folder / 'headers'), '--output', str(folder / 'body'),
        '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code} %{time_total}', url]
    save(folder / 'started.json', {'command': argv, 'url': url,
        'started_at': datetime.now(timezone.utc).isoformat(), 'logical_request': key,
        'intended_context': 'trusted; sandbox DNS failure retained in source101',
        'automatic_retries': 0, 'redirects': False})
    return {'status': 'READY_FOR_EXACT_GET', 'command': argv}


def finish(key, code, transfer):
    frozen(); assert key in SECTIONS
    folder = HERE / 'requests' / key
    headers = (folder / 'headers').read_text() if (folder / 'headers').exists() else ''
    matches = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers)
    status = int(matches[-1]) if matches else None
    save(folder / 'receipt.json', {'status': 'RETAINED' if code == 0 and status == 200 else 'UNAVAILABLE',
        'curl_exit_code': code, 'http_status': status, 'actual_transfer_seconds': transfer,
        'conservative_charge_seconds': 40, 'execution_context': 'trusted',
        'url': read(folder / 'started.json')['url'],
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'receipt.json'}})
    return {'status': 'RECORDED', 'key': key, 'http_status': status, 'resources': costs()}


def extract(key):
    frozen(); assert key in SECTIONS
    began = time.monotonic(); folder = HERE / 'requests' / key; output = HERE / 'local' / key
    receipt = read(folder / 'receipt.json')
    for name, checksum in receipt['files'].items():
        assert sha(folder / name) == checksum, name
    result = {'status': 'UNAVAILABLE', 'key': key}
    if receipt['status'] == 'RETAINED':
        try:
            raw = (folder / 'body').read_bytes(); assert 0 < len(raw) <= 2 * 1024**2
            lengths = re.findall(r'(?im)^content-length:\s*(\d+)\s*$', (folder / 'headers').read_text())
            assert not lengths or len(raw) == int(lengths[-1]), 'Complete declared body required'
            charset = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', raw[:8192], re.I)
            assert charset, 'Declared encoding required'
            html = raw.decode(charset[1].decode('ascii'), errors='strict')
            title = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
            assert title and html.rstrip().lower().endswith('</html>'), 'Complete HTML required'
            title = unescape(title[1]); number, heading = SECTIONS[key]
            assert 'WpHG' in title and f'§ {number}' in title, 'Exact statute/section required'
            parser = SourceHTML(); parser.feed(html); parser.close()
            text = '\n'.join(line for line in (' '.join(x.split())
                for x in ''.join(parser.text).splitlines()) if line) + '\n'
            assert '\ufffd' not in text and heading in text and '(1)' in text
            output.mkdir(parents=True, exist_ok=True)
            with (output / 'text.txt').open('x') as stream:
                stream.write(text)
            save(output / 'links.json', parser.links)
            result = {'status': 'PASS', 'key': key, 'title': title, 'url': receipt['url'],
                'source_sha256': sha(folder / 'body'), 'body_bytes': len(raw),
                'historical_application_established': False, 'operative_review_required': True}
        except Exception as error:
            result = {'status': 'INVALID_SOURCE', 'key': key,
                'kind': type(error).__name__, 'error': str(error)}
    result['wall_seconds'] = time.monotonic() - began
    save(output / 'result.json', result); costs()
    return result


def seal():
    frozen(); assert (HERE / 'SOURCE-REVIEW.md').is_file() and (HERE / 'RESULT.md').is_file()
    assert set(p.parent.name for p in HERE.glob('local/*/result.json')) == set(SECTIONS)
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'LINKED_ELECTION_SECTIONS_REVIEW', 'production_changed': False,
        'sources': {p.parent.name: read(p)['status'] for p in HERE.glob('local/*/result.json')},
        'resources': costs(), 'next_action': 'Review conditional integration only for complete operative sources; preserve historical and implementing dependencies'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p)['command'] for p in HERE.glob('requests/*/started.json')],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'No numerical/GPU execution',
        'seeds': 'N/A deterministic source acquisition', 'data_version': sha(PREP / 'freeze.json'),
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
