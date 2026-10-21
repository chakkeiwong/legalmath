"""No-network comparison with the four exact failed production candidates."""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, BoundDispatch
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.phased import downstream_input, account_input, account_encoding, tool_input
from legalmath.interpretation.assurance.phased.synthesis_recovery import historical_request
from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import TOKENIZER
from scripts.legal_integration_campaign import provider
WORK = Path(__file__).parent
OLD = ROOT/'artifacts/legal-mission-control/2026-10-19/synthesis-resolution/live'


def main():
    program = read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
    envelope = read(ROOT/program['prerequisite_repair']['source']['path'])
    route = ContextRoute(envelope, tokenizer(ROOT/TOKENIZER), limits=Limits())
    service = provider()
    ledger = ref(ROOT,ROOT/'artifacts/legal-mission-control/2026-10-13/master/live-calls.json')
    reports = {}
    for q in ('p10','p14','evidence','gatecoin'):
        source = OLD/q/'product'
        require(route.records == read(source/'source-store.json'), 'Source population changed')
        result = read(source/'result.json')
        for finding in result['answers'][q]['findings']:
            folder = source/'calls'/finding['id']
            raw = read(folder/'raw.json')
            events = [json.loads(x) for x in raw['provenance']['events_jsonl'].splitlines() if x]
            messages = [e['item']['text'] for e in events if e.get('item',{}).get('type')=='agent_message'
                and e['item']['text'].strip()]
            require(len(messages)==1, 'Ambiguous original response')
            wire = read(folder/'reference-binding.json')
            original = historical_request(wire,reviewed=True)
            def saved(request,schema):
                require(request==original and schema==wire['original_schema'],'Changed original decoding contract')
                return deepcopy(wire)
            with patch.object(bounded_references,'prepare',saved):
                value=bounded_references.resolve(json.loads(messages[0]),wire,maximum_bytes=route.limits.decoded_output_bytes)
            require(value==finding['value']==read(folder/'result.json')['value'],'Changed original finding')
            finding['value']=value
        p=object.__new__(BoundedProduct)
        p.root,p.directory,p.route=ROOT,WORK/'probe'/q,route
        p.selected_tools,p.active_questions=(),(q,)
        p.downstream_input_profile=None
        captured=[]
        class Capture:
            def call(self,key,request,schema,validator):
                captured.append((key,request,schema))
                return {'status':'FAILED','error':'DEBUG_NO_DISPATCH'}
        p.dispatch=Capture()
        question=next(x for x in envelope['original_questions'] if x['question_id']==q)
        p.tools(q,question,None,findings=result['answers'][q]['findings'])
        require(len(captured)==1,'Unexpected constructor calls')
        key,request,schema=captured[0]
        dispatch=BoundDispatch(service,WORK/'probe'/q/'calls',route,maximum_calls=8100)
        phase=read(source/'phases'/('call-candidates-'+q)/'phase.json')
        require(dispatch.request_identity(request,schema)==phase['contract']['calls'][0]['identity'],
            'Actual failed candidate identity changed')
        try: dispatch.measure(request,schema)
        except LegalMathError as exc:
            require(exc.code=='E_RESOURCE_LIMIT','Different original failure')
            original_failure=str(exc.details or exc)
        else: raise AssertionError('Original failure did not reproduce')
        p.downstream_input_profile=downstream_input.PROFILE
        p.downstream_capacity_profile=downstream_input.CAPACITY_PROFILE
        selected=p.tool_request(request,request['records'])
        plain=bounded_references.prepare(request,schema)
        packed=bounded_references.prepare(selected,schema)
        expanded=account_encoding.expand({'request':packed['request'],'response_schema':packed['schema']})
        restored=account_input.expand(tool_input.expand(expanded['request']))
        for field in ('downstream_input_profile','downstream_capacity_profile'): del restored[field]
        require(restored==plain['request'] and expanded['response_schema']==plain['schema'],
            'Candidate transport changed content or schema')
        try:
            measured=dispatch.measure(selected,schema)
            provider_measured=service.measure(packed['request'],packed['schema'])
            fit=True
        except LegalMathError as exc:
            fit=False;measured={'error':exc.code,'reason':str(exc.details or exc)};provider_measured=None
        diagnosis=diagnose(ROOT,source,q)
        require(diagnosis['prepared'] and len(diagnosis['optional_incomplete_phases'])==1,
            'Prepared baseline still blocked or optional error lost')
        save(WORK/'requests'/(q+'.json'),{'key':key,'request':selected,'schema':schema})
        reports[q]=dict(actual_request_identity_matches=True,original_failure=original_failure,
            lossless_roundtrip=True,fits=fit,measurement=measured,provider_measurement=provider_measured,
            baseline_prepared=True,optional_failures=diagnosis['optional_incomplete_phases'],
            prepared_result=ref(ROOT,source/'result.json'),phase=ref(ROOT,source/'phases'/('call-candidates-'+q)/'phase.json'))
        print(json.dumps({'question':q,**{k:v for k,v in reports[q].items() if k not in ('optional_failures','prepared_result','phase')}}),flush=True)
    require(ref(ROOT,ROOT/'artifacts/legal-mission-control/2026-10-13/master/live-calls.json')==ledger,'Provider ledger changed')
    save(WORK/'replay.json',dict(profile='exact-candidate-replay.v1',reports=reports,provider_calls=0,
        ledger_unchanged=True,legal_acceptance=False,verdict='PASS' if all(r['fits'] for r in reports.values()) else 'CAPACITY_REMAINS'))

if __name__=='__main__': main()
