"""Record the verified finite stop and recovery prerequisites without dispatch."""
import sys
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, '/home/chakwong/python/legalmath')
from scripts.legal_integration_coverage import (
    ROOT, OUT, DOC, PLAN, DEADLINE, verify, tested, test_directory, review_path,
    checked_review, immutable, read, ref, check_ref)

checked = verify()
assert not checked['execution_complete']
assert checked['calls'] == 54 and checked['repairs'] == 20
assert checked['coverage']['assessed_pairs'] == 204
restart = read(OUT / 'restart-check/result.json')
assert restart['status'] == 'PASS' and restart['new_calls'] == 0
review = checked_review()
running = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        args = (p / 'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if any(a.endswith(b'/scripts/run_legal_integration_coverage.py') or
           a == b'scripts/run_legal_integration_coverage.py' for a in args):
        running.append(int(p.name))
assert not running, running
result = {**checked, 'status': 'STOPPED_REPAIR_LIMIT_WITH_INCOMPLETE_COVERAGE',
    'reason': 'The final second perspective assigned another candidate\'s executable meaning to an unformalized reading.',
    'latest_failure': ref(OUT / 'batches/combined/17/attempt-02/receipt.json'),
    'independent_trace': ref(OUT / 'final-rejection-trace.json'),
    'provider_calls_remaining': 46, 'repair_entries_remaining': 0,
    'provider_repair_allocation_remaining': 0, 'minimum_calls_to_finish_with_valid_perspective_reuse': 47,
    'new_authorization_required_for_live_repair': True,
    'new_authorization_inferred': False, 'runner_processes': running,
    'restart': ref(OUT / 'restart-check/result.json'),
    'next_step': 'Review candidate-specific bindings and reuse of the retained first perspective after an explicit new repair/call authorization; no generic retry.',
    'deadline_epoch_unchanged': DEADLINE}
immutable(OUT / 'stop-result.json', result)
immutable(OUT / 'continuation-decision.json', {
    'status': result['status'], 'phase': 'C2_STOPPED_C3_PARTIAL_REPORT_COMPLETE',
    'next_phase_plan': ref(OUT / 'next-phase-plan.json'),
    'stop_result': ref(OUT / 'stop-result.json'), 'remaining_pairs': 288,
    'pending_second_perspective_pairs': 12, 'undispatched_pairs': 276,
    'live_continuation_authorized': False,
    'prerequisites': ['explicit repair allowance', 'at least 47 remaining calls for the stated reuse design',
                      'reviewed candidate-binding remedy and perspective-reuse mechanism',
                      'fresh regression and retained-evidence checks',
                      'unchanged absolute deadline or explicit time extension if it has expired'],
    'legal_accuracy_established': False, 'legal_obligations_closed': 0})
reports = OUT / 'reporting-source'
reports.mkdir(exist_ok=True)
for filename in ('legal_coverage_result_report.py', 'legal_coverage_restart_check.py',
                 'legal_coverage_stop_trace.py', 'legal_coverage_close_record.py'):
    source = Path('/tmp') / filename
    target = reports / filename
    if target.exists():
        assert target.read_bytes() == source.read_bytes()
    else:
        shutil.copyfile(source, target)
initial = read(OUT / 'run-manifest.json')
summary = read(OUT / 'execution-summary.json')
manifest = {
    'status': result['status'],
    'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'initial_git_commit': initial['git_commit'], 'worktree_dirty': True,
    'environment': str(ROOT / '.venv/bin/python'),
    'CPU_GPU': 'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPU devices',
    'seed_policy': 'External provider seeds are not exposed or controlled; no statistical ranking.',
    'data_version': ref(OUT / 'inputs.json'), 'partition': ref(OUT / 'partition.json'),
    'plan': ref(PLAN), 'review': ref(review_path()), 'source_manifest': review['source_manifest'],
    'repair_reviews': [ref(p) for p in sorted(DOC.glob('repair-review-v*.md'))],
    'authorization': ref(OUT / 'authorization.json'), 'allowance': ref(OUT / 'allowance.json'),
    'repairs': ref(OUT / 'repairs.json'),
    'allocation_revision': ref(OUT / 'allocation-revision-v12.json'),
    'allocation_checkpoint': ref(OUT / 'allocation-checkpoint-v12.json'),
    'predecessor_independent_check': ref(OUT / 'independent-historical-check.json'),
    'tests': ref(test_directory() / 'result.json'), 'test_counts': tested()['counts'],
    'commands_executed': [
        '.venv/bin/python scripts/run_legal_integration_coverage.py execute',
        '.venv/bin/python scripts/run_legal_integration_coverage.py test',
        '.venv/bin/python scripts/run_legal_integration_coverage.py verify',
        '.venv/bin/python scripts/run_legal_integration_coverage.py repair',
        '.venv/bin/python /tmp/legal_coverage_restart_check.py',
        '.venv/bin/python /tmp/legal_coverage_result_report.py',
        '.venv/bin/python /tmp/legal_coverage_stop_trace.py',
        '.venv/bin/python /tmp/legal_coverage_close_record.py'],
    'wall_seconds_through_processing_report': summary['wall_seconds'],
    'result': ref(OUT / 'stop-result.json'), 'summary': ref(OUT / 'execution-summary.json'),
    'report': ref(DOC / 'execution-result.md'), 'pair_assessments': ref(OUT / 'pair-assessments.json'),
    'followups': ref(OUT / 'model-followups.json'),
    'additional_concerns': ref(OUT / 'model-additional-concerns.json'),
    'tool_inventory': ref(OUT / 'tool-check-inventory.json'),
    'transport_inventory': ref(OUT / 'transport-summary.json'),
    'restart': ref(OUT / 'restart-check/result.json'),
    'continuation_decision': ref(OUT / 'continuation-decision.json'),
    'reporting_source': [ref(p) for p in sorted(reports.glob('*.py'))],
    'report_generation_note': 'Generated from verified records, then reviewed and amended with the final rejection trace and recovery requirements.',
    'operator_docs': [ref(DOC / p) for p in ('README.md', 'operator.md', 'reset-memo.md', 'remaining-gaps.md')]}
immutable(OUT / 'completion-manifest.json', manifest)
print({'status': result['status'], 'calls': 54, 'repair_entries': 20,
       'pairs_complete': 204, 'tests_passed': tested()['counts']['tests'],
       'new_restart_calls': 0, 'runner_processes': running})
