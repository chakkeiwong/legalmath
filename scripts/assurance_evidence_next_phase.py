"""Prepare complete, receipt-linked recovery work without provider dispatch."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import time

import assurance_evidence_core as c
from legalmath.canonical import digest

PLAN = Path('docs/plans/assurance-evidence-reviewed-recovery.md')
AUDIT_PLAN = Path('docs/plans/assurance-evidence-recovery-budget-review.md')
REQUIRED = ('work-items.json', 'evidence-request.md', 'reviewed-plan.md',
            'run-manifest.json', 'allowance-checkpoint.json')
DATE_RULE = ('Establish the actual assessment period independently. Any 20 April 2026 '
             'date in retained questions identifies the supplied circular edition; '
             'it does not establish the period to assess.')


def current_allowance(root, ex):
    """Use the combined current-review ledger when its authorization exists."""
    auth = root/ex.RUN/'current-review'/'authorization.json'
    if auth.exists() or any((auth.parent/'reservations').glob('*.json')):
        import assurance_evidence_review_runtime as current
        combined = current.Allowance(root).verify()
        historical = ex.Allowance(root).verify()['task_spending']
        if set(historical) & set(combined['task_spending']):
            c.fail('E_INTEGRITY', 'Historical and current review task identities overlap')
        return {**combined, 'task_spending': {**historical, **combined['task_spending']},
            'final_issue_limit': 50}, current.RUN
    return ex.Allowance(root).verify(), ex.RUN


def reservation_refs(root, ex, run):
    refs = ex.master.files_in(root/ex.RUN/'reservations', root)
    if run != ex.RUN:
        refs += ex.master.files_in(root/run/'reservations', root)
    return refs


def assemble(inventory, obligations, definitions, rows, allowance, *, now):
    identities = [(r['role'], r['reading_id']) for r in inventory]
    obligation_ids = [r['obligation']['obligation_id'] for r in obligations]
    task_ids = [t['id'] for t in definitions]
    if (len(identities) != 70 or len(set(identities)) != 70
            or len(obligation_ids) != 46 or len(set(obligation_ids)) != 46
            or not task_ids or len(task_ids) != len(set(task_ids))):
        c.fail('E_INTEGRITY', 'Recovery inventory lost or duplicated identities')
    latest = {}
    for row in sorted(rows, key=lambda r: (r['attempt'], r.get('allowance_slot') or 0)):
        if row['phase'] == 'final':
            latest[row['task']] = row
    if set(latest) != set(task_ids):
        c.fail('E_INTEGRITY', 'Recovery plan lacks an outcome for a scheduled final task')
    final_limit = allowance.get('final_issue_limit', 20)
    audits = []
    for task in definitions:
        row = latest[task['id']]
        if row['role'] != task['role'] or row['issues'] != task['issues']:
            c.fail('E_INTEGRITY', 'Final outcome has a different role or canonical issue')
        error = row.get('details', '')
        failure = ('CLOSURE_STATUS_CONTRADICTION' if error == 'Qualified finding claimed full closure'
                   else 'NON_SOURCE_QUOTATION' if 'Evidence must occur exactly once' in error
                   else 'OTHER_VALIDATOR_FAILURE' if row['status'] != 'VALIDATED' else None)
        audits.append({'task': task['id'], 'role': task['role'], 'issues': task['issues'],
            'retained_status': row['status'], 'error': row.get('error'), 'details': error,
            'failure_class': failure, 'receipt': row['receipt'],
            'validated_findings': deepcopy(row.get('value', {}).get('findings', [])),
            'remaining_task_attempts': max(0, 2-allowance['task_spending'].get(task['id'], 0)),
            'canonical_calls_remaining': {i: max(0, final_limit-allowance['new_issue_spending'].get(i, 0)) for i in task['issues']},
            'required_work': ('Correct the exact validator defect; retain all substantive uncertainty. '
                              if failure else 'Retain every substantive finding. ')+
                'Rebuild the affected review against current diagnostics and actual repaired code/results before dispatch.',
            'review_of_current_evidence': 'PENDING', 'counted_repair': True,
            'dispatch_authorized': False})
    programs = []
    for row in inventory:
        if not row['baseline_program_present'] or not row['required_program_repairs']:
            continue
        issue = 'reading.'+row['reading_id']+'.'+row['role']
        programs.append({**deepcopy(row), 'canonical_issue': issue,
            'canonical_calls_remaining': max(0, 4-allowance['new_issue_spending'].get(issue, 0)),
            'next_action': 'Implement and check the explicit requirements; preserve the original program and unresolved legal classifications. Obtain affected review before acceptance.',
            'dispatch_authorized': False})
    evidence = [{**deepcopy(row), 'assessment_period_instruction': DATE_RULE,
        'status': 'OPEN', 'original_text_preserved': True} for row in obligations]
    issue_demand = Counter(i for t in definitions for i in t['issues'])
    shortfalls = {i: n-max(0, final_limit-allowance['new_issue_spending'].get(i, 0))
                  for i, n in issue_demand.items()
                  if n > max(0, final_limit-allowance['new_issue_spending'].get(i, 0))}
    return {'status': 'PREPARED_WITH_BLOCKED_DEPENDENCIES', 'provider_calls': 0, 'repair_calls': 0,
        'inventory': deepcopy(inventory), 'program_repairs': programs, 'final_audits': audits,
        'evidence_requests': evidence, 'assessment_period': None,
        'budget': {'remaining_total_calls': allowance['remaining'],
            'remaining_repair_calls': allowance['repair_remaining'], 'ends_at': allowance['ends_at'],
            'expired_at_preparation': now >= allowance['ends_at'],
            'current_evidence_review_calls_without_retries': len(definitions),
            'current_evidence_review_repair_shortfall': max(0, len(definitions)-allowance['repair_remaining']),
            'current_evidence_review_issue_shortfalls': shortfalls,
            'tasks_without_attempt_headroom': [a['task'] for a in audits if not a['remaining_task_attempts']],
            'program_issues_without_call_headroom': [p['canonical_issue'] for p in programs if not p['canonical_calls_remaining']],
            'estimate_scope': 'One renewed call per existing final packet only; program work and retries are additional. Repartitioning requires new coverage and budget review.'},
        'counts': {'reading_reviews': len(inventory), 'original_obligations_open': len(evidence),
            'program_repairs': len(programs), 'inventory_statuses': dict(Counter(r['status'] for r in inventory)),
            'scheduled_final_audits': len(audits),
            'failed_final_audits': sum(a['retained_status'] != 'VALIDATED' for a in audits),
            'failure_classes': dict(Counter(a['failure_class'] for a in audits if a['failure_class']))},
        'legal_correctness': 'NOT_ESTABLISHED', 'accepted_program_repairs': 0,
        'closed_original_obligations': 0, 'release_eligible': False}


def attach_current_review(work, report, derived, post_ref):
    phases = report['state']['phases']
    done = not report['state']['halt'] and all(phases.get(p, {}).get('status') == 'COMPLETED'
        for p in ('engineering', 'dispositions'))
    work['current_review'] = {'status': report['status'], 'completed': done,
        'structurally_validated_tasks': report['structurally_validated_tasks'],
        'findings': deepcopy(report['findings']), 'unaccounted_slots': report['unaccounted_slots'],
        'later_local_candidate': post_ref, 'later_candidate_reviewed': False,
        'accepted_substantive_repairs': 0}
    work['next_phase'] = 'GENERAL_EVIDENCE_ANALYSIS_AND_LATER_CANDIDATE_REVIEW' if done else 'CURRENT_REVIEW_REMAINS_INCOMPLETE'
    budget = work['budget']
    budget['hypothetical_full_repeat_calls_without_retries'] = budget['current_evidence_review_calls_without_retries']
    budget['hypothetical_full_repeat_repair_shortfall'] = budget['current_evidence_review_repair_shortfall']
    budget['historical_partition_issue_shortfalls'] = budget.pop('current_evidence_review_issue_shortfalls')
    budget['current_evidence_review_calls_without_retries'] = 0 if done else report['packet_count']-report['attempted_tasks']
    budget['current_evidence_review_repair_shortfall'] = max(0,
        budget['current_evidence_review_calls_without_retries']-budget['remaining_repair_calls'])
    budget['provider_dispatch_planned'] = False
    budget['estimate_scope'] = 'Completed review coverage is retained. Full-repeat cost is hypothetical, not scheduled work. Later changed inputs need bounded review and separate capacity preflight within existing limits.'
    for audit in work['final_audits']:
        audit['review_of_current_evidence'] = 'SUPERSEDED_BY_COMPLETED_REVIEW_COVERAGE' if done else 'CURRENT_ROUND_PENDING'
        audit['required_work'] = 'Retain historical response and all findings. Inspect later current-review findings and any local candidate changes; historical schema rejection is not a new unattempted task.'
    index = {row['obligation']['obligation_id']: {**deepcopy(row), 'derived_requests': []}
        for row in work['evidence_requests']}
    identities = set()
    if derived:
        keys = [(e['role'], e['reading_id']) for e in derived]
        expected = {(e['role'], e['reading_id']) for e in work['inventory']}
        if len(keys) != 70 or len(set(keys)) != 70 or set(keys) != expected:
            c.fail('E_INTEGRITY', 'Derived evidence map lost reading identities')
        for entry in derived:
            for request in entry['operative']['obligations']:
                key = request['question_id']
                identity = (key, entry['role'], entry['reading_id'])
                if key not in index or identity in identities or request['original_question_answered']:
                    c.fail('E_INTEGRITY', 'Invalid, duplicate or closed derived obligation request')
                if [o['question_id'] for o in entry['original']['obligations']] != [o['question_id'] for o in entry['operative']['obligations']]:
                    c.fail('E_INTEGRITY', 'Derived obligation identities differ from the original packet')
                identities.add(identity)
                index[key]['derived_requests'].append({'role': entry['role'],
                    'reading_id': entry['reading_id'], 'request': deepcopy(request),
                    'derived_record': post_ref, 'review_task': entry['review_task'],
                    'direct_subject': entry['reading_id'] in index[key]['obligation']['candidate_ids']})
        original = {(o['question_id'], e['role'], e['reading_id']) for e in derived for o in e['original']['obligations']}
        required = {(key, role, cid) for key, row in index.items()
            for role in c.ROLES for cid in row['obligation']['candidate_ids']}
        if identities != original or not required <= identities:
            c.fail('E_INTEGRITY', 'Incomplete original obligation/role/reading request coverage')
    work['obligation_evidence_map'] = list(index.values())


def evidence_text(work):
    text = ('# Evidence needed for the remaining assessment\n\n'+DATE_RULE+'\n\n'
        'Identify the provider(s), product, arrangement boundaries, assessment start and end, '
        'and appointment, migration, replacement and termination dates. Supply records with '
        'source, author, effective date, covered entity and period, and any contrary evidence.\n\n'
        '- Authority: applicable dated legislation, product rules and scheme conditions, amendments, '
        'modifications, ownership/finality rules, and interpretation of paragraph 10, paragraphs 14–16 and footnote 5.\n'
        '- Case facts: responsibility and supervision records, ownership/register inventories, '
        'on-chain/off-chain reconciliation, settlement finality, requests, incidents and remediation.\n'
        '- Interpretation: independently supported criteria for retention, conduct, achieved adequacy, '
        'SHOULD, temporal coverage and liability. Keep section 6.8 and the non-exhaustive Appendix within their scopes.\n\n'
        'The following are the exact retained requests. Their date premises remain subject to the '
        'assessment-period instruction above. Empty or unavailable evidence leaves the request open.\n')
    for row in work['evidence_requests']:
        obligation = row['obligation']
        text += '\n## '+obligation['obligation_id']+'\n\nDimension: '+obligation['dimension']+'\n\n'
        for role, response in row['current_responses'].items():
            text += role+': '+response['followup_question']+'\n\n'
    if work.get('current_review'):
        text += '\n# Current derived evidence requests\n\nThe earlier requests above are preserved history. The following provisional requests incorporate the later local corrections; all obligations remain open.\n'
        for row in work['obligation_evidence_map']:
            text += '\n## '+row['obligation']['obligation_id']+'\n\n'
            for item in row['derived_requests']:
                request = item['request']
                text += item['role']+' / '+item['reading_id']+': '+request['answer']+'\n\n'
                for needed in request['needed_evidence']:
                    text += '- '+needed+'\n'
                text += '\n'
    return text


def plan_text(work):
    n, budget = work['counts'], work['budget']
    if work.get('current_review'):
        review = work['current_review']
        return ('# Current recovery plan\n\n'
            f"Current review: {review['status']}; {review['structurally_validated_tasks']} structurally validated tasks, "
            f"{len(review['findings'])} retained findings. The {n['failed_final_audits']} rejected responses in the historical partition remain preserved.\n\n"
            f"Current capacity: {budget['remaining_total_calls']} total calls and {budget['remaining_repair_calls']} repair calls; expiry {budget['ends_at']}. "
            f"Pending initial calls in the current round: {budget['current_evidence_review_calls_without_retries']}. "
            'No provider call is scheduled by this local package.\n\n'
            '1. Review the later local candidate against its precise code and disposition changes; the previous model round does not accept it.\n'
            '2. Continue general source and interpretation analysis using the 46 entries in obligation-evidence-map.json and the corrected requests in evidence-request.md. Keep edition dates and actual assessment dates separate.\n'
            '3. For an actual case, establish provider, product, arrangement and assessment interval, then obtain the applicable authority chain and ownership, finality, supervision, incident and remediation records.\n'
            '4. Refresh the plan after new evidence or a reproducible defect. Any later model review must fit the remaining shared repair capacity and preserve cumulative spending.\n\n'
            'All 46 original obligations remain open. Synthetic checks, complete response coverage and consistent receipts establish no legal truth or release readiness.\n')
    guarded = work.get('guarded_repair')
    progress = (f"Local mechanical guards passed {guarded['synthetic_checks']} synthetic cases for "
        f"{guarded['programs']} programs. The formulas are unchanged; substantive acceptance is pending. "
        f"Evidence: {guarded['receipt']['path']}.\n\n" if guarded else '')
    program_step = ('2. Review the implemented guards and complete the remaining source-specific and interpretive requirements; '
        if guarded else '2. Implement the exact program requirements in work-items.json; ')
    return ('# Executable recovery checkpoint\n\n'
        f"Prepared {n['program_repairs']} program repair specifications, {n['scheduled_final_audits']} final audit entries "
        f"({n['failed_final_audits']} rejected), and {n['original_obligations_open']} original evidence requests. "
        'All source identities and unresolved findings remain attached.\n\n'+progress+
        '1. Establish the assessment period and collect the records in evidence-request.md; classify their '
        'applicability and meaning independently of availability.\n'
        +program_step+'retain unknown/conflict handling, scope, provenance and conditional labels. Preserve unformalized readings until representable.\n'+
        '3. Check changed programs with the specified contrary cases. Keep unsupported classifications unresolved.\n'
        '4. Rebuild review packets from the changed programs, v3 diagnostic and current controller. Correct the '
        'recorded audit-response defects without editing their old outputs. Review all affected evidence.\n'
        '5. Refresh this package after evidence or accounting changes; retain prior packages.\n\n'
        f"Budget: {budget['remaining_total_calls']} total calls and {budget['remaining_repair_calls']} repairs remain. "
        f"Renewing the existing final partition alone needs {budget['current_evidence_review_calls_without_retries']} "
        'corrective calls without retries; this estimate excludes program work. '
        f"Canonical final-issue shortfalls: {budget['current_evidence_review_issue_shortfalls']}. "
        f"Program issues with no call headroom: {len(budget['program_issues_without_call_headroom'])}. "
        f"Grant expiry: {budget['ends_at']}. No new dispatch is authorized by this package.\n\n"
        '| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |\n'
        '|---|---|---|---|---|---|\n'
        '| Local preparation complete | Exact inventory and receipt coverage | Missing or altered evidence stops execution | Legal meaning and case facts | Resolve listed dependencies | Legal closure or release |\n\n'
        'Post-run review: validator repair alone cannot accept a substantive finding or a newer controller. '
        'The weakest evidence remains unresolved classifications and absent case records. Contrary authority '
        'or case evidence can overturn conditional interpretations. Candidate rejection does not reject the research direction.\n')


def verify_package(root, ex, ref):
    path = c.checked(ref, root)
    base = (root/ex.RUN/'local-recovery').resolve()
    if path.name != 'completion-receipt.json' or not path.parent.is_relative_to(base):
        c.fail('E_INTEGRITY', 'Foreign local recovery receipt')
    receipt = c.read(path)
    covered = set()
    for item in receipt['files']:
        file = c.checked(item, root)
        if file.parent != path.parent:
            c.fail('E_INTEGRITY', 'Foreign local recovery output')
        covered.add(file.name)
    if not set(REQUIRED) <= covered:
        c.fail('E_INTEGRITY', 'Incomplete local recovery package')
    for item in receipt['inputs']:
        c.checked(item, root)
    work = c.read(path.parent/'work-items.json')
    if work.get('current_review') and 'obligation-evidence-map.json' not in covered:
        c.fail('E_INTEGRITY', 'Current recovery package omits its obligation evidence map')
    return work


def summary(root, ex):
    pointer = root/ex.RUN/'current-local-recovery.json'
    if not pointer.exists():
        return None
    ref = c.read(pointer)['receipt']
    work = verify_package(root, ex, ref)
    allowance, _ = current_allowance(root, ex)
    report = {'status': work['status'], 'receipt': ref, 'counts': work['counts'],
        'plan': str(Path(ref['path']).parent/'reviewed-plan.md'),
        'evidence_request': str(Path(ref['path']).parent/'evidence-request.md'),
        'budget_at_preparation': work['budget'], 'provider_calls': 0, 'repair_calls': 0,
        'current_review': work.get('current_review'),
        'evidence_map': str(Path(ref['path']).parent/'obligation-evidence-map.json') if work.get('current_review') else None}
    checkpoint = c.read((root/ref['path']).parent/'allowance-checkpoint.json')
    if checkpoint != allowance:
        report.update(status='STALE_BUDGET_CHECKPOINT', current_allowance=allowance,
            stale_checkpoint=checkpoint,
            next_action='Regenerate this zero-call package from the combined current-review ledger before dispatch.')
    return report


def execute(root, ex):
    """Called by the locked frozen master after all scheduled phases finish."""
    from assurance_evidence_completion import adopted_diagnostic
    from legalmath.interpretation.search.providers import CodexProvider
    began = time.monotonic()
    manifest = ex.verify(root)
    if Path(__file__).resolve().parents[1] != (root/manifest['frozen_root']).resolve():
        c.fail('E_AUTHORITY', 'Local recovery must execute the reviewed frozen snapshot')
    if any(ex.engine().state(root)['phases'].get(p, {}).get('status') != 'COMPLETED' for p in ex.PHASES):
        c.fail('E_DEPENDENCY', 'Scheduled phases must finish before recovery preparation')
    diagnostic = adopted_diagnostic(root, ex)
    if diagnostic is None:
        c.fail('E_DEPENDENCY', 'Current diagnostic required before recovery preparation')
    checkdir = c.checked(diagnostic['current'], root).parent
    before, allowance_run = current_allowance(root, ex)
    reservations = reservation_refs(root, ex, allowance_run)
    files = [checkdir/'program-inventory.json', root/c.OLD/'remaining-obligations.json',
        root/ex.RUN/'final/task-definitions.json', root/ex.RUN/'final/coverage.json',
        root/PLAN, root/AUDIT_PLAN, root/ex.POLICY, root/ex.RUN/'authorization.json']
    refs = [c.receipt(f, root) for f in files]+reservations+[
        c.read(root/ex.RUN/'active-revision.json')['receipt'],
        c.read(root/ex.RUN/'current-diagnostic.json')['receipt']]
    from assurance_evidence_guarded import summary as guarded_summary
    guarded = guarded_summary(root, ex)
    if guarded:
        refs.append(guarded['receipt'])
    rows = ex.engine().task_rows(root)
    refs += [r['receipt'] for r in rows]
    inventory = c.read(files[0])
    coverage = c.read(files[3])
    covered = [(r['role'], r['reading_id']) for r in coverage]
    if len(covered) != len(set(covered)) or set(covered) != {(r['role'], r['reading_id']) for r in inventory}:
        c.fail('E_INTEGRITY', 'Final coverage differs from current reading inventory')
    current_report, derived, post_ref = None, [], None
    if allowance_run != ex.RUN:
        import assurance_evidence_review_runtime as current
        import assurance_evidence_current_review as packets
        current_report = current.summary(root)
        package = packets.verified(root, ex)
        refs += [c.receipt(root/current.AUTHORIZATION, root),
            c.receipt(package/'completion-receipt.json', root)]
        refs += [r['receipt'] for r in current.engine().task_rows(root)]
        from assurance_evidence_post_review import summary as post_summary
        post = post_summary(root, ex)
        if post is not None:
            post_ref = post['receipt']
            refs.append(post_ref)
            derived = c.read((root/post_ref['path']).parent/'dispositions.json')
    folder = root/ex.RUN/'local-recovery'/digest({'inputs': refs, 'allowance': before})[:24]
    receipt_path = folder/'completion-receipt.json'
    def forbidden(*args, **kwargs):
        c.fail('E_AUTHORITY', 'Local recovery cannot dispatch or reserve calls')
    from assurance_evidence_review_runtime import Allowance as ReviewAllowance
    complete, reserve, review_reserve = CodexProvider.complete, ex.Allowance.reserve, ReviewAllowance.reserve
    CodexProvider.complete, ex.Allowance.reserve, ReviewAllowance.reserve = forbidden, forbidden, forbidden
    try:
        if receipt_path.exists():
            verify_package(root, ex, c.receipt(receipt_path, root))
        else:
            prepared = folder/'prepared-at.json'
            if not prepared.exists():
                ex.immutable(prepared, {'at': c.now()})
            work = assemble(inventory, c.read(files[1]), c.read(files[2]), rows, before, now=c.read(prepared)['at'])
            if current_report is not None:
                attach_current_review(work, current_report, derived, post_ref)
                ex.immutable(folder/'obligation-evidence-map.json', work['obligation_evidence_map'])
            if guarded:
                work['guarded_repair'] = guarded
                if not work.get('current_review'):
                    work['next_phase'] = 'CURRENT_EVIDENCE_REVIEW_AND_REMAINING_INTERPRETATION'
                for program in work['program_repairs']:
                    program['mechanical_status'] = 'GUARD_IMPLEMENTED_AND_CHECKED_CONDITIONALLY'
                    program['next_action'] = 'Review the implemented guard and resolve remaining interpretive and source-specific requirements; retain the original questions.'
            ex.immutable(folder/'work-items.json', work)
            c.write_text(folder/'evidence-request.md', evidence_text(work))
            c.write_text(folder/'reviewed-plan.md', plan_text(work))
            ex.immutable(folder/'allowance-checkpoint.json', before)
            run_metadata = {'command': ex.PREFIX+['extend'],
                'git_commit': manifest['git_commit'], 'environment': str(root/'.venv'),
                'frozen_root': manifest['frozen_root'], 'code_revision': c.read(root/ex.RUN/'active-revision.json')['receipt'],
                'cpu_only': True, 'gpu_hidden': os.environ.get('CUDA_VISIBLE_DEVICES') == '-1',
                'seeds': 'N/A: deterministic local preparation', 'data_version': refs,
                'wall_seconds': round(time.monotonic()-began, 3), 'plan': str(PLAN),
                'result': str(folder.relative_to(root)/'work-items.json'), 'audit_plan': str(AUDIT_PLAN),
                'provider_calls': 0, 'repair_calls': 0}
            manifest_path = folder/'run-manifest.json'
            if manifest_path.exists():
                prior = c.read(manifest_path)
                run_metadata['wall_seconds'] = prior['wall_seconds']
            ex.immutable(manifest_path, run_metadata)
            if current_allowance(root, ex)[0] != before or reservation_refs(root, ex, allowance_run) != reservations:
                c.fail('E_INTEGRITY', 'Local recovery changed the call ledger')
            ex.immutable(receipt_path, {'inputs': refs,
                'files': ex.master.files_in(folder, root, ('completion-receipt.json',))})
        if current_allowance(root, ex)[0] != before or reservation_refs(root, ex, allowance_run) != reservations:
            c.fail('E_INTEGRITY', 'Local recovery changed the call ledger')
        verify_package(root, ex, c.receipt(receipt_path, root))
        c.save(root/ex.RUN/'current-local-recovery.json', {'receipt': c.receipt(receipt_path, root)})
        return summary(root, ex)
    finally:
        CodexProvider.complete, ex.Allowance.reserve, ReviewAllowance.reserve = complete, reserve, review_reserve
