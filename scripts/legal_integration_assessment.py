"""Finite assessment-state and evidence-binding repair; no budget extensions."""
import argparse
import fcntl
import json
import os
from pathlib import Path
from copy import deepcopy
import shutil
import subprocess
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from scripts.legal_gap_program import ROOT, OUT as PRIOR, read, save, ref, check_ref, ledger, repair, command
from scripts.legal_integration_repair import OUT as PREDECESSOR, budgets
from scripts.legal_gap_recovery import ProgramGrant

OUT = ROOT / 'artifacts/legal-integration-assessment/2026-10-08'
DOC = ROOT / 'docs/implementation/legal-integration-assessment'
PLAN = ROOT / 'docs/plans/legal-integration-assessment-program.md'
ACTIONS = ('assess-check', 'assess-execute', 'assess-status', 'assess-verify')
PREFIX = ['.venv/bin/python', 'scripts/run_legal_integration_repair.py']


def review_path():
    # This one explicit local successor preserves the initial failed suite and
    # original review. It grants no extra calls, repair batch or phase.
    if (DOC / 'final-audit.md').exists(): return DOC / 'review-final.json'
    if (DOC / 'verification-review.md').exists(): return DOC / 'review-verification.json'
    return DOC / ('review-local-validation.json' if (DOC / 'local-validation-review.md').exists() else 'review.json')


def selected_inputs():
    from scripts.legal_gap_recovery import retained_inputs, select_pairs
    inputs = retained_inputs('baseline')
    pairs = select_pairs(inputs)
    unavailable = sorted(cid for cid, r in inputs['candidates'].items()
                         if r['formalization'] is None and inputs['questions'][cid]['result_kind'] == 'DUTY_TRIGGER')
    if unavailable:
        pairs += [(claim, unavailable[0]) for claim, _ in pairs.copy()]
    return inputs, pairs, {'unformalized_trigger_candidate': unavailable[0] if unavailable else None,
        'selection': 'First stable-ID retained request-trigger candidate and two retained duty claims; optional first retained unformalized DUTY_TRIGGER reading.',
        'missing_prerequisite': None if unavailable else 'No retained unformalized reading has a DUTY_TRIGGER question. Live unavailable assessment is untested; retain the original two pairs.'}


def input_inventory():
    from legalmath.canonical import digest
    from legalmath.interpretation.assurance.semantics import representation
    from legalmath.interpretation.assurance.scoped_investigation import capacity
    inputs, pairs, selection = selected_inputs()
    rows = [{'claim_id': c['claim_id'], 'claim_relevance': c['relevance'], 'candidate_id': cid, 'reading_hash': digest(r),
             'question_hash': digest(inputs['questions'][cid]),
             'executable_available': not representation(r).startswith('UNAVAILABLE_EXECUTABLE_MEANING:'),
             'assessed_by_this_inventory': False}
            for c in inputs['claims'] for cid, r in inputs['candidates'].items()]
    gaps = read(PRIOR / 'G4/attempt-1/gap-tool-matrix.json')
    readings = read(PRIOR / 'G4/attempt-1/reading-coverage.json')
    broad_pairs = sum(r['claim_relevance'] != 'CONTEXT' for r in rows)
    if len(rows) != 492 or broad_pairs != 420 or len(gaps) != 46 or len(readings) != 35:
        raise ValueError('Original source/reading denominator changed')
    value = {'retained_input_refs': inputs['references'], 'pairs': rows, 'selected_pairs': pairs,
             'selection': selection, 'full_pair_denominator': len(rows), 'broad_pair_denominator': broad_pairs,
             'context_pair_denominator': len(rows) - broad_pairs,
             'unavailable_executable_pairs': sum(not r['executable_available'] for r in rows),
             'minimum_full_scoped_capacity': capacity(len(rows), 12, 200),
             'original_obligations': gaps, 'original_readings': readings,
             'tool_dispositions': read(ROOT / 'docs/implementation/legal-tool-gap-validation/benchmark.json')['not_selected'],
             'legal_gaps_closed': 0}
    path = OUT / 'input-inventory.json'
    if path.exists() and read(path) != json.loads(json.dumps(value)):
        raise ValueError('Retained inventory changed; preserve the prior inventory before any successor')
    save(path, value)
    return value


