"""Bind the current batch review to an unsubmitted component proposal."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from legalmath.prospectus.execution_authority import Authority,REL,read,write,digest,file_hash

PLAN='docs/plans/prospectus-post-repair-installed-batch-2026-10-17.md'


def main(revision):
    a=Authority(ROOT);old,_,_=a.spec()
    assert old['revision']==revision-1
    proposal=ROOT/REL/'proposals'/('component-'+str(revision)+'.json')
    p=read(proposal);r=read(proposal.with_name('component-'+str(revision)+'-review.json'))
    task=next(t for t in p['tasks'] if t.get('current_component_validation',{}).get('review')==REL+'/reviews/component-'+str(revision))
    task['inputs']=sorted(set(task['inputs'])|{PLAN,str(Path(__file__).relative_to(ROOT))})
    task['reason']='Verify the current452-file frozen package delivers original complete '+task['current_component_validation']['kind']+' outputs and refusals; preserve original wider scope'
    r['changes']=[task['reason'],'One common wheel reused across five separately admitted original components']
    r['skeptical_audit']['post_repair_review']={'plan':PLAN,'sha256':file_hash(ROOT/PLAN),'baseline_revision':old['revision']}
    r['budget_revision']['reason']=task['reason']
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=revision
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=digest(task),phase=0,mode='local',remaining=task['reason'],
                next_action='Execute current/isolated component check with complete original controls, record/refresh; reuse identical wheel for next component.')
        elif row['task']=='basf-office':
            row.update(phase=3,remaining='003 recorded exact30/45-day conditional notice calculation,insolvency branch and80 unchanged earlier answers; actual office/events remain unresolved.',
                next_action='Preserve completed003; actual office facts belong to later case application. Continue distinct conditional role/office cases only with reviewed new evidence.')
    route=REL+'/closure-routes-2026-10-17-post-repair-'+str(revision)+'.json'
    write(ROOT/route,routes,exclusive=True)
    p['continuation_review'].update(plan=PLAN,routes=route)
    for n in (PLAN,route,str(Path(__file__).relative_to(ROOT))):p['continuation_review']['bindings'][n]=file_hash(ROOT/n)
    a.validate_program(p)
    write(proposal.with_name('post-repair-'+str(revision)+'.json'),p,exclusive=True)
    write(proposal.with_name('post-repair-'+str(revision)+'-review.json'),r,exclusive=True)
    print(json.dumps({'reviewed_revision':revision,'task':task['id'],'kind':task['current_component_validation']['kind'],'audit':'PASS'}))


if __name__=='__main__':main(int(sys.argv[1]))
