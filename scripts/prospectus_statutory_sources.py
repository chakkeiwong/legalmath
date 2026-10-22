"""Bounded primary-source work for the original BASF reference task.

No interpretation or ordinary-consumer invocation. Each acquire command performs
one GET, without redirects/retries; raw failed responses are retained as evidence.
"""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time
from urllib.parse import urljoin, urlsplit

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/statutory-sources-282'
HERE = AUTH / 'attempts/basf-references/attempt-023'
PLAN = 'docs/plans/prospectus-statutory-source-investigation-2026-10-18.md'
METHOD = 'scripts/prospectus_statutory_sources.py'
PREFLIGHT_METHOD = 'scripts/prospectus_statutory_sources_preflight.py'
CONTRACT = 'docs/implementation/prospectus-basf-reference-repair/source-review-002/basf-base-september-2022-exchange.txt'
LEDGER = 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz'
HOSTS = {'www.gesetze-im-internet.de', 'www.govinfo.gov', 'home.treasury.gov',
         'www.bgbl.de', 'www.recht.bund.de'}
WANTED = {'historical_candidate_lines': {16, 28, 35, 38, 39, 40},
          'additional_explicit_review_findings': {2, 3, 7, 8, 11, 12}}
CONTEXTS = {'historical_candidate_lines': {16: (7240, 7320), 28: (7733, 7740),
            35: (7840, 7940), 38: (7938, 7965), 39: (7938, 7965), 40: (7938, 7965)},
            'additional_explicit_review_findings': {2: (6878, 6948), 3: (7640, 7701),
            7: (7950, 8000), 8: (7982, 8058), 11: (6620, 6660), 12: (6465, 6542)}}


def read(path):
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == '.gz' else raw)


def save(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with p.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if p.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def utc():
    return datetime.now(timezone.utc).isoformat()


def checked_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.fragment:
        raise ValueError('Source URL outside reviewed HTTPS official hosts')
    if p.port not in (None, 443):
        raise ValueError('Unreviewed source port')
    return url


def manifests():
    for number in (21, 22):
        folder = AUTH / f'attempts/basf-references/attempt-{number:03d}'
        for name, checksum in read(folder / 'outputs.json').items():
            if sha(folder / name) != checksum:
                raise ValueError('Combined baseline drift: ' + name)
    assert read(AUTH / 'attempts/basf-references/attempt-021/result.json')['trial_status'] == 'FAIL'
    assert read(AUTH / 'attempts/basf-references/attempt-022/result.json')['status'] == 'PASS'


def frozen():
    from legalmath.prospectus.execution_authority import digest
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    for name, checksum in admission['binding'].items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Source admission drift: ' + name)


def costs():
    receipts = (list(HERE.glob('requests/*/receipt.json')) + list(HERE.glob('local/*/receipt.json'))
                + list(HERE.glob('local/*/finalization-failure.json')) + list(PREP.glob('preflight*.json')))
    started = list(HERE.glob('requests/*/started.json'))
    local_started = list(HERE.glob('local/*/started.json'))
    unfinished = [p for p in started + local_started if not (p.parent / 'receipt.json').exists()]
    if unfinished:
        raise ValueError('Interrupted acquisition requires retained diagnosis: ' + rel(unfinished[0]))
    seconds = sum(read(p)['wall_seconds'] for p in receipts)
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (METHOD, PREFLIGHT_METHOD, PLAN))
    size = sum(p.stat().st_size for p in paths)
    if seconds >= 1200 or size >= 23 * 1024**2 or len(started) > 32:
        raise ValueError('Additional reviewed source-work bounds exhausted')
    return {'additional_measured_seconds': seconds, 'additional_bytes': size,
            'GET_attempts': len(started), 'seconds_bound': 1200,
            'bytes_bound_including_reserve': 24 * 1024**2, 'reserve_bytes': 1024**2,
            'retained_prior_resources': read(PREP / 'baseline.json')['resources'],
            'authoring_reading_controller_seconds': 'UNKNOWN'}


def request_row(key):
    initial = read(PREP / 'requests.json')['requests']
    rows = list(initial)
    for p in sorted((HERE / 'request-reviews').glob('*.json')):
        review = read(p)
        assert review['verdict'] == 'PASS' and review['reason']
        row = review['request']
        # Follow-ups cite a retained source and exact literal href. A constructed
        # publication URL instead requires an explicit citation-based rationale.
        if 'source' in review:
            source = ROOT / review['source']
            assert source.resolve().is_relative_to(HERE.resolve())
            assert sha(source) == review['source_sha256']
            assert review['href'] in source.read_text(errors='replace')
            assert urljoin(review['base_url'], review['href']) == row['url']
            checked_url(review['base_url'])
        else:
            assert review['publication_citation'] and review['constructed_url_rationale']
        rows.append(row)
    assert len(initial) <= 16 and len(rows) - len(initial) <= 16
    assert len({r['id'] for r in rows}) == len(rows)
    for row in rows:
        assert re.fullmatch(r'[a-z][a-z0-9-]*', row['id'])
        checked_url(row['url'])
    return next(r for r in rows if r['id'] == key)


