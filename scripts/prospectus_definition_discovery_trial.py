"""Bounded, staged discovery trial. Preparation never imports the candidate."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1')
from legalmath.prospectus.execution_authority import Authority, CODE, digest
from scripts.prospectus_definition_scope_investigation import clipped, costs as retained_costs

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/definition-discovery-286'
SOURCE = AUTH / 'attempts/basf-references/attempt-026'
HERE = AUTH / 'attempts/basf-references/attempt-027'
METHOD = 'scripts/prospectus_definition_discovery_trial.py'
PLAN = 'docs/plans/prospectus-definition-discovery-2026-10-18.md'
PREPARATION = ('prepare', 'propose')
STAGES = ('evaluate', 'verify', 'source', 'adverse', 'reconcile', 'seal')


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def source_check():
    for name, expected in read(SOURCE / 'outputs.json').items():
        assert sha(SOURCE / name) == expected, 'Sealed026 changed: ' + name
    return read(SOURCE / 'selected-source.json.gz')


def costs(extra=0):
    old = retained_costs()
    measured = old['additional_measured_seconds'] + extra
    measured += read(PREP / 'case-author-receipt.json')['wall_seconds']
    receipts = [p for d in (PREP, HERE) for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                for p in d.glob(pattern)]
    measured += sum(read(p)['wall_seconds'] for p in receipts)
    paths = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (METHOD, PLAN, 'docs/implementation/prospectus-execution-authority/revisions/0286.json'))
    size = old['additional_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    assert measured < 1800 and size < 60 * 1024**2, 'Cumulative026/027 resources exhausted'
    return {'cumulative026_027_measured_seconds': measured, 'cumulative026_027_bytes': size,
        'seconds_bound': 1800, 'bytes_bound_including_4MiB_reserve': 64 * 1024**2,
        'new_time_or_byte_allowance': 0, 'prior_costs_reset': False,
        'retained026_current_resources': old, 'manual_authoring_reading_controller_seconds': 'UNKNOWN'}


def frozen():
    source_check()
    for name, expected in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == expected, 'Frozen trial method/input changed: ' + name
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    for name in read(PREP / 'freeze.json')['bindings']:
        assert admission['binding'][name] == sha(ROOT / name)


def cases_check():
    freeze = read(PREP / 'cases-freeze.json')
    for name, expected in freeze['bindings'].items():
        assert sha(ROOT / name) == expected, 'Independent cases changed'
    receipt = read(PREP / 'case-author-receipt.json')
    assert receipt['candidate_present_at_authoring'] is False
    assert receipt['expected_results_from_candidate'] is False
    data = read(PREP / 'cases.json')
    text = (SOURCE / 'selected-text.txt').read_text()
    for row in data['cases']:
        assert hashlib.sha256(row['text'].encode()).hexdigest() == row['text_sha256']
        if row['kind'] == 'ORIGINAL_EXCERPT':
            a, b = row['original_interval']['start'], row['original_interval']['end']
            assert row['original_sha256'] == sha(SOURCE / 'selected-text.txt')
            assert text[a:b] == row['text']
        for name in ('expected_names', 'expected_uses'):
            keys = []
            for item in row[name]:
                assert row['text'][item['start']:item['end']] == item['raw']
                keys.append((item['start'], item['end'], item['label']))
            assert len(keys) == len(set(keys)), 'Duplicate gold occurrence'
    return data


def prepare():
    source = source_check()
    data = cases_check()
    modules = {}
    for name, module in tuple(sys.modules.items()):
        if not (name.startswith('legalmath.') or name.startswith('scripts.')):
            continue
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            expected = ROOT / ('src' if name.startswith('legalmath.') else 'scripts')
            assert path.is_relative_to(expected), (name, str(path))
            modules[name] = {'path': rel(path), 'sha256': sha(path)}
    save(PREP / 'identity-probe.json', {'status': 'PASS', 'role': 'SOURCE_CASES_AND_IMPORT_IDENTITY_ONLY',
        'modules': modules, 'source_p2_sha256': source['p2_sha256'],
        'selected_contract_sha256': source['selected_contract_sha256'],
        'source_outputs_sha256': sha(SOURCE / 'outputs.json'),
        'case_count': len(data['cases']), 'whole_contract_names': len(data['whole_contract_expected_names']),
        'candidate_imported_or_evaluated': False})
    return {'status': 'PASS', 'cases': len(data['cases']), 'candidate_imported_or_evaluated': False}


def candidate():
    path = PREP / 'candidate.py'
    spec = importlib.util.spec_from_file_location('reviewed_definition_discovery_286', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.discover


def request(row):
    return {k: deepcopy(row[k]) for k in ('text', 'text_sha256', 'language', 'regions')}


def evaluate():
    data = cases_check()
    discover = candidate()
    actual = []
    for row in data['cases']:
        result = discover(request(row))
        actual.append({'case': row['id'], 'input_sha256': digest(request(row)), 'output': result})
    # The actual candidate artifacts precede, and cannot be edited by, verification.
    save(HERE / 'actual-cases.json.gz', actual)
    return {'status': 'PASS', 'candidate_outputs_retained': len(actual), 'comparison_run': False}


def verify_maps(text, row):
    a, b = row['start'], row['end']
    assert text[a:b] == row['raw']
    assert ' '.join(row['raw'].split()) == row['label']
    mapping = row['normalization_map']
    assert len(mapping) == len(row['label'])
    cursor = a
    for char, (x, y) in zip(row['label'], mapping):
        assert type(x) is int and type(y) is int and cursor == x < y <= b
        raw = text[x:y]
        assert raw.isspace() if char == ' ' else (y == x + 1 and raw == char)
        cursor = y
    assert cursor == b


def verify_output(req, output):
    text = req['text']
    assert output['text_sha256'] == hashlib.sha256(text.encode()).hexdigest() == req['text_sha256']
    assert output['meaning_admitted'] is output['scope_admitted'] is False
    names = {n['id']: n for n in output['names']}
    assert len(names) == len(output['names'])
    regions = {r['id']: r for r in req['regions']}
    for kind in ('names', 'uses'):
        keys = []
        for row in output[kind]:
            verify_maps(text, row)
            r = regions[row['region']]
            assert r['selected'] and r['language'] == req['language']
            assert r['start'] <= row['start'] < row['end'] <= r['end']
            assert row['review_required'] is True
            keys.append((row['start'], row['end'], row['label']))
            if kind == 'names':
                assert row['kind'] == 'QUOTED_LABEL_CANDIDATE'
                assert text[row['quote_start']] == text[row['quote_end'] - 1] == '"'
                assert r['start'] <= row['quote_start'] < row['start'] < row['end'] < row['quote_end'] <= r['end']
                assert not text[row['quote_start'] + 1:row['start']].strip()
                assert not text[row['end']:row['quote_end'] - 1].strip()
            else:
                assert row['kind'] == 'LITERAL_USE_CANDIDATE' and row['governing_scope'] is None
                alternatives = [n['id'] for n in output['names'] if n['label'] == row['label']]
                assert row['name_candidates'] == alternatives, 'Alternative quote occurrences lost/chosen'
        assert len(keys) == len(set(keys))
    for row in output['issues']:
        r = regions[row['region']]
        assert r['selected'] and r['language'] == req['language']
        assert r['start'] <= row['start'] < row['end'] <= r['end']


def exact_rows(rows):
    return sorted((r['start'], r['end'], r['raw'], r['label'], r['region']) for r in rows)


def verify():
    cases = cases_check()['cases']
    actual = read(HERE / 'actual-cases.json.gz')
    assert [r['case'] for r in actual] == [r['id'] for r in cases]
    comparisons = []
    for gold, row in zip(cases, actual):
        req, output = request(gold), row['output']
        assert row['input_sha256'] == digest(req)
        verify_output(req, output)
        assert exact_rows(output['names']) == exact_rows(gold['expected_names']), 'Naming set: ' + gold['id']
        assert exact_rows(output['uses']) == exact_rows(gold['expected_uses']), 'Use set: ' + gold['id']
        assert sorted(r['kind'] for r in output['issues']) == sorted(gold['expected_issue_kinds']), 'Issues: ' + gold['id']
        comparisons.append({'case': gold['id'], 'status': 'PASS', 'complete_names_and_uses': True,
            'actual_output_sha256': digest(output), 'original_or_constructed': gold['kind']})
    save(HERE / 'case-comparison.json', comparisons)
    return {'status': 'PASS', 'complete_set_comparisons': len(comparisons)}


def source_request():
    source = read(SOURCE / 'selected-source.json.gz')
    text = source['candidate_text']
    return {'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'language': 'de',
            'regions': [{'id': 'selected-contract', 'language': 'de', 'selected': True, 'start': 0, 'end': len(text)}]}


def source():
    req = source_request()
    output = candidate()(req)
    save(HERE / 'actual-selected-source.json.gz', output)
    verify_output(req, output)
    assert exact_rows(output['names']) == exact_rows(cases_check()['whole_contract_expected_names'])
    assert not output['issues']
    view = read(SOURCE / 'selected-source.json.gz')
    bound = []
    for kind in ('names', 'uses'):
        for row in output[kind]:
            interval = {'start': row['start'], 'end': row['end'], 'quote': row['raw']}
            bound.append({'kind': kind, 'label': row['label'], **clipped(view, interval)})
    save(HERE / 'bound-selected-proposals.json.gz', {'source_snapshot_sha256': sha(SOURCE / 'selected-source.json.gz'),
         'actual_output_sha256': sha(HERE / 'actual-selected-source.json.gz'), 'proposals': bound,
         'provenance_gaps_repaired': False, 'scope_or_meaning_admitted': False})
    return {'status': 'PASS', 'whole_contract_exact_naming_set': len(output['names']),
            'descriptive_use_count': len(output['uses']), 'whole_contract_use_recall_established': False,
            'source_composition': dict(Counter(p['kind'] for r in bound for p in r['source_pieces'])),
            'ordinary_answers_run': 0}


def adverse():
    discover = candidate()
    valid = request(cases_check()['cases'][4])
    mutations = []
    def add(label, mutate):
        req = deepcopy(valid)
        mutate(req)
        mutations.append((label, req))
    add('changed-text-identity', lambda r: r.update(text='X' + r['text']))
    add('changed-sha-identity', lambda r: r.update(text_sha256='0' * 64))
    add('shifted-region-start', lambda r: r['regions'][0].update(start=1))
    add('shifted-region-end', lambda r: r['regions'][0].update(end=len(r['text']) - 1))
    add('bool-offset', lambda r: r['regions'][0].update(start=False))
    add('numeric-selection', lambda r: r['regions'][0].update(selected=1))
    add('missing-language', lambda r: r.update(language=None))
    add('duplicate-region-id', lambda r: r['regions'].append(deepcopy(r['regions'][0])))
    add('empty-source', lambda r: r.update(text='', text_sha256=hashlib.sha256(b'').hexdigest()))
    add('oversize-source', lambda r: r.update(text='x' * 100001, text_sha256=hashlib.sha256(b'x' * 100001).hexdigest()))
    def too_many_regions(r):
        r.update(text='x' * 257, text_sha256=hashlib.sha256(b'x' * 257).hexdigest(),
                 regions=[{'id': str(i), 'start': i, 'end': i + 1,
                           'language': 'de', 'selected': True} for i in range(257)])
    add('too-many-regions', too_many_regions)
    rows = []
    for label, req in mutations:
        try:
            discover(req)
        except ValueError as exc:
            rows.append({'case': label, 'actual_refusal': str(exc), 'input': req})
        else:
            raise AssertionError('Actual discovery request not refused: ' + label)
    # An internally consistent identity change is a different source. It is not
    # counterfeit proof of the frozen source; explicit source binding must fail.
    shifted = deepcopy(valid)
    shifted['text'] = 'X ' + shifted['text']
    shifted['text_sha256'] = hashlib.sha256(shifted['text'].encode()).hexdigest()
    shifted['regions'][0]['end'] = len(shifted['text'])
    changed = discover(shifted)
    assert changed['text_sha256'] != valid['text_sha256']
    assert exact_rows(changed['names']) != exact_rows(discover(valid)['names'])
    try:
        verify_output(valid, changed)
    except AssertionError:
        changed_binding = 'ACTUAL_VERIFIER_REFUSAL_DIFFERENT_IDENTITY'
    else:
        raise AssertionError('Different source was accepted against original binding')
    output_mutations = []
    def alter(label, mutate):
        output = deepcopy(discover(valid))
        mutate(output)
        try:
            verify_output(valid, output)
        except (AssertionError, KeyError):
            output_mutations.append({'case': label, 'actual_verifier_refusal': True, 'altered_output': output})
        else:
            raise AssertionError('Altered proposal escaped independent verifier: ' + label)
    alter('shifted-use-offset', lambda o: o['uses'][0].update(start=o['uses'][0]['start'] + 1))
    alter('shifted-whitespace-map', lambda o: o['uses'][0]['normalization_map'][0].__setitem__(0, 1))
    alter('invented-scope', lambda o: o['uses'][0].update(governing_scope='document'))
    alter('meaning-admission', lambda o: o.update(meaning_admitted=True))
    alter('lost-name-alternatives', lambda o: o['uses'][0].update(name_candidates=[]))
    save(HERE / 'adverse-requests.json', {'actual_refusals': rows,
        'actual_proposal_verifier_refusals': output_mutations,
        'validly_reidentified_source': {'request': shifted, 'actual_output': changed,
                                      'original_source_binding': changed_binding}})
    return {'status': 'PASS', 'actual_request_refusals': len(rows),
            'actual_proposal_verifier_refusals': len(output_mutations), 'different_source_offsets_retained': True}


def reconcile():
    original = read(SOURCE / 'reconciliation.json.gz')
    inventory = read(SOURCE / 'bound-inventory.json.gz')
    actual = read(HERE / 'actual-selected-source.json.gz')
    rows = []
    for record in inventory['records']:
        associations = []
        for use in record['uses']:
            matches = [r for r in actual['uses'] if r['start'] == use['start'] and r['end'] == use['end']]
            overlaps = [r for r in actual['uses'] if r['start'] < use['end'] and use['start'] < r['end']]
            associations.append({'start': use['start'], 'end': use['end'], 'quote': use['quote'],
                'source_reading_classification': use['classification'],
                'discovery_status': 'EXACT_LITERAL_PROPOSAL' if matches else
                    'OVERLAPPING_PROPOSAL_ONLY' if overlaps else 'NO_QUOTED_LABEL_LITERAL_PROPOSAL',
                'proposal_name_candidates': [r['name_candidates'] for r in matches],
                'source_reading_and_scope_retained': True})
        rows.append({'source_record': record, 'discovery_associations': associations})
    assert len(rows) == 62 and original['original_reference_records'] == 60
    save(HERE / 'reconciliation.json.gz', {'original_reconciliation': original,
         'original_reconciliation_sha256': sha(SOURCE / 'reconciliation.json.gz'),
         'source_records_and_associations': rows, 'original_reference_records': 60,
         'original_definition_records': 62, 'denominator_replaced': False,
         'known_misses': inventory['known_misses'], 'remaining': inventory['remaining'],
         'source_scope_readings_are_not_parser_admissions': True})
    return {'status': 'PASS', 'original_reference_records': 60, 'source_records': len(rows),
            'source_use_associations': dict(Counter(a['discovery_status'] for r in rows for a in r['discovery_associations'])),
            'original_task_complete': False}


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'result_kind': 'FINITE_QUOTED_LABEL_LITERAL_DISCOVERY',
        'original_task_complete': False, 'production_integrated': False, 'ordinary_answers_run': 0,
        'complete_case_comparisons': read(HERE / 'stages/verify/result.json')['complete_set_comparisons'],
        'whole_source': read(HERE / 'stages/source/result.json'),
        'adverse': read(HERE / 'stages/adverse/result.json'), 'resources': costs(),
        'next_action': 'Review scope admission and actual ordinary-consumer integration; preserve missing declarations and source provenance gaps',
        'not_concluded': ['General linguistic recall', 'Governing legal scope', 'Ordinary-answer integration',
                          'Fundamental external-package limitation', 'Original task or build completion']}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'commands': [r['command'] for r in sorted((read(p) for p in (HERE / 'stages').glob('*/started.json')), key=lambda r: r['started_at'])],
        'preparation_receipts': rel(PREP / 'stages'), 'environment': str(ROOT / '.venv/bin/python'),
        'cpu_gpu': 'CPU; GPU intentionally hidden', 'data_version': sha(SOURCE / 'outputs.json'),
        'random_seeds': 'N/A deterministic lexical trial', 'wall_time': costs(), 'plan': PLAN,
        'result': rel(HERE / 'result.json'), 'artifacts': rel(HERE), 'method_freeze': sha(PREP / 'freeze.json')})
    with (HERE / 'RESULT.md').open('x') as out:
        out.write('''# Bounded definition discovery trial

The independent original-source and constructed cases test lexical proposals,
not declarations or governing meanings. Actual outputs were retained before
verification. The full-contract naming set is independently authored; its other
use counts are descriptive. Quoted speech remains a review-required candidate.
All sixty original references, sixty-two source readings, competing scopes,
missing definitions and unresolved source-copy bindings remain retained.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite lexical mechanism for further integration | Exact complete sets on the frozen cases and full-source naming set | Actual request refusals and map checks retained | Shared source-reading mistakes, unsupported language and legal scope | Review scope admission and matched ordinary-answer effects | Automatic legal interpretation or whole-build completion |

The local capability gap motivated this mechanism. This trial does not establish
a fundamental limitation of any external package. Passing finite development
cases cannot establish unrestricted linguistic recall. An internally consistent
different source remains a different source, with different offsets and identity.
The strongest alternative explanation is a shared omission in source reading and
oracle authoring. Wider independent cases and downstream answer comparisons can
overturn this limited result. Production integration has not been attempted.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': result['resources']}


def propose():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 285
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(set(attempts)) == len(attempts) == 26
    assert next(e for e in reversed(events) if e.get('attempt') == rel(SOURCE))['kind'] == 'RECORD'
    assert read(PREP / 'stages/prepare/result.json')['status'] == 'PASS'
    source_check()
    cases_check()
    assert (PREP / 'PRE-ADMISSION-REVIEW.md').is_file()
    bindings = {rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    bindings.update({name: sha(ROOT / name) for name in (*CODE, METHOD, PLAN)})
    bindings.update({rel(p): sha(p) for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for module in read(PREP / 'identity-probe.json')['modules'].values():
        assert sha(ROOT / module['path']) == module['sha256']
        bindings[module['path']] = module['sha256']
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 286
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
        reason='Evaluate frozen independent quoted-label/literal-use cases; no automatic scope or downstream acceptance',
        definition_discovery_trial={'review': rel(PREP), 'source': rel(SOURCE), 'production_changes': False,
            'scope_admitted': False, 'cumulative026_027_bounds': {'seconds': 1800, 'bytes': 64 * 1024**2}})
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 27
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 286
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Evaluate independent frozen discovery cases; retain exact maps, original records and unresolved scopes; then review ordinary-consumer integration',
                stop_condition='27 cumulative admissions;180s stages;reuse026 cumulative1800s/64MiB;no unchanged retries')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Independent cases frozen before candidate implementation', 'Bound review-only discovery and actual source-offset evidence',
                    'Preserve original references and source scopes without replacing their denominator'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'PRE-ADMISSION-REVIEW.md')},
        'evidence_contract': {'primary': 'Exact complete sets on frozen cases and independently read full-source quoted naming set',
            'promotion_veto': ['Missing/invented interval', 'Unsafe map', 'Excluded-region crossing', 'Invented scope'],
            'continuation_veto': ['Frozen drift', 'Corrupted source/cases', 'Exhausted cumulative026 resources'],
            'explanatory_only': ['Whole-source use counts', 'Runtime', 'Counts and hashes'],
            'not_concluded': ['General recall', 'Legal binding', 'Ordinary-answer integration', 'Task/build completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 26, 'new_maximum': 27,
            'retained_attempts': attempts, 'reason': 'Source investigation026 sealed; independently frozen lexical mechanism is now discriminating next work',
            'next_discriminating_check': 'Exact candidate output against independent complete finite oracle before scope/consumer integration',
            'stop_condition': '180s stages;reuse026 cumulative1800s/64MiB including4MiB reserve;no unchanged retries',
            'same_scope_authorization': 'User requested refreshed master and continued general build with internal supported-behavior proof'},
        'resources_before_admission': costs(), 'new_time_or_storage_allowance': 0,
        'old_costs_and_admissions_retained': True, 'original_obligations_preserved': True}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 286, 'resources': costs()}


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in (*PREPARATION, *STAGES)
    stage = sys.argv[1]
    preparation = stage in PREPARATION
    folder = (PREP if preparation else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged retry refused'
    dependencies = {'prepare': (), 'propose': ('prepare',), 'evaluate': ('propose',), 'verify': ('evaluate',),
                    'source': ('verify',), 'adverse': ('source',), 'reconcile': ('adverse',), 'seal': ('reconcile',)}
    for dependency in dependencies[stage]:
        base = PREP if dependency in PREPARATION else HERE
        assert read(base / 'stages' / dependency / 'result.json')['status'] == 'PASS', dependency
    costs()
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_definition_discovery_trial', stage],
                                 'started_at': datetime.now(timezone.utc).isoformat(), 'stage_seconds': 180})
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Discovery trial stage bound')))
    signal.alarm(180)
    try:
        if not preparation:
            frozen()
        result = globals()[stage]()
        if not preparation:
            frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                                       if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result, ensure_ascii=False))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
                                     'wall_seconds': time.monotonic() - start})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
