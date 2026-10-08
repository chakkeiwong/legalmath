"""Seal verified continuation results and record final recovery state."""
import sys
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, '/home/chakwong/python/legalmath')
from scripts import legal_coverage_resume as r

summary = r.read(r.OUT / 'execution-summary.json')
verified = r.verify()
assert summary['execution_complete'] == verified['execution_complete']
assert summary['new_calls'] == verified['new_calls']
assert summary['new_repairs'] == verified['new_repairs']
assert r.read(r.OUT / 'restart-check/result.json')['new_calls'] == 0
running = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try: args = (p / 'cmdline').read_bytes().split(b'\0')
    except (PermissionError, FileNotFoundError, ProcessLookupError): continue
    if any(a == b'scripts/run_legal_integration_coverage.py' or
           a.endswith(b'/scripts/run_legal_integration_coverage.py') for a in args): running.append(p.name)
assert not running, running
r.immutable(r.OUT / 'verification.json', verified)
doc = r.ROOT / 'docs/implementation/legal-integration-coverage/resumption'
state = 'COMPLETE' if verified['execution_complete'] else 'STOPPED_INCOMPLETE'
(doc / 'README.md').write_text(f'''# Legal integration coverage continuation

Current state: **{state}**, with **{verified['coverage']['assessed_pairs']}/492**
original claim–candidate pairs assessed in both perspectives. Read
[the execution result](execution-result.md) for findings, actual tool use and
remaining legal gaps, and [the reset memo](reset-memo.md) for recovery details.

The governing program is `docs/plans/legal-integration-coverage-resumption.md`.
It extends the original finite coverage program under the user's additional
200-call and 100-repair grant. Actual use is {verified['new_calls']} calls and
{verified['new_repairs']} repair entries. Previous grants and their evidence are
preserved; the original expiry was never extended. Current tests passed
{summary['tests']['tests']}; the completed restart verification used zero calls.

The candidate-binding repair prevents foreign executable selections and
unsupported comparisons for unformalized readings. A separately reviewed
recovery handled a returned HTTP 502 while retaining the identical request,
original tool context and valid peer. Every attempt remains recorded.
The later batch 36 timeout has its own reviewed, request-bound 450-second
successor; ordinary calls remain capped at 300 seconds. Review v3's settings
mismatch failed preflight before live dispatch and was corrected in review v4.

Artifacts are in
`artifacts/legal-integration-coverage/2026-10-08/additional-200-calls-100-repairs/`.
Use `.venv/bin/python scripts/run_legal_integration_coverage.py resume-verify`
for local verification. No runner is active. Completed execution is reusable
without a new provider call; failed or uncertain attempts need exact review.

All **46 original legal obligations remain open**. Completed scoped processing
does not establish general English or case-law correctness, supply client facts
or governing standards, or establish release readiness. The complete original
register remains in
`docs/implementation/legal-integration-assessment/remaining-gaps.md`.
''')
(doc / 'reset-memo.md').write_text(f'''# Legal integration continuation: {state}

No runner is active. The combined original matrix has
{verified['coverage']['assessed_pairs']}/492 pairs assessed in both perspectives.
This explicit additional grant consumed {verified['new_calls']}/200 calls and
{verified['new_repairs']}/100 repair entries. Previous ledgers remain at 54/100
calls and 20/20 repairs; do not reset either grant or infer another one.
The completed local restart verification added zero calls.

Current program: `docs/plans/legal-integration-coverage-resumption.md`, extending
the original coverage program. Current result: `execution-result.md` in this
directory. Artifacts:
`artifacts/legal-integration-coverage/2026-10-08/additional-200-calls-100-repairs/`.
Read `execution-summary.json`, `verification.json`, `candidate-results.json`,
`pair-assessments.json`, `model-followups.json`, `tool-check-inventory.json` and
`completion-manifest.json`. The current source is sealed by the highest numbered
`review-v*.json`; current tests passed {summary['tests']['tests']} with no failures.

The last historical batch's valid source-first perspective was reused with its
original receipt and never supplied to its peer. Candidate-specific permitted
expressions and explicit pair descriptions replaced the rejected candidate
confusion. New roles have independent journals and provider reservations. All
old proposals, failed attempts, grants, reviews and source snapshots remain.
The original expiry 1791519402.34676 was never extended.

The returned HTTP 502 at batch 21 was preserved and recovered through a
separately reviewed attempt. Its original tool context was reused, with exact
request and schema identity checked before another charged reservation.
Read `role-attempt-history.json` for every new role attempt, including failures,
and the hash-bound `latest.json` selection in each repaired role directory.
`resume-repair` only reuses its specifically reviewed completed attempt on
restart; a further failure needs another exact review.
Batch 36's locally terminated timeout was also reviewed separately. Its
successor permits 450 seconds through explicit recovery settings, while the
ordinary product cap remains 300 seconds. Review v3 was conditional and never
executed because preflight found a settings mismatch; review v4 preserves the
correction, its tests and the failed preflight evidence.

Use the saved fixed prefix `.venv/bin/python scripts/run_legal_integration_coverage.py`
with `resume-verify` for verification. `resume-execute` reuses complete results
or stops on an already failed role; it does not retry failures. Local checks
use the sandbox; any genuinely new live action needs the existing trusted
provider wrapper. Started-without-receipt roles require investigation and must
not be silently resent. Do not change reviewed source while a runner is active.

All 46 original substantive obligations remain open. Coverage does not establish
legal-English or case-law accuracy, governing standards, client facts, independent
calibration or release readiness. Read the original remaining-gap register before
planning further substantive work. This was scoped-stage execution on retained
generated readings, not a fresh end-to-end product generation. No commit or push
was requested or performed.
''')
report_sources = r.OUT / 'reporting-source'
report_sources.mkdir(exist_ok=True)
for name in ('report_legal_coverage_resumption.py', 'close_legal_coverage_resumption.py'):
    source = Path('/tmp') / name; target = report_sources / name
    if target.exists(): assert target.read_bytes() == source.read_bytes()
    else: shutil.copyfile(source, target)
