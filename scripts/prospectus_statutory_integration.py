"""Bounded, immutable installation and trials of the reviewed statutory profile."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/statutory-integration-283'
HERE = AUTH / 'attempts/basf-references/attempt-024'
PRIOR = AUTH / 'attempts/basf-references/attempt-023'
LAW = AUTH / 'attempts/law-applicability/attempt-002'
PLAN = 'docs/plans/prospectus-statutory-integration-2026-10-18.md'
METHOD = 'scripts/prospectus_statutory_integration.py'
ORACLE = 'scripts/prospectus_statutory_integration_oracle.py'
DEST = 'src/legalmath/prospectus/successor/'
IDS = ('H16', 'H28', 'H35', 'H38', 'H39', 'H40', 'A2', 'A3', 'A7', 'A8', 'A11', 'A12')
PREPARATION = ('prepare', 'prepare-source-boundary', 'preflight', 'propose')


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


def baseline(label):
    from scripts.prospectus_internal_consumer_continuation import retained
    return retained(label + '-answer')


def costs(extra_seconds=0):
    start = read(PREP / 'accounting-start.json')
    receipts = [p for d in (PREP, HERE) for p in d.glob('stages/*/result.json')]
    receipts += [p for d in (PREP, HERE) for p in d.glob('stages/*/failure.json')]
    seconds = extra_seconds + sum(read(p)['wall_seconds'] for p in receipts)
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (PLAN, METHOD, ORACLE))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    revision = AUTH / 'revisions/0283.json'
    if revision.exists():
        paths.add(revision)
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    installed_bytes = sum(max(0, (ROOT / p).stat().st_size - old)
                          for p, old in start['production_bytes'].items() if (ROOT / p).exists())
    size += installed_bytes
    if seconds >= 3600 or size >= 188 * 1024**2:
        raise ValueError('Additional statutory integration resource bound exhausted')
    return {'additional_measured_seconds': seconds, 'additional_bytes': size,
            'seconds_bound': 3600, 'bytes_bound_including_reserve': 192 * 1024**2,
            'reserve_bytes': 4 * 1024**2, 'prior_admissions': 23,
            'installed_production_growth_bytes': installed_bytes,
            'retained_023_resources': start['prior_resources'],
            'historical_authoring_reading_controller_seconds': 'UNKNOWN'}


def quote(text, start, end):
    return {'start': start, 'end': end, 'quote': text[start:end],
            'line_first': text.count('\n', 0, start) + 1,
            'line_last': text.count('\n', 0, end) + 1}


def sections(text, numbers):
    result = []
    headers = list(re.finditer(r'(?m)^§\s+(\d+[a-z]?)\s+[^\n]+', text))
    for number in numbers:
        matches = [i for i, m in enumerate(headers) if m.group(1) == str(number)]
        if len(matches) != 1:
            raise ValueError('Ambiguous statutory section: ' + str(number))
        i = matches[0]
        result.append(quote(text, headers[i].start(), headers[i + 1].start() if i + 1 < len(headers) else len(text)))
    return result


def source_evidence(path, identity):
    text = path.read_text()
    if path.is_relative_to(PRIOR / 'local'):
        key = path.parent.name.removeprefix('extract-')
        receipt = read(PRIOR / 'requests' / key / 'receipt.json')
        extraction = read(path.parent / 'receipt.json')
        raw = PRIOR / 'requests' / key / 'body'
        assert sha(raw) == receipt['files']['body'] == extraction['source_sha256']
        assert sha(path) == extraction['text_sha256']
        info = {'raw_path': rel(raw), 'raw_sha256': sha(raw), 'url': receipt['effective_url'],
                'acquired_at': receipt['finished_at'], 'extraction_method': extraction['method'],
                'receipt_path': rel(PRIOR / 'requests' / key / 'receipt.json')}
        choices = {'H16': {'wpug-full': [29, 30]}, 'H35': {'aktg-full': [15, 16, 17, 18, 19, 291, 292]},
                   'A3': {'stabwg-full': [3, 7, 8, 10, 13]},
                   'A8': {'aktg-full': [135, 136, 137, 138]},
                   'A11': {'inso-full': list(range(38, 56))}}
        if key in choices.get(identity, {}):
            excerpts = sections(text, choices[identity][key])
        elif key.endswith('-index') or key == 'treasury-fatca':
            # An index is provenance/edition evidence, not a substantive act.
            excerpts = [quote(text, 0, len(text))]
        elif key == 'plaw-111-147':
            a = text.index('SEC. 502.')
            b = text.index('SEC. 511.', a)
            excerpts = [quote(text, a, b)]
        else:
            excerpts = [quote(text, 0, len(text))]
        info['reading_extent'] = ('Articles1-10 and AnnexII read; AnnexI searched only' if key == 'treasury-germany-iga'
                                  else 'Exact excerpts retained; see the source-review reading for inspected scope')
    elif path == LAW / 'schvg-utf8.txt':
        entry = read(LAW / 'source-bindings.json')['schvg.html']
        raw = LAW / 'schvg.html'
        assert sha(raw) == entry['sha256']
        info = {'raw_path': rel(raw), 'raw_sha256': sha(raw), 'url': entry['url'],
                'acquired_at': entry['recorded_at'], 'extraction_method': 'retained UTF-8 derivative',
                'receipt_path': rel(LAW / entry['receipt']), 'reading_extent': 'Full24-section source previously read'}
        numbers = {'H38': [5], 'H39': [5, 18], 'H40': [5], 'A7': [7, 8, 19], 'A8': [16]}[identity]
        excerpts = sections(text, numbers)
    else:
        return None  # Commentary stays commentary, never primary law.
    return {**info, 'text_path': rel(path), 'text_sha256': sha(path), 'excerpts': excerpts,
            'historical_application': 'NOT_PROVED', 'local_acquisition_is_earlier_knowledge': False}


def prepare():
    from legalmath.prospectus.successor.contracts import digest
    from legalmath.prospectus.successor.occurrences import segments
    p, _ = baseline('candidate')
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {u['id']: u for u in graph['units']}
    contexts = read(PRIOR / 'original-contexts.json')['records']
    findings = read(PRIOR / 'investigation.json')['records']
    literals = {'H16': 'WpÜG30(2)', 'H28': 'BGB801(1) sentence1', 'H35': 'AktG15',
                'H38': 'SchVG5(3) numbers1-8', 'H39': 'SchVG18 and5ff.', 'H40': 'SchVG5ff.',
                'A2': 'IRC1471(b),1471-1474 and implementing instruments', 'A3': 'StAbwG and regulations, dynamically in force',
                'A7': 'SchVG representative rights/duties/removal', 'A8': 'Analogous stock-law voting procedure unless notice overrides',
                'A11': 'Unspecified mandatory statutory priorities', 'A12': 'US tax certification, distinct tax purposes'}
    records = []
    for identity, context, finding in zip(IDS, contexts, findings):
        assert (context['family'], context['index']) == (finding['family'], finding['index'])
        parts = context['retained_selected_source_pieces']
        selected = [{'original': r['original'], 'selected': r['current_selection'],
                     'segments': segments(graph, r['current_selection'], _raw=raw)} for r in parts]
        primary = [source_evidence(ROOT / s['path'], identity) for s in finding['source_findings']]
        primary = [s for s in primary if s is not None]
        assert primary
        discovery = [{'reference': r, 'source_use': part['selected']['unit']}
                     for part in selected for r in graph['references']
                     if r['unit'] == part['original']['unit'] and r['start'] < part['original']['end']
                     and part['original']['start'] < r['end']]
        reading = finding['source_findings'][0]['reading']
        records.append({'id': identity, 'original_family': context['family'], 'original_index': context['index'],
                        'citation': literals[identity], 'contract_selection': selected,
                        'context_anchors': [s['original'] for s in selected],
                        'contract_context': context['raw_contract_context'],
                        'discovery_bindings': discovery, 'legal_sources': primary,
                        'reviewed_reading': reading, 'unresolved_application': finding['unresolved'],
                        'retrieved_edition': 'As labelled in retained primary sources; not proven2022 application',
                        'historical_validity': 'UNKNOWN',
                        'literal_extent': 'OPEN' if identity in ('H39','H40','A2','A3','A7','A8','A11','A12') else 'FINITE_CITATION',
                        'onward_scope': 'OPEN', 'operative_contract_target': False})
    spec = {'version': 'statutory-reference-profile.v1', 'profile': 'basf-statutory-reviewed-2026-10-18.v1',
            'source_investigation': rel(PRIOR / 'investigation.json'),
            'source_investigation_sha256': sha(PRIOR / 'investigation.json'), 'records': records}
    save(PREP / 'candidate/statutory_references_spec.json', spec)
    module = PREP / 'candidate/statutory_references.py'
    text = module.read_text()
    assert text.count('PROFILE_DIGEST_PENDING') == 1
    module.write_text(text.replace('PROFILE_DIGEST_PENDING', digest(spec)))
    installation = []
    for name in ('service.py', 'contracts.py'):
        path = ROOT / (DEST + name)
        before = path.read_bytes()
        (PREP / 'baseline').mkdir(exist_ok=True)
        (PREP / 'baseline' / name).write_bytes(before)
        text = before.decode()
        def replace(old, new):
            nonlocal text
            assert text.count(old) == 1, (name, old, text.count(old))
            text = text.replace(old, new, 1)
        if name == 'contracts.py':
            replace('"incorporation_admission", "relation_discovery", "archive_observations"}',
                                '"incorporation_admission", "relation_discovery", "archive_observations", "statutory_references"}')
        else:
            replace('    result = list(request["bundle"].get("dependencies", []))',
                '    from . import statutory_references\n    statutory = statutory_references.admit(graph, assembly, request)\n'
                '    result = list(request["bundle"].get("dependencies", []))\n'
                '    result.extend(statutory_references.dependencies(statutory))')
            replace('"governing_admission", "incorporation_admission"})',
                                '"governing_admission", "incorporation_admission", "statutory_references"})')
            replace('    assembly = selected["assembly"]\n    from .basf_call_references',
                '    assembly = selected["assembly"]\n    from . import statutory_references\n'
                '    statutory = statutory_references.admit(graph, assembly, request)\n    from .basf_call_references')
            replace("    if incorporation is not None:\n        result['incorporation_review'] = incorporation",
                '    if statutory is not None:\n        result["statutory_references"] = statutory\n'
                "    if incorporation is not None:\n        result['incorporation_review'] = incorporation")
            replace('    return seal("P4", request["bundle"], {"P1": source["sha256"], "P3": interpretation["sha256"]},\n'
                '                {"question": question, "cases": cases or [], "law_input": law_input})',
                '    from . import statutory_references\n'
                '    statutory = interpretation["payload"].get("statutory_references")\n'
                '    result = {"question": statutory_references.law_question(question, statutory),\n'
                '              "cases": cases or [], "law_input": law_input}\n'
                '    if statutory is not None:\n'
                '        result.update(conditional_question=question, statutory_references=statutory)\n'
                '    return seal("P4", request["bundle"], {"P1": source["sha256"], "P3": interpretation["sha256"]}, result)')
            replace('    interpretation_input = {**request, **(semantic.get(\'interpretation_input\') or {})}',
                '    interpretation_input = {**request, **(semantic.get(\'interpretation_input\') or {})}\n'
                '    from . import statutory_references\n'
                '    statutory = statutory_references.verify_consumed(graph, selected["assembly"], interpretation_input, semantic)\n'
                '    statutory_references.verify_law(verify(law, "P4", bundle, {"P1": source["sha256"], "P3": interpretation["sha256"]}), request, graph, statutory)')
            replace('"mode": "ASSISTED" if supplied_legal_model or ',
                                '"mode": "ASSISTED" if statutory is not None or supplied_legal_model or ')
            replace('    from .source_graph import native_text_gaps',
                '    if statutory is not None:\n        result["statutory_references"] = statutory\n'
                '    from .source_graph import native_text_gaps')
        assert text != before.decode(), name
        (PREP / 'candidate' / name).write_text(text)
    for name in ('service.py','contracts.py','statutory_references.py','statutory_references_spec.json'):
        target = ROOT / (DEST + name)
        installation.append({'target': DEST + name, 'baseline': rel(PREP / 'baseline' / name) if target.exists() else None,
                             'before_sha256': sha(target) if target.exists() else None,
                             'candidate': rel(PREP / 'candidate' / name),
                             'after_sha256': sha(PREP / 'candidate' / name)})
    save(PREP / 'installation.json', {'version': 'exact-installation.v1', 'files': installation,
         'input_replacements': {r['target']: [r['baseline'], r['candidate']] for r in installation if r['baseline']},
         'controller_unchanged': True, 'historical_freezes_unchanged': True})
    for name in ('service.py','contracts.py','statutory_references.py'):
        compile((PREP / 'candidate' / name).read_text(), name, 'exec')
    return {'status': 'PASS', 'records': len(records), 'discovery_bindings': sum(len(r['discovery_bindings']) for r in records),
            'production_changed': False, 'compiled_candidate': True, 'specification_sha256': digest(spec)}


def frozen(installed=True):
    from legalmath.prospectus.execution_authority import Authority, digest
    admission = read(HERE / 'admission.json')
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for path, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / path) == checksum, path
    for row in read(PREP / 'installation.json')['files']:
        target = ROOT / row['target']
        wanted = row['after_sha256'] if installed else row['before_sha256']
        assert (sha(target) if target.exists() else None) == wanted, row['target']


def install():
    frozen(installed=False)
    for row in read(PREP / 'installation.json')['files']:
        path = ROOT / row['target']
        temporary = path.with_name(path.name + '.statutory-install')
        assert not temporary.exists()
        with temporary.open('xb') as stream:
            stream.write((ROOT / row['candidate']).read_bytes())
        temporary.replace(path)
    frozen()
    return {'status': 'PASS', 'exact_reviewed_files_installed': 4, 'controller_unchanged': True}


def retain(label, products, answer=None):
    from scripts.prospectus_typed_delta import changes, apply, equal
    from legalmath.prospectus.successor.contracts import digest
    original, old_answer = baseline(label.split('-')[0])
    delta = changes(original, products)
    equal(apply(original, delta), products, 'Lossy statutory product retention')
    row = {'products_delta': delta, 'products_sha256': digest(products)}
    if answer is not None:
        delta = changes(old_answer, answer)
        equal(apply(old_answer, delta), answer, 'Lossy statutory answer retention')
        row.update(answer_delta=delta, answer_sha256=digest(answer))
    save(HERE / (label + '.json.gz'), row)


def retained(label):
    from scripts.prospectus_typed_delta import apply
    from legalmath.prospectus.successor.contracts import digest
    original, answer = baseline(label.split('-')[0])
    row = read(HERE / (label + '.json.gz'))
    p = apply(original, row['products_delta'])
    assert digest(p) == row['products_sha256']
    if 'answer_delta' not in row:
        return p, None
    a = apply(answer, row['answer_delta'])
    assert digest(a) == row['answer_sha256']
    return p, a


def build(label):
    from legalmath.prospectus.successor import service, statutory_references
    prefix, state = label.split('-')
    p, _ = baseline(prefix)
    value = deepcopy(p['P3']['payload']['interpretation_input'])
    if state != 'absent':
        value['statutory_references'] = statutory_references.packet('RETAINED' if state == 'retained' else 'NOT_SUPPLIED')
    old_law, old_finance = p['P4']['payload'], p['P5']['payload']
    p['P3'] = service.interpretation_product(p['P1'], p['P2'], value)
    p['P4'] = service.law_product(p['P1'], p['P3'], old_law['cases'], old_law['law_input'])
    p['P5'] = service.financial_product(p['P1'], p['P2'], p['P3'], old_finance['cases'], old_finance['scenario_input'])
    retain(label + '-products', p)
    return {'status': 'PASS', 'products_retained_before_consumption': True}


def consume(label):
    from legalmath.prospectus.successor import service
    p, _ = retained(label + '-products')
    answer = service.consume(p, ROOT, mode='frozen')
    retain(label + '-answer', p, answer)
    return {'status': 'PASS', 'ordinary_answer_retained_before_verification': True}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 282
    assert read(PREP / 'stages/preflight/result.json')['status'] == 'PASS'
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 23
    binding = {rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    binding.update({name: sha(ROOT / name) for name in (*CODE, PLAN, METHOD, ORACLE)})
    save(PREP / 'freeze.json', {'bindings': binding})
    proposal = deepcopy(program)
    proposal['revision'] = 283
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    replacements = read(PREP / 'installation.json')['input_replacements']
    assert all(name in task['inputs'] for name in replacements)
    task['inputs'] = [name for name in task['inputs'] if name not in replacements]
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(binding) + [rel(PREP / 'freeze.json')]))
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
                reason='Install exact reviewed statutory profile; preserve original discovery closure and prove ordinary-answer uncertainty effects',
                statutory_integration={'review': rel(PREP), 'installation': rel(PREP / 'installation.json'),
                    'bounds': {'stage_seconds': 180, 'additional_measured_seconds': 3600, 'bytes': 192 * 1024**2},
                    'original_task_complete': False})
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 24
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 283
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task), remaining='Twelve source readings retained; historical/application and definition/discovery work remain.',
                       next_action='Exact staged installation; independent ordinary answers and resealed controls; retain partial result and continue original remainder.',
                       acceptance='Full-answer comparison with both021 answers, exact legal uncertainty and actual adverse refusals; no original-task completion.',
                       stop_condition='24 cumulative admissions;180s stages;3600 additional measured seconds;192MiB including4MiB reserve;no unchanged retries.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN), rel(PREP / 'routes.json'): sha(PREP / 'routes.json'),
                                                      rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Exact immutable candidate/baseline installation replaces only two mutable task inputs',
                    'Finite assisted source profile; retain historical/application UNKNOWN and original unresolved contract discovery',
                    'Independent full-answer comparator and actual upstream/resealed downstream controls'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
                            'production_changed_before_admission': False, 'no_historical_freeze_rewritten': True},
        'evidence_contract': {'primary': 'Independent twelve-source reconstruction, exact Q1/Q2/Q4 uncertainty in ordinary answers and whole unaffected-answer equality with both021 comparators',
            'veto': ['Accepted forgery','Hidden uncertainty','Changed unrelated answer','Wrong source/edition','Frozen/resource invalidity'],
            'not_concluded': ['2022 applicability','Entitlement','Automatic discovery','Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 23, 'new_maximum': 24,
            'retained_attempts': attempts, 'reason': '023 source investigation complete; distinct ordered source-to-answer integration under original task',
            'next_discriminating_check': 'Actual ordinary Q1/Q2/Q4 propagation and resealed consumer refusal',
            'stop_condition': '180s stages;3600 additional measured seconds;192MiB;no unchanged automatic retry',
            'same_scope_authorization': 'User directs refreshed master and continued general build, internally demonstrated conditional correctness'},
        'resources_before_admission': costs(), 'original_obligations_preserved': True}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 283, 'prior_admissions_retained': 23, 'resources': costs()}


def main():
    label = sys.argv[1]
    if label == 'start':
        save(PREP / 'accounting-start.json', {'program_bytes': (AUTH / 'program.json').stat().st_size,
            'production_bytes': {DEST + name: (ROOT / (DEST + name)).stat().st_size
                                  if (ROOT / (DEST + name)).exists() else 0 for name in
                                  ('service.py','contracts.py','statutory_references.py','statutory_references_spec.json')},
            'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
            'prior_resources': read(PRIOR / 'result.json').get('resources', 'See sealed023 result'),
            'started_at': datetime.now(timezone.utc).isoformat()})
        print('{"status":"PASS","accounting_started":true}')
        return
    preparation = label in PREPARATION
    folder = (PREP if preparation else HERE) / 'stages' / label
    assert not (folder / 'started.json').exists(), 'Stage already started; unchanged retry refused'
    resources = costs()
    from scripts.prospectus_statutory_integration_oracle import prerequisites
    for dependency in prerequisites(label):
        base = PREP if dependency in PREPARATION else HERE
        assert read(base / 'stages' / dependency / 'result.json')['status'] == 'PASS', dependency
    save(folder / 'started.json', {'command': ['.venv/bin/python','-m','scripts.prospectus_statutory_integration',label],
         'started_at': datetime.now(timezone.utc).isoformat(), 'stage_seconds': 180})
    began = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Statutory integration stage bound')))
    signal.alarm(180)
    try:
        if not preparation:
            frozen(installed=label != 'install')
        if label.startswith('build-'):
            result = build(label.removeprefix('build-'))
        elif label.startswith('consume-'):
            result = consume(label.removeprefix('consume-'))
        elif label == 'prepare-source-boundary':
            failure = read(PREP / 'stages/prepare/failure.json')
            assert failure['type'] == 'ValueError' and failure['message'] == 'substring not found'
            assert not (PREP / 'candidate/statutory_references_spec.json').exists()
            result = prepare()
        elif label in ('prepare','install','propose'):
            result = globals()[label]()
        else:
            from scripts import prospectus_statutory_integration_oracle as oracle
            result = oracle.dispatch(label)
        if not preparation:
            frozen()
        costs(time.monotonic() - began)
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps({k: v for k, v in result.items() if k != 'details'}))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
                                     'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