def acquire(key):
    frozen()
    before = costs()
    assert before['GET_attempts'] < 32
    row = request_row(key)
    folder = HERE / 'requests' / key
    folder.mkdir(parents=True, exist_ok=False)
    body, headers = folder / 'body', folder / 'headers'
    maximum = min(2 * 1024**2, 23 * 1024**2 - before['additional_bytes'] - 128 * 1024)
    assert maximum > 0
    command = ['curl', '--silent', '--show-error', '--proto', '=https',
               '--max-time', '20', '--connect-timeout', '8', '--max-filesize', str(maximum),
               '--dump-header', str(headers), '--output', str(body), '--write-out', '%{json}', row['url']]
    began = time.monotonic()
    save(folder / 'started.json', {'started_at': utc(), 'request': row, 'command': command,
                                  'redirects': False, 'automatic_retries': 0})
    error = None
    def limit_response_files():
        # curl7.81 cannot enforce --max-filesize on every chunked response.
        # Enforce a kernel file-size cap as well; headers are bounded too.
        resource.setrlimit(resource.RLIMIT_FSIZE, (maximum, maximum))
    try:
        result = subprocess.run(command, capture_output=True, timeout=25,
                                preexec_fn=limit_response_files)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = None, exc.stdout or b'', exc.stderr or b''
        error = 'Local25second timeout'
    except OSError as exc:
        code, stdout, stderr = None, b'', b''
        error = type(exc).__name__ + ': ' + str(exc)
    (folder / 'curl-metadata').write_bytes(stdout)
    (folder / 'curl-stderr').write_bytes(stderr)
    try:
        metadata = json.loads(stdout)
    except (ValueError, UnicodeDecodeError):
        metadata = {}
    ok = code == 0 and metadata.get('http_code') == 200
    receipt = {'status': 'RESPONSE_RETAINED' if ok else 'UNAVAILABLE_RESPONSE_RETAINED',
               'requested_url': row['url'], 'effective_url': metadata.get('url_effective'),
               'http_code': metadata.get('http_code'), 'curl_exit_code': code,
               'error': error, 'finished_at': utc(), 'wall_seconds': time.monotonic() - began,
               'actual_substantive_source_review': False,
               'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file()}}
    save(folder / 'receipt.json', receipt)
    frozen()
    return {**{k: receipt[k] for k in ('status', 'http_code', 'curl_exit_code', 'wall_seconds')},
            'id': key, 'resources': costs()}


class SourceHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'li', 'tr'):
            self.text.append('\n')
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'tr'):
            self.text.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def extract(key):
    frozen()
    costs()
    source = HERE / 'requests' / key
    receipt = read(source / 'receipt.json')
    for name, checksum in receipt['files'].items():
        assert sha(source / name) == checksum
    assert receipt['http_code'] == 200 and receipt['curl_exit_code'] == 0
    folder = HERE / 'local' / ('extract-' + key)
    folder.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    save(folder / 'started.json', {'started_at': utc(), 'source_sha256': sha(source / 'body'),
        'whole_stage_limit_seconds': 180, 'command': [
            '.venv/bin/python', '-m', 'scripts.prospectus_statutory_sources', 'extract', key]})
    def expired(signum, frame):
        raise TimeoutError('Whole extraction stage exceeded180seconds')
    previous_handler = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 180)
    extraction = 'not selected'
    try:
        raw = (source / 'body').read_bytes()
        if raw.startswith(b'%PDF-'):
            extraction = 'pdftotext -layout'
            result = subprocess.run(['pdftotext', '-layout', str(source / 'body'), str(folder / 'text.txt')],
                                    capture_output=True, timeout=170)
            (folder / 'stderr').write_bytes(result.stderr)
            assert result.returncode == 0, 'pdftotext failed: ' + str(result.returncode)
        else:
            encoding = 'utf-8'
            match = re.search(br'charset\s*=\s*["\x27]?([a-zA-Z0-9-]+)', raw[:8192], re.I)
            if match:
                encoding = match[1].decode('ascii')
            extraction = 'stdlib HTMLParser; ' + encoding
            html = raw.decode(encoding)  # Do not silently replace unreadable text.
            parser = SourceHTML()
            parser.feed(html)
            lines = [' '.join(s.split()) for s in ''.join(parser.text).splitlines()]
            (folder / 'text.txt').write_text('\n'.join(s for s in lines if s) + '\n')
            save(folder / 'links.json', [{'href': h, 'url': urljoin(receipt['requested_url'], h)}
                                        for h in dict.fromkeys(parser.links)])
    except Exception as exc:
        save(folder / 'receipt.json', {'status': 'FAIL', 'wall_seconds': time.monotonic() - began,
            'source_sha256': sha(source / 'body'), 'method': extraction,
            'error_type': type(exc).__name__, 'error': str(exc),
            'actual_substantive_source_review': False})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    save(folder / 'receipt.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began,
        'source_sha256': sha(source / 'body'), 'method': extraction,
        'text_sha256': sha(folder / 'text.txt'), 'actual_substantive_source_review': False})
    return {'status': 'PASS', 'id': key, 'method': extraction, 'resources': costs()}


