"""Bounded live development investigations; no hidden expected rule reaches models."""
from argparse import ArgumentParser
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from legalmath.canonical import raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import Allowance, CodexProvider
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.assurance.engine import AssuranceSettings
from legalmath.interpretation.assurance.integrated import IntegratedInvestigation
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.transport import transient_service_failure


def run(out):
    contract = json.loads((ROOT/'docs/implementation/interpretation-round12/case-contract.json').read_text())
    auth = json.loads((ROOT/'docs/implementation/interpretation-round12/authorization.json').read_text())
    ledger = ROOT/auth['allowance_path']; rows = []
    start = len(json.loads(ledger.read_text())['calls'])
    harness_failures = []
    # Complete the nearly finished margin case first, then the eIP repair and
    # new STR transfer case before the longer gifts inventory. This declared
    # adaptive order is resource scheduling, not a fair method comparison.
    priority = {'25ec71': 0, '24ec50': 1, '26ec2': 2, '23ec46': 3}
    for case in sorted(contract['cases'], key=lambda c: priority[c['case_id']]):
        raw = (ROOT/case['source']).read_bytes()
        if raw_digest(raw) != case['source_sha256']: raise ValueError('Frozen source changed')
        current = len(json.loads(ledger.read_text())['calls'])
        job = ROOT/'artifacts/interpretation/round12/live-cases'/case['case_id']
        cache = job/'model-evidence/journal.json'
        consumed = len(json.loads(cache.read_text())['value']['actions']) if cache.exists() else 0
        available = max(0, min(case['call_cap']-consumed, auth['ceiling']-current))
        if available < 12 and not cache.exists():
            rows.append({'case_id': case['case_id'], 'status': 'ALLOWANCE_RETAINED_AS_INCOMPLETE',
                         'reason': 'Insufficient reserved capacity for the required workflow'})
            continue
        provider = CodexProvider(allowance=Allowance(ledger, 500, reservation_ceiling=current+available))
        settings = AssuranceSettings(investigate_abstractions=True, total_model_calls=case['call_cap'],
            deadline_seconds=7200,
            semantic_repair_rounds=1, semantic_repairs_per_issue=2, max_derived_comparisons=0,
            max_context_passes=1, max_reference_depth=0, run_formula_challenges=True,
            inventory_piece_characters=4000 if case['case_id'] in ('23ec46', '26ec2') else 0,
            inventory_piece_units=16,
            max_fidelity_pairs_per_call=16 if case['case_id'] == '25ec71' else 8,
            search=Settings(max_model_calls=5, max_rounds=2, scheduler='bfs', max_candidates=18,
                            reconstruction_required=False, timeout_seconds=300,
                            max_input_bytes=200000, max_output_bytes=200000))
        root = {'url': case['url'], 'data': raw, 'media_type': 'application/json'}
        # The source-only generator receives no reference cases or expected RuleIR.
        print('Investigating '+case['case_id']+' with at most '+str(available)+' new calls', flush=True)
        try:
            workflow = IntegratedInvestigation(job, provider,
                ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1', contract['at'], settings=settings,
                deadline_seconds=14400)
            workflow_passes = []
            for attempt in range(2):
                before = workflow.cache.journal.report()['consumed_actions']
                result = workflow.run([root], case['selected_slice'])
                after = workflow.cache.journal.report()['consumed_actions']
                workflow_passes.append({'attempt': attempt + 1, 'execution_complete': result['execution_complete'],
                                        'new_model_actions': after - before})
                # A semantic disagreement is retained. Retry an incomplete
                # execution only when the new pass made progress and still has
                # capacity; exact returned responses remain reusable evidence.
                if result['execution_complete'] or after == before or after >= case['call_cap']:
                    break
            save(job/'workflow-passes.json', workflow_passes)
            # Snapshot the durable job: later repairs may append evidence to it,
            # while this phase attempt remains immutable and independently readable.
            shutil.copytree(job, out/case['case_id'])
            row = {'case_id': case['case_id'], 'status': result['status'],
                   'execution_complete': result['execution_complete'],
                   'candidates': len(result['interpretation']['report'].get('candidate_ids', [])),
                   'binaries': len(result['independent']['binaries']),
                   'findings': len(result['residual_questions']),
                   'new_calls': len(json.loads(ledger.read_text())['calls'])-current,
                   'consumed_case_actions': result['model_actions'],
                   'workflow_passes': workflow_passes,
                   'report': str(out/case['case_id']/'report.json'), 'release_eligible': False}
        except Exception as exc:
            # A malformed or corrupted harness cannot become an ordinary live
            # abstention. Only bounded provider/resource failures permit the
            # independent regression phase to continue with an incomplete mark.
            if not (isinstance(exc, LegalMathError) and
                    (exc.code == 'E_RESOURCE_LIMIT' or transient_service_failure(exc))):
                harness_failures.append({'case_id': case['case_id'], 'error': repr(exc)})
            if job.exists() and not (out/case['case_id']).exists():
                shutil.copytree(job, out/case['case_id'])
            row = {'case_id': case['case_id'], 'status': 'FAILED_RETAINED',
                   'error': getattr(exc, 'code', type(exc).__name__), 'details': str(getattr(exc, 'details', None) or exc),
                   'new_calls': len(json.loads(ledger.read_text())['calls'])-current}
        rows.append(row); save(out/'progress.json', rows)
        if harness_failures:
            break
    result = {'engineering_status': 'PASS' if all(r.get('execution_complete') for r in rows) else 'INCOMPLETE',
              'cases': rows, 'new_calls': len(json.loads(ledger.read_text())['calls'])-start,
              'ledger': str(ledger), 'ceiling': auth['ceiling'], 'development_sources': True,
              'heldout_legal_accuracy_evaluated': False, 'release_eligible': False,
              'harness_failures': harness_failures,
              'not_started_case_ids': [c['case_id'] for c in contract['cases']
                                       if c['case_id'] not in {r['case_id'] for r in rows}],
              'continuation_status': 'HARNESS_REPAIR_REQUIRED' if harness_failures else 'INDEPENDENT_CHECKS_MAY_CONTINUE',
              'reference_basis': contract['reference_basis']}
    save(out/'result.json', result)
    if harness_failures:
        raise RuntimeError('Live harness failed; inspect retained exceptions')
    return result


if __name__ == '__main__':
    parser = ArgumentParser(__doc__); parser.add_argument('--out', required=True); args = parser.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    result = run(out); print(json.dumps(result))
    if result['engineering_status'] != 'PASS':
        sys.exit(2)  # Explicit incomplete evidence, never success or hidden skip.
