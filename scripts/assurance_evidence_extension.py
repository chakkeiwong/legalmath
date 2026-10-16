"""Immutable additional 100-call / 20-repair grant after the 95-call checkpoint."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import assurance_evidence_core as c
import assurance_evidence_continuation as old
import assurance_evidence_master as master
import assurance_evidence_phases as phases
import assurance_evidence_protocol as protocol
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import commitment

RUN = c.BASE / 'additional-100-repair-20'
PLAN = Path('docs/plans/assurance-evidence-additional-100-repair-20.md')
POLICY = Path('docs/implementation/assurance-evidence-master/extension-allowlist.json')
PREFIX = old.PREFIX
PHASES = ('reviews', 'programs', 'checks', 'final')
TESTS = old.TESTS + ['tests/assurance/test_assurance_evidence_extension.py',
    'tests/assurance/test_assurance_evidence_next_phase.py',
    'tests/assurance/test_assurance_evidence_guarded.py',
    'tests/assurance/test_assurance_evidence_current_review.py',
    'tests/assurance/test_assurance_evidence_post_review.py',
    'tests/assurance/test_assurance_evidence_recovery_budget.py']
BASELINE = 95


def immutable(path, value):
    if path.exists():
        if c.read(path) != value:
            c.fail('E_INTEGRITY', 'Immutable supplemental record changed: '+str(path))
    else:
        c.save(path, value)


class Allowance:
    maximum = 100

    def __init__(self, root, task=None, correction=False):
        self.root, self.task, self.correction = Path(root), task, correction
        self.grant_path = self.root/RUN/'authorization.json'
        self.path = self.root/RUN/'allowance.json'
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = c.read(self.grant_path)
        self.verify()

    def ledger(self):
        previous, calls = raw_digest(self.grant_bytes), []
        for slot, path in enumerate(sorted((self.root/RUN/'reservations').glob('*.json')), BASELINE+1):
            row = c.read(path)
            if path.name != f'{slot:04}.json' or row['previous_hash'] != previous or row['call']['slot'] != slot:
                c.fail('E_INTEGRITY', 'Supplemental reservation chain changed')
            previous = digest(row)
            calls.append(row['call'])
        if self.path.exists():
            saved = c.read(self.path)
            prefix = saved['calls']
            if saved['authorization_hash'] != raw_digest(self.grant_bytes) or len(prefix) > len(calls) or prefix != calls[:len(prefix)]:
                c.fail('E_INTEGRITY', 'Supplemental journal/projection mismatch')
        return calls

    def verify(self):
        g = self.grant
        if (self.grant_path.read_bytes() != self.grant_bytes or g['baseline_used'] != BASELINE
                or g['maximum'] != 100 or g['repair_maximum'] != 20 or g['issue_limit'] != 4
                or g['final_issue_limit'] != 20 or g['old_unused_calls_carried'] != 0 or g['attempts_per_task'] != 2):
            c.fail('E_AUTHORITY', 'Unexpected supplementary grant')
        for ref in g['protected_checkpoint']:
            c.checked(ref, self.root)
        calls, counts, task_counts = self.ledger(), Counter(), Counter()
        repairs = 0
        for row in calls:
            if (row['phase'] not in ('propagation', 'scope', 'final') or not row['issues']
                    or len(row['issues']) != len(set(row['issues'])) or not set(row['issues']) <= set(g['allowed_issues'])
                    or type(row['repair']) is not bool or not re.fullmatch('[0-9a-f]{64}', row['request_hash'])
                    or not g['starts_at'] <= row['issued_at'] < g['ends_at']):
                c.fail('E_INTEGRITY', 'Invalid supplemental reservation')
            counts.update(row['issues'])
            task_counts[row['task']] += 1
            repairs += int(row['repair'])
        if (len(calls) > 100 or repairs > 20 or any(n > 2 for n in task_counts.values())
                or any(n > (20 if issue.startswith('final.') else 4) for issue, n in counts.items())):
            c.fail('E_INTEGRITY', 'Supplemental quota exceeded')
        combined = Counter(g['baseline_issue_spending'])
        combined.update(counts)
        return {'used': len(calls), 'remaining': 100-len(calls), 'maximum': 100,
                'baseline_used': BASELINE, 'combined_used': BASELINE+len(calls),
                'old_unused_calls': 5, 'old_unused_calls_carried': 0,
                'repair_calls': repairs, 'repair_remaining': 20-repairs,
                'new_issue_spending': dict(counts), 'combined_issue_spending': dict(combined),
                'task_spending': dict(task_counts), 'ends_at': g['ends_at']}

    def reserve(self, request_hash):
        task = self.task
        if (not task or task['phase'] not in ('propagation', 'scope', 'final') or not task['issues']
                or len(task['issues']) != len(set(task['issues'])) or not set(task['issues']) <= set(self.grant['allowed_issues'])
                or not re.fullmatch('[0-9a-f]{64}', request_hash)):
            c.fail('E_AUTHORITY', 'Undeclared supplemental task')
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if ((self.root/RUN/'current-review/authorization.json').exists()
                    or any((self.root/RUN/'current-review/reservations').glob('*.json'))):
                c.fail('E_AUTHORITY', 'Approved current review owns the remaining allowance; original spending is frozen')
            s = self.verify()
            if c.now() >= self.grant['ends_at'] or not s['remaining']:
                c.fail('E_RESOURCE_LIMIT', 'Supplemental total/window exhausted')
            if s['task_spending'].get(task['id'], 0) >= 2:
                c.fail('E_RESOURCE_LIMIT', 'Two supplemental attempts exhausted for this task')
            if any(s['new_issue_spending'].get(i, 0) >= (20 if i.startswith('final.') else 4) for i in task['issues']):
                c.fail('E_RESOURCE_LIMIT', 'Supplemental canonical issue limit exhausted')
            if self.correction and not s['repair_remaining']:
                c.fail('E_RESOURCE_LIMIT', 'Twenty supplemental repair calls exhausted')
            if any(r['task'] == task['id'] and r['request_hash'] == request_hash for r in self.ledger()):
                c.fail('E_INTEGRITY', 'Duplicate supplemental request')
            slot = BASELINE+s['used']+1
            journal = self.root/RUN/'reservations'
            journal.mkdir(exist_ok=True)
            previous = digest(c.read(journal/f'{slot-1:04}.json')) if s['used'] else raw_digest(self.grant_bytes)
            call = {'slot': slot, 'task': task['id'], 'phase': task['phase'], 'issues': task['issues'],
                    'repair': self.correction, 'request_hash': request_hash, 'issued_at': c.now()}
            immutable(journal/f'{slot:04}.json', {'previous_hash': previous, 'call': call})
            c.save(self.path, {'authorization_hash': raw_digest(self.grant_bytes), 'calls': self.ledger()})
            return slot


def engine():
    # Separate module instance: no mutation of historical controller globals.
    spec = importlib.util.spec_from_file_location('assurance_extension_engine', old.__file__)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    value.RUN, value.Allowance, value.refresh = RUN, Allowance, refresh
    return value


def accepted_rows(root):
    latest = {r['task']: r for r in c.read(root/RUN/'baseline-accepted.json')}
    for row in sorted(engine().task_rows(root), key=lambda r: r.get('allowance_slot') or 0):
        if row['status'] == 'VALIDATED':
            latest[row['task']] = row
    return list(latest.values())


def coverage(root):
    rows = [r for r in accepted_rows(root) if 'reading_updates' in r['value']]
    ids = [(r['role'], u['reading_id']) for r in rows for u in r['value']['reading_updates']]
    expected = {(role, cid) for role in c.ROLES for cid in phases.context(root)['candidates']}
    if len(ids) != len(set(ids)) or not set(ids) <= expected:
        c.fail('E_INTEGRITY', 'Duplicate or foreign combined reading coverage')
    return rows, sorted(expected-set(ids))


def status(root):
    from assurance_evidence_completion import adopted_diagnostic
    from assurance_evidence_next_phase import summary as recovery_summary
    from assurance_evidence_guarded import summary as guarded_summary
    a, accepted = Allowance(root).verify(), accepted_rows(root)
    _, missing = coverage(root)
    diagnostic = adopted_diagnostic(root, sys.modules[__name__])
    report = {'allowance': {k:v for k,v in a.items() if k not in ('new_issue_spending','combined_issue_spending','task_spending')},
        'state': engine().state(root), 'accepted_reading_reviews': 70-len(missing), 'missing_reviews': missing,
        'scope_corrections': sum(r['phase']=='scope' for r in accepted),
        'validated_program_candidate_tasks': sum('assessments' in r['value'] for r in accepted),
        'accepted_program_repair_tasks': 0,
        'accepted_final_review_tasks': sum(r['phase']=='final' for r in accepted),
        'current_diagnostic': None if diagnostic is None else {
            'status': diagnostic['status'], 'result': diagnostic['current'],
            'comparison': c.read(root/RUN/'current-diagnostic.json')['receipt'],
            'qualification_before': diagnostic['qualification_before'],
            'qualification_after': diagnostic['qualification_after'],
            'final_review_scope': diagnostic['final_review_scope']},
        'local_recovery': recovery_summary(root, sys.modules[__name__]),
        'guarded_candidates': guarded_summary(root, sys.modules[__name__]),
        'remaining_original_obligations': 46, 'release_eligible': False}
    from assurance_evidence_review_runtime import summary as review_summary
    report['current_review'] = review_summary(root)
    if report['current_review'] and 'allowance' in report['current_review']:
        report['allowance'] = {k: v for k, v in report['current_review']['allowance'].items()
            if k not in ('new_issue_spending', 'combined_issue_spending', 'task_spending')}
    from assurance_evidence_post_review import summary as post_summary
    report['post_review_repairs'] = post_summary(root, sys.modules[__name__])
    return report


def diagnostic_note(report):
    d = report.get('current_diagnostic')
    if d is None:
        return ''
    return (f"Current diagnostic: {d['result']['path']}. Qualification counts: "
        f"{d['qualification_before']} -> {d['qualification_after']}. "
        "Six historical schema blockers are resolved; all retained programs, questions "
        "and assumptions are identical. The 16 conditional checks and 384 native/Java "
        "probes establish no legal closure; production target executions remain zero. "
        + d['final_review_scope'] + "\n")


def current_review_note(report):
    value = report.get('current_review')
    if value is None:
        return ''
    return (f"Current-evidence review: {value['status']}; {value['packet_count']} packets, "
        f"at most {value['worst_case_calls']} calls. Preflight: {value['preflight']}. "
        f"Prior expiry: {value['prior_ends_at']}; expired: {value['prior_window_expired']}. "
        +(f"Authorized cumulative limits: 100 total and 50 repairs; renewed expiry {value['allowance']['ends_at']}.\n"
         if 'allowance' in value else 'Recorded 48-hour authorization will bind after the current package passes preflight.\n'))


def recovery_note(report):
    recovery = report.get('local_recovery')
    if recovery is None:
        return ''
    counts = recovery['counts']
    guarded = report.get('guarded_candidates')
    guard_note = (f"Mechanical guards now checked for {guarded['programs']} programs in "
        f"{guarded['synthetic_checks']} synthetic cases; formulas are unchanged and substantive acceptance remains pending. "
        if guarded else '')
    return (guard_note+f"Reviewed recovery package: {recovery['plan']}. "
        f"{counts['program_repairs']} exact program repair specifications; "
        f"{counts['scheduled_final_audits']} final audit entries, including "
        f"{counts['failed_final_audits']} rejected responses; "
        f"{counts['original_obligations_open']} source-linked evidence requests. "
        f"Evidence checklist: {recovery['evidence_request']}. "
        "The package records global, canonical-issue, task and time limits separately. "
        "Preparation used zero provider calls and accepts no substantive repair.\n"+current_review_note(report)+
        (f"Later local repair candidate: {report['post_review_repairs']['receipt']['path']}; not reviewed by the earlier provider round.\n" if report.get('post_review_repairs') else ''))


def refresh(root, reason):
    report = status(root)
    current = report['state']
    next_phase = next((p for p in PHASES if current['phases'].get(p, {}).get('status') != 'COMPLETED'), None)
    repair_blocked = report['allowance']['repair_remaining'] == 0
    action = ('All scheduled provider tasks have been attempted. Further corrective provider calls require an increased repair limit. '
        'Keep challenged programs and unaccepted final audits excluded; obtain dated authority, interpretation and case evidence.'
        if next_phase is None and repair_blocked else 'Continue the next incomplete phase within the recorded budgets and evidence requirements.')
    if report.get('post_review_repairs'):
        action = ('Local repairs completed with zero provider calls. Follow '+
            report['local_recovery']['plan']+
            '. The earlier provider round does not accept this later candidate; substantive authority and case evidence remain required.')
    report.update(refreshed_at=c.now(), reason=reason, next_phase=next_phase,
        next_required_work=['Repair challenged programs and unaccepted final audit responses.',
            'Establish the actual assessment period and applicable authority chain.',
            'Supply provider, arrangement, ownership, settlement, incident and remediation evidence.'],
        action=action, repair_dispatch_blocked=repair_blocked,
        independent_nonrepair_calls_remaining=report['allowance']['remaining'],
        legal_correctness='NOT_ESTABLISHED')
    history = root/RUN/'plan-history'
    history.mkdir(exist_ok=True)
    immutable(history/f"{len(list(history.glob('*.json')))+1:04}.json", report)
    c.save(root/RUN/'next-phase-plan.json', report)
    a = report['allowance']
    c.write_text(root/RUN/'next-phase-plan.md', '# Supplemental next phase\n\n'+reason+
        f"\n\nNext scheduled phase: {next_phase}; halt: {current['halt']}. New calls {a['used']}/100; "
        f"repairs {a['repair_calls']}/{a.get('repair_maximum', 20)}; combined charged {a['combined_used']}. Reviews {report['accepted_reading_reviews']}/70. "
        'All 46 original obligations remain open.\n\n'+diagnostic_note(report)+'\n'+action+
        '\n\nTotal and repair allowances are enforced separately. '
        'Local checks remain available; do not rename corrections as independent work.\n\n'+recovery_note(report))
    return report


def explicit_contract(task):
    task = deepcopy(task)
    r = task['request']
    typ = protocol.CompactPropagation if r['kind']=='propagation' else c.ReviewResponse if r['kind']=='review' else phases.repair.AssessmentResponse
    r['response_schema'] = typ.model_json_schema()
    r['instructions'] += (' Return exactly response_schema with every required field. Copy the supplied binding_hash. '
        'Copy quotations character-for-character including capitalization; choose unique contiguous spans. '
        'For propagation include EVERY question alias exactly once, with groups limited to one reading. '
        'For formal repair preserve all original assumptions and unresolved questions; no new readings.')
    if r['kind'] == 'review':
        r['instructions'] += (' For every finding, original_question_answered must be false unless '
            'status is SUPPORTED_UNDER_STATED_SCOPE and the entire declared question is answered. '
            'Keep all qualified or unresolved findings; never change their status merely to pass validation. '
            'Evidence quotes must come from source_packet.units text. Put your own analysis or quoted '
            'assessment commentary in answer/qualifications, never present it as a published source quote.')
    if r['kind'] == 'formal_repair':
        defs = r['response_schema'].get('$defs', {})
        assessment = defs.get('Assessment')
        if assessment is not None:
            props = assessment.setdefault('properties', {})
            related = props.setdefault('related_readings', {})
            related['items'] = {'enum': list(r['selected'])}
            related['maxItems'] = len(r['selected'])
        r['response_schema']['properties']['assessments']['minItems'] = len(r['selected'])
        r['response_schema']['properties']['assessments']['maxItems'] = len(r['selected'])
        r['response_schema']['properties']['newly_proposed_readings']['maxItems'] = 0
        r['instructions'] += (' This packet contains only the selected readings. '
            'Set related_readings to an empty list unless a selected reading is genuinely related; '
            'never name a reading outside selected. Return no newly proposed readings.')
    r.pop('binding_hash')
    r['binding_hash'] = digest(r)
    protocol.transport(task)
    return task


def initial_tasks(root):
    tasks = c.read(root/old.RUN/'initial-tasks.json')
    missing = set(old.unresolved_task_ids(root, tasks))
    result = []
    for t in tasks:
        if t['id'] not in missing:
            continue
        pieces = old.split_timeout_task(t) if t['phase']=='propagation' and len(t['request']['selected'])==2 else [deepcopy(t)]
        for child in pieces:
            child['counted_repair'] = True
            child['id'] += '.additional-grant'
            r = child['request']
            r['supplemental_authorization'] = 'New 100-call / 20-repair grant; old evidence and failures retained.'
            if 'timeout_repair' in r:
                r['timeout_repair']['instruction'] = 'Authorized singleton repair; answer every original question without inferring omitted prior answers.'
            r.pop('binding_hash')
            r['binding_hash'] = digest(r)
            result.append(explicit_contract(child))
    return result


def prepare(root):
    work = root/RUN
    old.verify(root)
    prior = old.Allowance(root).verify()
    if prior['used'] != BASELINE:
        c.fail('E_AUTHORITY', 'Supplement bound to the disclosed 95-call checkpoint')
    if old.consecutive_failures(root) >= 2:
        c.fail('E_DEPENDENCY', 'Prior route veto requires causal repair')
    if (work/'authorization.json').exists():
        # Initialization requests are protected history, not a prompt template
        # to regenerate when later engineering instructions change.
        grant = Allowance(root)
        protected = {r['path'] for r in grant.grant['protected_checkpoint']}
        if not {str(RUN/'baseline-accepted.json'), str(RUN/'initial-tasks.json')} <= protected:
            c.fail('E_INTEGRITY', 'Supplemental grant omits initialization receipts')
    else:
        immutable(work/'baseline-accepted.json', old.accepted_rows(root))
        immutable(work/'initial-tasks.json', initial_tasks(root))
        names = ('amendment.json','allowance.json','state.json','final-result.json','manifest.json','active-revision.json','initial-tasks.json','explicit-response-contracts.json')
        refs = [c.receipt(root/old.RUN/n, root) for n in names]
        refs += [c.receipt(p, root) for p in sorted((root/old.RUN/'reservations').glob('*.json'))]
        refs += [c.receipt(work/n, root) for n in ('baseline-accepted.json','initial-tasks.json')]
        immutable(work/'authorization.json', {'authorization': 'you have 100 calls more and 20 more repair limit. continue the execution',
            'created_at': c.now(), 'baseline_used': BASELINE, 'maximum': 100, 'repair_maximum': 20,
            'old_unused_calls_carried': 0, 'issue_limit': 4, 'final_issue_limit': 20, 'attempts_per_task': 2,
            'starts_at': c.now(), 'ends_at': prior['ends_at'],
            'allowed_issues': c.read(root/old.RUN/'amendment.json')['allowed_issues'],
            'baseline_issue_spending': prior['combined_issue_spending'], 'protected_checkpoint': refs})
    if not (work/'state.json').exists():
        c.save(work/'state.json', {'phases': {}, 'halt': None})
    return Allowance(root).verify()


def activate(root):
    prepare(root)
    work = root/RUN
    directory = work/'revisions'/f"revision-{len(list((work/'revisions').glob('revision-*')))+1:02}"
    directory.mkdir(parents=True, exist_ok=False)
    diagnostic_plan = root/'docs/plans/assurance-evidence-diagnostic-restart.md'
    recovery_plan = root/'docs/plans/assurance-evidence-reviewed-recovery.md'
    guarded_plan = root/'docs/plans/assurance-evidence-guarded-continuation.md'
    operations_policy = root/'docs/implementation/assurance-evidence-master/operations/allowlist.json'
    operations_rules = operations_policy.with_name('allow.rules')
    current_review_plan = root/'docs/plans/assurance-evidence-current-review.md'
    review_renewal_plan = root/'docs/plans/assurance-evidence-current-review-renewal.md'
    approved_review_plan = root/'docs/plans/assurance-evidence-100-50-48h.md'
    approved_review_policy = root/'docs/implementation/assurance-evidence-master/approved-100-50-48h.json'
    post_review_plan = root/'docs/plans/assurance-evidence-post-review-repairs.md'
    recovery_audit_plan = root/'docs/plans/assurance-evidence-recovery-budget-review.md'
    c.write_text(directory/'audit.md', guarded_plan.read_text()+'\n'+current_review_plan.read_text()+'\n'+review_renewal_plan.read_text()+'\n'+approved_review_plan.read_text()+'\n'+post_review_plan.read_text()+'\n'+recovery_audit_plan.read_text())
    frozen = directory/'frozen'
    hashes = c.code_material(root)
    hashes['pyproject.toml'] = raw_digest((root/'pyproject.toml').read_bytes())
    for name in hashes:
        target = frozen/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    program_defs = work/'programs/task-definitions-repaired-v2.json'
    preflight_tasks = c.read(work/'initial-tasks.json') + (c.read(program_defs) if program_defs.exists() else program_tasks(root))
    sizes = [{'task':t['id'], 'bytes':len(canonical(protocol.transport(t)[0]))} for t in preflight_tasks]
    c.save(directory/'preflight.json', sizes)
    argv = [str(root/'.venv/bin/python'), '-m', 'pytest', '-q', *TESTS]
    env = {**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1',
           'PYTHONPATH':str(frozen/'src')+os.pathsep+str(frozen/'scripts')}
    with (directory/'tests.log').open('w') as stream:
        ran = subprocess.run(argv,cwd=frozen,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
    manifest = {'status':'REPAIR_VALIDATED' if ran.returncode==0 else 'REPAIR_REJECTED',
        'created_at':c.now(),'frozen_root':str(frozen.relative_to(root)),'code_hashes':hashes,
        'references':[c.receipt(p,root) for p in (root/PLAN,root/POLICY,diagnostic_plan,recovery_plan,guarded_plan,current_review_plan,review_renewal_plan,approved_review_plan,approved_review_policy,post_review_plan,recovery_audit_plan,operations_policy,operations_rules,work/'authorization.json',work/'initial-tasks.json',directory/'tests.log',directory/'preflight.json',directory/'audit.md')],
        'command':PREFIX+['extend'],'test_command':argv,'environment':str(root/'.venv'),
        'cpu_only':True,'gpu_hidden':True,'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'source_version':'Protected 95-call checkpoint and retained publisher bytes',
        'seeds':'N/A deterministic local checks; remote generation uncontrolled','plan':str(PLAN),
        'result':str(RUN/'final-result.json'),'test_exit_code':ran.returncode}
    immutable(directory/'manifest.json',manifest)
    if ran.returncode:
        return {'status':manifest['status'],'tests':(directory/'tests.log').read_text()[-9000:]}
    c.save(work/'active-revision.json',{'receipt':c.receipt(directory/'manifest.json',root)})
    refresh(root,'Supplemental audit, frozen tests and actual initial packets passed')
    return {'status':manifest['status'],'preflight':sizes,'tests':(directory/'tests.log').read_text()[-2000:],'allowance':status(root)['allowance']}


def verify(root):
    old.verify(root)
    Allowance(root).verify()
    m = c.read(c.checked(c.read(root/RUN/'active-revision.json')['receipt'],root))
    if m['status'] != 'REPAIR_VALIDATED':
        c.fail('E_INTEGRITY','Supplemental revision not validated')
    for ref in m['references']:
        c.checked(ref,root)
    for name,sha in m['code_hashes'].items():
        if raw_digest((root/m['frozen_root']/name).read_bytes()) != sha:
            c.fail('E_INTEGRITY','Supplemental frozen code changed: '+name)
    rt = engine()
    calls = {r['slot']:r for r in Allowance(root).ledger()}
    for row in rt.task_rows(root):
        task = c.read(root/RUN/'tasks'/row['task']/f"attempt-{row['attempt']:02}"/'task.json')
        wire,schema,reverse = protocol.transport(task)
        call = calls.get(row.get('allowance_slot'))
        if call:
            if call['task'] != row['task'] or call['request_hash'] != digest(wire):
                c.fail('E_INTEGRITY','Supplemental response detached from reservation')
            folder = rt.provider_folder(root,call,wire,schema)
            if row['status']=='VALIDATED' and (folder is None or protocol.validate(c.read(folder/'result.json'),task,reverse) != row['value']):
                c.fail('E_INTEGRITY','Accepted supplemental response changed')
        elif row['status']=='VALIDATED':
            c.fail('E_INTEGRITY','Accepted supplemental response without reservation')
    for phase in rt.state(root)['phases'].values():
        record = c.read(c.checked(phase['result'],root))
        for ref in record['files']:
            c.checked(ref,root)
    completion = root/RUN/'checks-current-v2/completion-receipt.json'
    if completion.exists():
        for ref in c.read(completion)['files']:
            c.checked(ref, root)
    return m


def run_task(root,task):
    rt = engine()
    saved_correction = root/RUN/'tasks'/task['id']/'attempt-02/task.json'
    if saved_correction.exists() and (saved_correction.parent/'result.json').exists():
        row = rt.attempt(root, c.read(saved_correction), number=2)
        if row['status'] == 'VALIDATED':
            return row
    saved_first = root/RUN/'tasks'/task['id']/'attempt-01/result.json'
    if saved_first.exists() and c.read(saved_first)['status'] == 'VALIDATED':
        return rt.attempt(root, task)
    if rt.consecutive_failures(root)>=2:
        c.fail('E_DEPENDENCY','Two consecutive provider failures; route repair required')
    row = rt.attempt(root,task)
    if (row['status']!='VALIDATED' and row.get('allowance_slot') and row.get('error') in ('E_REFERENCE','E_SCHEMA','E_UNSUPPORTED_PROFILE') and rt.consecutive_failures(root)<2 and Allowance(root).verify()['repair_remaining']>0):
        refresh(root,'Exact validator repair triggered: '+task['id'])
        correction = dict(row)
        if task['request'].get('kind') == 'formal_repair':
            correction['rejected_value'] = None
            correction['details'] = str(row.get('details',''))[:1800] + ' Full rejected response is retained in the attempt receipt; reconstruct only the requested selected readings.'
        row = rt.attempt(root,task,number=2,correction=correction)
    refresh(root,'Task completed or retained as failed: '+task['id'])
    a = Allowance(root).verify()
    master.output({'task':task['id'],'status':row['status'],'error':row.get('error'),'new_calls':a['used'],'repairs':a['repair_calls']})
    if rt.consecutive_failures(root)>=2:
        c.fail('E_DEPENDENCY','Two consecutive provider failures; no further dispatch')
    return row


def program_tasks(root):
    # Build bounded repairs only for challenged readings with existing programs.
    by_role = {role: [] for role in c.ROLES}
    skipped = []
    spending = Allowance(root).verify()['new_issue_spending']
    for row in accepted_rows(root):
        if 'reading_updates' not in row['value']:
            continue
        base = RUN if (row.get('allowance_slot') or 0)>BASELINE else old.RUN
        original = c.read(root/base/'tasks'/row['task']/f"attempt-{row['attempt']:02}"/'task.json')
        for update in row['value']['reading_updates']:
            cid = update['reading_id']
            if update['disposition'] != 'CHALLENGED' or not update['required_program_repairs']:
                continue
            prior = original['request']['prior_assessments'][cid]
            issue = 'reading.'+cid+'.'+row['role']
            if prior.get('formalization') is None:
                skipped.append({'reading_id': cid, 'role': row['role'], 'status': 'RETAIN_UNFORMALIZED',
                    'reason': 'Concrete repair text is retained as a future formalization condition; no existing program can be repaired.',
                    'required_program_repairs': update['required_program_repairs']})
                continue
            by_role[row['role']].append({'row': row, 'original': original, 'update': update, 'reading_id': cid})
    immutable(root/RUN/'programs/skipped.json', skipped)
    tasks = []
    for role, entries in by_role.items():
        for offset in range(0, len(entries), 3):
            batch = entries[offset:offset+3]
            selected = [entry['reading_id'] for entry in batch]
            first = deepcopy(batch[0]['original'])
            request = first['request']
            request['selected'] = selected
            request['readings'] = {cid: entry['original']['request']['readings'][cid] for cid, entry in zip(selected, batch)}
            request['questions'] = {cid: entry['original']['request']['questions'][cid] for cid, entry in zip(selected, batch)}
            request['prior_assessments'] = {cid: entry['original']['request']['prior_assessments'][cid] for cid, entry in zip(selected, batch)}
            request['reading_hashes'] = {cid: entry['original']['request']['reading_hashes'][cid] for cid, entry in zip(selected, batch)}
            request['concrete_repairs'] = [entry['update'] for entry in batch]
            combined = {'id': first['id'], 'phase': first['phase'], 'role': role, 'issues': [], 'request': request}
            response = {'value': {'reading_updates': [entry['update'] for entry in batch]}}
            task = phases.formal_repair_task(root, combined, response)
            task['id'] = 'program-repair-v4.'+role+'.'+digest(selected)[:16]
            task['phase'], task['program_repair'] = 'propagation', True
            task['issues'] = ['reading.'+cid+'.'+role for cid in selected]
            task['request']['scope'] = 'Concrete repair under the additional grant; preserve every unresolved legal prerequisite.'
            task['request']['reading_hashes'] = {cid: commitment(task['request']['readings'][cid]) for cid in selected}
            task['request']['instructions'] += (' Repair only these selected canonical readings. '
                'Preserve every supplied assumption and unresolved question; do not add related readings.')
            task['request'].pop('binding_hash')
            task['request']['binding_hash'] = digest(task['request'])
            tasks.append(explicit_contract(task))
    immutable(root/RUN/'programs/scheduled-skip.json', skipped)
    return tasks


def checks(root):
    if coverage(root)[1]:
        c.fail('E_REFERENCE','Incomplete combined coverage blocks runtime and final checks')
    work = root/RUN/'checks'
    work.mkdir(exist_ok=True)
    rows = [{**r,'phase':'P3' if r['phase']=='propagation' else r['phase']} for r in accepted_rows(root)]
    evidence,detail = phases.propagate_and_check(root,work,rows)
    runtime = phases.runtime_checks(root,work,evidence)
    value = {'propagation':detail,'runtime':runtime,'production_release':False,'original_obligations_open':46}
    immutable(work/'result.json',value)
    if detail['missing_reading_dispositions'] or runtime['expression_statuses'].get('BLOCKED'):
        c.fail('E_REFERENCE','Missing dispositions or blocked conditional expression checks')
    return value


def final_tasks(root):
    from assurance_evidence_completion import final_tasks as build
    return build(root, sys.modules[__name__])


def phase_done(root,phase,data):
    work = root/RUN/phase
    work.mkdir(exist_ok=True)
    immutable(work/'phase-result.json',{'phase':phase,'data':data,'files':master.files_in(work,root,('phase-result.json',))})
    current = engine().state(root)
    current['phases'][phase] = {'status':'COMPLETED','result':c.receipt(work/'phase-result.json',root)}
    c.save(root/RUN/'state.json',current)
    refresh(root,phase+' completed; next phase regenerated from retained results')


def recover_orphan_reservations(root):
    # A killed stream can leave a counted reservation without result.json.
    # Record that charged attempt as an interrupted dependency failure; never replay it.
    work = root/RUN
    rows = []
    ledger = Allowance(root).ledger()
    for call in ledger:
        task_dir = work/'tasks'/call['task']
        matched = []
        for directory in sorted(task_dir.glob('attempt-*')):
            request = directory/'request.json'
            if request.exists():
                try:
                    if digest(c.read(request)) == call['request_hash']:
                        matched.append(directory)
                except Exception:
                    pass
        if len(matched) != 1:
            continue
        directory = matched[0]
        result_path = directory/'result.json'
        if result_path.exists():
            continue
        task = c.read(directory/'task.json')
        wire = c.read(directory/'request.json')
        retained = engine().provider_folder(root, call, wire, c.read(directory/'schema.json'))
        if retained is not None and (retained/'result.json').exists():
            engine().attempt(root, task, number=int(directory.name.split('-')[-1]),
                provider_factory=lambda **kw: c.fail('E_INTEGRITY','Offline recovery cannot dispatch'))
            rows.append({'slot': call['slot'], 'task': call['task'], 'status': 'RECOVERED_PROVIDER_OUTPUT'})
            continue
        row = {'task': task['id'], 'phase': task['phase'], 'role': task['role'], 'issues': task['issues'],
            'attempt': int(directory.name.split('-')[-1]), 'request_hash': digest(wire),
            'request_bytes': len(canonical(wire)), 'started_at': call['issued_at'], 'ended_at': c.now(),
            'allowance_slot': call['slot'], 'status': 'FAILED', 'error': 'E_DEPENDENCY',
            'details': 'Reservation was charged but the controller stream ended before a result was written; provider evidence is retained and this attempt is not replayed.',
            'interrupted_reservation': True}
        c.save(result_path, row)
        c.save(directory/'receipt.json', {'files': master.files_in(directory, root, ('receipt.json',))})
        rows.append({'slot': call['slot'], 'task': call['task'], 'status': 'RECOVERED_INTERRUPTED'})
    if rows:
        immutable(work/'orphan-recovery-history'/f'{digest(rows)[:20]}.json', rows)
    return rows


def result(root,began=None):
    if ((root/RUN/'final/task-definitions.json').exists()
            and all(engine().state(root)['phases'].get(p, {}).get('status') == 'COMPLETED' for p in PHASES)
            and (root/RUN/'current-diagnostic.json').exists()):
        from assurance_evidence_guarded import execute as guarded_repair
        guarded_repair(root, sys.modules[__name__])
        from assurance_evidence_current_review import prepare as prepare_current_review
        prepare_current_review(root, sys.modules[__name__])
        from assurance_evidence_post_review import execute as repair_after_review
        repair_after_review(root, sys.modules[__name__])
        from assurance_evidence_next_phase import execute as prepare_recovery
        prepare_recovery(root, sys.modules[__name__])
    report = status(root)
    charged = {r['slot'] for r in Allowance(root).ledger()}
    slots = [r['allowance_slot'] for r in engine().task_rows(root) if r.get('allowance_slot')]
    if len(slots)!=len(set(slots)) or set(slots)!=charged:
        c.fail('E_INTEGRITY','Supplemental charged calls not fully accounted')
    finals = [r for r in accepted_rows(root) if r['phase']=='final']
    findings = [{'task':r['task'],'role':r['role'],**f} for r in finals for f in r['value']['findings']]
    defs = root/RUN/'final/task-definitions.json'
    expected = {t['id'] for t in c.read(defs)} if defs.exists() else set()
    ok = bool(expected) and {r['task'] for r in finals}==expected and all(f['status']=='SUPPORTED_UNDER_STATED_SCOPE' and f['original_question_answered'] for f in findings)
    report.update(status='HALTED_SUPPLEMENT' if report['state']['halt'] else 'EXECUTED_WITH_OPEN_EVIDENCE',
        completed_at=c.now(),wall_seconds=round(time.monotonic()-began,3) if began is not None else None,
        unaccounted_slots=[],final_review_findings=findings,final_review_acceptance='ACCEPTED_WITHIN_SCOPE' if ok else 'OPEN_OR_UNACCEPTED',
        closed_original_obligations=0,legal_correctness='NOT_ESTABLISHED')
    review = report.get('current_review')
    if review and 'state' in review:
        report['unaccounted_slots'] = review['unaccounted_slots']
        if review['state']['halt']:
            report['status'] = 'HALTED_CURRENT_REVIEW'
    diagnostic = report['current_diagnostic']
    checkpath = (c.checked(diagnostic['result'],root) if diagnostic else
        root/RUN/('checks-current-v2/result.json' if (root/RUN/'checks-current-v2/result.json').exists() else 'checks/result.json'))
    report['checks'] = c.read(checkpath) if checkpath.exists() else None
    report['checks_source'] = str(checkpath.relative_to(root))
    if diagnostic:
        report['checks_stale_v2'] = c.read(root/RUN/'checks-current-v2/result.json')
        report['checks_comparison'] = diagnostic['comparison']
        report['diagnostic_run_manifest'] = diagnostic['comparison']
        report['final_review_evidence_scope'] = diagnostic['final_review_scope']
        report['final_review_acceptance'] = 'OPEN_OR_UNACCEPTED'
    inventory = checkpath.parent/'program-inventory.json'
    if inventory.exists():
        report['program_inventory_statuses'] = dict(Counter(x['status'] for x in c.read(inventory)))
        report['remaining_program_findings'] = [x for x in c.read(inventory) if x['required_program_repairs']]
    report['repair_calls_exhausted'] = report['allowance']['repair_remaining'] == 0
    report['next_justified_actions'] = ['Retain the current verified diagnostic on every restart.',
        'Retain unaccepted findings and unresolved program challenges; use the current approved review limits and saved next-phase plan.',
        'Resolve dated authority, interpretation and actual case facts; all 46 original obligations remain open.']
    c.save(root/RUN/'final-result.json',report)
    a = report['allowance']
    note = (f"# Supplemental execution result\n\n{report['status']}. Fresh calls {a['used']}/100; repairs {a['repair_calls']}/{a.get('repair_maximum', 20)}; combined charged {a['combined_used']}. "
        f"Five old calls remain unused and separate.\n\nReviews {report['accepted_reading_reviews']}/70; scope corrections {report['scope_corrections']}/4. "
        f"Final acceptance: {report['final_review_acceptance']}. All 46 original obligations remain open.\n\n"
        '| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |\n|---|---|---|---|---|---|\n'
        f"| Retain validated evidence | Exact coverage, receipts and checks | {report['state']['halt'] or report['final_review_acceptance']} | Authority dates, meaning, facts | Saved next phase and findings | Legal correctness or release |\n\n"
        '| Inference status | Finding |\n|---|---|\n| Hard veto | Invalid responses excluded; unresolved prerequisites retained |\n'
        '| Statistically supported ranking | None |\n| Descriptive only | Counts and conditional checks |\n| Default readiness | No change |\n| Next evidence | Dated authority, interpretation and case records |\n\n'
        'Post-run red-team: complete responses and finite truth tables do not establish source entailment. Applicable contrary authority or actual case records can overturn conditional results.\n')
    note += '\n'+diagnostic_note(report)+'\n'+recovery_note(report)
    c.write_text(root/RUN/'execution-result.md',note)
    c.write_text(root/'docs/implementation/assurance-evidence-master/reset-memo.md',
        '# Recovery memo\n\nActive run: '+str(RUN)+'. Read final-result.json and next-phase-plan.md.\n\n'+
        f"New calls {a['used']}/100; repairs {a['repair_calls']}/{a.get('repair_maximum', 20)}; combined {a['combined_used']}. "
        'Resume `.venv/bin/python scripts/assurance_evidence_master.py ops-run`. Old grants are immutable.\n\n'+
        diagnostic_note(report)+'\nContinue only within the recorded current-review authorization and phase plan. '
        'Local checks remain available.\n\n'+recovery_note(report))
    refresh(root,'Result, open findings and next-phase checkpoint saved')
    return report


def run(root):
    began = time.monotonic()
    recover_orphan_reservations(root)
    verify(root)
    rt = engine()
    current = rt.state(root)
    if current['halt']:
        stop = current['halt']
        detail = stop.get('details','') if isinstance(stop,dict) else str(stop)
        if isinstance(stop,dict) and stop.get('error') == 'E_RESOURCE_LIMIT' and 'Actual propagation packet' in detail:
            immutable(root/RUN/'recovery-history'/'packet-size-stop.json', stop)
            current['halt'] = None
            current['repair_reason'] = 'Corrected merged repair hashes and compacted validator corrections; interrupted reservation retained.'
            c.save(root/RUN/'state.json', current)
        elif isinstance(stop,dict) and stop.get('error') == 'E_RESOURCE_LIMIT' and 'Actual final packet' in detail:
            from assurance_evidence_completion import checked_candidates
            checked_candidates(root, sys.modules[__name__])
            definitions = root/RUN/'final/task-definitions.json'
            tasks = final_tasks(root)
            immutable(definitions, tasks)
            immutable(root/RUN/'recovery-history/final-size-stop.json', stop)
            current['halt'] = None
            current['repair_reason'] = 'Full final packets partitioned by reading; challenged programs kept diagnostic and historical assumptions preserved. No new repair calls.'
            c.save(root/RUN/'state.json', current)
        else:
            return result(root,began)
    try:
        for phase in PHASES:
            if rt.state(root)['phases'].get(phase,{}).get('status')=='COMPLETED':
                continue
            refresh(root,phase+' starting after verified predecessor evidence')
            if phase=='checks':
                from assurance_evidence_completion import checked_candidates
                data = checked_candidates(root, sys.modules[__name__])
            else:
                if phase == 'programs':
                    path = root/RUN/phase/'task-definitions-repaired-v2.json'
                    frontier_path = root/RUN/phase/'frontier-repaired-v2.json'
                else:
                    path = root/RUN/phase/'task-definitions.json'
                    frontier_path = root/RUN/phase/'frontier.json'
                if path.exists():
                    tasks = c.read(path)
                else:
                    tasks = c.read(root/RUN/'initial-tasks.json') if phase=='reviews' else program_tasks(root) if phase=='programs' else final_tasks(root)
                    for task in tasks:
                        protocol.transport(task)
                    immutable(path,tasks)
                outcomes = []
                if phase == 'final':
                    for offset in range(0, len(tasks), 2):
                        if rt.consecutive_failures(root) >= 2:
                            c.fail('E_DEPENDENCY', 'Two consecutive provider failures veto further final calls')
                        batch = tasks[offset:offset+2]
                        # Each request is independent. Final calls do not consume
                        # repair reserve unless an actual corrective dispatch occurs.
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            futures = [pool.submit(rt.attempt, root, task) for task in batch]
                            results = [f.result() for f in futures]
                        outcomes += [{'task': task['id'], 'status': row['status'], 'receipt': row['receipt']} for task,row in zip(batch,results)]
                        c.save(frontier_path,outcomes)
                        refresh(root, 'Independent final audit batch saved; failed responses remain unaccepted')
                        master.output({'final_tasks_attempted':len(outcomes),'final_tasks_planned':len(tasks),
                            'statuses':[r['status'] for r in results],'allowance':status(root)['allowance']})
                        if rt.consecutive_failures(root) >= 2:
                            c.fail('E_DEPENDENCY','Two consecutive provider failures halt further final audits')
                else:
                    for task in tasks:
                        row = run_task(root,task)
                        outcomes.append({'task':task['id'],'status':row['status'],'receipt':row['receipt']})
                        c.save(frontier_path,outcomes)
                        if row['status']!='VALIDATED' and phase!='programs':
                            c.fail('E_REFERENCE','Required review remains unaccepted: '+task['id'])
                if not tasks:
                    c.save(frontier_path,[])
                data = {'outcomes':outcomes}
                if phase=='reviews' and (coverage(root)[1] or status(root)['scope_corrections']!=4):
                    c.fail('E_REFERENCE','Complete reading and scope coverage required')
            phase_done(root,phase,data)
    except (LegalMathError,ValueError,KeyError) as exc:
        current = rt.state(root)
        current['halt'] = {'error':getattr(exc,'code',type(exc).__name__),'details':str(getattr(exc,'details',exc))[:2500]}
        c.save(root/RUN/'state.json',current)
        refresh(root,'Dependent execution halted on a retained concrete failure')
    return result(root,began)


def entry(root,code,action):
    master.check_command(c.read(root/POLICY),PREFIX+[action])
    if action=='extend-status':
        master.output(status(root) if (root/RUN/'authorization.json').exists() else {'status':'NOT_STARTED'})
        return
    with (root/c.BASE/'.master.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if action in ('extend-preflight','extend-repair'):
            if action=='extend-preflight' and (root/RUN/'active-revision.json').exists():
                verify(root)
                master.output(status(root))
            else:
                master.output(activate(root))
            return
        m = verify(root)
        frozen = root/m['frozen_root']
        os.set_inheritable(lock.fileno(),True)
        env = {**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1',
               'PYTHONPATH':str(frozen/'src')+os.pathsep+str(frozen/'scripts'),'LEGALMATH_EXTENSION_LOCK':str(lock.fileno()), 'LEGALMATH_EXTENSION_ACTION':action}
        os.execve(root/'.venv/bin/python',[str(root/'.venv/bin/python'),str(frozen/'scripts/assurance_evidence_extension.py')],env)


if __name__=='__main__':
    root = Path('/home/chakwong/python/legalmath')
    try:
        os.fstat(int(os.environ.pop('LEGALMATH_EXTENSION_LOCK')))
        m = verify(root)
        if Path(__file__).resolve().parents[1] != (root/m['frozen_root']).resolve():
            c.fail('E_AUTHORITY','Supplement must execute its reviewed frozen snapshot')
        action = os.environ.pop('LEGALMATH_EXTENSION_ACTION', 'extend')
        if action == 'extend-diagnostic':
            from assurance_evidence_completion import offline_diagnostic
            master.output(offline_diagnostic(root, sys.modules[__name__]))
        elif action == 'extend':
            v = run(root)
            from assurance_evidence_review_runtime import run as review_current
            if review_current(root) is not None:
                v = result(root)
            master.output({k:v[k] for k in ('status','allowance','accepted_reading_reviews','scope_corrections','accepted_program_repair_tasks','accepted_final_review_tasks','final_review_acceptance','checks_source')})
        else:
            c.fail('E_AUTHORITY', 'Unknown frozen extension action')
    except Exception as exc:
        err = {'status':'STOPPED','error':getattr(exc,'code',type(exc).__name__),'details':str(getattr(exc,'details',exc))[:2500]}
        c.save(root/RUN/'current-stop.json',err)
        master.output(err)
        sys.exit(1)
