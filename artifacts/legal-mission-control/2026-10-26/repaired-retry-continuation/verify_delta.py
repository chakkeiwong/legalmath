"""Verify final narrow source delta against the completed full staged validation."""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import json,runpy,time
ROOT=Path('/home/chakwong/python/legalmath');WORK=Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
driver=runpy.run_path(str(ROOT/WORK/'deploy.py'));driver['candidate_imports']()
from scripts.legal_integration_master import BASE,DOC,PROGRAM,STATE,PLAN
from scripts.legal_mission_execution import read,save,ref,verify,require,digest
from scripts import legal_repaired_retry_continuation as module,legal_mission_execution as execution
from scripts.legal_integration_acceptance_revision import historical_projection
old=read(ROOT/WORK/'fully-validated-stage/program.json');new=read(ROOT/WORK/'registration-stage/program.json')
prior_receipt=read(ROOT/WORK/'before-diagnostic-staged-verification.json')
require(prior_receipt['verdict']=='PASS' and prior_receipt['mission']['program']['sha256']==ref(ROOT,WORK/'fully-validated-stage/program.json')['sha256']
    and prior_receipt['mission']['state']['sha256']==ref(ROOT,WORK/'fully-validated-stage/state.json')['sha256'],
    'Full staged validation receipt does not authenticate baseline')
before,after=old[module.KEY],new[module.KEY]
allowed={'src/legalmath/interpretation/assurance/phased/retry_checkpoint.py',
    'src/legalmath/interpretation/assurance/phased/capacity_checkpoint.py',
    'tests/assurance/test_repaired_retry_continuation.py','scripts/legal_repaired_retry_continuation.py'}
changed={p for p,v in before['implementation'].items() if after['implementation'][p]!=v}
require(changed==allowed,'Unexpected source delta')
aliases={(before['implementation'][p]['path'],before['implementation'][p]['sha256']):after['implementation'][p] for p in changed}
aliases[(before['result']['path'],before['result']['sha256'])]=after['result']
require(historical_projection(old,aliases)==new,'Final delta changed graph, authority, checkpoints or acceptance')
for pointer in new['protected_evidence']:
    if pointer['path'] in after['implementation']:
        require(ref(ROOT,WORK/'source'/pointer['path'])['sha256']==pointer['sha256'],'Candidate source changed')
old_state=read(ROOT/WORK/'fully-validated-stage/state.json');new_state=read(ROOT/WORK/'registration-stage/state.json')
normalized=json.loads(json.dumps(new_state));normalized['program_hash']=old_state['program_hash']
normalized['events'][-1]['at_utc']=old_state['events'][-1]['at_utc']
require(normalized==old_state,'Final delta changed owner state or history')
require(read(ROOT/WORK/'fully-validated-stage/service-recovery.json')==read(ROOT/WORK/'registration-stage/service-recovery.json'),
    'Final delta changed retry charges')
prep=read(ROOT/WORK/'preparation.json');stage=WORK/'registration-stage'
overrides={ROOT/p:ROOT/v['path'] for p,v in prep['sources'].items()}
overrides[ROOT/PLAN]=ROOT/prep['plan']['path']
service=Path(read(ROOT/BASE/'current-binding.json')['phase_service_scope']['path']).parent
overrides.update({ROOT/p:ROOT/stage/n for p,n in ((PROGRAM,'program.json'),(STATE,'state.json'),
    (BASE/'current-binding.json','binding.json'),(service/'service-recovery.json','service-recovery.json'))})
originals={n:getattr(Path,n) for n in ('read_text','read_bytes','is_file','exists')}
previous_program=read(ROOT/after['prior_program']['path'])
original_validate=execution.validate_program
def validate_with_checked_predecessor(program,root):
    if program==previous_program:
        # Its complete recursive check succeeded in the full receipt above.
        # Recheck the unchanged graph and current archived input references.
        return execution.validate_task_graph(program,root,
            reviewed={t['id']:t['maximum_attempts'] for t in program['tasks']},ceiling_limit=41)
    return original_validate(program,root)
started=time.monotonic()
with ExitStack() as stack:
    for name,method in originals.items():
        stack.enter_context(patch.object(Path,name,lambda p,*a,_method=method,**k:_method(overrides.get(p,p),*a,**k)))
    stack.enter_context(patch.object(execution,'validate_program',validate_with_checked_predecessor))
    from scripts import legal_integration_master,legal_mission_control
    stack.enter_context(patch.object(legal_integration_master,'validate_program',validate_with_checked_predecessor,create=True))
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_integration_campaign import provider
    mission=read(ROOT/stage/'mission.json');legal_mission_control.verify_refs(ROOT,mission)
    checked=validate_staged_mission(ROOT,stage,mission,68)
    p=provider();ledger=p.check();require(len(ledger['calls'])==6471,'Provider preflight changed charges')
    require(p.allowance.service_scope()[0]==read(ROOT/BASE/'current-binding.json')['phase_service_scope'],'Changed service scope')
result=dict(verdict='PASS',provider_calls=0,elapsed_seconds=time.monotonic()-started,mission=checked,
    validation_method='Full historical validation plus exact final source delta, current graph/state/mission/provider checks',
    full_predecessor_receipt=ref(ROOT,WORK/'before-diagnostic-staged-verification.json'),changed_sources=sorted(changed),
    files={str(p.relative_to(ROOT)):ref(ROOT,v) for p,v in overrides.items()},mission_candidate=ref(ROOT,stage/'mission.json'))
save(ROOT/WORK/'staged-verification.json',result)
print(json.dumps(dict(verdict='PASS',elapsed_seconds=result['elapsed_seconds'],changed_sources=sorted(changed)),indent=2))
