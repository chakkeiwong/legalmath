"""Conservative local corrections after the completed, retained provider review."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import os
import time

import assurance_evidence_core as c
import assurance_evidence_current_review as packets
import assurance_evidence_review_runtime as review
from legalmath.canonical import digest

PLAN = Path('docs/plans/assurance-evidence-post-review-repairs.md')
SUBDIR = 'post-review-repairs'
OPEN_QUESTIONS = {
    'deferred.2bc034bb48ed295565d54a40': {
        'question.0ac95a2cc4a3f686e02ea642077c3087d4c6266e1852c33cc36370126a802698',
        'question.a07abe5a1b6a261b99e30e7fc6e43b219f16096d21da9ac1262513627ee00cfc'},
    'deferred.8e90af0c22246aec5c2d05d0': {
        'question.ee12cd348c3f75090bd5a27613d28b400026c818a47a702d9be310a697a532fe',
        'question.57a5b0e3c7198bcdcee9fcbeea9f10ed97c7fb4fb6d6149ac75c678456337faf',
        'question.d34aa3dfedeb280e528b06aa990666dd5ca2882708ef36b07251c11a74550c7e',
        'question.bff3987f25c7f6607cfb8f2b65a6be0ecf0d16eb4897f678a86b9e5f1752f25e',
        'question.df255a26f61012901696e53c519969693cb7a07af2582ed0cf533c812e82a117',
        'question.27b5146c61729f5a1984c09a42305465a19825a3eb51922c1534f596edf398a3'},
    'deferred.81d2c93ff70be47b96c5b4ae': {
        'question.daac5eda072783c6e1e558cae14f23ec858b53ef521bb3f0edd10574d72281d8',
        'question.a778b07c3cf92e66edcf621fb267f6d048bed5a9b534f2179401060c3ce456b7'}}

ANNOTATIONS = [
    'This derived record is provisional local work. The retained model round reviewed the earlier frozen code and responses, not these repairs. Same-family model reviews are not independent evidence.',
    'UT Chapter 6 and its introduction, the securities circular and Appendix (sources 50–53) are acquired. Acquisition establishes neither applicability nor completeness of governing authority.',
    'Paragraph 14 conditions demonstration on an SFC request; footnote 5 states confirmation and demonstration without that wording. Their interaction remains unresolved. Do not infer that demonstration is exclusively request-triggered.',
    'Only exception-challenger/deferred.744c4b5d99bc07afffce029b permits an evidenced false conjunct to determine the predicate while another required classification is unresolved. Other guarded readings require every required classification.',
    'Inventory dispositions record substantive acceptance. Eight programs labelled excluded unrepaired in that inventory also have separately recorded mechanical guards. Four retained conditional programs are outside the twenty new guards.',
    'Unchanged formulas means equality against the retained v3 and guarded baseline. It does not assert equality with every historical program.',
    'The actual provider, arrangement, assessment interval, applicable authority, ownership and finality, incidents and remediation remain unestablished. All 46 original obligations remain open.'
]


def expand(item):
    result = deepcopy(item)
    grouped = result.pop('question_dispositions')
    result['questions'] = [{**deepcopy(grouped['groups'][i]['shared_disposition']),
        'question_id': grouped['groups'][i]['question_ids'][j]}
        for i, j in grouped['original_order']]
    return result


def repair_entry(task, original):
    role, cid = task['request']['reviewed_role'], original['reading']['reading_id']
    operative = expand(original)
    changes = []

    def change(path, value, reason, kind):
        parent = operative
        for key in path[:-1]:
            parent = parent[key]
        before = deepcopy(parent[path[-1]])
        if before == value:
            c.fail('E_INTEGRITY', 'Repair no longer matches its original input')
        parent[path[-1]] = value
        changes.append({'path': list(path), 'before': before, 'after': deepcopy(value),
            'reason': reason, 'kind': kind})

    if role == 'exception-challenger':
        for i, q in enumerate(operative['questions']):
            if q['question_id'] in OPEN_QUESTIONS.get(cid, set()):
                if q['status'] != 'ANSWERED_UNDER_STATED_PREMISES':
                    c.fail('E_INTEGRITY', 'Expected answered disposition changed')
                change(('questions', i, 'status'), 'REMAINS_OPEN',
                    'The retained explanation leaves the original factual or interpretive question unresolved.', 'question_status')
        replacements = {
            'alternative.017.22bacfbbe572a908': ('No SFC request suspends neither paragraph 10 nor confirmation.',
                'Absence of an SFC request suspends neither paragraph 10 responsibility nor confirmation.'),
            'alternative.020.25356e7c001b28fe': ('No SFC request excuses neither responsibility nor confirmation.',
                'Absence of an SFC request excuses neither responsibility nor confirmation.'),
            'alternative.016.3c59f3e8bfcda88b': (
                'the supplied sources provide no criteria for discharge, adequacy, deficiencies, remediation or assessment timing.',
                'the supplied sources identify relevant staffing, controls, records, interoperability and incident considerations without settling a complete paragraph 10 discharge test, its thresholds or the actual assessment period.')}
        if cid in replacements:
            before, after = replacements[cid]
            text = operative['reading']['explanation']
            if text.count(before) != 1:
                c.fail('E_INTEGRITY', 'Expected editorial passage changed')
            change(('reading', 'explanation'), text.replace(before, after),
                'Correct the confirmed wording defect while retaining unresolved standards.', 'editorial')
        if cid == 'alternative.001.fccab3d6d9633fa2':
            assumptions = operative['reading']['added_assumptions']
            matches = [i for i, a in enumerate(assumptions) if a.endswith('civil liability relatives.')]
            if len(matches) != 1:
                c.fail('E_INTEGRITY', 'Expected liability typo changed')
            i = matches[0]
            change(('reading', 'added_assumptions', i), assumptions[i].replace('civil liability relatives.', 'civil liability.'),
                'Remove the extraneous word; preserve enforceability and liability uncertainty.', 'editorial')
    if role == 'structure-reader':
        if cid == 'alternative.004.3104c53459d53628':
            text = operative['reading']['explanation']
            cutoff = 'Missing facts or unresolved ownership conflicts prevent evaluation unless the relevant accountability classification is independently decid '
            if not text.endswith(cutoff):
                c.fail('E_INTEGRITY', 'Expected reading cutoff changed')
            change(('reading', 'explanation'), text[:-len(cutoff)]+
                'Evaluation requires established applicability, scope and every required accountability classification. Missing required classifications or ownership conflicts affecting them leave the predicate unresolved.',
                'Complete the cut-off sentence consistently with this reading’s guard.', 'editorial')
        endings = {
            'alternative.004.3104c53459d53628': ('are未', 'remain unresolved.'),
            'alternative.014.f17e746329048376': ('any relaxation,', 'any relaxation, the actual assessment period and case facts remain unestablished.'),
            'alternative.010.036b7b89f3747a27': ('historical references to missing sources do',
                'historical references to missing sources do not describe current acquisition, and acquisition alone does not establish applicability.'),
            'alternative.016.3c59f3e8bfcda88b': ('actor and\u00a0',
                'actor and activity-specific applicability, the assessment period and actual case facts remain unresolved.')}
        if cid in endings:
            before, after = endings[cid]
            matches = [(i, q['explanation']) for i, q in enumerate(operative['questions']) if q['explanation'].endswith(before)]
            if len(matches) != 2:
                c.fail('E_INTEGRITY', 'Expected two expanded question cutoffs')
            for i, text in matches:
                change(('questions', i, 'explanation'), text[:-len(before)]+after,
                    'Complete the retained truncated explanation without answering the open question.', 'editorial')
    for i, obligation in enumerate(operative['obligations']):
        for j, request in enumerate(obligation['needed_evidence']):
            # Explicit edition-plus-actual-period inquiries already preserve this distinction.
            if '20 April 2026' not in request or 'actual assessment period' in request:
                continue
            revised = request
            for phrase in ('as at', 'effective on', 'on', 'through', 'for', 'to'):
                revised = revised.replace(phrase+' 20 April 2026',
                    'for the independently established assessment period')
            if '20 April 2026' in revised:
                c.fail('E_INTEGRITY', 'Unexamined date phrase in operative evidence request')
            change(('obligations', i, 'needed_evidence', j), revised,
                'The source revision date does not establish the actual assessment interval. The original edition-specific inquiry remains in the retained original record.', 'assessment_period')
    return {'role': role, 'reading_id': cid, 'review_task': task['id'],
        'status': 'LOCAL_PROVISIONAL_DERIVED_RECORD', 'original': deepcopy(original),
        'operative': operative, 'changes': changes, 'qualifications': ANNOTATIONS,
        'accepted_substantive_repair': False}


def derive(tasks):
    entries = [repair_entry(t, item) for t in tasks for item in t['request'].get('result_under_review', [])]
    keys = {(v['role'], v['reading_id']) for v in entries}
    counts = Counter(change['kind'] for entry in entries for change in entry['changes'])
    if len(entries) != 70 or len(keys) != 70 or counts['question_status'] != 10 or counts['editorial'] != 13:
        c.fail('E_INTEGRITY', 'Derived corrections differ from inspected review coverage')
    return entries, dict(counts)


def checked_tree(root, ref, seen=None):
    seen = set() if seen is None else seen
    path = c.checked(ref, root)
    if str(path) in seen:
        return path
    seen.add(str(path))
    if path.name in ('receipt.json', 'completion-receipt.json'):
        record = c.read(path)
        for item in record.get('files', [])+record.get('inputs', []):
            checked_tree(root, item, seen)
    return path


def verify(root, ex, ref):
    path = c.checked(ref, root)
    base = (root/ex.RUN/SUBDIR).resolve()
    if path.name != 'completion-receipt.json' or not path.parent.is_relative_to(base):
        c.fail('E_INTEGRITY', 'Foreign post-review receipt')
    record = c.read(path)
    covered = set()
    for item in record['files']:
        file = c.checked(item, root)
        if file.parent != path.parent or file.name in covered:
            c.fail('E_INTEGRITY', 'Foreign or duplicate post-review output')
        covered.add(file.name)
    required = {'dispositions.json', 'findings.json', 'result.json', 'run-manifest.json', 'next-phase-plan.json', 'next-phase-plan.md', 'result.md'}
    if covered != required:
        c.fail('E_INTEGRITY', 'Incomplete post-review receipt')
    for item in record['inputs']:
        checked_tree(root, item)
    return c.read(path.parent/'result.json')


def summary(root, ex):
    pointer = root/ex.RUN/'current-post-review-repairs.json'
    if not pointer.exists():
        return None
    ref = c.read(pointer)['receipt']
    return {**verify(root, ex, ref), 'receipt': ref}


def spending(root, ex):
    return {'original': ex.Allowance(root).verify(), 'review': review.Allowance(root).verify(),
        'reservations': ex.master.files_in(root/ex.RUN/'reservations', root)
            +ex.master.files_in(root/review.RUN/'reservations', root)}


def execute(root, ex):
    from assurance_evidence_guarded import summary as guard_summary
    from legalmath.interpretation.search.providers import CodexProvider
    began = time.monotonic()
    manifest = ex.verify(root)
    if Path(__file__).resolve().parents[1] != (root/manifest['frozen_root']).resolve():
        c.fail('E_AUTHORITY', 'Post-review repairs require active frozen code')
    state = review.engine().state(root)
    if not all(state['phases'].get(p, {}).get('status') == 'COMPLETED' for p in ('engineering', 'dispositions')):
        return None
    report = review.summary(root)
    if state['halt'] or report['unaccounted_slots'] or report['structurally_validated_tasks'] != 26:
        c.fail('E_DEPENDENCY', 'Complete, accounted review required before local corrections')
    folder = packets.verified(root, ex)
    reviewed_root = c.read(folder/'run-manifest.json')['frozen_root']
    guard = guard_summary(root, ex)
    if guard is None or guard['programs'] != 20 or guard['synthetic_checks'] != 1040:
        c.fail('E_DEPENDENCY', 'Repaired ownership guards have not passed all contrary cases')
    tasks = c.read(folder/'task-definitions.json')
    prior = {(t['request']['reviewed_role'], v['reading']['reading_id']): v['guarded_candidate']['formalization']
        for t in tasks for v in t['request'].get('result_under_review', []) if 'guarded_candidate' in v}
    guard_path = c.checked(guard['receipt'], root).parent
    current = {(v['role'], v['reading_id']): v['formalization'] for v in c.read(guard_path/'programs.json')}
    if prior != current:
        c.fail('E_INTEGRITY', 'Post-review guard formulas differ from the reviewed baseline')
    refs = [c.receipt(folder/'completion-receipt.json', root), c.receipt(root/review.AUTHORIZATION, root),
        guard['receipt'], c.read(root/ex.RUN/'active-revision.json')['receipt'], c.receipt(root/PLAN, root)]
    refs += [r['receipt'] for r in review.engine().task_rows(root)]
    refs += ex.master.files_in(root/review.RUN/'provider-evidence', root)
    output = root/ex.RUN/SUBDIR/digest(refs)[:24]
    receipt_path = output/'completion-receipt.json'
    before = spending(root, ex)
    blocked = [(CodexProvider, 'complete'), (ex.Allowance, 'reserve'),
        (review.Allowance, 'reserve'), (ex.old.Allowance, 'reserve'), (c.EvidenceAllowance, 'reserve')]
    originals = [(obj, name, getattr(obj, name)) for obj, name in blocked]
    def forbidden(*args, **kwargs):
        c.fail('E_AUTHORITY', 'Post-review local repairs cannot dispatch or reserve calls')
    try:
        for obj, name, _ in originals:
            setattr(obj, name, forbidden)
        if not receipt_path.exists():
            entries, counts = derive(tasks)
            ex.immutable(output/'dispositions.json', entries)
            ex.immutable(output/'findings.json', report['findings'])
            next_phase = {'status': 'LOCAL_REPAIRS_COMPLETE_SUBSTANTIVE_EVIDENCE_PENDING',
                'provider_dispatch_planned': False, 'provider_calls': 0,
                'next_actions': ['Review this later local candidate against its exact changes and preserved 74 findings.',
                    'Establish provider, product, arrangement and actual assessment interval.',
                    'Obtain the applicable dated authority and product conditions; resolve the paragraph 10 conduct/outcome standard and paragraph 14/footnote 5 interaction.',
                    'Obtain ownership, settlement finality, responsibility, incident and remediation records; assess each of the 46 obligations against them.'],
                'repair_trigger': 'New applicable authority, case evidence, or a reproducible software defect.',
                'continuation_veto': 'Changed protected evidence, detached receipt, changed formula or unintended spending.',
                'promotion_veto': 'Missing legal and factual prerequisites or substantive review of the later candidate.',
                'allowance': before['review'], 'original_obligations_open': 46,
                'no_conclusion': 'Mechanical checks and corrected prose do not establish legal correctness or release readiness.'}
            ex.immutable(output/'next-phase-plan.json', next_phase)
            note = '# Refreshed phase after local repairs\n\n'+ '\n\n'.join(next_phase['next_actions'])+'\n\n'+next_phase['no_conclusion']+'\n'
            write_immutable_text(output/'next-phase-plan.md', note)
            result = {'status': next_phase['status'], 'derived_readings': len(entries),
                'changes': counts, 'retained_review_findings': len(report['findings']),
                'provider_calls': 0, 'repair_calls': 0, 'formula_changes': 0,
                'guarded_programs': 20, 'synthetic_checks': 1040,
                'reviewed_frozen_root': reviewed_root, 'repaired_frozen_root': manifest['frozen_root'],
                'later_candidate_reviewed': False, 'accepted_substantive_repairs': 0,
                'original_obligations_open': 46, 'release_eligible': False,
                'next_phase_plan': str((output/'next-phase-plan.md').relative_to(root))}
            ex.immutable(output/'result.json', result)
            note = ('# Local post-review repair result\n\n'
                f"{len(entries)} derived reading records; {counts['question_status']} answered statuses reopened, "
                f"{counts['editorial']} editorial field corrections and {counts.get('assessment_period', 0)} evidence-request date corrections. "
                'All original source, question, response and formula records are retained.\n\n'
                f"Reviewed code: {reviewed_root}. Later repaired code: {manifest['frozen_root']}. "
                'The provider round does not accept the later code or derived dispositions.\n\n'
                '| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |\n'
                '|---|---|---|---|---|---|\n'
                '| Retain local repair candidate | Focused tests, 1040 guard cases, unchanged formulas | Receipt or spending mismatch rejects | Applicable authority, interpretation and facts | Saved next phase | Legal correctness or release |\n\n'
                'Post-run red-team: supplied classifications can remain wrong despite mechanically correct aggregation. '
                'The unresolved responsibility standard and actual case evidence are the weakest support. '
                'Contrary applicable authority or factual records can overturn the conditional interpretations.\n')
            write_immutable_text(output/'result.md', note)
            after = spending(root, ex)
            if after != before:
                c.fail('E_INTEGRITY', 'Local post-review work changed spending')
            run_manifest = {'command': ex.PREFIX+['ops-run'], 'git_commit': manifest['git_commit'],
                'environment': str(root/'.venv'), 'cpu_only': True,
                'gpu_hidden': os.environ.get('CUDA_VISIBLE_DEVICES') == '-1',
                'seeds': 'N/A: deterministic local derivation', 'frozen_root': manifest['frozen_root'],
                'reviewed_frozen_root': reviewed_root, 'data_version': refs, 'plan': str(PLAN),
                'result': str((output/'result.json').relative_to(root)),
                'wall_seconds': round(time.monotonic()-began, 3), 'spending_before': before, 'spending_after': after}
            if (output/'run-manifest.json').exists():
                run_manifest['wall_seconds'] = c.read(output/'run-manifest.json')['wall_seconds']
            ex.immutable(output/'run-manifest.json', run_manifest)
            ex.immutable(receipt_path, {'inputs': refs, 'files': ex.master.files_in(output, root, ('completion-receipt.json',))})
        if spending(root, ex) != before:
            c.fail('E_INTEGRITY', 'Post-review restart changed spending')
        ref = c.receipt(receipt_path, root)
        verify(root, ex, ref)
        c.save(root/ex.RUN/'current-post-review-repairs.json', {'receipt': ref})
        return summary(root, ex)
    finally:
        for obj, name, method in originals:
            setattr(obj, name, method)


def write_immutable_text(path, value):
    if path.exists():
        if path.read_text() != value:
            c.fail('E_INTEGRITY', 'Immutable post-review text changed')
    else:
        c.write_text(path, value)
