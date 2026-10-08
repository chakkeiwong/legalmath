"""Prepare lossless, bounded current-evidence review packets without spending."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import time

import assurance_evidence_core as c
import assurance_evidence_protocol as protocol
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError

PLAN = Path('docs/plans/assurance-evidence-current-review.md')
RENEWAL_PLAN = Path('docs/plans/assurance-evidence-current-review-renewal.md')
APPROVED_PLAN = Path('docs/plans/assurance-evidence-100-50-48h.md')
APPROVAL = Path('docs/implementation/assurance-evidence-master/approved-100-50-48h.json')
SUBDIR = Path('current-review')
PACKET_LIMIT = 180000


def delta(base, value, path=()):
    """Exact changes to a retained case, including deleted judgment values."""
    if isinstance(base, dict) and isinstance(value, dict):
        changes = [{'remove': list(path+(key,))} for key in base if key not in value]
        for key, item in value.items():
            changes += delta(base[key], item, path+(key,)) if key in base else [
                {'set': list(path+(key,)), 'value': item}]
        return changes
    return [] if base == value else [{'set': list(path), 'value': value}]


def restore(base, changes):
    value = deepcopy(base)
    for change in changes:
        path = change.get('set', change.get('remove'))
        if not path:
            value = deepcopy(change['value'])
            continue
        parent = value
        for key in path[:-1]:
            parent = parent[key]
        if 'remove' in change:
            del parent[path[-1]]
        else:
            parent[path[-1]] = deepcopy(change['value'])
    return value


def case_packet(row):
    base = row['checks'][0]['case']
    result_base = row['checks'][0]['result']
    checks = []
    for probe in row['checks']:
        changes = delta(base, probe['case'])
        if restore(base, changes) != probe['case']:
            c.fail('E_INTEGRITY', 'Case compression changed a diagnostic input')
        result_changes = delta(result_base, probe['result'])
        if restore(result_base, result_changes) != probe['result']:
            c.fail('E_INTEGRITY', 'Case compression changed a diagnostic result')
        checks.append({'case_id': probe['case_id'], 'changes': changes,
            'expected': probe['expected'], 'result_changes': result_changes})
    return {'case_base': base, 'result_base': result_base, 'checks': checks,
        'encoding': 'Apply each check changes/result_changes to fresh copies of case_base/result_base. set replaces the path; remove deletes the key. All actual inputs and results are retained losslessly.'}



def review_case_packet(row):
    names = {'no-sfc-request', 'defective-records-with-remediation',
        'approval-is-separate', 'adequate-outcome-without-retention', 'false-with-other-unknown'}
    selected = [probe for probe in row['checks'] if probe['case_id'] in names]
    if {probe['case_id'] for probe in selected} != names:
        c.fail('E_INTEGRITY', 'Missing a required supplied contrary case')
    return {'total_executed_cases': len(row['checks']),
        'outcome_counts': dict(Counter(probe['result']['status'] for probe in row['checks'])),
        'detailed_contrary_cases': case_packet({'checks': selected}),
        'scope': 'These five supplied contrary cases retain complete actual inputs and outputs. Other executed cases are represented only by aggregate counts. The full cases.json is retained under guard_completion; it is not supplied in this packet. Counts do not establish substantive correctness.'}

def rebind(task):
    task = deepcopy(task)
    task['request'].pop('binding_hash', None)
    task['request']['binding_hash'] = digest(task['request'])
    return task


def group_questions(rows):
    groups, index, positions = [], {}, []
    for row in rows:
        value = {key: item for key, item in row.items() if key != 'question_id'}
        key = digest(value)
        if key not in index:
            index[key] = len(groups)
            groups.append({'question_ids': [], 'shared_disposition': value})
        position = index[key]
        groups[position]['question_ids'].append(row['question_id'])
        positions.append([position, len(groups[position]['question_ids'])-1])
    decoded = [{**groups[i]['shared_disposition'], 'question_id': groups[i]['question_ids'][j]}
        for i, j in positions]
    if decoded != rows:
        c.fail('E_INTEGRITY', 'Question grouping changed a retained disposition')
    return {'groups': groups, 'original_order': positions,
        'encoding': 'For each original_order pair [group,index], use shared_disposition plus question_id=question_ids[index]. Every question and its complete disposition is preserved.'}


def bounded(items, build):
    # Bounded whole-reading packing; order has no legal meaning.
    groups = []
    for item in sorted(items, key=lambda v: len(canonical(v)), reverse=True):
        choices = []
        for i, chunk in enumerate(groups):
            if len(chunk) >= 4:
                continue
            try:
                task = build(chunk+[item], i+1)
                size = len(canonical(protocol.transport(task)[0]))
                if size <= PACKET_LIMIT:
                    choices.append((size, i))
            except LegalMathError as exc:
                if exc.code != 'E_RESOURCE_LIMIT':
                    raise
        if choices:
            groups[max(choices)[1]].append(item)
        else:
            task = build([item], len(groups)+1)
            if len(canonical(protocol.transport(task)[0])) > PACKET_LIMIT:
                c.fail('E_RESOURCE_LIMIT', 'Single complete reading exceeds correction headroom')
            groups.append([item])
    return [build(chunk, i+1) for i, chunk in enumerate(groups)]


def build(root, ex, manifest):
    work = root/ex.RUN
    definitions = c.read(work/'final/task-definitions.json')
    old_rows = ex.engine().task_rows(root)
    old_by_id = {t['id']: [r for r in old_rows if r['task'] == t['id']] for t in definitions}
    inventory = c.read(work/'checks-current-v3/program-inventory.json')
    checks = c.read(work/'checks-current-v3/result.json')
    from assurance_evidence_guarded import verify as verify_guards
    guard_ref = c.read(work/'current-guarded-repair.json')['receipt']
    verify_guards(root, guard_ref)
    guard_dir = (root/guard_ref['path']).parent
    programs = {(p['role'], p['reading_id']): p for p in c.read(guard_dir/'programs.json')}
    cases = {(p['role'], p['reading_id']): review_case_packet(p) for p in c.read(guard_dir/'cases.json')}
    frozen = root/manifest['frozen_root']
    common = {'checks_v3': checks, 'guard_result': c.read(guard_dir/'result.json'),
        'guard_completion': guard_ref, 'frozen_revision': c.read(work/'active-revision.json')['receipt'],
        'tests': (frozen.parent/'tests.log').read_text(), 'legal_correctness': 'NOT_ESTABLISHED',
        'limitations': 'All 46 original obligations remain open. Guard candidates are mechanical only. The finite cases do not validate supplied legal classifications. No current-evidence review has yet accepted them.'}
    controller_files = [
        'scripts/assurance_evidence_master.py', 'scripts/assurance_evidence_extension.py',
        'scripts/assurance_evidence_operations.py', 'scripts/assurance_evidence_review_runtime.py',
        'scripts/assurance_evidence_protocol.py']
    candidate_files = [
        'scripts/assurance_evidence_continuation.py', 'scripts/assurance_evidence_completion.py',
        'scripts/assurance_evidence_guarded.py', 'scripts/assurance_evidence_current_review.py',
        'scripts/assurance_evidence_next_phase.py']
    tasks, coverage = [], []
    for role in c.ROLES:
        previous = next(t for t in definitions if t['role'] == role and
            t['issues'] == ['final.engineering.'+role])
        for part, files in enumerate((controller_files, candidate_files), 1):
            units = [{'unit_id': 'engineering.file.'+str(i), 'text': (frozen/name).read_text()}
                for i, name in enumerate(files)]
            units.append({'unit_id': 'engineering.current', 'text': canonical(common).decode()})
            task = protocol.make_task('final', role, previous['issues'], {
                'kind': 'review', 'source_packet': {'units': units},
                'supplied_files': dict(zip((u['unit_id'] for u in units), [*files, 'current-results'])),
                'predecessors': {previous['id']: {'retained_responses_json': canonical(old_by_id[previous['id']]).decode()}},
                'questions': [{'id': 'current-engineering-'+str(part), 'missing':
                    'Audit the supplied current code and executed diagnostics for concrete engineering defects, including allowance preservation, frozen execution, restart, truthful reporting and conditional guard behavior. This question covers only the listed supplied files and current-results; other project files are outside this packet. Inspect interactions visible here and state dependencies you cannot check.'}],
                'instructions': 'Prior review prose is evidence about the old review, never published legal authority. Cite exact unique substrings from a supplied code or result unit. Keep concrete defects and unverified dependencies explicit. A supported finding approves only the declared engineering subset, never a substantive repair or legal obligation.'})
            task['id'] = 'current-review.engineering.'+role+'.'+str(part)
            task.update(counted_repair=True, predecessors=[previous['id']], review_phase='engineering')
            tasks.append(ex.explicit_contract(task))
        old_tasks = [t for t in definitions if t['role'] == role and 'result_under_review' in t['request']]
        source = old_tasks[0]['request']['source_packet']
        items = []
        for previous in old_tasks:
            if previous['request']['source_packet'] != source:
                c.fail('E_INTEGRITY', 'Disposition source packets differ')
            for item in previous['request']['result_under_review']:
                value = deepcopy(item)
                key = (previous['request']['reviewed_role'], item['reading']['reading_id'])
                value['current_status'] = next(i for i in inventory if (i['role'], i['reading_id']) == key)
                value['predecessor_task'] = previous['id']
                value['question_dispositions'] = group_questions(value.pop('questions'))
                if key in programs:
                    program = programs[key]
                    value['guarded_candidate'] = {k: v for k, v in program.items() if k != 'reading_or_prior_assessment'}
                    value['executed_cases'] = cases[key]
                items.append(value)
        def packet(chunk, part):
            predecessors = list(dict.fromkeys(v['predecessor_task'] for v in chunk))
            request = {'kind': 'review', 'source_packet': source,
                'reviewed_role': old_tasks[0]['request']['reviewed_role'],
                'result_under_review': chunk, 'current_engineering': {
                    'guard_result': common['guard_result'], 'guard_completion': guard_ref,
                    'scope': 'Complete controller and guard source is supplied in the engineering packets. This packet assesses dispositions and the stated conditional behavior; it does not independently audit code implementation.'},
                'predecessors': {key: {'retained_responses_json': canonical(old_by_id[key]).decode()} for key in predecessors},
                'questions': [{'id': 'current-reading.'+v['reading']['reading_id'], 'missing':
                    'Audit the complete supplied reading, original question texts, question and obligation dispositions, retained assumptions, candidate and any conditional guard for reading '+v['reading']['reading_id']+'. Name concrete unsupported interpretations, incorrect source-availability or applicability claims, or incomplete repairs. Assess whether the conditional behavior and stated open conditions are accurate; no original obligation is closed.'} for v in chunk],
                'instructions': 'Return one finding for every supplied reading question. Sources remain complete. All original assumptions, questions and required repairs remain operative. Quote only published source units; put code analysis and prior review commentary in answer or qualifications. Qualified or unresolved status requires original_question_answered=false.'}
            if any('guarded_candidate' in v for v in chunk):
                request['guard_code_scope'] = 'The complete guard module and test generator are supplied in engineering packet 2. This disposition packet preserves exact formulas and five complete contrary cases per guarded reading. It cannot independently approve implementation correctness.'
            task = protocol.make_task('final', role, ['final.dispositions.'+role], request)
            task['id'] = 'current-review.dispositions.'+role+'.'+str(part)
            task.update(counted_repair=True, predecessors=predecessors, review_phase='dispositions')
            return ex.explicit_contract(task)
        batch = bounded(items, packet)
        tasks += batch
        coverage += [{'task': t['id'], 'reviewer': role, 'role': t['request']['reviewed_role'],
            'reading_id': v['reading']['reading_id'], 'guarded': 'guarded_candidate' in v}
            for t in batch for v in t['request']['result_under_review']]
    expected = {(i['role'], i['reading_id']) for i in inventory}
    actual = [(i['role'], i['reading_id']) for i in coverage]
    if len(actual) != len(set(actual)) or set(actual) != expected or len(actual) != 70:
        c.fail('E_INTEGRITY', 'Current review lost or duplicated a reading')
    if {(i['role'], i['reading_id']) for i in coverage if i['guarded']} != set(programs) or len(programs) != 20:
        c.fail('E_INTEGRITY', 'Current review lost a guarded candidate')
    return tasks, coverage


def preflight(tasks, baseline):
    costs = Counter(i for t in tasks for i in t['issues'])
    initial = len(tasks)
    capacity = min(baseline['remaining']-2, 50-baseline['repair_calls'])
    corrections = max(0, min(initial, capacity-initial))
    scheduled = initial+corrections
    violations = []
    if initial > capacity:
        violations.append('Initial review coverage exceeds total or repair capacity')
    issue_worst = {}
    for issue, count in costs.items():
        issue_worst[issue] = baseline['new_issue_spending'].get(issue, 0)+count+min(count, corrections)
        if issue_worst[issue] > 50:
            violations.append('Cumulative canonical issue cap: '+issue)
    sizes = []
    for task in tasks:
        wire, _, _ = protocol.transport(task)
        size = len(canonical(wire))
        sizes.append({'task': task['id'], 'bytes': size, 'request_hash': digest(wire)})
        if size > PACKET_LIMIT:
            violations.append('Insufficient correction headroom: '+task['id'])
    return {'status': 'PREFLIGHT_BLOCKED' if violations else 'PREFLIGHT_PASSED',
        'violations': violations, 'tasks': sizes, 'packet_count': initial,
        'unconstrained_two_attempt_calls': 2*initial, 'shared_correction_maximum': corrections,
        'worst_case_calls': scheduled, 'maximum_bytes': max(r['bytes'] for r in sizes),
        'phase_tasks': dict(Counter(t['review_phase'] for t in tasks)),
        'cumulative_issue_worst_case': issue_worst,
        'provider_calls': 0, 'repair_calls': 0}


def verified(root, ex):
    pointer = root/ex.RUN/SUBDIR/'prepared.json'
    if not pointer.exists():
        return None
    ref = c.read(pointer)['receipt']
    path = c.checked(ref, root)
    parent = root/ex.RUN/SUBDIR/'packages'
    if not path.is_relative_to(parent.resolve()) or path.name != 'completion-receipt.json':
        c.fail('E_INTEGRITY', 'Current review receipt is outside its package directory')
    value = c.read(path)
    required = {'task-definitions.json', 'coverage.json', 'preflight.json', 'proposed-amendment.json', 'run-manifest.json'}
    covered = set()
    for entry in value['files']:
        file = c.checked(entry, root)
        if file.parent != path.parent:
            c.fail('E_INTEGRITY', 'Foreign current review output')
        covered.add(file.name)
    if not required <= covered:
        c.fail('E_INTEGRITY', 'Current review receipt omits required output')
    for entry in value['inputs']:
        c.checked(entry, root)
    return path.parent


def summary(root, ex):
    folder = verified(root, ex)
    if folder is None:
        return None
    pre = c.read(folder/'preflight.json')
    recorded = (root/ex.RUN/SUBDIR/'authorization.json').exists()
    return {'status': ('PREPARED_WITH_RECORDED_AUTHORIZATION' if recorded else 'PREPARED_AWAITING_NUMERICAL_APPROVAL') if pre['status'] == 'PREFLIGHT_PASSED' else pre['status'],
        'package': c.receipt(folder/'completion-receipt.json', root),
        'preflight': str((folder/'preflight.json').relative_to(root)),
        'packet_count': pre['packet_count'], 'worst_case_calls': pre['worst_case_calls'],
        'maximum_bytes': pre['maximum_bytes'], 'violations': pre['violations'],
        'authorization_recorded': recorded, 'dispatch_authorized': False,
        'dispatch_scope': 'Preparation does not decide dispatch; inspect current-review runtime status.',
        'prior_ends_at': c.read(folder/'proposed-amendment.json')['ends_at'],
        'prior_window_expired': c.now() >= c.read(folder/'proposed-amendment.json')['ends_at'],
        'requested_window_hours': 48}


def prepare(root, ex):
    started = time.monotonic()
    manifest = ex.verify(root)
    if Path(__file__).resolve().parents[1] != (root/manifest['frozen_root']).resolve():
        c.fail('E_AUTHORITY', 'Current review preparation must execute frozen code')
    work = root/ex.RUN
    if (work/SUBDIR/'authorization.json').exists():
        verified(root, ex)
        return summary(root, ex)
    baseline = ex.Allowance(root).verify()
    refs = [c.read(work/name)['receipt'] for name in ('active-revision.json', 'current-guarded-repair.json', 'current-diagnostic.json')]
    refs += [c.receipt(path, root) for path in (root/PLAN, root/RENEWAL_PLAN, root/APPROVED_PLAN, root/APPROVAL, work/'allowance.json',
        work/'authorization.json', work/'final/task-definitions.json', work/'checks-current-v3/completion-receipt.json')]
    refs += [r['receipt'] for r in ex.engine().task_rows(root)]
    folder = work/SUBDIR/'packages'/digest(refs)[:24]
    if (work/SUBDIR/'authorization.json').exists() and verified(root, ex) != folder.resolve():
        c.fail('E_AUTHORITY', 'Approved review is bound to its original frozen inputs')
    receipt = folder/'completion-receipt.json'
    if not receipt.exists():
        from legalmath.interpretation.search.providers import CodexProvider
        complete, reserve = CodexProvider.complete, ex.Allowance.reserve
        def forbidden(*args, **kwargs):
            c.fail('E_AUTHORITY', 'Review preparation cannot dispatch or reserve calls')
        CodexProvider.complete, ex.Allowance.reserve = forbidden, forbidden
        try:
            tasks, coverage = build(root, ex, manifest)
            pre = preflight(tasks, baseline)
            for name, value in [('task-definitions.json', tasks), ('coverage.json', coverage), ('preflight.json', pre)]:
                ex.immutable(folder/name, value)
            proposal = {'status': 'PROPOSED_NOT_APPROVED', 'requested_window_hours': 48, 'maximum': 100, 'repair_maximum': 50,
                'final_disposition_limit': 50, 'other_final_issue_limit': 50, 'attempts_per_task': 2,
                'ends_at': baseline['ends_at'], 'baseline': baseline,
                'baseline_calls': ex.Allowance(root).ledger(),
                'old_unused_calls_carried': 0, 'count_all_current_review_calls_as_repairs': True,
                'tasks': c.receipt(folder/'task-definitions.json', root),
                'preflight': c.receipt(folder/'preflight.json', root),
                'plan': c.receipt(root/PLAN, root), 'renewal_plan': c.receipt(root/RENEWAL_PLAN, root),
                'approved_plan': c.receipt(root/APPROVED_PLAN, root), 'approval': c.receipt(root/APPROVAL, root)}
            ex.immutable(folder/'proposed-amendment.json', proposal)
            run = {'command': ex.PREFIX+['ops-run'], 'git_commit': manifest['git_commit'],
                'environment': str(root/'.venv'), 'cpu_only': True,
                'gpu_hidden': os.environ.get('CUDA_VISIBLE_DEVICES') == '-1',
                'seeds': 'N/A: deterministic request preparation, no model calls',
                'data_version': refs, 'frozen_root': manifest['frozen_root'], 'plan': str(PLAN),
                'result': str((folder/'preflight.json').relative_to(root)),
                'provider_calls': 0, 'wall_seconds': round(time.monotonic()-started, 3)}
            if (folder/'run-manifest.json').exists():
                run['wall_seconds'] = c.read(folder/'run-manifest.json')['wall_seconds']
            ex.immutable(folder/'run-manifest.json', run)
            ex.immutable(receipt, {'inputs': refs, 'files': ex.master.files_in(folder, root, ('completion-receipt.json',))})
        finally:
            CodexProvider.complete, ex.Allowance.reserve = complete, reserve
    if ex.Allowance(root).verify() != baseline:
        c.fail('E_INTEGRITY', 'Review preparation changed spending')
    c.save(work/SUBDIR/'prepared.json', {'receipt': c.receipt(receipt, root)})
    if c.read(folder/'preflight.json')['status'] == 'PREFLIGHT_PASSED':
        approval = c.read(root/APPROVAL)
        if (approval['approval_text'] != 'you have 100 celing and limits 50 with 48 hour window.  continue'
                or approval['status'] != 'APPROVED_BY_USER'):
            c.fail('E_AUTHORITY', 'Current continuation approval text changed')
        ex.immutable(work/SUBDIR/'authorization.json', {**approval,
            'approval_source': c.receipt(root/APPROVAL, root),
            'proposal': c.receipt(folder/'proposed-amendment.json', root),
            'prepared': c.receipt(receipt, root)})
    return summary(root, ex)