def baseline():
    path = OUT / 'baseline.json'
    if path.exists():
        value = read(path)
        for row in value['copies']:
            check_ref(row['copy'])
        return value
    from scripts.legal_integration_repair import verify as verify_predecessor
    checked = verify_predecessor()
    paths = [p for base in ('src/legalmath', 'scripts', 'tests/assurance', 'tests/tooling')
             for p in (ROOT / base).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.json', '.java', '.lean', '.sql')]
    paths += [PLAN, ROOT / 'docs/plans/legal-integration-repair-program.md']
    paths += [p for p in (ROOT / 'docs/implementation/legal-integration-repair').rglob('*') if p.is_file()]
    copies = []
    for p in sorted(set(paths)):
        target = OUT / 'baseline' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        copies.append({'live': ref(p), 'copy': ref(target)})
    mutable = {PRIOR / name for name in ('provider-allowance.json', 'repairs.json', 'provider.lock')}
    receipts = [ref(p) for base in (PRIOR, PREDECESSOR) for p in sorted(base.rglob('*'))
                if p.is_file() and p not in mutable and p.name != '.lock'
                and not p.name.endswith(('-wal', '-shm'))]
    for name in ('provider-allowance.json', 'repairs.json'):
        save(OUT / 'baseline' / name, read(PRIOR / name))
    value = {'captured_at': time.time(), 'predecessor_verification': checked,
             'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
             'copies': copies, 'predecessor_evidence': receipts, 'budgets': budgets()}
    save(path, value)
    return value


def check():
    value = baseline()
    inventory = input_inventory()
    from legalmath.interpretation.assurance.integrated import implementation_identity
    from scripts.legal_gap_live import Provider
    from scripts.legal_integration_tools import ProductToolBackend
    reviewed = {'status': 'PASS_BOUNDED_ASSESSMENT_REPAIR', 'plan': ref(PLAN),
                'review': ref(DOC / 'review.md'), 'implementation': implementation_identity(),
                'files': [ref(ROOT / p) for p in REVIEWED_FILES],
                'route': Provider().routing, 'backend': ProductToolBackend().identity(),
                'maximum_new_live_calls': 5, 'arm_calls': {'baseline': 3, 'combined': 2},
                'maximum_new_repairs': 1, 'original_pair_denominator': 492, 'broad_pair_denominator': 420,
                'input_inventory': ref(OUT / 'input-inventory.json')}
    path = review_path()
    if path.name != 'review.json':
        reviewed['predecessor_review'] = ref(DOC / 'review.json')
        reviewed['local_validation_review'] = ref(DOC / 'local-validation-review.md')
        reviewed['preserved_reviewed_source'] = ref(OUT / 'local-validation-baseline.json')
    if path.name in ('review-verification.json', 'review-final.json'):
        reviewed['verification_review'] = ref(DOC / 'verification-review.md')
        reviewed['predecessor_validation_review'] = ref(DOC / 'review-local-validation.json')
        reviewed['preserved_verification_source'] = ref(OUT / 'verification-baseline.json')
    if path.name == 'review-final.json':
        reviewed['final_audit'] = ref(DOC / 'final-audit.md')
        reviewed['predecessor_verification_review'] = ref(DOC / 'review-verification.json')
        reviewed['verification_order_baseline'] = ref(OUT / 'verification-order-baseline.json')
    if path.exists() and read(path) != reviewed:
        raise ValueError('Sealed review changed; preserve the old review and audit a successor explicitly')
    save(path, reviewed)
    return {'status': 'BASELINE_PRESERVED', 'files': len(value['copies']),
            'predecessor_files': len(value['predecessor_evidence']), 'budgets': budgets(),
            'review': ref(path), 'selection': inventory['selection']}


def status():
    return {'state': read(OUT / 'state.json') if (OUT / 'state.json').exists() else 'PREPARED',
            'budgets': budgets()}


def checked_review():
    from legalmath.interpretation.assurance.integrated import implementation_identity
    from scripts.legal_gap_live import Provider
    from scripts.legal_integration_tools import ProductToolBackend
    reviewed = read(review_path())
    for row in [reviewed['plan'], reviewed['review'], reviewed['input_inventory'], *reviewed['files']]:
        check_ref(row)
    if 'predecessor_review' in reviewed:
        for key in ('predecessor_review', 'local_validation_review', 'preserved_reviewed_source'):
            check_ref(reviewed[key])
        for row in read(check_ref(reviewed['preserved_reviewed_source']))['copies']:
            check_ref(row['copy'])
    if 'verification_review' in reviewed:
        for key in ('verification_review', 'predecessor_validation_review', 'preserved_verification_source'):
            check_ref(reviewed[key])
        for row in read(check_ref(reviewed['preserved_verification_source']))['copies']:
            check_ref(row['copy'])
    if 'final_audit' in reviewed:
        for key in ('final_audit', 'predecessor_verification_review', 'verification_order_baseline'):
            check_ref(reviewed[key])
        check_ref(read(check_ref(reviewed['verification_order_baseline']))['source'])
    if (reviewed['implementation'] != implementation_identity() or reviewed['route'] != Provider().routing
            or reviewed['backend'] != ProductToolBackend().identity()):
        raise ValueError('Reviewed implementation, provider or installed tool identity changed')
    return reviewed


class AssessmentGrant(ProgramGrant):
    """Apply the five-call sublimit before the original nonrefundable reservation."""
    def reserve(self, request_hash):
        initial = read(OUT / 'baseline.json')['budgets']
        current = budgets()
        if (current['used'] - initial['used'] >= 5
                or current['arm_used'][self.counter.arm.removeprefix('product.')] -
                   initial['arm_used'][self.counter.arm.removeprefix('product.')] >=
                   {'product.baseline': 3, 'product.combined': 2}[self.counter.arm]):
            raise RuntimeError('Assessment program sublimit exhausted; no reset or new namespace')
        return super().reserve(request_hash)


def regression():
    import xml.etree.ElementTree as ET
    folder = OUT / 'A1'
    receipt = command([ROOT / '.venv/bin/python', '-m', 'pytest', *TESTS, '-q', '--disable-warnings',
                       '--junitxml', folder / 'tests.xml'], folder, 'regression', timeout=600)
    suites = ET.parse(folder / 'tests.xml').getroot().findall('testsuite')
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'errors', 'failures', 'skipped')}
    return {'engineering_pass': not counts['errors'] and not counts['failures'], 'counts': counts,
            'execution': receipt, 'evidence': ref(folder / 'tests.xml')}