review = r.check_review()
r.immutable(r.OUT / 'completion-manifest.json', {
    'status': summary['status'], 'execution_complete': verified['execution_complete'],
    'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=r.ROOT, text=True).strip(),
    'worktree_dirty': True, 'environment': str(r.ROOT / '.venv/bin/python'),
    'CPU_GPU': 'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPU devices',
    'seed_policy': 'External provider seeds unavailable; no statistical ranking.',
    'wall_seconds': summary['wall_seconds'], 'runner_processes': running,
    'plan': r.ref(r.PLAN), 'review': r.ref(r.review_path()), 'source_manifest': review['source_manifest'],
    'run_manifest': r.ref(r.OUT / 'run-manifest.json'),
    'data_version': r.ref(r.BASE / 'inputs.json'), 'partition': r.ref(r.BASE / 'partition.json'),
    'predecessor_checkpoint': r.ref(r.OUT / 'predecessor-checkpoint.json'),
    'authorization': r.ref(r.OUT / 'authorization.json'), 'allowance': r.ref(r.OUT / 'allowance.json'),
    'repairs': r.ref(r.OUT / 'repairs.json'), 'tests': r.ref(r.test_directory() / 'result.json'),
    'retained_candidate_check': r.ref(r.OUT / 'retained-candidate-schema-check.json'),
    'verification': r.ref(r.OUT / 'verification.json'), 'summary': r.ref(r.OUT / 'execution-summary.json'),
    'execution_result': r.ref(r.OUT / 'result.json'),
    'review_history_verification': r.ref(r.OUT / 'review-history-verification.json'),
    'pairs': r.ref(r.OUT / 'pair-assessments.json'), 'candidates': r.ref(r.OUT / 'candidate-results.json'),
    'candidate_targets': r.ref(r.OUT / 'candidate-targets.json'),
    'followups': r.ref(r.OUT / 'model-followups.json'), 'concerns': r.ref(r.OUT / 'model-additional-concerns.json'),
    'tools': r.ref(r.OUT / 'tool-check-inventory.json'),
    'role_attempts': r.ref(r.OUT / 'role-attempt-history.json'),
    'recovery_reviews': [r.ref(p) for p in sorted(r.OUT.glob('service-recovery-*.json'))],
    'restart': r.ref(r.OUT / 'restart-check/result.json'),
    'next_phase_plan': r.ref(r.OUT / 'next-phase-plan.json'),
    'report': r.ref(doc / 'execution-result.md'), 'reset_memo': r.ref(doc / 'reset-memo.md'),
    'readme': r.ref(doc / 'README.md'),
    'service_recovery_result': r.ref(doc / 'service-recovery-result.md'),
    'timeout_review': r.ref(doc / 'timeout-recovery-review.md'),
    'timeout_settings_review': r.ref(doc / 'timeout-settings-review.md'),
    'timeout_recovery_result': r.ref(doc / 'timeout-recovery-result.md'),
    'preflight_failure': r.ref(r.OUT / 'v3-preflight-failure.json'),
    'remaining_gaps': r.ref(doc / 'remaining-gaps.md'),
    'reporting_source': [r.ref(p) for p in sorted(report_sources.glob('*.py'))],
    'legal_obligations_open': 46, 'legal_accuracy_established': False, 'release_eligible': False})
print({'status': summary['status'], 'coverage': verified['coverage']['assessed_pairs'],
       'new_calls': verified['new_calls'], 'new_repairs': verified['new_repairs'], 'active_runners': running})
