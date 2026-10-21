"""Replay all completed preparation through run_product, with network forbidden."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import json
import os
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.errors import LegalMathError
from scripts import legal_integration_phased_live as live
from scripts.legal_integration_candidate_retry import WORK, QUESTIONS, OLD, KEY
from scripts.legal_integration_campaign import provider
from scripts.legal_mission_execution import read, ref, save, require
from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose


def main():
    program = read(ROOT/live.PROGRAM)
    replay = WORK/'checkpoint-replay'
    program[KEY] = dict(work=str(replay), checkpoints={q:ref(ROOT,WORK/'checkpoints'/(q+'.json')) for q in QUESTIONS})
    def projected_read(path):
        return deepcopy(program) if Path(path)==ROOT/live.PROGRAM else read(path)
    requested=[]
    def forbid(owner):
        def admitted(name,count):
            require(name.startswith('call-candidates-') and count==1,
                'Completed work was unexpectedly redispatched: '+name)
            requested.append(dict(owner=owner,phase=name,count=count))
            raise LegalMathError('E_RESOURCE_LIMIT',details='DEBUG ONLY: optional dispatch deliberately withheld')
        return admitted
    service=provider()
    ledger=ref(ROOT,live.BASE/'live-calls.json')
    reports={}
    with patch.object(live,'read',projected_read), patch.object(live,'phase_admit',forbid), \
            patch.object(service,'complete',side_effect=AssertionError('Network forbidden during replay')):
        for q in QUESTIONS:
            result=live.product_route(q,None,service,preparation_only=True)
            old=read(ROOT/OLD/q/'product/result.json')
            require(result['answers'][q].get('status')=='PREPARED',str(result['answers'][q]))
            require(result['answers'][q]['findings']==old['answers'][q]['findings'],'Different prepared finding')
            diagnosis=diagnose(ROOT,ROOT/replay/'live'/q/'product',q,result=result)
            require(diagnosis['prepared'] and len(diagnosis['optional_incomplete_phases'])==1,
                'Independent prepared baseline still blocked')
            reports[q]=dict(findings_unchanged=True,baseline_prepared=True,source_and_lineage_authenticated=True,
                original_populations=result['original_populations'],
                result=ref(ROOT,replay/'live'/q/'product/result.json'))
            print(json.dumps({'question':q,**reports[q]}),flush=True)
    require(ref(ROOT,live.BASE/'live-calls.json')==ledger,'Replay changed paid ledger')
    value=dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,legal_acceptance=False,
        reports=reports,withheld_optional_calls=requested,
        scope='Exact saved preparation through real product entry. Optional candidate admission deliberately withheld; no model response fabricated.')
    save(ROOT/WORK/'checkpoint-replay.json',value)


if __name__=='__main__':main()
