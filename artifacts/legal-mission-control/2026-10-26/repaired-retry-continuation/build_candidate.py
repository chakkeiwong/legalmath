"""Build reviewed candidate sources without mutating installed hash-bound code."""
from pathlib import Path
import os
import sys

ROOT = Path('/home/chakwong/python/legalmath')
WORK = Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]

def patch(path, old, new):
    target = ROOT/WORK/'source'/path
    body = (target if target.exists() else ROOT/path).read_text()
    assert body.count(old) == 1, (path, old[:100], body.count(old))
    body = body.replace(old, new, 1)
    compile(body, path, 'exec')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)

P = 'src/legalmath/interpretation/assurance/bounded_provider.py'
patch(P, '\ndef review_service_policy(policy):', '''
# Explicit 26 October successor; retain every spent replacement and global limit.
SERVICE_REPAIRED_RETRY_POLICY = {**SERVICE_REVIEW_DEPLOYMENT_POLICY,
    'profile': 'counted-service-recovery.v8', 'maximum_replacements': 788,
    'backoff_seconds': [300] * 788}

def review_service_policy(policy):''')
patch(P, 'return policy in (SERVICE_REVIEW_REPAIR_POLICY, SERVICE_REVIEW_DEPLOYMENT_POLICY)',
    'return policy in (SERVICE_REVIEW_REPAIR_POLICY, SERVICE_REVIEW_DEPLOYMENT_POLICY, SERVICE_REPAIRED_RETRY_POLICY)')
patch(P, '                           SERVICE_REVIEW_DEPLOYMENT_POLICY),',
    '                           SERVICE_REVIEW_DEPLOYMENT_POLICY, SERVICE_REPAIRED_RETRY_POLICY),')
patch(P, '            if policy == SERVICE_REVIEW_DEPLOYMENT_POLICY:',
    '            if policy in (SERVICE_REVIEW_DEPLOYMENT_POLICY, SERVICE_REPAIRED_RETRY_POLICY):')
anchor = "            require(len(state['charges']) < state['maximum'], 'Stage replacement reserve exhausted', 'E_RESOURCE_LIMIT')"
patch(P, anchor, '''            if policy == SERVICE_REPAIRED_RETRY_POLICY:
                previous = read_evidence(binding['repaired_retry_service_predecessor'], self.root)
                authority = read_evidence(binding['repaired_retry_authority'], self.root)
                require(previous['profile'] == SERVICE_REVIEW_DEPLOYMENT_POLICY['profile']
                    and len(previous['charges']) == previous['maximum'] == 288
                    and state['charges'][:288] == previous['charges']
                    and authority['additional_service_recoveries'] == 500
                    and authority['cumulative_service_recoveries'] == 788
                    and authority['global_calls_added'] == 0
                    and authority['deadline_extended'] is False
                    and authority['user_instruction'],
                    'Lost 288 predecessor charges or unbound 500-retry amendment', 'E_AUTHORITY')
''' + anchor)
P = 'src/legalmath/interpretation/assurance/phased/capacity_checkpoint.py'
patch(P, "        if policy.annotate(request) != wanted:", '''        from .retry_checkpoint import equivalent
        if not equivalent(request, wanted, checkpoint, candidate):''')
anchor = "    if row['mode'] == 'RETAINED_FAILURE':"
patch(P, anchor, '''    if row['mode'] == 'REVIEWED_FAILURE_RETRY':
        from .retry_checkpoint import retryable
        retryable(checkpoint, row, request, prior, product.root)
        return None
''' + anchor)
P = 'src/legalmath/interpretation/assurance/phased/product.py'
anchor = "    def audit_answer(self, qid, question, answer, details, *, prefix=''):\n"
patch(P, anchor, anchor + '''        if not prefix:
            from .retry_checkpoint import fixed_correction
            fixed = fixed_correction(self, qid, question, answer, details)
            if fixed is not None:
                return deepcopy(fixed['original_reviews'])
''')
anchor = "    def correct_answer(self, qid, question, answer, reviews, details, dependencies):\n"
patch(P, anchor, anchor + '''        from .retry_checkpoint import resume_correction
        resumed = resume_correction(self, qid, question, answer, details, dependencies)
        if resumed is not None:
            return resumed
''')
P = 'scripts/legal_mission_execution.py'
anchor = "    if program.get('baseline_corpus_repair'):\n"
patch(P, anchor, '''    if program.get('repaired_retry_continuation'):
        from scripts.legal_repaired_retry_continuation import validate
        reviewed = validate(program, root, program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
''' + anchor)
anchor = "            if self.program.get('baseline_corpus_repair'):\n"
patch(P, anchor, '''            if self.program.get('repaired_retry_continuation'):
                from scripts.legal_repaired_retry_continuation import validate_history
                validate_history(self.program, state, self.root)
            elif self.program.get('baseline_corpus_repair'):
''')
P = 'scripts/legal_mission_control.py'
anchor = '    else:\n        master_state = None\n'
patch(P, anchor, '''        retry = master.get('repaired_retry_continuation')
        if retry:
            require(retry.get('profile') == 'reviewed-repaired-retry-continuation.v1'
                and retry.get('prior_detours') == detours == 67
                and retry.get('additional_consolidated_revision') == 1
                and retry.get('calls_added') == 0 and retry.get('replacements_added') == 500
                and retry.get('attempt_additions') == {'baseline-p14':1,'baseline-gatecoin':1}
                and program.get('repaired_retry_continuation') == retry,
                'Unreviewed repaired retry continuation')
            require(any(r['id'] == 'repaired-retry-continuation-2026-10-26'
                and retry['review'] in r['result_evidence'] for r in history),
                'Missing repaired retry history')
            verify_refs(root, retry)
            detours += 1
''' + anchor)
P = 'scripts/legal_integration_phased_live.py'
patch(P, 'def active_live(program):\n', '''def active_live(program):
    if program.get('repaired_retry_continuation'):
        return Path(program['repaired_retry_continuation']['runtime'])
''')
anchor = "    if program.get('baseline_corpus_repair') and not preparation_only:\n"
patch(P, anchor, '''    if program.get('repaired_retry_continuation') and not preparation_only:
        options['bounded_capacity_checkpoint'] = program['repaired_retry_continuation']['arm_checkpoints'].get(q, {}).get(
            tool or 'baseline', options['bounded_capacity_checkpoint'])
''' + anchor)
P = 'scripts/legal_review_repair_service.py'
patch(P, "    service_work = Path(deployment['runtime']).parent if deployment else WORK", '''    successor = program.get('repaired_retry_continuation')
    service_work = Path(successor['work']) if successor else (Path(deployment['runtime']).parent if deployment else WORK)
    service_policy = successor['service_policy'] if successor else program[KEY]['service_policy']''')
patch(P, "and binding['service_recovery_policy'] == program[KEY]['service_policy'],",
    "and binding['service_recovery_policy'] == service_policy,")
print('Candidate patches written; installed sources unchanged.')
