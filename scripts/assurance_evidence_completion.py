"""Complete bounded diagnostics and final audits without promoting challenged repairs."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
import time

import assurance_evidence_core as c
import assurance_evidence_phases as phases
import assurance_evidence_protocol as protocol
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError


def preserve_history(prior, proposed):
    value = deepcopy(proposed)
    for key in ('added_assumptions', 'unresolved_questions'):
        value[key] = list(dict.fromkeys([*prior[key], *proposed[key]]))
    return value


def checked_candidates(root, ex, diagnostic_dir='checks-current-v2'):
    """Build or replay a named offline diagnostic directory."""
    directory = Path(diagnostic_dir)
    if (not diagnostic_dir or directory.name != diagnostic_dir or
            diagnostic_dir in {'.', '..'}):
        c.fail('E_AUTHORITY', 'Diagnostic directory must be one fixed relative name')
    work = root/ex.RUN/diagnostic_dir
    receipt = work/'completion-receipt.json'
    if receipt.exists():
        verify_completion(root, work)
        return c.read(work/'result.json')
    propagation, missing = ex.coverage(root)
    if missing:
        c.fail('E_REFERENCE', 'Complete reading coverage required for diagnostic replay')
    ctx = phases.context(root)
    prior = c.read(root/c.OLD/'assessment-evidence.json')
    proposed = {(row['role'], a['reading_id']): (a, row['receipt'])
        for row in ex.accepted_rows(root) for a in row['value'].get('assessments', [])}
    evidence, inventory, questions, obligations = [], [], [], []
    for row in propagation:
        role = row['role']
        questions += [{**q, 'role': role, 'receipt': row['receipt']} for q in row['value']['question_updates']]
        obligations += [{**q, 'role': role, 'receipt': row['receipt']} for q in row['value']['obligation_updates']]
        for update in row['value']['reading_updates']:
            cid = update['reading_id']
            baseline = prior[role][cid]
            candidate = proposed.get((role, cid))
            entry = {'role': role, 'reading_id': cid, 'review_disposition': update['disposition'],
                'required_program_repairs': update['required_program_repairs'], 'review_receipt': row['receipt'],
                'baseline_program_present': baseline['formalization'] is not None,
                'candidate_response_validated': candidate is not None,
                'candidate_disposition': candidate[0]['disposition'] if candidate else None,
                'repair_accepted': False, 'production_release': False}
            if candidate:
                current = preserve_history(baseline, candidate[0])
                entry.update(status='CANDIDATE_DIAGNOSTIC_ONLY', candidate_receipt=candidate[1],
                    retained_prior_assumptions=baseline['added_assumptions'],
                    retained_prior_questions=baseline['unresolved_questions'])
            elif baseline['formalization'] is None:
                current = deepcopy(baseline)
                entry['status'] = 'UNFORMALIZED_WITH_OPEN_CONDITIONS'
            elif update['disposition'] == 'CHALLENGED':
                entry['status'] = 'EXCLUDED_UNREPAIRED_PROGRAM'
                inventory.append(entry)
                continue
            else:
                current = deepcopy(baseline)
                entry['status'] = 'RETAINED_CONDITIONAL_PROGRAM'
            current['added_assumptions'] = list(dict.fromkeys([*current['added_assumptions'], *update['added_assumptions']]))
            current['unresolved_questions'] = list(dict.fromkeys([*current['unresolved_questions'],
                *update['remaining_questions'], *update['required_program_repairs']]))
            formal = phases.repair.formal_evidence(ctx['packet'], ctx['candidates'][cid], ctx['questions'][cid], current)
            evidence.append({'role': role, 'reading_id': cid, 'update': update, **formal,
                'diagnostic_scope': entry['status'], 'repair_accepted': False})
            entry['certificate_status'] = formal['certificate']['status']
            entry['conditional_program_hash'] = digest(formal['derived_reading']['formalization'])
            inventory.append(entry)
    if len(inventory) != 70 or len({(r['role'], r['reading_id']) for r in inventory}) != 70:
        c.fail('E_INTEGRITY', 'Current evidence inventory must retain all 70 reading/role dispositions')
    for name, value in [('formal-evidence.json', evidence), ('program-inventory.json', inventory),
            ('question-dispositions.json', questions), ('obligation-dispositions.json', obligations)]:
        ex.immutable(work/name, value)
    runtime = phases.runtime_checks(root, work, evidence)
    # The inherited bridge experiment uses predecessor programs. Its role remains
    # explanatory baseline evidence; it is not a check of changed candidate programs.
    bridge = phases.bridge_checks(root, work)
    result = {'propagation': {'missing_reading_dispositions': [],
        'formal_statuses': dict(Counter(e['certificate']['status'] for e in evidence)),
        'question_updates': len(questions), 'availability_updates': sum(q['status']=='SOURCE_NOW_AVAILABLE' for q in questions),
        'conditional_bridge': {**bridge, 'scope': 'UNCHANGED_PREDECESSOR_PROGRAMS_ONLY', 'candidate_promotion': False}},
        'runtime': runtime, 'inventory_statuses': dict(Counter(x['status'] for x in inventory)),
        'validated_candidate_assessments': len(proposed), 'accepted_repairs': 0,
        'original_obligations_open': 46, 'production_release': False,
        'interpretation': 'Candidate programs remain CHALLENGED. Finite/native/Java checks establish only conditional computation under supplied judgments. Preserved original assumptions and questions are unioned explicitly; raw model responses are unchanged.'}
    if runtime['expression_statuses'].get('BLOCKED'):
        c.fail('E_REFERENCE', 'A current conditional expression check failed')
    ex.immutable(work/'result.json', result)
    ex.immutable(receipt, {'files': ex.master.files_in(work, root, ('completion-receipt.json',))})
    return result



def verify_completion(root, work):
    receipt = c.read(work/'completion-receipt.json')
    covered = set()
    for ref in receipt['files']:
        path = c.checked(ref, root)
        if not path.is_relative_to(work.resolve()):
            c.fail('E_INTEGRITY', 'Foreign diagnostic completion file')
        covered.add(path)
    required = {work/name for name in ('result.json', 'program-inventory.json',
        'runtime-summary.json', 'formal-evidence.json', 'question-dispositions.json',
        'obligation-dispositions.json', 'conditional-bridge-checks.json')}
    if not {p.resolve() for p in required} <= covered:
        c.fail('E_INTEGRITY', 'Diagnostic completion receipt omits required evidence')


def check_historical_allowance(root, ex, report, ref):
    """Bind the old projection to its journal prefix, allowing later spending."""
    allowance = ex.Allowance(root)
    allowance.verify()
    before, after = report['allowance_before'], report['allowance_after']
    count = before['used']
    calls = allowance.ledger()
    if (before != after or report['provider_calls'] != 0 or report['repair_calls'] != 0
            or type(count) is not int or not 0 <= count <= len(calls)):
        c.fail('E_INTEGRITY', 'Invalid historical diagnostic allowance checkpoint')
    checkpoint = {'authorization_hash': raw_digest(allowance.grant_bytes), 'calls': calls[:count]}
    encoded = (json.dumps(checkpoint, indent=2, ensure_ascii=False)+'\n').encode()
    if raw_digest(encoded) != ref['sha256']:
        c.fail('E_INTEGRITY', 'Historical diagnostic reservation prefix changed')


def adopted_diagnostic(root, ex):
    pointer = root/ex.RUN/'current-diagnostic.json'
    if not pointer.exists():
        return None
    ref = c.read(pointer)['receipt']
    if ref['path'] != str(ex.RUN/'diagnostic-refresh/report.json'):
        c.fail('E_INTEGRITY', 'Unexpected current diagnostic report')
    report = c.read(c.checked(ref, root))
    for item in report['references']:
        if item['path'] == str(ex.RUN/'allowance.json'):
            check_historical_allowance(root, ex, report, item)
        else:
            c.checked(item, root)
    for name in ('checks-current-v2', 'checks-current-v3'):
        verify_completion(root, root/ex.RUN/name)
    for name, dirname in (('baseline', 'checks-current-v2'), ('current', 'checks-current-v3')):
        expected = c.receipt(root/ex.RUN/dirname/'result.json', root)
        if report[name] != expected or expected not in report['references']:
            c.fail('E_INTEGRITY', 'Current diagnostic is detached from its checked result')
    return report


def offline_diagnostic(root, ex):
    """Verify retained v3 and persist its selection; never invoke a provider."""
    began = time.monotonic()
    manifest = ex.verify(root)
    frozen = root/manifest['frozen_root']
    if Path(__file__).resolve().parents[1] != frozen.resolve():
        c.fail('E_AUTHORITY', 'Diagnostic must execute the reviewed frozen snapshot')
    directory = root/ex.RUN/'diagnostic-refresh'
    directory.mkdir(exist_ok=True)
    before = ex.Allowance(root).verify()
    reservations = ex.master.files_in(root/ex.RUN/'reservations', root)
    allowance = c.receipt(root/ex.RUN/'allowance.json', root)
    def forbidden(*args, **kwargs):
        c.fail('E_AUTHORITY', 'Offline diagnostic cannot dispatch or reserve calls')
    from legalmath.interpretation.search.providers import CodexProvider
    original_complete, original_reserve = CodexProvider.complete, ex.Allowance.reserve
    CodexProvider.complete, ex.Allowance.reserve = forbidden, forbidden
    try:
        prior = adopted_diagnostic(root, ex)
        if prior is None:
            report_path = directory/'report.json'
            if report_path.exists():
                ex.immutable(root/ex.RUN/'current-diagnostic.json',
                    {'receipt': c.receipt(report_path, root)})
                prior = adopted_diagnostic(root, ex)
            else:
                baseline_dir = root/ex.RUN/'checks-current-v2'
                current_dir = root/ex.RUN/'checks-current-v3'
                if not (current_dir/'completion-receipt.json').exists():
                    c.fail('E_REFERENCE', 'This bounded action verifies the already completed v3 replay')
                for work in (baseline_dir, current_dir):
                    verify_completion(root, work)
                baseline, current = (c.read(work/'result.json') for work in (baseline_dir, current_dir))
                retained = ('formal-evidence.json', 'program-inventory.json',
                    'question-dispositions.json', 'obligation-dispositions.json',
                    'conditional-bridge-checks.json')
                unchanged = {}
                for name in retained:
                    left, right = baseline_dir/name, current_dir/name
                    if left.read_bytes() != right.read_bytes():
                        c.fail('E_INTEGRITY', 'Diagnostic replay changed retained evidence: '+name)
                    unchanged[name] = raw_digest(right.read_bytes())
                old = {r['key']: r for r in c.read(baseline_dir/'runtime-summary.json')}
                new = {r['key']: r for r in c.read(current_dir/'runtime-summary.json')}
                if set(old) != set(new) or len(new) != current['runtime']['programs']:
                    c.fail('E_INTEGRITY', 'Diagnostic comparison changed program identities')
                changed = [{'reading_id': r['reading_id'], 'role': r['role'], 'key': key,
                    'previous_status': old[key]['qualification_status'],
                    'previous_error': old[key].get('qualification_error'),
                    'current_status': r['qualification_status']}
                    for key, r in new.items() if old[key]['qualification_status'] != r['qualification_status']]
                after = ex.Allowance(root).verify()
                if after != before or ex.master.files_in(root/ex.RUN/'reservations', root) != reservations:
                    c.fail('E_INTEGRITY', 'Offline diagnostic changed the call ledger')
                c.checked(allowance, root)
                refs = [c.receipt(work/name, root) for work in (baseline_dir,current_dir)
                    for name in ('result.json','completion-receipt.json','runtime-summary.json')]
                refs += [allowance, *reservations, c.read(root/ex.RUN/'active-revision.json')['receipt'],
                    c.receipt(root/'docs/plans/assurance-evidence-diagnostic-restart.md', root),
                    c.receipt(root/ex.POLICY, root)]
                prior_record = current_dir/'run-manifest.json'
                if prior_record.exists():
                    refs.append(c.receipt(prior_record, root))
                prior = {'status':'VERIFIED_EXISTING_V3_ZERO_CALLS',
                    'created_at':c.now(), 'command':ex.PREFIX+['extend-diagnostic'],
                    'execution_mode':'FROZEN_RECEIPT_VERIFICATION_OF_EXISTING_V3',
                    'initial_v3_execution':'Worktree computation; revision 08 subsequently verified the existing receipt. Revision 08 did not freshly execute v3.',
                    'baseline':c.receipt(baseline_dir/'result.json',root),
                    'current':c.receipt(current_dir/'result.json',root),
                    'references':refs, 'unchanged_evidence_hashes':unchanged,
                    'qualification_before':baseline['runtime']['qualification_statuses'],
                    'qualification_after':current['runtime']['qualification_statuses'],
                    'changed_programs':changed, 'provider_calls':0, 'repair_calls':0,
                    'allowance_before':before, 'allowance_after':after,
                    'wall_seconds':round(time.monotonic()-began,3),
                    'initial_runtime_seconds_sum':round(sum(r['elapsed_seconds'] for r in new.values()),3),
                    'git_commit':manifest['git_commit'], 'environment':str(root/'.venv'),
                    'frozen_root':manifest['frozen_root'],
                    'cpu_only':True, 'gpu_hidden':os.environ.get('CUDA_VISIBLE_DEVICES')=='-1',
                    'seeds':'N/A: deterministic verification of retained artifacts',
                    'data_version':c.receipt(current_dir/'formal-evidence.json',root),
                    'plan':'docs/plans/assurance-evidence-diagnostic-restart.md',
                    'result':str(ex.RUN/'final-result.json'),
                    'final_review_scope':'Existing final reviews covered v2. No final review accepts v3 or the new controller.',
                    'legal_correctness':'NOT_ESTABLISHED', 'release_eligible':False}
                ex.immutable(report_path, prior)
                ex.immutable(root/ex.RUN/'current-diagnostic.json',
                    {'receipt':c.receipt(report_path, root)})
                adopted_diagnostic(root, ex)
        if ex.Allowance(root).verify() != before or ex.master.files_in(root/ex.RUN/'reservations',root) != reservations:
            c.fail('E_INTEGRITY', 'Offline diagnostic changed the allowance')
        c.checked(allowance, root)
        summary = ex.result(root, began)
        return {'status':'OFFLINE_DIAGNOSTIC_COMPLETED','allowance':summary['allowance'],
            'result':summary['checks'],'report':c.read(root/ex.RUN/'current-diagnostic.json')['receipt']}
    finally:
        CodexProvider.complete, ex.Allowance.reserve = original_complete, original_reserve


def partition(items, build, limit=180000):
    """Keep every whole reading and its complete evidence; split only at boundaries."""
    tasks, coverage = [], []
    start = 0
    while start < len(items):
        size = min(3, len(items)-start)
        while size:
            chunk = items[start:start+size]
            try:
                task = build(chunk, len(tasks)+1)
                wire, _, _ = protocol.transport(task)
                if len(canonical(wire)) > limit:
                    raise LegalMathError('E_RESOURCE_LIMIT', details='Final packet headroom')
                break
            except LegalMathError as exc:
                if exc.code != 'E_RESOURCE_LIMIT' or size == 1:
                    raise
                size -= 1
        tasks.append(task)
        coverage += [{'task': task['id'], 'reviewer': task['role'], 'role': task['request']['reviewed_role'],
                      'reading_id': item['reading']['reading_id']} for item in chunk]
        start += size
    return tasks, coverage


def final_tasks(root, ex):
    propagation, missing = ex.coverage(root)
    if missing:
        c.fail('E_REFERENCE', 'Incomplete reading coverage blocks final audits')
    work = root/ex.RUN
    checked = c.read(work/'checks-current-v2/result.json')
    inventory = c.read(work/'checks-current-v2/program-inventory.json')
    invmap = {(i['role'], i['reading_id']): i for i in inventory}
    prior = c.read(root/c.OLD/'assessment-evidence.json')
    ctx = phases.context(root)
    rows = ex.accepted_rows(root)
    repairs = {(row['role'], a['reading_id']): a for row in rows for a in row['value'].get('assessments', [])}
    manifest = c.read(c.checked(c.read(work/'active-revision.json')['receipt'], root))
    engineering = {'allowance': ex.status(root)['allowance'], 'checks': checked,
        'program_frontier': c.read(work/'programs/frontier-repaired-v2.json'),
        'program_acceptance': 'Every validated repair candidate still has CHALLENGED disposition. None is accepted as a completed substantive repair.',
        'scope_corrections': [row['value'] for row in rows if row['phase']=='scope'],
        'tests': (root/Path(manifest['frozen_root']).parent/'tests.log').read_text(),
        'calls': [{'task': r['task'], 'slot': r.get('allowance_slot'), 'status': r['status'], 'error': r.get('error')} for r in ex.engine().task_rows(root)],
        'controller': Path(ex.__file__).read_text(), 'completion_controller': Path(__file__).read_text(),
        'transport_controller': Path(ex.old.__file__).read_text(),
        'known_failures': ['Wrong full-object hash in earlier formal-repair prompts caused charged rejections; original packets remain immutable.',
            'Repair ceiling exhausted; 8 challenged programs lack validated repair proposals, 6 challenged readings have no executable program.',
            'The inherited bridge check is labelled predecessor-only. No original legal obligation is closed.']}
    tasks, reviewed = [], []
    for role in c.ROLES:
        task = protocol.make_task('final', role, ['final.engineering.'+role], {
            'kind':'review', 'source_packet': {'units':[{'unit_id':'engineering.executed', 'text':canonical(engineering).decode()}]},
            'questions':[{'id':'final-engineering', 'missing':'Audit the executed controller, tests, charged failures and current diagnostic results. Identify concrete engineering defects. The reported result explicitly preserves unresolved program repairs and all legal gaps. Supported scope means accurate bounded engineering evidence, never substantive repair acceptance or production readiness.'}],
            'instructions':'Return exact schema, quote exact unique source substrings, keep answer under 1800 characters. Preserve concrete defects even though repair calls are exhausted.'})
        tasks.append(ex.explicit_contract(task))
    packet = protocol.compact_packet(phases.sources.current_packet(root, c.read(root/c.BASE/'P0/authority-context.json')))
    questions = {r['reading_id']: r['questions'] for r in phases.inventory(root)}
    for role in c.ROLES:
        other = next(r for r in c.ROLES if r != role)
        items = []
        for row in propagation:
            if row['role'] != other:
                continue
            for update in row['value']['reading_updates']:
                cid = update['reading_id']
                items.append({'reading':update, 'original_reading':ctx['candidates'][cid],
                    'question_texts':questions[cid], 'questions':[q for q in row['value']['question_updates'] if q['reading_id']==cid],
                    'obligations':row['value']['obligation_updates'], 'candidate_repair':repairs.get((other,cid)),
                    'prior_program':prior[other][cid]['formalization'],
                    'retained_prior_assumptions':prior[other][cid]['added_assumptions'],
                    'retained_prior_questions':prior[other][cid]['unresolved_questions'], 'current_status':invmap[(other,cid)]})
        def build(chunk, part):
            t = protocol.make_task('final', role, ['final.dispositions.'+role], {
                'kind':'review', 'source_packet':packet, 'result_under_review':chunk,
                'checks':checked, 'reviewed_role':other,
                'questions':[{'id':'final-dispositions', 'missing':'Audit all supplied reading, question and obligation dispositions against complete sources, plus any challenged candidate repair. Name exact reading/question IDs for overstated availability, dates, meaning, facts or incomplete repairs. Original assumptions/questions remain operative. No candidate repair or original legal obligation has been accepted as closed. Supported scope approves only the accuracy of this declared subset and its stated open status.'}],
                'instructions':'Keep answer under 1800 characters, use exact source quotes, preserve every material issue. Unavailable repair budget does not justify favorable findings.'})
            t['id'] += f'.bounded-{part:02}'
            return ex.explicit_contract(t)
        batch, covered = partition(items, build)
        if len(batch) > 20:
            c.fail('E_RESOURCE_LIMIT', 'Complete final partition exceeds canonical final-issue allowance')
        tasks += batch
        reviewed += covered
    identities = [(r['role'],r['reading_id']) for r in reviewed]
    expected = {(r['role'],u['reading_id']) for r in propagation for u in r['value']['reading_updates']}
    if len(identities)!=len(set(identities)) or set(identities)!=expected:
        c.fail('E_INTEGRITY','Final review partition lost or duplicated a reading')
    for task in tasks:
        protocol.transport(task)
    ex.immutable(work/'final/coverage.json', reviewed)
    return tasks
