"""Independent retained-source reconstruction and real statutory product controls.

Expected answers are constructed from023 and the two protected021 answers;
production admit/verify helpers are never the answer oracle.
"""
from copy import deepcopy
import ast
from datetime import datetime, timezone
import importlib.util
import inspect
import subprocess
import sys

from scripts import prospectus_statutory_integration as run
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_typed_delta import equal

LABELS = tuple(a + '-' + b for a in ('candidate', 'missing') for b in ('absent', 'retained', 'unavailable'))
PREFIX = 'statutory-reference:'
MODULE = 'legalmath.prospectus.successor.statutory_references'
PROFILE_ERROR = 'Statutory reference requires the exact registered source reading and edition'
READING_ERROR = 'Consumed statutory reference reading differs from reconstruction'
CONTROLS = {
    **{'reading-' + key: (READING_ERROR, 'verify_consumed') for key in run.IDS},
    'report-drop': (READING_ERROR, 'verify_consumed'),
    'input-drop': ('Consumed statutory reference lacks supplied evidence', 'verify_consumed'),
    'input-forgery': (PROFILE_ERROR, 'admit'),
    'dependency-drop': ('Consumed statutory dependencies differ from reconstruction', 'verify_consumed'),
    'dependency-resolve': ('Consumed statutory dependencies differ from reconstruction', 'verify_consumed'),
    'q1-hidden': ('Consumed statutory question hides or invents uncertainty', 'verify_consumed'),
    'q2-subquestion-hidden': ('Consumed statutory question hides or invents uncertainty', 'verify_consumed'),
    'q1-resolve': ('Consumed statutory question resolves uncertainty', 'verify_consumed'),
    'q4-resolve': ('Consumed statutory law uncertainty differs from reconstruction', 'verify_law'),
    'q4-hidden': ('Consumed statutory law uncertainty differs from reconstruction', 'verify_law'),
    'q4-conditional': ('Consumed statutory law uncertainty differs from reconstruction', 'verify_law'),
    'q4-report': ('Consumed statutory law uncertainty differs from reconstruction', 'verify_law'),
}
STAGES = ('install', 'tests', *sum((('build-' + label, 'consume-' + label, 'verify-' + label)
                                 for label in LABELS), ()), 'request-route', 'upstream',
          *('control-' + case for case in CONTROLS), 'reconcile', 'seal')


def prerequisites(label):
    if label in ('prepare', 'prepare-source-boundary'):
        return ()
    if label == 'preflight':
        return ('prepare-source-boundary',)
    if label == 'propose':
        return ('preflight',)
    if label == 'install':
        return ('propose',)
    if label not in STAGES:
        raise ValueError('Unregistered statutory stage: ' + label)
    if label == 'tests' or label.startswith('build-'):
        return ('install',) if label == 'tests' else ('tests',)
    if label.startswith('consume-'):
        return ('build-' + label.removeprefix('consume-'),)
    if label.startswith('verify-'):
        return ('consume-' + label.removeprefix('verify-'),)
    if label in ('request-route', 'upstream') or label.startswith('control-'):
        return ('verify-candidate-retained', 'verify-missing-unavailable')
    if label == 'reconcile':
        return tuple(s for s in STAGES if s.startswith(('verify-', 'control-'))) + ('request-route', 'upstream')
    return ('reconcile',)