def contexts():
    ledger = read(ROOT / LEDGER)
    # Line coordinates come from newline-based source inspection; form feeds
    # are page markers inside those lines, not additional line delimiters.
    with (ROOT / CONTRACT).open() as stream:
        lines = stream.readlines()
    records = []
    for row in ledger['records']:
        family, index = row['family'], row['index']
        if index not in WANTED.get(family, set()):
            continue
        first, last = CONTEXTS[family][index]
        text = ''.join(lines[first - 1:last])
        normalized = ' '.join(text.split())
        original = row['original']
        for anchor in original.get('source_pieces', original.get('sources', [])):
            assert ' '.join(anchor['quote'].split()) in normalized
        records.append({'family': family, 'index': index, 'original': original,
            'retained_selected_source_pieces': row['source_pieces'],
            'raw_contract_context': {'path': CONTRACT, 'sha256': sha(ROOT / CONTRACT),
                'line_first': first, 'line_last': last, 'text': text,
                'text_sha256': hashlib.sha256(text.encode()).hexdigest()},
            'context_note': 'Raw prospectus includes optional branches; retained selections stay unchanged. Context is not a new final-term activation.'})
    assert len(records) == 12
    save(HERE / 'original-contexts.json', {'version': 'twelve-original-contexts.v1',
        'ledger': LEDGER, 'ledger_sha256': sha(ROOT / LEDGER), 'records': records,
        'new_reviewed_contract_links': 0, 'original_task_complete': False})
    return {'status': 'PASS', 'original_records': len(records), 'new_reviewed_contract_links': 0}


def seal():
    manifests()
    originals = read(HERE / 'original-contexts.json')['records']
    findings = read(HERE / 'investigation.json')['records']
    assert len(findings) == 12
    assert {(r['family'], r['index']) for r in findings} == {(r['family'], r['index']) for r in originals}
    for finding in findings:
        original = next(r for r in originals if (r['family'], r['index']) == (finding['family'], finding['index']))
        assert finding['original'] == original['original']
        assert finding['context_sha256'] == original['raw_contract_context']['text_sha256']
        assert finding['source_findings'] and finding['unresolved'] and finding['model_consequence']
        assert finding['complete_legal_interpretation'] is False
        for source in finding['source_findings']:
            assert source['reading'] and sha(ROOT / source['path']) == source['sha256']
    for name in ('SOURCE-REVIEW.md', 'SOURCE-TO-MODEL.md', 'RESULT.md'):
        assert (HERE / name).stat().st_size > 200
    result = {'status': 'PASS', 'task': 'basf-references',
        'result_kind': 'TWELVE_ORIGINAL_SOURCE_INVESTIGATION_AND_DESIGN',
        'original_task_complete': False, 'production_changed': False,
        'new_ordinary_consumers': 0, 'original_records_retained': 60,
        'original_remnants_investigated': 12, 'reviewed_contract_links_unchanged': 47,
        'covered_original_records_unchanged': 48,
        'acceptance_limit': 'Seal checks retention and declared investigation; it does not prove a legal construction',
        'next_action': 'Separately review legal-source representation and actual ordinary-answer integration; continue definitions/discovery'}
    result['_manifest'] = {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'seeds': 'N/A deterministic source work', 'data_version': sha(ROOT / CONTRACT),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'artifacts': rel(HERE),
        'commands': [read(p)['command'] for p in HERE.glob('requests/*/started.json')],
        'local_stage_records': [rel(p) for p in HERE.glob('local/*/started.json')],
        'method_freeze': sha(PREP / 'freeze.json')}
    return result


