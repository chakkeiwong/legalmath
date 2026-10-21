"""Offline registration rehearsal with virtual production reads; never adopts."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
STAGE=WORK/'staging'
PROBE=WORK/'registration-probe'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(STAGE/'src'),str(STAGE),str(ROOT)]
from scripts import legal_integration_common_capacity as repair
from scripts.legal_mission_execution import read,save,ref,digest,validate_program
from scripts.legal_integration_acceptance_revision import historical_projection


def main():
    started=time.time()
    old=read(ROOT/repair.PROGRAM)
    before=read(ROOT/repair.STATE)
    # Simulate settlement solely in a local diagnostic copy. It is not a
    # reconciliation receipt and cannot authorize production adoption.
    simulated=[]
    for tid,row in before['tasks'].items():
        if row['status']=='RUNNING':
            row.update(status='INTERRUPTED',reason='Offline simulation only')
            simulated.append(tid)
    paths={repair.PROGRAM,repair.STATE,repair.DOC/'mission.json',repair.BASE/'current-binding.json',
        repair.BASE/'live-calls.json',repair.BASE/'live-grant.json',repair.PLAN}
    paths|={Path(p) for p in repair.implementation(ROOT) if (ROOT/p).exists()}
    archived=[]
    for path in sorted(paths):
        dest=PROBE/'before'/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        if path==repair.STATE:save(dest,before)
        else:shutil.copy2(ROOT/path,dest)
        original=ref(ROOT,ROOT/path)
        if path==repair.STATE:original['sha256']=ref(ROOT,dest)['sha256']
        archived.append(dict(previous=original,archive=ref(ROOT,dest)))
    baseline=dict(prior_detours=59,running_owners=0,calls=len(read(ROOT/repair.BASE/'live-calls.json')['calls']),archived=archived)
    save(PROBE/'baseline.json',baseline)
    held={r['previous']['path']:r['archive'] for r in archived}
    checkpoints={}
    for q in repair.QUESTIONS:
        metadata=read(ROOT/old['candidate_capacity_retry']['checkpoints'][q]['path'])
        path=PROBE/'checkpoints'/(q+'.json')
        save(path,dict(profile='common-capacity-checkpoint.v1',input_hash=metadata['input_hash'],calls={}))
        checkpoints[q]=ref(ROOT,path)
    targets={ROOT/p:STAGE/p for p in repair.implementation(ROOT)}
    targets[ROOT/repair.PLAN]=STAGE/repair.PLAN
    original_text,original_bytes=Path.read_text,Path.read_bytes
    def mapped(path):
        if path.is_relative_to(STAGE):
            relative=path.relative_to(STAGE)
            if relative.parts[0] not in ('src','scripts','tests','pyproject.toml'):
                path=ROOT/relative
        return targets.get(path,path)
    # Historical helper modules import ROOT from the master. They read the
    # real immutable evidence, with only reviewed implementation reads overlaid.
    from scripts import legal_integration_master, legal_mission_execution
    for module in (repair,legal_integration_master,legal_mission_execution): module.ROOT=ROOT
    with patch.object(Path,'read_text',lambda path,*a,**k:original_text(mapped(path),*a,**k)), \
         patch.object(Path,'read_bytes',lambda path,*a,**k:original_bytes(mapped(path),*a,**k)):
        additions=repair.repair_targets(old,before)
        revision=dict(profile='integration-common-capacity.v1',user_instruction=repair.USER,work=str(repair.WORK),
            capacity_profile=repair.CAPACITY,prior_detours=59,additional_consolidated_revision=1,
            live_calls_added=0,additional_transport_replacements=0,attempts_reset=False,service_scope_reset=False,
            attempt_additions=additions,reopened_nodes=sorted(additions),
            baseline=ref(ROOT,PROBE/'baseline.json'),review=ref(ROOT,repair.REVIEW),result=ref(ROOT,WORK/'local-result.json'),
            implementation={p:ref(ROOT,p) for p in sorted(repair.implementation(ROOT))},checkpoints=checkpoints,arm_checkpoints={},
            recoveries=old['candidate_capacity_retry']['recoveries'],
            prior_program=held[str(repair.PROGRAM)],prior_state=held[str(repair.STATE)],
            prior_binding=held[str(repair.BASE/'current-binding.json')],prior_ledger=held[str(repair.BASE/'live-calls.json')],
            prior_grant=held[str(repair.BASE/'live-grant.json')])
        program=repair.expected_program(historical_projection(old,repair.projection(baseline,root=ROOT)),before,revision,ROOT)
        save(PROBE/'program.json',program)
        validate_program(program,ROOT)
        state=repair.project_state(before,program,datetime.now(timezone.utc).isoformat())
        repair.validate_state_history(program,state,ROOT)
        save(PROBE/'state.json',state)
    result=dict(verdict='PASS',provider_calls=0,production_writes=0,simulation_only=True,
        simulated_settled_owners=simulated,scope='Full nested program and state-history validation; actual settled mission/provider binding remains required',
        program=ref(ROOT,PROBE/'program.json'),state=ref(ROOT,PROBE/'state.json'),
        wall_seconds=time.time()-started)
    save(WORK/'registration-probe.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
