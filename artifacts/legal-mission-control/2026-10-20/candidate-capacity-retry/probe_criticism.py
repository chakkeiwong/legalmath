"""Constructor/transport probe with real sources and labelled fixture candidates."""
from pathlib import Path
from copy import deepcopy
import os
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from scripts.legal_integration_candidate_retry import WORK,QUESTIONS
from scripts.legal_integration_master import TOKENIZER,BASE
from scripts.legal_integration_campaign import provider
from scripts.legal_mission_execution import read,ref,save,require
from legalmath.interpretation.assurance.arguments import Criticism,criticism_request
from legalmath.interpretation.assurance.bounded_context import ContextRoute,Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct,BoundDispatch
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased import downstream_input,account_input,account_encoding,tool_input


def main():
    program=read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
    route=ContextRoute(read(ROOT/program['prerequisite_repair']['source']['path']),tokenizer(ROOT/TOKENIZER),limits=Limits())
    service=provider()
    ledger=ref(ROOT,BASE/'live-calls.json')
    p=object.__new__(BoundedProduct)
    p.downstream_input_profile=downstream_input.PROFILE
    p.downstream_capacity_profile=downstream_input.CAPACITY_PROFILE
    rows={}
    for q in QUESTIONS:
        candidate=read(ROOT/WORK/'requests'/(q+'.json'))['request']
        packet,records=candidate['source_packet'],candidate['records']
        fixture={f'probe-{i}':dict(local_id=f'probe-{i}',family='scope',subject='CAPACITY FIXTURE',
            statement='Synthetic transport probe; no legal finding.',distinction='No legal evaluation.',
            citations=[dict(unit_id=r['id'],quote=r['text'])],assumptions=[],questions=[],formalization=None)
            for i,r in enumerate(records)}
        request=p.tool_request(criticism_request(packet,[],fixture),records)
        schema=Criticism.model_json_schema()
        plain=prepare({k:v for k,v in request.items() if not k.startswith('downstream_')},schema)
        packed=prepare(request,schema)
        expanded=account_encoding.expand(dict(request=packed['request'],response_schema=packed['schema']))
        restored=account_input.expand(tool_input.expand(expanded['request']))
        for k in ('downstream_input_profile','downstream_capacity_profile'):restored.pop(k)
        require(restored==plain['request'] and expanded['response_schema']==plain['schema'],'Changed criticism content')
        dispatch=BoundDispatch(service,ROOT/WORK/'criticism-probe'/q,route)
        rows[q]=dict(measurement=dispatch.measure(request,schema),source_records=len(records),
            synthetic_candidates=len(fixture),roundtrip_exact=True)
    require(ref(ROOT,BASE/'live-calls.json')==ledger,'Probe changed charges')
    save(ROOT/WORK/'criticism-probe.json',dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,
        legal_acceptance=False,rows=rows,
        scope='Real production source sets with one synthetic candidate per source. Actual generated candidates still require ordinary measurement and response validation.'))
    print('Four criticism constructor probes passed; zero provider calls; candidates were synthetic.')


if __name__=='__main__':main()