def staged():
    name = 'legalmath.prospectus.successor._statutory_candidate'
    spec = importlib.util.spec_from_file_location(name, run.PREP / 'candidate/statutory_references.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_sources():
    for number in (21, 22, 23):
        folder = run.AUTH / f'attempts/basf-references/attempt-{number:03d}'
        for path, checksum in run.read(folder / 'outputs.json').items():
            assert run.sha(folder / path) == checksum, ('Sealed evidence changed', number, path)
    spec = run.read(run.PREP / 'candidate/statutory_references_spec.json')
    findings = run.read(run.PRIOR / 'investigation.json')['records']
    contexts = run.read(run.PRIOR / 'original-contexts.json')['records']
    assert spec['source_investigation_sha256'] == run.sha(run.PRIOR / 'investigation.json')
    assert [r['id'] for r in spec['records']] == list(run.IDS)
    checks = []
    for record, finding, context in zip(spec['records'], findings, contexts):
        assert (record['original_family'], record['original_index']) == (context['family'], context['index'])
        assert (context['family'], context['index']) == (finding['family'], finding['index'])
        equal(record['contract_context'], context['raw_contract_context'], 'Original context changed')
        equal(record['reviewed_reading'], finding['source_findings'][0]['reading'], 'Source reading changed')
        equal(record['unresolved_application'], finding['unresolved'], 'Unresolved application changed')
        equal([p['original'] for p in record['contract_selection']],
              [p['original'] for p in context['retained_selected_source_pieces']], 'Original anchors changed')
        equal([p['selected'] for p in record['contract_selection']],
              [p['current_selection'] for p in context['retained_selected_source_pieces']], 'Selected context changed')
        assert record['historical_validity'] == 'UNKNOWN' and record['onward_scope'] == 'OPEN'
        assert record['operative_contract_target'] is False
        expected_paths = [s['path'] for s in finding['source_findings']
                          if (run.ROOT / s['path']).is_relative_to(run.PRIOR / 'local')
                          or run.ROOT / s['path'] == run.LAW / 'schvg-utf8.txt']
        equal([s['text_path'] for s in record['legal_sources']], expected_paths, 'Primary-law source set changed')
        for source in record['legal_sources']:
            text_path, raw_path = (run.ROOT / source[k] for k in ('text_path', 'raw_path'))
            assert run.sha(text_path) == source['text_sha256']
            assert run.sha(raw_path) == source['raw_sha256']
            assert source['historical_application'] == 'NOT_PROVED'
            assert source['local_acquisition_is_earlier_knowledge'] is False
            text = text_path.read_text()
            assert source['excerpts']
            for q in source['excerpts']:
                assert type(q['start']) is int and type(q['end']) is int
                assert 0 <= q['start'] < q['end'] <= len(text)
                assert text[q['start']:q['end']] == q['quote']
                assert q['line_first'] == text.count('\n', 0, q['start']) + 1
                assert q['line_last'] == text.count('\n', 0, q['end']) + 1
            if text_path == run.LAW / 'schvg-utf8.txt':
                receipt = run.read(run.LAW / 'source-bindings.json')['schvg.html']
                assert receipt['sha256'] == source['raw_sha256'] and receipt['url'] == source['url']
            else:
                receipt = run.read(run.ROOT / source['receipt_path'])
                extraction = run.read(text_path.parent / 'receipt.json')
                assert receipt['files']['body'] == extraction['source_sha256'] == source['raw_sha256']
                assert extraction['text_sha256'] == source['text_sha256']
                assert receipt['finished_at'] == source['acquired_at']
                assert receipt['effective_url'] == source['url']
            checks.append({'record': record['id'], 'text_path': source['text_path'],
                           'text_sha256': source['text_sha256'], 'excerpts': len(source['excerpts'])})
    # Reading identity alone is not correctness. These inspected023 safeguards
    # must stay visible, including the corrected excise-purpose exception.
    note = (run.PRIOR / 'SOURCE-REVIEW.md').read_text()
    for phrase in ('502(e)', 'blank', 'AnnexI', 'participating voting rights', 'individual-case exception'):
        assert phrase in note
    return spec, checks


def expected_report(products, state):
    spec = run.read(run.PREP / 'candidate/statutory_references_spec.json')
    records = deepcopy(spec['records'])
    for r in records:
        r.update(availability='RETAINED_PRIMARY_READING' if state == 'retained' else 'NOT_SUPPLIED',
                 application='UNKNOWN', uncertainties=['HISTORICAL_EDITION_NOT_PROVED', 'ONWARD_SCOPE_OPEN',
                                                       'APPLICATION_PREMISES_NOT_ESTABLISHED'])
        if state != 'retained':
            r['uncertainties'].insert(0, 'PRIMARY_READING_NOT_SUPPLIED')
            r['legal_sources'] = []
    bundle = products['P1']['payload']['request']['bundle']
    return {'version': 'statutory-reference-review.v1', 'profile': spec['profile'],
            'profile_sha256': digest(spec), 'evidence_state': 'RETAINED' if state == 'retained' else 'NOT_SUPPLIED',
            'as_of': {k: bundle[k] for k in ('issue_date', 'effective_at', 'known_at')},
            'records': records, 'automatic_discovery': False, 'historical_application_proved': False,
            'complete_reference_graph': False,
            'meaning': 'Reviewed source readings with unresolved historical and conditional application'}


def expected_dependencies(report):
    result = []
    for r in report['records']:
        result.append({'id': PREFIX + r['id'], 'kind': 'LEGAL_AUTHORITY', 'questions': ['Q1', 'Q2', 'Q4'],
            'status': 'UNRESOLVED', 'profile_sha256': report['profile_sha256'], 'record_sha256': digest(r),
            'source_uses': [p['selected']['unit'] for p in r['contract_selection']],
            **{k: r[k] for k in ('availability','historical_validity','literal_extent','onward_scope','application','uncertainties')}})
    return result


def question(previous, ids, *, ordered=False):
    value = deepcopy(previous)
    value.update(status='CONFLICT' if value['status'] == 'CONFLICT' else 'UNKNOWN', value=None)
    combined = [*value['unresolved'], *ids]
    value['unresolved'] = list(dict.fromkeys(combined)) if ordered else sorted(set(combined))
    return value


def questions(previous, ids):
    result = deepcopy(previous)
    for key in ('Q1', 'Q2'):
        result[key] = question(result[key], ids)
        for name, old in previous[key].get('subquestions', {}).items():
            result[key]['subquestions'][name] = question(old, ids)
    q3 = result['Q3']
    for key in ('Q1', 'Q2'):
        if key in q3['value']:
            q3['value'][key]['unresolved'] = result[key]['unresolved']
            q3['value'][key]['complete'] = False
    q3['status'] = 'PARTIAL'
    return result


def preflight():
    spec, checks = validate_sources()
    before = (run.PREP / 'baseline/service.py').read_text()
    after = (run.PREP / 'candidate/service.py').read_text()
    def functions(text):
        return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(text).body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    b, a = functions(before), functions(after)
    assert set(b) == set(a)
    assert {k for k in b if b[k] != a[k]} == {'dependencies', 'interpretation_product', 'law_product', 'consume'}
    assert after.index('statutory_references.verify_consumed(') < after.index('call_references = verify_call_references(')
    assert after.count('statutory_references.verify_law(') == 1
    assert 'statutory_references' in (run.PREP / 'candidate/contracts.py').read_text()
    module = staged()
    for prefix in ('candidate', 'missing'):
        p, _ = run.baseline(prefix)
        graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
        request = {**p['P1']['payload']['request'], **p['P3']['payload']['interpretation_input']}
        assert module.admit(graph, assembly, request) is None
        for state in ('retained', 'unavailable'):
            supplied = {**request, 'statutory_references': module.packet('RETAINED' if state == 'retained' else 'NOT_SUPPLIED')}
            equal(module.admit(graph, assembly, supplied), expected_report(p, state), 'Staged source reconstruction differs')
    return {'status': 'PASS', 'role': 'PREPARATION_ONLY', 'source_bindings': checks,
            'records': len(spec['records']), 'production_installed': False,
            'ordinary_answers_run': 0, 'changed_service_functions': ['dependencies','interpretation_product','law_product','consume']}


def tests():
    command = [sys.executable, '-m', 'pytest', '-q', 'tests/prospectus_successor/test_reference_consumer_integrity.py',
               'tests/prospectus_successor/test_law_assistance_mode.py', 'tests/prospectus_successor/test_unavailable_references.py']
    result = subprocess.run(command, cwd=run.ROOT, capture_output=True, text=True, timeout=150)
    run.save(run.HERE / 'checks/targeted-tests.json', {'command': command, 'returncode': result.returncode,
                                                     'stdout': result.stdout, 'stderr': result.stderr})
    assert result.returncode == 0, result.stdout[-1800:] + result.stderr[-1000:]
    return {'status': 'PASS', 'targeted_tests': result.stdout.strip()[-500:], 'role': 'ENGINEERING_REGRESSION_ONLY'}


def verify_answer(label):
    prefix, state = label.split('-')
    p, answer = run.retained(label + '-answer')
    old, baseline_answer = run.baseline(prefix)
    if state == 'absent':
        equal(p, old, 'Absent profile changed complete products')
        equal(answer, baseline_answer, 'Absent profile changed complete ordinary answer')
    else:
        report = expected_report(p, state)
        deps = expected_dependencies(report)
        ids = [d['id'] for d in deps]
        expected = deepcopy(old['P3']['payload'])
        spec = run.read(run.PREP / 'candidate/statutory_references_spec.json')
        expected['interpretation_input']['statutory_references'] = {
            'profile': spec['profile'], 'evidence_state': report['evidence_state'], 'records': spec['records']}
        expected['statutory_references'] = report
        index = len(old['P1']['payload']['request']['bundle'].get('dependencies', []))
        expected['dependencies'][index:index] = deps
        expected['questions'] = questions(expected['questions'], ids)
        equal(p['P3']['payload'], expected, 'Complete statutory P3 differs from independent reconstruction')
        expected = deepcopy(old['P4']['payload'])
        expected['conditional_question'] = deepcopy(expected['question'])
        expected['question'] = question(expected['question'], ids, ordered=True)
        expected['statutory_references'] = report
        equal(p['P4']['payload'], expected, 'Complete statutory P4 differs from independent reconstruction')
        equal(p['P5']['payload'], old['P5']['payload'], 'Unrelated financial payload changed')
        equal(p['P1'], old['P1'], 'Source phase changed')
        equal(p['P2'], old['P2'], 'Construction phase changed')
        expected = deepcopy(baseline_answer)
        expected['statutory_references'] = report
        expected['questions'] = questions(expected['questions'], ids)
        expected['questions']['Q4'] = question(baseline_answer['questions']['Q4'], ids, ordered=True)
        if 'Q4' in expected['questions']['Q3']['value']:
            expected['questions']['Q3']['value']['Q4'].update(complete=False,
                unresolved=expected['questions']['Q4']['unresolved'])
        expected['consumed_products'] = {s: p[s]['sha256'] for s in p}
        expected['mode'] = 'ASSISTED'
        expected['report_sha256'] = digest({k: v for k, v in expected.items() if k != 'report_sha256'})
        equal(answer, expected, 'Whole ordinary answer differs outside enumerated statutory effects')
        assert 'dependencies' not in answer, 'Invented ordinary API member'
        assert answer['independent_legal_acceptance'] is False and answer['may_execute_transaction'] is False
    return {'status': 'PASS', 'complete_answer_checked': True, 'complete_products_checked': True,
            'comparator': prefix + '-answer in sealed021', 'state': state,
            'answer_sha256': digest(answer), 'original_task_complete': False}


def refusal(exc, expected, function):
    frames = []
    tb = exc.__traceback__
    while tb:
        frames.append({'module': tb.tb_frame.f_globals.get('__name__'),
                       'function': tb.tb_frame.f_code.co_name, 'line': tb.tb_lineno})
        tb = tb.tb_next
    assert type(exc) is ValueError and str(exc) == expected, (str(exc), expected)
    assert (frames[-1]['module'], frames[-1]['function']) == (MODULE, function), frames[-1]
    return {'message': str(exc), 'origin': frames[-1], 'traceback': frames}


def reseal(products, payloads):
    from legalmath.prospectus.successor import service
    p = dict(products)
    for stage in ('P3', 'P4', 'P5'):
        inputs = {**products[stage]['inputs']}
        if stage != 'P3':
            inputs['P3'] = p['P3']['sha256']
        p[stage] = service.seal(stage, p['P1']['payload']['request']['bundle'], inputs,
                                payloads.get(stage, products[stage]['payload']))
        service.verify(p[stage], stage, p['P1']['payload']['request']['bundle'], inputs)
    return p


def control(case):
    from legalmath.prospectus.successor import service
    p, _ = run.retained('candidate-retained-answer')
    semantic, law = deepcopy(p['P3']['payload']), deepcopy(p['P4']['payload'])
    if case.startswith('reading-'):
        row = next(r for r in semantic['statutory_references']['records'] if r['id'] == case.removeprefix('reading-'))
        row['reviewed_reading'] += '\nUnsupported unconditional application.'
    elif case == 'report-drop':
        del semantic['statutory_references']
    elif case == 'input-drop':
        del semantic['interpretation_input']['statutory_references']
    elif case == 'input-forgery':
        semantic['interpretation_input']['statutory_references']['records'][0]['historical_validity'] = 'PROVED_2022'
    elif case.startswith('dependency-'):
        d = next(d for d in semantic['dependencies'] if d['id'].startswith(PREFIX))
        if case == 'dependency-drop':
            semantic['dependencies'].remove(d)
        else:
            d['status'] = 'RESOLVED'
    elif case.startswith(('q1-', 'q2-')):
        q = semantic['questions']['Q1' if case.startswith('q1') else 'Q2']
        if case == 'q2-subquestion-hidden':
            q = q['subquestions']['possible_common']
        if case.endswith('hidden'):
            q['unresolved'].remove(PREFIX + run.IDS[0])
        else:
            q.update(status='YES', value=True)
    elif case == 'q4-resolve':
        law['question'].update(status='YES', value=True)
    elif case == 'q4-hidden':
        law['question']['unresolved'].remove(PREFIX + run.IDS[0])
    elif case == 'q4-conditional':
        law['conditional_question']['status'] = 'INVENTED'
    elif case == 'q4-report':
        law['statutory_references']['records'][0]['application'] = 'PROVED'
    else:
        raise ValueError('Unknown statutory control')
    bad = reseal(p, {'P3': semantic, 'P4': law})
    assert digest(bad) != digest(p)
    run.retain('candidate-control-' + case, bad)
    expected, function = CONTROLS[case]
    try:
        service.consume(bad, run.ROOT, mode='frozen')
    except ValueError as exc:
        receipt = refusal(exc, expected, function)
        run.save(run.HERE / ('controls/' + case + '.json'), {'case': case, 'validly_resealed': True,
            'original_products_sha256': digest(p), 'forged_products_sha256': digest(bad), **receipt})
        return {'status': 'PASS', 'case': case, 'actual_consumer_refusal': receipt['message'],
                'validly_resealed': True, 'origin': receipt['origin']}
    raise ValueError('Validly resealed statutory forgery accepted: ' + case)


def upstream():
    from legalmath.prospectus.successor import service
    p, _ = run.retained('candidate-retained-answer')
    original = p['P3']['payload']['interpretation_input']
    cases = [('reading-' + key, key, 'reviewed_reading', 'Unsupported unconditional reading') for key in run.IDS]
    cases += [('edition-' + key, key, 'retrieved_edition', 'PROVED_2022') for key in run.IDS]
    cases += [('wrong-law','H16','citation','Contract section5'), ('missing-numbered-item','H38','citation','SchVG5(3)1-7'),
              ('closed-ff','H39','onward_scope','CLOSED'), ('deduplicate-ff','H40','id','H39'),
              ('omitted-regulations','A2','citation','IRC1471 only; regulations irrelevant'),
              ('owner-institution','A2','reviewed_reading','Every beneficial owner is a reporting institution'),
              ('later-law-earlier','A3','historical_validity','PROVED_2022'),
              ('backdated-acquisition','A3','retrieved_edition','Acquired and known2022'),
              ('mandate-is-exercise','A7','reviewed_reading','Power proves effective exercise'),
              ('wrong-vote-denominator','A8','reviewed_reading','75% of outstanding nominal amount'),
              ('ignored-notice','A8','reviewed_reading','The notice cannot override the voting procedure'),
              ('exhaustive-priorities','A11','onward_scope','CLOSED_EXHAUSTIVE_38_55'),
              ('erased-excise-exception','A12','reviewed_reading','502(a) abolished every foreign bearer exception including4701(b)')]
    receipts = []
    for name, key, field, value in cases:
        bad = deepcopy(original)
        row = next(r for r in bad['statutory_references']['records'] if r['id'] == key)
        row[field] = value
        run.save(run.HERE / ('upstream/' + name + '-input.json.gz'), {'interpretation_input': bad})
        try:
            service.interpretation_product(p['P1'], p['P2'], bad)
        except ValueError as exc:
            receipt = {'case': name, **refusal(exc, PROFILE_ERROR, 'admit')}
            run.save(run.HERE / ('upstream/' + name + '-actual.json'), receipt)
            receipts.append(receipt)
        else:
            raise ValueError('Altered statutory profile admitted: ' + name)
    bad = deepcopy(original)
    ref = next(d['reference'] for r in bad['statutory_references']['records'] for d in r['discovery_bindings'])
    bad.setdefault('reference_dispositions', {})[ref['id']] = {'reason': 'Coincidentally numbered contract5',
        'source_sha256': ref['source_sha256'], 'targets': []}
    run.save(run.HERE / 'upstream/contract5-input.json.gz', {'interpretation_input': bad})
    try:
        service.interpretation_product(p['P1'], p['P2'], bad)
    except ValueError as exc:
        receipt = {'case': 'contract5', **refusal(exc, 'Statutory reference cannot target an operative contract clause', 'admit')}
        run.save(run.HERE / 'upstream/contract5-actual.json', receipt)
        receipts.append(receipt)
    else:
        raise ValueError('Statutory contract5 redirect accepted')
    return {'status': 'PASS', 'actual_upstream_refusals': len(receipts), 'cases': [r['case'] for r in receipts]}


def request_route():
    from unittest.mock import patch
    from legalmath.prospectus.successor import service, sealed_source, sealed_runtime, statutory_references
    p, _ = run.baseline('candidate')
    request = deepcopy(p['P1']['payload']['request'])
    request['statutory_references'] = statutory_references.packet()
    snapshot = run.HERE / 'transport-snapshot'
    manifest = sealed_runtime.snapshot(snapshot, {'/review/installation.json': run.PREP / 'installation.json'})
    runtime = sealed_source.SourceRuntime(snapshot, sealed_runtime.digest(manifest))
    # Exercise the existing sealed-source delegation and actual intake validation.
    # Only extraction is replaced by an already retained graph; no model/native
    # execution or fresh-derivative claim follows from this transport diagnostic.
    with patch.object(service.source_graph, 'build', return_value=p['P1']['payload']['graph']) as build:
        source = sealed_source.source_product(request, run.ROOT, runtime)
    assert build.call_count == 1
    assert runtime.receipts == []
    equal(source['payload']['request'], request, 'Sealed-source route dropped statutory input')
    selected = service.seal('P2', request['bundle'], {'P1': source['sha256']}, p['P2']['payload'])
    semantic = service.interpretation_product(source, selected, p['P3']['payload']['interpretation_input'])
    equal(semantic['payload']['statutory_references'], expected_report(p, 'retained'), 'Request-side statutory profile dropped')
    run.save(run.HERE / 'request-route.json', {'source_request_sha256': digest(source['payload']['request']),
        'semantic_sha256': semantic['sha256'], 'native_calls': 0, 'model_calls': 0,
        'extraction_stub': 'Already retained graph; transport diagnostic only', 'request_profile_preserved': True})
    return {'status': 'PASS', 'request_profile_preserved': True, 'native_execution_proved': False}


def reconcile():
    receipts = {stage: run.read(run.HERE / 'stages' / stage / 'result.json')
                for stage in prerequisites('reconcile')}
    for r in receipts.values():
        assert r['status'] == 'PASS'
    ledger = run.read(run.AUTH / 'attempts/basf-references/attempt-022/candidate-answer-reconciliation.json.gz')
    assert len(ledger['records']) == 60
    by_original = {(r['family'], r['index']): r for r in ledger['records']}
    spec, checks = validate_sources()
    for row in spec['records']:
        original = by_original[(row['original_family'], row['original_index'])]
        original.update(statutory_profile_record=row['id'], current_statutory_status='SOURCE_READING_AVAILABLE_APPLICATION_UNKNOWN',
                        complete_legal_interpretation=False)
    run.save(run.HERE / 'original-ledger-reconciliation.json.gz', ledger)
    return {'status': 'PASS', 'original_inventory_records': 60, 'statutory_records': 12,
            'complete_ordinary_answers_checked': len(LABELS), 'actual_consumer_refusals': len(CONTROLS),
            'actual_upstream_refusals': receipts['upstream']['actual_upstream_refusals'],
            'source_bindings_checked': len(checks), 'original_task_complete': False}


def seal():
    result = run.read(run.HERE / 'stages/reconcile/result.json')
    result = {**result, 'task': 'basf-references', 'result_kind': 'FINITE_STATUTORY_SOURCE_TO_ANSWER_INTEGRATION',
              'resources': run.costs(), 'remaining': ['Historical statutory editions and application constructions',
                  'Unqualified defined terms', 'Original acceptance and general discovery'],
              'next_action': 'Reviewed same-task continuation for original definition/discovery and historical/application remainder'}
    run.save(run.HERE / 'result.json', result)
    run.save(run.HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=run.ROOT, text=True).strip(),
        'commands': [run.read(run.HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(run.ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'data_version': run.sha(run.PRIOR / 'investigation.json'), 'random_seeds': 'N/A deterministic',
        'wall_time': result['resources'], 'plan': run.PLAN, 'result': run.rel(run.HERE / 'result.json'),
        'artifacts': run.rel(run.HERE), 'method_freeze': run.sha(run.PREP / 'freeze.json')})
    with (run.HERE / 'RESULT.md').open('x') as stream:
        stream.write('''# Twelve statutory readings now affect ordinary answers

The finite assisted profile preserves twelve separate original references and
their exact contract contexts, retained primary quotations and source identities.
It distinguishes available readings, unproved historical wording, open onward
scope and missing application premises. Q1/Q2 and every subquestion retain those
dependencies; Q4 remains conditional and its previous supplied-law result is
preserved separately. Sources do not become operative contract clauses.

Six complete ordinary answers were retained before independent comparison with
both021 comparators: absent inputs reproduce both originals, retained evidence
and unavailable-evidence variants preserve all unrelated answer content and P5.
Actual upstream refusals and validly resealed consumer forgeries are retained.
The sealed-source request transport was checked with extraction replaced by the
retained graph; it establishes no fresh native extraction or model execution.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite integration | Full products and ordinary answers independently reconstructed; actual adverse refusals | No integration promotion veto | Historical law, application rules, definitions and discovery | Continue original remainder | Entitlement, automatic discovery or whole-build completion |

The repair addresses our missing source-to-answer integration. It supplies no
evidence of a fundamental limitation of an external package. The strongest
alternative explanation is an error shared by the retained legal readings and
the finite profile. Contrary primary-source evidence would overturn that reading;
identity checks and successful uncertainty propagation cannot establish legal
application. The weakest evidence remains historical validity and open onward
law, explicitly UNKNOWN throughout. No external adviser opinion is required.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': result['resources']}


def dispatch(label):
    if label.startswith('verify-'):
        return verify_answer(label.removeprefix('verify-'))
    if label.startswith('control-'):
        return control(label.removeprefix('control-'))
    return {'preflight': preflight, 'tests': tests, 'upstream': upstream,
            'request-route': request_route, 'reconcile': reconcile, 'seal': seal}[label]()