def mixed_responder(request):
    from tests.assurance.test_successor_workflow import complete_responder
    value = complete_responder(request)
    if request['task'] == 'GENERATE':
        unencoded = deepcopy(value['readings'][0])
        unencoded['local_id'] = 'unencoded.gift'
        unencoded['formalization'] = None
        unencoded['distinction'] = 'Retained source reading without an executable model.'
        unencoded['questions'] = ['What formalization represents the gift exception?']
        value['readings'].append(unencoded)
    elif request['task'] == 'SCOPED_SOURCE_FIDELITY':
        candidates = {r['candidate_id']: r for r in request['candidates']}
        for row in value['checks']:
            if candidates[row['candidate_id']]['representation'].startswith('UNAVAILABLE_EXECUTABLE_MEANING:'):
                row['executable_correspondence'].update(status='UNAVAILABLE', representation_quotes=[],
                    rationale='The controlled reading is retained without executable code.')
                row['followup_questions'] = ['What formalization represents this retained reading?']
    return value


def historical_verification():
    """Resolve old source references within a preserved root, never reseal them."""
    from legalmath.interpretation.assurance.complete_investigation import verify as verify_dossier
    folder = OUT / 'historical-root'
    dossier_path = PREDECESSOR / 'R2/revision-2/dossier.json'
    receipt = OUT / 'historical-verification.json'
    if receipt.exists():
        retained = read(receipt)
        for row in retained['copies']: check_ref(row['copy'])
        result = verify_dossier(folder, read(folder / dossier_path.relative_to(ROOT)))
        # The replay verifier iterates a set of required methods. Only this
        # reason-list order is nonsemantic; preserve every reason verbatim.
        def normalized(value):
            value = deepcopy(value)
            if value.get('replay'):
                value['replay']['blocking_reasons'].sort(key=lambda r: json.dumps(r, sort_keys=True))
            return value
        if normalized(result) != normalized(retained['result']):
            raise ValueError('Historical verification result changed')
        return retained
    sources = [(check_ref(r['copy']), r['live']) for r in read(OUT / 'baseline.json')['copies']
               if r['live']['path'].startswith('src/legalmath/')]
    sources += [(p, ref(p)) for p in sorted((PREDECESSOR / 'R2/revision-2').rglob('*'))
                if p.is_file() and p.name != '.lock' and not p.name.endswith(('-wal', '-shm'))]
    old = read(dossier_path); replay = read(check_ref(old['replay']['dossier']))
    known = {row['path'] for _, row in sources}
    sources += [(check_ref(r), r) for r in replay['upstream_inputs'] if r['path'] not in known]
    copies = []
    for source, original in sources:
        target = folder / original['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if ref(target)['sha256'] != original['sha256']: raise ValueError('Historical snapshot changed')
        else: shutil.copyfile(source, target)
        copies.append({'original': original, 'copy': ref(target)})
    result = verify_dossier(folder, read(folder / dossier_path.relative_to(ROOT)))
    retained = {'result': result, 'copies': copies,
                'meaning': 'Current verifier checks frozen historical files; no remote execution or legal correctness attestation.'}
    save(receipt, retained)
    return retained


def offline():
    from legalmath.canonical import digest
    from legalmath.errors import LegalMathError
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify as verify_dossier
    from legalmath.interpretation.assurance.optional_tools import ToolSession
    from scripts.legal_integration_tools import ProductToolBackend
    from tests.search.support import FunctionProvider
    from tests.assurance.test_integration import source, settings
    from tests.assurance.test_round16 import JDK, AT
    folder = OUT / 'A2'; folder.mkdir(parents=True, exist_ok=True)
    backend = ProductToolBackend(); provider = FunctionProvider(mixed_responder)
    runner = CompleteInvestigation(ROOT, folder / 'controlled-product', provider, JDK, AT,
        settings=settings(), maximum_scoped_actions=12, scoped_rounds=1, optional_tool_backend=backend)
    dossier = runner.run([source()], 'Selected gift control')
    save(folder / 'dossier.json', dossier)
    if provider.requests:
        save(folder / 'provider-requests.json', provider.requests)
    checked = verify_dossier(ROOT, dossier)
    candidates = read(check_ref(dossier['candidates']))
    coverage = dossier['scoped']['assessment_coverage']
    if (not checked['execution_complete'] or not coverage['unavailable_pairs']
            or not coverage['executable_compared_pairs'] or len(candidates) != 2
            or dossier['legal_correctness_established'] or dossier['release_eligible']):
        raise ValueError('Mixed controlled workflow did not retain both completed assessment and unresolved meaning')
    restarted_provider = FunctionProvider(lambda r: (_ for _ in ()).throw(AssertionError('Completed product redispatched')))
    restarted = CompleteInvestigation(ROOT, folder / 'controlled-product', restarted_provider, JDK, AT,
        settings=settings(), maximum_scoped_actions=12, scoped_rounds=1, optional_tool_backend=backend)
    if restarted.run([source()], 'Selected gift control') != dossier or restarted_provider.requests:
        raise ValueError('Mixed product failed exact restart')
    # A self-consistent changed outer binding must still be rejected by the
    # independently retained backend journal, not merely by a digest mismatch.
    forged = deepcopy(dossier)
    forged['binding']['optional_tools'] = {'different_backend': True}
    forged['revision'] = digest(forged['binding'])
    try: verify_dossier(ROOT, forged)
    except LegalMathError as exc:
        if exc.code != 'E_INTEGRITY' or 'Optional backend differs' not in str(exc.details): raise
    else: raise ValueError('Dossier accepted the wrong optional backend')
    historical_checked = historical_verification()['result']
    inputs, pairs, selection = selected_inputs()
    tools = ToolSession(backend, folder / 'retained-product-tools')
    retained = tools.candidates(inputs['packet'], inputs['candidates'])
    save(folder / 'retained-tools.json', tools.report())
    retained_requests = read(folder / 'provider-requests.json')
    context_kinds = {task: sorted({c['kind'] for r in retained_requests if r['task'] == task
                                  for c in r.get('external_tool_context', {}).get('checks', [])})
                     for task in ('SOURCE_FIDELITY', 'DEFINE_EXACT_QUESTIONS', 'SCOPED_SOURCE_FIDELITY')}
    if ('candidates' not in context_kinds['SOURCE_FIDELITY']
            or 'criticism' not in context_kinds['DEFINE_EXACT_QUESTIONS']
            or 'candidates' not in context_kinds['SCOPED_SOURCE_FIDELITY']):
        raise ValueError('Optional evidence did not reach product requests')
    return {'engineering_pass': True, 'controlled_product': ref(folder / 'dossier.json'),
            'controlled_provider_actions': len(retained_requests), 'restarted_provider_actions': 0,
            'coverage': coverage, 'context_kinds': context_kinds, 'retained_tools': retained,
            'wrong_backend_rejected': True, 'historical_v1_verification': historical_checked,
            'selected_pairs': pairs, 'selection': selection, 'full_pair_denominator': 492,
            'legal_gaps_closed': 0, 'full_live_completion': False,
            'limit': 'Scripted proposals test orchestration; actual installed engines test conditional computation only.'}


def sentinel(folder):
    from jsonschema import validate
    from scripts.legal_gap_live import Provider
    from legalmath.interpretation.search.models import Settings
    final = folder / 'result.json'
    if final.exists(): return read(final)
    if (folder / 'started.json').exists():
        return {'status': 'INTERRUPTED_REQUIRES_REVIEW', 'pass': False}
    if budgets()['remaining_seconds'] < 190:
        return {'status': 'UNTESTED_WINDOW', 'pass': False}
    request = {'task': 'Return status ready in the requested JSON. Do not use tools.'}
    schema = {'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['ready']}},
              'required': ['status'], 'additionalProperties': False}
    save(folder / 'request.json', request); save(folder / 'schema.json', schema)
    before = len(ledger()['calls'])
    save(folder / 'started.json', {'before': budgets(), 'maximum_new_calls': 1})
    try:
        completion = Provider(allowance=AssessmentGrant('baseline')).complete(request, schema,
            Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000))
        save(folder / 'response.json', completion.value); save(folder / 'provenance.json', completion.provenance)
        validate(completion.value, schema)
        row = {'status': 'PASS', 'pass': True, 'response': ref(folder / 'response.json'),
               'provenance': ref(folder / 'provenance.json')}
    except Exception as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'error': str(exc),
             'code': getattr(exc, 'code', None), 'details': str(getattr(exc, 'details', ''))[:3000]})
        row = {'status': 'FAILED', 'pass': False, 'failure': ref(folder / 'failure.json')}
    row['new_provider_reservations'] = len(ledger()['calls']) - before
    save(final, row)
    return row


