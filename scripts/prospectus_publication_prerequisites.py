"""Three bounded official-source requests, with independent branch completion."""
from copy import deepcopy
from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urljoin, urlsplit

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel
from scripts.prospectus_statutory_sources_accounted import SourceHTML
from legalmath.prospectus.execution_authority import Authority, digest

PREP = AUTH / 'reviews/publication-prerequisites-363'
HERE = AUTH / 'attempts/basf-references/attempt-098'
PRIOR = AUTH / 'attempts/basf-references/attempt-097'
PLAN = 'docs/plans/prospectus-publication-prerequisites-2026-10-20.md'
METHOD = 'scripts/prospectus_publication_prerequisites.py'
URLS = {'issuer-definition': 'https://www.gesetze-im-internet.de/wphg/__2.html',
        'ordinance-index': 'https://www.gesetze-im-internet.de/wpav/'}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    prior = start['prior']
    seconds = extra + sum(read(p).get('tool_wall_seconds', 0) for p in HERE.glob('requests/*/receipt.json'))
    seconds += sum(read(p).get('wall_seconds', 0) for p in HERE.glob('local/*/result.json'))
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in (PLAN, METHOD))
    files.add(AUTH / 'revisions/0363.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert seconds <= 180 and size < 44 * 1024**2, 'New source resource bound'
    total = prior['combined_measured_seconds'] + prior['conservative_extra_seconds'] + seconds + 120
    assert total < 27000 and prior['combined_bytes'] + size < 4092 * 1024**2
    return {'combined_measured_seconds': prior['combined_measured_seconds'] + seconds,
        'conservative_extra_seconds': prior['conservative_extra_seconds'] + 120,
        'combined_accounted_seconds': total, 'combined_bytes': prior['combined_bytes'] + size,
        'new_measured_seconds': seconds, 'new_bytes': size, 'old_costs_reset': False,
        'earlier_unmeasured_time': 'UNKNOWN', 'maximum_new_GETs': 3,
        'GETs_started': len(list(HERE.glob('requests/*/started.json')))}


def prepare():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 362
    events = Authority(ROOT).events()
    assert [e['kind'] for e in events if e.get('attempt', '').endswith('basf-meanings/attempt-023')][-1] == 'RECORD'
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 97
    for name, checksum in read(PRIOR / 'outputs.json').items(): assert sha(PRIOR / name) == checksum
    save(PREP / 'accounting-start.json', {'prior': read(PRIOR / 'result.json')['resources'],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    names = [PLAN, METHOD, 'scripts/prospectus_default_holder.py',
        'scripts/prospectus_statutory_sources_accounted.py', 'src/legalmath/prospectus/publication_routes.py',
        rel(PRIOR / 'outputs.json'), rel(PRIOR / 'result.json'), rel(PREP / 'accounting-start.json')]
    source = AUTH / 'attempts/basf-references/attempt-059/requests/section'
    names += [rel(source / n) for n in ('trusted-body', 'trusted-text.txt', 'trusted-receipt.json')]
    bindings = {n: sha(ROOT / n) for n in names}
    bindings.update({rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_changes': False})
    new = deepcopy(program); new['revision'] = 363
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Inspect missing WpHG issuer definitions and candidate implementing ordinance before changing publication hypotheses',
        publication_prerequisite_sources={'review': rel(PREP), 'maximum_new_GETs': 3,
            'original_task_complete': False, 'production_changes': False,
            'new_seconds': 180, 'new_bytes': 48 * 1024**2, 'cumulative_seconds': 27000, 'cumulative_bytes': 4096 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 98
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 363
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Read missing issuer/implementing sources; inspect both independent branches and retain unavailable evidence',
                stop_condition='98 admissions;three reviewed GETs;180s/48MiB new;27000s/4096MiB cumulative;no production change')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Two independent missing-source branches, then completion-only review', 'One additional original basf-references admission; all costs retained'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'current_section50_reused': True},
        'evidence_contract': {'primary': 'Complete correctly identified official text and source-specific conditions/exceptions review',
            'promotion_veto': ['Wrong or incomplete source', 'Lost qualifiers', 'Invented historical applicability'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Cumulative exhaustion'],
            'explanatory_only': ['HTTP status', 'Counts', 'Runtime'],
            'not_concluded': ['Consumer integration', 'Actual issuer qualification', 'Historical law', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 97, 'new_maximum': 98,
            'retained_attempts': attempts, 'reason': 'Existing source context expressly lacks issuer definition and implementing rules',
            'next_discriminating_check': 'Definition scope/exceptions and applicable WpAV sections before modeling',
            'stop_condition': 'Three GETs;180s/48MiB new;27000s/4096MiB cumulative',
            'same_scope_authorization': 'User authorized source research, general build and continuation after restart'},
        'acquisition_revision': {'additional_official_GETs': 3, 'old_allowances_reset': False}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 363, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name
    costs()


def start(key):
    frozen()
    if key == 'ordinance-full':
        index = read(HERE / 'local/ordinance-index/result.json')
        assert index['status'] == 'PASS'
        url = index['complete_text_url']
        p = urlsplit(url)
        assert p.scheme == 'https' and p.netloc == 'www.gesetze-im-internet.de' and p.path.startswith('/wpav/')
        assert not p.query and not p.fragment
    else: url = URLS[key]
    folder = HERE / 'requests' / key
    assert len(list(HERE.glob('requests/*/started.json'))) < 3
    command = ['curl', '--silent', '--show-error', '--proto', '=https', '--max-time', '20',
        '--connect-timeout', '8', '--max-filesize', '2097152', '--dump-header', str(folder / 'headers'),
        '--output', str(folder / 'body'), '--stderr', str(folder / 'stderr'), '--write-out', '%{http_code}', url]
    save(folder / 'started.json', {'command': command, 'url': url,
         'started_at': datetime.now(timezone.utc).isoformat(), 'retries': 0, 'redirects': False})
    return {'status': 'READY_FOR_EXACT_GET', 'key': key, 'command': command}


def finish(key, code, wall):
    frozen()
    folder = HERE / 'requests' / key
    request = read(folder / 'started.json')
    headers = (folder / 'headers').read_text() if (folder / 'headers').exists() else ''
    matches = re.findall(r'(?m)^HTTP/[^ ]+ (\d{3})', headers)
    status = int(matches[-1]) if matches else None
    save(folder / 'receipt.json', {'status': 'RETAINED' if code == 0 and status == 200 else 'UNAVAILABLE',
        'curl_exit_code': code, 'http_status': status, 'url': request['url'], 'tool_wall_seconds': wall,
        'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'receipt.json'}})
    return {'status': 'RECORDED', 'key': key, 'http_status': status, 'curl_exit_code': code}


def extract(key):
    frozen(); started = time.monotonic()
    folder = HERE / 'requests' / key; receipt = read(folder / 'receipt.json')
    output = HERE / 'local' / key
    if receipt['status'] != 'RETAINED':
        save(output / 'result.json', {'status': 'UNAVAILABLE', 'key': key, 'wall_seconds': time.monotonic() - started})
        return {'status': 'UNAVAILABLE', 'key': key}
    for name, checksum in receipt['files'].items(): assert sha(folder / name) == checksum
    raw = (folder / 'body').read_bytes(); assert 0 < len(raw) <= 2097152
    match = re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', raw[:8192], re.I)
    assert match, 'Response charset required'
    charset = match[1].decode('ascii'); html = raw.decode(charset, errors='strict')
    title = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    assert title and html.rstrip().lower().endswith('</html>'), 'Complete HTML title/document required'
    title = unescape(title[1]); assert ('§ 2 WpHG' in title if key == 'issuer-definition' else 'WpAV' in title)
    parser = SourceHTML(); parser.feed(html); parser.close()
    text = '\n'.join(line for line in (' '.join(x.split()) for x in ''.join(parser.text).splitlines()) if line) + '\n'
    assert '\ufffd' not in text
    result = {'status': 'PASS', 'key': key, 'title': title, 'charset': charset,
        'source_sha256': sha(folder / 'body'), 'historical_edition_established': False}
    if key == 'ordinance-index':
        links = [urljoin(receipt['url'], h) for h in parser.links if re.search(r'BJNR\d+\.html$', h)]
        assert len(set(links)) == 1, 'Exactly one explicit official complete-HTML link required'
        result['complete_text_url'] = links[0]
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'text.txt').open('x') as stream: stream.write(text)
    save(output / 'links.json', parser.links)
    result['wall_seconds'] = time.monotonic() - started
    save(output / 'result.json', result)
    return result


def seal():
    frozen()
    assert (HERE / 'SOURCE-REVIEW.md').is_file() and (HERE / 'RESULT.md').is_file()
    results = {key: read(HERE / 'local' / key / 'result.json')['status'] for key in URLS}
    if results['ordinance-index'] == 'PASS': results['ordinance-full'] = read(HERE / 'local/ordinance-full/result.json')['status']
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'PUBLICATION_PREREQUISITE_SOURCE_REVIEW', 'source_results': results,
        'consumer_integration_established': False, 'resources': costs(),
        'next_action': 'Use reviewed full source conditions to design explicit publication prerequisites; preserve historical applicability unknown'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in HERE.glob('requests/*/started.json')],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; no GPU imports',
        'seeds': 'N/A source reading', 'data_version': {p.parent.name: sha(p) for p in HERE.glob('requests/*/body')},
        'wall_time': costs(), 'plan': PLAN, 'result': rel(HERE / 'result.json')})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in ('admission.json', 'outputs.json')})
    return result


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare': result = prepare()
    elif action == 'start': result = start(sys.argv[2])
    elif action == 'finish': result = finish(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
    elif action == 'extract': result = extract(sys.argv[2])
    elif action == 'seal': result = seal()
    else: raise SystemExit('Unknown source action')
    print(json.dumps(result))
