from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import json,runpy,time
ROOT=Path('/home/chakwong/python/legalmath');WORK=Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
driver=runpy.run_path(str(ROOT/WORK/'deploy.py'));driver['candidate_imports']()
from scripts.legal_integration_master import BASE,PROGRAM,STATE,PLAN
from scripts.legal_mission_execution import read,save,require
prep=read(ROOT/WORK/'preparation.json');stage=WORK/'registration-stage'
overrides={ROOT/p:ROOT/v['path'] for p,v in prep['sources'].items()}
overrides[ROOT/PLAN]=ROOT/prep['plan']['path']
service=Path(read(ROOT/BASE/'current-binding.json')['phase_service_scope']['path']).parent
overrides.update({ROOT/p:ROOT/stage/n for p,n in ((PROGRAM,'program.json'),(STATE,'state.json'),
    (BASE/'current-binding.json','binding.json'),(service/'service-recovery.json','service-recovery.json'))})
original={n:getattr(Path,n) for n in ('read_text','read_bytes','is_file','exists')}
started=time.monotonic()
with ExitStack() as stack:
    for name,method in original.items():
        stack.enter_context(patch.object(Path,name,lambda p,*a,_method=method,**k:_method(overrides.get(p,p),*a,**k)))
    from scripts.legal_integration_campaign import provider
    from legalmath.interpretation.assurance.time_authority import effective_deadline
    from scripts.legal_review_repair_service import terminal_receipt
    from legalmath.interpretation.assurance.phased.branch_budget import check
    p=provider();l=p.check();binding=read(ROOT/BASE/'current-binding.json')
    require(len(l['calls'])==6471 and l['maximum']==8100,'Changed global calls')
    require(p.allowance.service_scope()[0]==binding['phase_service_scope'],'Changed service scope')
    require(effective_deadline(ROOT,ROOT/BASE)=='2026-10-27T05:15:09+00:00','Changed deadline')
    check(ROOT,binding,l,'service-requalification',1)
    h=l['calls'][-1]['request_hash']
    request,schema,failure,manifest=terminal_receipt(ROOT,BASE,6471,h,allow_terminal_499=True)
    result=dict(verdict='PASS',provider_calls=0,calls=6471,remaining_calls=1629,
        exact_failure=type(failure).__name__,failed_slot=6471,
        service_request_budget_admissible=True,elapsed_seconds=time.monotonic()-started)
save(ROOT/WORK/'provider-preflight.json',result);print(json.dumps(result,indent=2))