def live():
    from scripts.legal_gap_live import Provider
    from scripts.legal_integration_tools import ProductToolBackend
    from legalmath.interpretation.assurance.optional_tools import ToolSession
    from legalmath.interpretation.assurance import scoped_investigation
    from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
    from legalmath.interpretation.search.models import Settings
    folder = OUT / 'A3'
    print('SERVICE SENTINEL', flush=True)
    service = sentinel(folder / 'sentinel')
    if not service['pass']:
        return {'sentinel': service, 'arms': {}, 'live_status': 'DEPENDENT_DISPATCH_VETOED',
                'full_pair_denominator': 492, 'legal_gaps_closed': 0, 'full_live_completion': False}
    inputs, pairs, selection = selected_inputs(); arms = {}
    for arm in ('baseline', 'combined'):
        target = folder / arm; final = target / 'result.json'
        if final.exists(): arms[arm] = read(final); continue
        if (target / 'started.json').exists():
            arms[arm] = {'status': 'INTERRUPTED_REQUIRES_REVIEW'}; continue
        current = budgets()
        if (current['remaining_seconds'] < 400 or current['maximum'] - current['used'] < 2
                or current['arm_maximum'] - current['arm_used'][arm] < 2):
            arms[arm] = {'status': 'UNTESTED_BUDGET_OR_WINDOW'}; continue
        checked_review()
        save(target / 'started.json', {'before': current, 'maximum_new_calls': 2,
                                      'selected_pairs': pairs, 'full_pair_denominator': 492})
        tools = ToolSession(ProductToolBackend(), target / 'tools') if arm == 'combined' else None
        before = len(ledger()['calls'])
        print('SCOPED ' + arm, flush=True)
        result = scoped_investigation.investigate(inputs['packet'], inputs['claims'], inputs['candidates'],
            inputs['questions'], Provider(allowance=AssessmentGrant(arm)), target / 'scoped',
            required_pairs=pairs, batch_size=len(pairs), maximum_rounds=1, maximum_actions=2,
            deadline_seconds=400, settings=Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000),
            schedule='round-first', reference_protocol=PROTOCOL, input_profile='readable-tables.v1',
            optional_tools=tools, stop_on_rejection=True)
        row = {'status': 'ASSESSED' if scoped_investigation.execution_complete(result) else 'INCOMPLETE',
               'result': ref(target / 'scoped/result.json'), 'coverage': result['assessment_coverage'],
               'new_provider_reservations': len(ledger()['calls']) - before,
               'internal_matched_reservations': result['live_calls'], 'tools': tools.report() if tools else None,
               'selected_pairs': pairs, 'full_pair_denominator': 492, 'legal_gaps_closed': 0}
        save(final, row); arms[arm] = row
    return {'sentinel': service, 'arms': arms, 'selection': selection, 'live_status': 'BOUNDED_DIAGNOSTIC_FINISHED',
            'full_pair_denominator': 492, 'legal_gaps_closed': 0, 'full_live_completion': False,
            'ranking': 'Unsupported: tiny development diagnostic, same-model perspectives, no independent labels or uncertainty estimate.'}


