"""Validate design examples and bounded controller obligations, not a live product."""
from collections import Counter, deque
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import hashlib
import json
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT/'docs/monograph/contracts'

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def check(pack):
    errors=[]
    def require(condition,message):
        if not condition: errors.append(message)
    for name, key in [('policy','policy'),('run','run'),('candidate','candidates'),
                      ('issue','issues'),('action','actions'),('coverage','coverage'),
                      ('report','report'),('review-decision','review_decisions'),('issue-decision','issue_decisions'),('evidence','evidence')]:
        schema=json.loads((DIR/f'{name}.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema,format_checker=FormatChecker())
        records=pack[key] if isinstance(pack[key],list) else [pack[key]]
        for rec in records:
            errors.extend(f'{name}: {e.message}' for e in validator.iter_errors(rec))
    if errors: return errors
    policy,run,report,coverage=(pack[k] for k in ('policy','run','report','coverage'))
    candidates={x['candidate_id']:x for x in pack['candidates']}
    issues={x['issue_id']:x for x in pack['issues']}
    actions={x['action_id']:x for x in pack['actions']}
    evidence={x['evidence_id']:x for x in pack['evidence']}
    for records,index in [(pack['candidates'],candidates),(pack['issues'],issues),(pack['actions'],actions)]:
        require(len(records)==len(index),'duplicate record identity')
    sh=digest(pack['source_packet'])
    require(run['source_packet_hash']==sh==report['source_packet_hash']==coverage['source_packet_hash'],'source identity')
    require(run['policy_hash']==digest(policy) and run['policy_id']==policy['policy_id'],'policy identity')
    require(policy['max_initial_actions']<=policy['max_actions_total'],'inconsistent initial budget')
    require(len(policy['required_initial_roles'])<=policy['max_initial_actions'],'required roles exceed initial cap')
    require(run['actions_issued']==len(actions)<=policy['max_actions_total'],'global issued accounting')
    require(run['rounds_issued']<=policy['max_resolution_rounds'],'round budget')
    require(run['no_progress_rounds']<=run['rounds_issued'],'progress counter')
    require(report['actions_issued']==run['actions_issued'] and report['rounds_issued']==run['rounds_issued'],'report counters')
    require(report['run_status']==run['status'],'report status')
    require(set(run['candidate_ids'])==set(candidates)==set(report['candidate_ids']),'candidate coverage')
    require(set(run['issue_ids'])==set(issues)==set(report['all_issue_ids']),'issue coverage')
    require(set(run['action_ids'])==set(actions),'action coverage')
    require(run['coverage_id']==report['coverage_id']==coverage['coverage_id'],'coverage identity')
    require(run['report_id']==report['report_id'],'report identity')
    require(set(coverage['inventory_unit_ids'])=={x['unit_id'] for x in coverage['dispositions']},'source-unit disposition coverage')
    require(len(coverage['dispositions'])==len(coverage['inventory_unit_ids']),'duplicate source disposition')
    require(set(report['missing_dependency_ids'])==set(coverage['required_dependency_ids'])-set(coverage['acquired_dependency_ids']),'dependency completeness')
    require(set(coverage['acquired_dependency_ids'])<=set(coverage['required_dependency_ids']),'unknown acquired dependency')
    require(set(report['unexplored_family_ids'])==set(coverage['identified_family_ids'])-set(coverage['explored_family_ids']),'frontier completeness')
    require(set(report['missing_initial_roles'])==set(policy['required_initial_roles'])-set(run['completed_initial_roles']),'role completeness')
    require(set(report['incomplete_mandatory_checks'])==set(policy['mandatory_checks'])-set(run['passed_mandatory_checks']),'check completeness')
    require(set(run['passed_mandatory_checks'])<=set(policy['mandatory_checks']),'unknown passed check')
    blocking={i for i,x in issues.items() if x['resolution_state']=='UNRESOLVED' and x['materiality']!='IMMATERIAL_REVIEWED'}
    require(set(report['material_unresolved_issue_ids'])==blocking,'blocking issue completeness')
    if run['status']=='READY_FOR_REVIEW':
        require(not blocking and all(x['disposition']!='UNRESOLVED' for x in coverage['dispositions']),'false readiness')
        require(coverage['inventory_review_status']!='UNREVIEWED','unreviewed inventory')
    initial=[x for x in actions.values() if x['kind']=='INITIAL_PROPOSAL']
    require(len(initial)<=policy['max_initial_actions'],'initial actions')
    completed={x['initial_role'] for x in initial if x['state']=='SUCCEEDED' and x['substantive_outcome']!='INVALID'}
    require(set(run['completed_initial_roles'])<=completed,'fabricated completed role')
    counts=Counter(x['issue_root_id'] for x in actions.values() if x['issue_root_id'])
    require(all(n<=policy['max_actions_per_issue_root'] for n in counts.values()),'root budget')
    for a in actions.values():
        require(a['run_id']==run['run_id'],'foreign action')
        require(a['round']<=run['rounds_issued'],'future action round')
        require(a['issued_at']<run['deadline'] and a['issued_at']>=run['created_at'],'dispatch outside deadline')
        require(a['timeout_seconds']<=policy['action_timeout_seconds'],'action timeout')
        if a['issue_root_id']:
            require(a['issue_root_id'] in issues and issues[a['issue_root_id']]['root_id']==a['issue_root_id'],'unknown root')
    for c in candidates.values():
        require(c['run_id']==run['run_id'] and c['source_packet_hash']==sh,'candidate context')
        require(set(c['issue_ids'])<=set(issues),'candidate issue reference')
        require(set(c['source_unit_ids'])<=set(coverage['inventory_unit_ids']),'candidate source reference')
        seen=set();parent=c
        while parent:
            if parent['candidate_id'] in seen:
                errors.append('candidate revision cycle');break
            seen.add(parent['candidate_id']);ident=parent['parent_id']
            require(ident is None or ident in candidates,'missing parent');parent=candidates.get(ident)
    for issue in issues.values():
        require(issue['run_id']==run['run_id'],'foreign issue')
        require(issue['root_id'] in issues,'missing issue root')
        require(set(issue['candidate_ids'])<=set(candidates),'issue candidate reference')
        require(set(issue['attempted_action_ids'])<=set(actions),'issue action reference')
        require(set(issue['resolution_evidence_refs'])<=set(evidence),'unretained resolution evidence')
        linked=[evidence[x] for x in issue['resolution_evidence_refs'] if x in evidence]
        if issue['resolution_state']!='UNRESOLVED':
            require(bool(linked) and all(e['validation_status']=='VALIDATED' for e in linked),'unvalidated closure')
        if issue['resolution_state']=='RESOLVED_ADJUDICATION':
            require(any(e['kind']=='HUMAN_ADJUDICATION' and e['review_decision_id'] in {r['decision_id'] for r in pack['issue_decisions'] if r['decision']=='RESOLVE_MEANING' and r['issue_id']==issue['issue_id']} for e in linked),'missing adjudication record')
        if issue['resolution_state']=='RESOLVED_EQUIVALENCE':
            require(any(e['kind']=='FORMAL_COMPARISON' and e['comparison_result']=='EQUIVALENT_WITHIN_DOMAIN' and e['domain_hash'] and e['legal_source_commitment_resolved'] for e in linked),'invalid equivalence closure')
        for ident in issue['attempted_action_ids']:
            if ident in actions:require(actions[ident]['issue_root_id']==issue['root_id'],'action assigned to wrong root')
    for e in evidence.values():
        require(e['run_id']==run['run_id'] and e['source_packet_hash']==sh,'foreign evidence')
        require(e['content_hash']==digest(e['statement']),'evidence content identity')
        require(e['action_id'] is None or e['action_id'] in actions,'missing evidence action')
    for decision in pack['issue_decisions']:
        require(decision['issue_id'] in issues and decision['run_id']==run['run_id'],'issue decision context')
        require(decision['candidate_hash'] in {digest(c) for c in candidates.values()},'issue decision candidate')
        require(decision['source_packet_hash']==sh,'issue decision source')
    for review in pack['review_decisions']:
        require(review['report_hash']==digest(report),'stale review report')
        require(review['candidate_hash'] in {digest(c) for c in candidates.values()},'stale review candidate')
        require(review['source_packet_hash']==sh,'stale review source')
    return errors


def controller_diagnostic():
    # A finite abstraction of issued accounting: two issue roots, global cap 3,
    # root cap 2. Each reservation models any success, crash or timeout outcome;
    # none may refund an issued count. Revisions retain their root.
    start=(0,0,0);queue=deque([start]);seen={start};edges=0
    while queue:
        a,x,y=queue.popleft()
        assert a==x+y and a<=3 and x<=2 and y<=2
        for root,n in enumerate((x,y)):
            if a<3 and n<2:
                nxt=(a+1,x+(root==0),y+(root==1));edges+=1
                assert (3-nxt[0]) < (3-a)
                if nxt not in seen:seen.add(nxt);queue.append(nxt)
    # Exhaust the release truth table: open issue, missing check, absent approval,
    # and failed integrity each veto release independently.
    release_rows=[]
    for bits in range(16):
        open_issue,complete,approved,integrity=[bool(bits&(1<<i)) for i in range(4)]
        allow=(not open_issue) and complete and approved and integrity
        release_rows.append({'open_issue':open_issue,'complete':complete,'approved':approved,'integrity':integrity,'allow':allow})
    assert sum(r['allow'] for r in release_rows)==1
    return {'states':len(seen),'reservation_edges':edges,'release_rows':release_rows,
            'scope':'Finite abstract accounting and release predicate only; not production concurrency or legal validity.'}


def main():
    pack=json.loads((DIR/'examples/blocked-investigation.json').read_text())
    assert not check(pack),check(pack)
    changes={
        'unknown_policy_field':lambda p:p['policy'].update(unlimited=True),
        'hidden_action_count':lambda p:p['run'].update(actions_issued=7),
        'root_budget_exceeded':lambda p:p['policy'].update(max_actions_per_issue_root=2),
        'omitted_blocking_issue':lambda p:p['report'].update(material_unresolved_issue_ids=[]),
        'false_readiness':lambda p:(p['report'].update(run_status='READY_FOR_REVIEW'),p['run'].update(status='READY_FOR_REVIEW')),
        'false_probability':lambda p:p['report'].update(probability_of_legal_correctness=0.99),
        'unretained_resolution':lambda p:p['issues'][0].update(resolution_evidence_refs=['invented-proof']),
        'source_mismatch':lambda p:p['candidates'][0].update(source_packet_hash='0'*64),
        'unbounded_paid_profile':lambda p:p['policy'].update(use='PAID_RUN'),
        'late_dispatch':lambda p:p['actions'][0].update(issued_at=p['run']['deadline']),
        'stale_review':lambda p:p['review_decisions'][0].update(report_hash='0'*64),
        'candidate_cycle':lambda p:p['candidates'][0].update(parent_id='candidate-repaired'),
        'hidden_source_unit':lambda p:p['coverage']['inventory_unit_ids'].append('fixture.p2'),
        'hidden_dependency':lambda p:p['report'].update(missing_dependency_ids=[]),
        'unvalidated_closure':lambda p:p['evidence'][1].update(validation_status='UNVERIFIED'),
        'false_equivalence_closure':lambda p:p['issues'][0].update(resolution_state='RESOLVED_EQUIVALENCE'),
    }
    rejected={}
    for name,change in changes.items():
        altered=deepcopy(pack);change(altered)
        # Remove stale policy/report hashes as accidental rejection causes.
        altered['run']['policy_hash']=digest(altered['policy'])
        if name!='stale_review':altered['review_decisions'][0]['report_hash']=digest(altered['report'])
        errors=check(altered);assert errors,name
        rejected[name]=errors
    tasks=json.loads((ROOT/'docs/monograph/implementation-plan.json').read_text())['tasks']
    seen=set()
    for task in tasks:
        assert set(task['depends_on'])<=seen
        assert task['status']=='PROPOSED_NOT_IMPLEMENTED' and task['acceptance_ids']
        seen.add(task['id'])
    result={'status':'DESIGN_CONTRACT_CHECKS_PASSED','positive_example':'blocked-investigation',
            'negative_examples_rejected':rejected,'task_count':len(tasks),
            'controller_diagnostic':controller_diagnostic(),
            'runtime_implemented':False,'legal_correctness_established':False}
    out=ROOT/'docs/monograph/review/contract-check.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'negative_checks':len(rejected),'tasks':len(tasks),
                      'abstract_states':result['controller_diagnostic']['states']}))

if __name__=='__main__':main()