def local(action):
    frozen()
    costs()
    folder = HERE / 'local' / action
    folder.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    save(folder / 'started.json', {'started_at': utc(), 'command': [
        '.venv/bin/python', '-m', 'scripts.prospectus_statutory_sources', action],
        'whole_stage_limit_seconds': 180})
    def expired(signum, frame):
        raise TimeoutError('Local source stage exceeded180seconds')
    previous_handler = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        # No second budget check while this local stage is unfinished.
        result = globals()[action]()
        frozen()
        save(folder / 'receipt.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began})
        if action == 'seal':
            manifest = result.pop('_manifest')
            result['resources'] = costs()
            manifest['wall_time'] = result['resources']
            save(HERE / 'result.json', result)
            save(HERE / 'run-manifest.json', manifest)
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts})
        return result
    except Exception as exc:
        prior_receipt = folder / 'receipt.json'
        elapsed = time.monotonic() - began
        if prior_receipt.exists():
            elapsed -= read(prior_receipt)['wall_seconds']
        save(folder / ('finalization-failure.json' if prior_receipt.exists() else 'receipt.json'),
             {'status': 'FAIL', 'wall_seconds': elapsed,
            'error_type': type(exc).__name__, 'error': str(exc)})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest
    manifests()
    program = read(AUTH / 'program.json')
    assert program['revision'] == 281
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 22
    prior = read(AUTH / 'attempts/basf-references/attempt-022/result.json')
    from scripts.prospectus_consumer_refusal_repair import costs as retained_costs
    save(PREP / 'baseline.json', {'resources': retained_costs(), 'prior_admissions': attempts,
        'combined_evidence': {'answers': 'attempt-021', 'controls_reconciliation': 'attempt-022'},
        'earlier_trial_status': 'FAIL', 'new_ordinary_answers_in022': 0})
    bindings = {rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()}
    assert read(PREP / 'preflight-v3.json')['status'] == 'PASS'
    assert read(PREP / 'preflight-contexts.json')['status'] == 'PASS'
    assert (PREP / 'PRE-ADMISSION-REVIEW.md').is_file()
    for name in (*CODE, PLAN, METHOD, PREFLIGHT_METHOD, CONTRACT, LEDGER):
        bindings[name] = sha(ROOT / name)
    for number in (21, 22):
        folder = AUTH / f'attempts/basf-references/attempt-{number:03d}'
        bindings.update({rel(folder / name): checksum for name, checksum in read(folder / 'outputs.json').items()})
        bindings[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
    law = AUTH / 'attempts/law-applicability/attempt-002'
    bindings.update({rel(law / name): checksum for name, checksum in read(law / 'outputs.json').items()})
    bindings[rel(law / 'outputs.json')] = sha(law / 'outputs.json')
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 282
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
        reason='Investigate all twelve remaining original legal references and editions before production design',
        statutory_source_review={'version': 'statutory-source-investigation.v1', 'review': rel(PREP),
            'original_task_complete': False, 'bounds': {'new_measured_seconds': 1200,
                'new_bytes': 24 * 1024**2, 'reserve_bytes': 1024**2, 'GET_attempts': 32,
                'request_seconds': 20, 'local_stage_seconds': 180},
            'automatic_retry_allowed': False, 'production_changes_allowed': False})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 23
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 282
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task),
                remaining='47 links covering48/60; twelve original legal references plus definitions/discovery remain.',
                next_action='Retain official sources and read all twelve contexts/editions; review reusable representation, then implement under a separate revision.',
                acceptance='Lossless twelve-record primary-source investigation and reviewed design; partial original-task evidence only.',
                stop_condition='23 cumulative admissions;32 GETs;20s requests;180s local stages;1200 additional measured seconds;24MiB including1MiB reserve.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Combined021 answer and022 controls baseline;021 remains FAIL',
            'Source-only investigation of all twelve original legal remnants',
            'Bounded official-source GETs; no redirects, retries or production changes'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
            'current_consolidation_not_historical_law': True, 'download_counts_not_acceptance': True},
        'evidence_contract': {'primary': 'Checked original contexts, retained primary source readings and edition/scope/application gaps for all twelve, then reviewed design',
            'veto': ['Wrong source/context/edition', 'False closed scope', 'Corrupt baseline', 'Resource exhaustion'],
            'not_concluded': ['Actual entitlement', '2022 applicability', 'Automatic discovery', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 22, 'new_maximum': 23,
            'retained_attempts': attempts, 'reason': 'Distinct source/design work after completed finite internal controls; original statutory obligations remain',
            'next_discriminating_check': 'Full primary provisions and exceptions versus original complete contractual context',
            'stop_condition': '32 GET attempts,20s each;180s local stages;1200 additional measured seconds;24MiB including1MiB reserve;no unchanged retry',
            'same_scope_authorization': 'User directs refreshed master program and continued general build; external adviser opinions are not prerequisites'},
        'additional_measured_seconds_bound': 1200, 'prior_lineage': read(PREP / 'baseline.json')}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 282, 'prior_admissions': len(attempts), 'resources': costs()}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'propose':
        output = propose()
    elif action == 'acquire':
        output = acquire(sys.argv[2])
    elif action == 'extract':
        output = extract(sys.argv[2])
    elif action in ('contexts', 'seal'):
        output = local(action)
    else:
        raise ValueError('Unknown source-only action')
    print(json.dumps(output, ensure_ascii=False))