def refresh(phase, state):
    value = {'phase': phase, 'completed': state['phases'], 'budgets': budgets(), 'plan': ref(PLAN),
             'question': {'A1': 'Do reviewed limitations and evidence bindings pass adversarial and regression tests?',
                         'A2': 'Does the mixed complete workflow retain unavailable readings and reach actual tools?',
                         'A3': 'Does the unchanged service route respond, then validate the retained scope in both arms?',
                         'COMPLETE': 'What evidence is still missing for legal closure and full live completion?'}[phase],
             'full_pair_denominator': 492, 'open_legal_obligations': 46,
             'continuation_veto': 'Corrupted evidence, stale reviewed method, exhausted original budget/window, or failed service sentinel for dependent live work.'}
    save(OUT / 'phase-plans' / (phase + '.json'), value)
    save(OUT / 'next-phase.json', value)


def execute():
    checked_review(); baseline()
    path = OUT / 'state.json'
    state = read(path) if path.exists() else {'status': 'EXECUTING', 'phases': {},
        'review': ref(review_path()), 'started': time.time(), 'initial_budgets': budgets()}
    check_ref(state['review'])
    state['current_review'] = ref(review_path())
    if state['status'] == 'EXECUTED_WITH_OPEN_LEGAL_GAPS':
        verify()
        return state
    # Reconcile an interruption after a repair entry without consuming a second entry.
    matches = [i for i, row in enumerate(read(PRIOR / 'repairs.json')['repairs'])
               if row['evidence'] == state['review']]
    if not matches:
        repair('Reviewed assessment completion and exact candidate/backend evidence repair; finite five-call diagnostic', state['review'])
        matches = [len(read(PRIOR / 'repairs.json')['repairs']) - 1]
    if len(matches) != 1: raise ValueError('Repair batch is not unique')
    state['repair_entry'] = matches[0] + 1
    save(path, state)
    for phase, run in (('A1', regression), ('A2', offline), ('A3', live)):
        if phase in state['phases']: check_ref(state['phases'][phase]); continue
        refresh(phase, state); checked_review()
        print('EXECUTING ' + phase, flush=True)
        target = OUT / phase
        if (target / 'result.json').exists():
            result = read(target / 'result.json')
        else:
            if (target / 'started.json').exists():
                raise RuntimeError('Interrupted phase requires review of retained evidence before continuation: ' + phase)
            save(target / 'started.json', {'at': time.time(), 'review': state['review'], 'budgets': budgets()})
            result = run()
            save(target / 'result.json', result)
        state['phases'][phase] = ref(OUT / phase / 'result.json')
        save(path, state)
        if result.get('engineering_pass') is False:
            state['status'] = 'LOCAL_REPAIR_REQUIRED'; save(path, state); return state
    state['status'] = 'EXECUTED_WITH_OPEN_LEGAL_GAPS'
    state['finished'] = time.time(); state['final_budgets'] = budgets()
    save(path, state)
    save(OUT / 'evidence-manifest.json', {'files': [ref(p) for name in ('A1', 'A2', 'A3', 'phase-plans')
        for p in sorted((OUT / name).rglob('*')) if p.is_file() and p.name != '.lock'
        and not p.name.endswith(('-wal', '-shm'))]})
    refresh('COMPLETE', state)
    state['verification'] = verify(); save(path, state)
    return state


