"""Preserve the inspected issue diagnoses alongside every original decision."""
from pathlib import Path
import json
import sys

ROOT = Path('/home/chakwong/python/legalmath')
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, digest

HERE = Path('artifacts/legal-mission-control/2026-10-23/p14-decisions')
DEPLOY = Path('artifacts/legal-mission-control/2026-10-23/p14-deployment')


def run():
    decisions = read(ROOT/HERE/'decisions.json')
    population = {r['assignment_id']: r for r in read(ROOT/DEPLOY/'context-preflight-population.json')}
    mappings = read(ROOT/HERE/'mapping-only-needs.json')['needs']
    authorities = read(ROOT/HERE/'retained-source-needs.json')['needs']
    rejects = [r for r in decisions if r['verdict']=='REJECT']
    assert len(rejects)==25 and len(population)==672
    # These are individually inspected positions in the immutable census, not
    # a classifier of new model decisions. Retain their actual assignments.
    wrong_assignment = {3,5,6,7,8,9,10,12,14,15,16,17,19,20}
    issue_rows = []
    for i, row in enumerate(rejects):
        category = ('DEPENDENCY_NECESSITY_OBJECTION' if i<15 else
            'EVIDENCE_DESCRIPTION_DEFECT' if i<24 else 'VERDICT_REASON_INCONSISTENCY')
        paths = ['/unresolved/2','/source_gaps','/conclusion'] if 15<=i<=22 else (
            ['/unresolved/2','/unresolved/3'] if i==23 else [])
        for j, issue in enumerate(row['full_decision']['issues']):
            issue_rows.append(dict(assignment_id=row['id'], issue_id=f'issue-{j}', text=issue,
                diagnosis=category, assignment_alignment='REASON_DISCUSSING_DIFFERENT_DEPENDENCY'
                    if i in wrong_assignment else 'NO_SPECIFIC_ALIGNMENT_DEFECT_ESTABLISHED',
                original_decision_hash=digest({**row['full_decision'],'considered':[row['id']]}),
                actual_assignment=row['assignment'], original_request=row['original_request'],
                candidate_answer_paths=paths,
                action=('Assess necessity against the actual conditional answer; no automatic relabeling.' if i<15 else
                    'Assess supported evidence-description defect, correct only warranted text, then review corrected answer.'
                    if i<24 else 'Assess the adverse issues independently; preserve inconsistent original verdict and reason.'),
                completion='Saved issue-specific warrant; supported correction and fresh review if warranted.',
                verdict_changed=False, resolved=False))
    assert len(issue_rows)==43
    save(ROOT/HERE/'reject-issue-remedies.json',dict(profile='p14-reviewed-issue-remedies.v1',
        census=ref(ROOT,HERE/'decisions.json'),issues=issue_rows,provider_calls=0,legal_acceptance=False))
    unresolved = []
    for row in decisions:
        if row['verdict']!='UNRESOLVED': continue
        prepared=population[row['id']]
        mapped=[n for n in mappings if n['assignment_id']==row['id']]
        retained=[n for n in authorities if n['assignment_id']==row['id']]
        unresolved.append(dict(assignment_id=row['id'],rationale=row['rationale'],
            original_needs=row['full_decision'].get('context_needs',[]),
            reviewed_mapping_needs=mapped,reviewed_retained_source_needs=retained,
            preparation=prepared,
            action='One exact-assignment continuation with all original needs, actual answer and jointly supplied source records.',
            acceptance_veto='Any still-required need, unsupported quotation, source gap, adverse issue or failed validation.',
            external_need_action='Preserve missing client facts and authority unless a specific sourced conditional-answer disposition shows them unnecessary.',
            original_verdict='UNRESOLVED',legal_resolution_established=False))
    save(ROOT/HERE/'unresolved-remedies.json',dict(profile='p14-reviewed-unresolved-remedies.v1',
        census=ref(ROOT,HERE/'decisions.json'),preparation=ref(ROOT,DEPLOY/'context-preflight-population.json'),
        decisions=unresolved,provider_calls=0,legal_acceptance=False))
    print(json.dumps(dict(unresolved=len(unresolved),rejected=len(rejects),issues=len(issue_rows),
        known_assignment_mismatches=len(wrong_assignment),original_verdicts_unchanged=True)))


if __name__=='__main__': run()
