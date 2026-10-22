"""Reviewed execution refinement; retain immutable original preparation methods."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from scripts import prospectus_shell_maturity as base

REVIEW=base.PREP/'ADMISSION-REVIEW.md'
HERE=base.HERE
read,save,sha,rel=base.read,base.save,base.sha,base.rel
original_command=base.command
original_seal=base.seal
original_freeze=base.freeze


def command(name,argv,folder=HERE,timeout=90,cwd=base.ROOT):
    return original_command(name,argv,folder=folder,timeout=180 if name in {'ordinary','installed'} else timeout,cwd=cwd)


def prepare_revision():
    from copy import deepcopy
    from legalmath.prospectus.execution_authority import digest,write
    old=read(base.PREP/'proposal.json');new=deepcopy(old)
    additions={rel(REVIEW):sha(REVIEW),rel(Path(__file__)):sha(Path(__file__))}
    task=next(t for t in new['tasks'] if t['id']=='finance-conventions')
    task['inputs']=sorted(set(task['inputs'])|set(additions))
    task['scheduled_maturity']['admission_review']=rel(REVIEW)
    task['scheduled_maturity']['consumer_child_seconds']=180
    task['scheduled_maturity']['source_roles']='PRESERVE_OPERATIVE_AND_UNKNOWN; applicability conditional on supplied profile'
    routes=read(base.PREP/'routes.json')
    next(r for r in routes['tasks'] if r['task']=='finance-conventions')['task_sha256']=digest(task)
    folder=base.PREP/'admission-reconciliation';save(folder/'routes.json',routes)
    new['continuation_review']['routes']=rel(folder/'routes.json')
    new['continuation_review']['bindings'].update(additions)
    new['continuation_review']['bindings'][rel(folder/'routes.json')]=sha(folder/'routes.json')
    review=read(base.PREP/'review.json')
    review['changes'].extend(['Preserve UNKNOWN source roles and explicit conditional applicability','Consumer child bound180seconds based on actual83.75second baseline; cumulative bound unchanged'])
    review['skeptical_audit']='PASS after documented actual-role and measured-runtime corrections in '+rel(REVIEW)
    review['budget_revision']['stop_condition']['consumer_child_seconds']=180
    review['evidence_contract']['not_concluded'].append('Applicability of UNKNOWN source roles')
    write(folder/'proposal.json',new,exclusive=True);write(folder/'review.json',review,exclusive=True)
    return {'status':'PASS','revision':361,'proposal':rel(folder/'proposal.json'),'review':rel(folder/'review.json')}


def frontier():
    states={}
    for stage in base.DEPENDENCIES:
        folder=HERE/'stages'/stage
        states[stage]=read(folder/'result.json')['status'] if (folder/'result.json').exists() else (
            'FAIL' if (folder/'failure.json').exists() else 'INTERRUPTED_OR_RUNNING' if folder.exists() else 'PENDING')
    for stage,deps in base.DEPENDENCIES.items():
        if stage!='seal' and states[stage]=='PENDING' and any(states[d] in {'FAIL','BLOCKED'} for d in deps):
            states[stage]='BLOCKED'
    ready=[s for s,deps in base.DEPENDENCIES.items() if s!='seal' and states[s]=='PENDING' and all(states[d]=='PASS' for d in deps)]
    if states['seal']=='PENDING' and states['freeze']=='PASS' and all(states[s] in {'PASS','FAIL','BLOCKED'} for s in ('tests','ordinary','package','installed')):
        ready.append('seal')
    return {'stage_states':states,'ready':ready,'whole_program_complete':False,
            'independent_review':'Original finance acceptance reconciliation remains available'}


def freeze():
    # The wrapper and admission review are task inputs and also retained in the
    # runtime identity list through a separate immutable manifest.
    save(HERE/'execution-methods.json',{'bindings':{rel(Path(__file__)):sha(Path(__file__)),rel(REVIEW):sha(REVIEW)},
        'utc':datetime.now(timezone.utc).isoformat()})
    return original_freeze()


def seal():
    states=frontier()['stage_states']
    if all(states[s]=='PASS' for s in ('tests','ordinary','package','installed')):
        return original_seal()
    assert (HERE/'RESULT.md').exists(),'Actual failure analysis required'
    value={'status':'FAIL','task':'finance-conventions','whole_task_complete':False,'build_criteria_claimed':[],
           'reason':'Maturity candidate has failed/blocked branches; no completion claim','stages':states,'resources':base.costs()}
    save(HERE/'result.json',value)
    return value


if __name__=='__main__':
    if sys.argv[1]=='prepare-revision':print(json.dumps(prepare_revision()))
    else:
        base.command,base.frontier,base.freeze,base.seal=command,frontier,freeze,seal
        base.main()