def verify():
    from legalmath.interpretation.assurance.complete_investigation import verify as verify_dossier
    from legalmath.interpretation.assurance import fidelity_v2, scoped_investigation
    reviewed = checked_review(); initial = read(OUT / 'baseline.json')
    for row in initial['copies']: check_ref(row['copy'])
    for row in initial['predecessor_evidence']: check_ref(row)
    for name, field in (('provider-allowance.json', 'calls'), ('repairs.json', 'repairs')):
        old = read(OUT / 'baseline' / name); new = read(PRIOR / name)
        if old['maximum'] != new['maximum'] or new[field][:len(old[field])] != old[field]:
            raise ValueError('Prior allowance history or ceiling changed')
    manifest = OUT / 'evidence-manifest.json'
    if manifest.exists():
        for row in read(manifest)['files']: check_ref(row)
    current = budgets(); delta = current['used'] - initial['budgets']['used']
    if (not 0 <= delta <= reviewed['maximum_new_live_calls']
            or current['repairs_used'] - initial['budgets']['repairs_used'] > 1
            or any(current['arm_used'][a] - initial['budgets']['arm_used'][a] > n
                   for a, n in reviewed['arm_calls'].items())):
        raise ValueError('Reviewed sublimit exceeded')
    state = read(OUT / 'state.json') if (OUT / 'state.json').exists() else {'phases': {}}
    for row in state['phases'].values(): check_ref(row)
    if 'A2' in state['phases']:
        local = read(check_ref(state['phases']['A2']))
        verify_dossier(ROOT, read(check_ref(local['controlled_product'])))
    historical_verification()
    if 'A3' in state['phases']:
        inputs, pairs, _ = selected_inputs()
        for arm, row in read(check_ref(state['phases']['A3']))['arms'].items():
            if 'result' not in row: continue
            result = read(check_ref(row['result']))
            if set(map(tuple, result['required_pairs'])) != set(pairs) or row['full_pair_denominator'] != 492:
                raise ValueError('Live diagnostic scope changed')
            for batch in result['batches']:
                for proposal in batch['proposals']:
                    fidelity_v2.validate(proposal, inputs['packet'], inputs['claims'], inputs['candidates'],
                                         inputs['questions'], batch['required_pairs'])
            if ((row['status'] == 'ASSESSED') != scoped_investigation.execution_complete(result)
                    or row['coverage'] != scoped_investigation.assessment_coverage(result['batches'])):
                raise ValueError('Live result falsely reports assessed coverage')
    return {'status': 'SOURCE_AND_HISTORICAL_EVIDENCE_VERIFIED', 'new_provider_reservations': delta,
            'phases': list(state['phases']), 'original_pairs': 492, 'legal_gaps_closed': 0,
            'baseline_copies': len(initial['copies']), 'predecessor_files': len(initial['predecessor_evidence']),
            'predecessor_live_source_review': 'STALE_AS_EXPECTED; frozen historical files verified', 'budgets': current}


from scripts.legal_integration_repair import TESTS as PRIOR_TESTS
TESTS = [*PRIOR_TESTS, 'tests/assurance/test_integration_assessment.py', 'tests/assurance/test_round16.py',
         'tests/assurance/test_executable_references.py', 'tests/assurance/test_successor_transport.py']
REVIEWED_FILES = ['scripts/run_legal_integration_repair.py', 'scripts/legal_integration_assessment.py',
                  'scripts/legal_integration_repair.py', 'scripts/legal_integration_tools.py',
                  'scripts/legal_gap_recovery.py', 'scripts/legal_gap_live.py', 'scripts/legal_gap_program.py',
                  *TESTS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.action == 'assess-status':
        result = status()
    else:
        with (OUT / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = globals()[args.action.removeprefix('assess-')]()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
