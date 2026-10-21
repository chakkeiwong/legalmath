import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import json,sys,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_synthesis_continuation import WORK
from scripts.legal_mission_execution import read,save,ref,verify,require
from legalmath.canonical import canonical,digest
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_references import resolve
from legalmath.interpretation.assurance.phased.account_receipt import historical_request
from legalmath.interpretation.assurance.phased.account_output import output_token_limit
from legalmath.interpretation.assurance.phased.downstream_instructions import validate_correction
from jsonschema import validate
began=time.monotonic();program=read(ROOT/PROGRAM);ledger=read(ROOT/BASE/'live-calls.json');ledger_ref=ref(ROOT,BASE/'live-calls.json')
encode=tokenizer(ROOT/TOKENIZER);limits=Limits()
class NoCalls:
    live=False
    def complete(self,*a,**kw):raise AssertionError('No dispatch in receipt validation')
out=[]
for q,key,slot in [('p14','reduce-p14-0-6',3097),('gatecoin','reduce-gatecoin-0-69',3099)]:
    directory=Path('artifacts/legal-mission-control/2026-10-18/request-variants')/q/'original'
    original=Path(program['repair_execution']['common_directories'][q])/'calls'/key
    row=dict(question=q,key=key,slot=slot,production_promoted=False)
    try:
        manifest=read(ROOT/directory/'manifest.json')
        require(manifest['global_slot']==slot,'Wrong diagnostic slot')
        for reference in manifest['files'].values():verify(ROOT,reference)
        prepared=read(ROOT/original/'reference-binding.json')
        wire=read(ROOT/directory/'request.json');schema=read(ROOT/directory/'schema.json');raw=read(ROOT/directory/'result.json')
        require(prepared['request']==wire and prepared['schema']==schema,'Diagnostic differs from production wire')
        require(ledger['calls'][slot-1]['request_hash']==digest(wire),'Diagnostic charge changed')
        prepared['original_request']=historical_request(prepared)
        request=prepared['original_request']
        require(request==read(ROOT/original/'request.json'),'Decoded original changed')
        validate(raw,schema)
        require(len(canonical(raw))<=limits.output_bytes and len(encode(canonical(raw).decode()))<=output_token_limit(request,limits),'Wire output over limit')
        decoded=resolve(raw,prepared,maximum_bytes=limits.decoded_output_bytes)
        validate(decoded,prepared['original_schema'])
        require(len(canonical(decoded))<=limits.decoded_output_bytes and len(encode(canonical(decoded).decode()))<=limits.decoded_output_tokens,'Decoded output over limit')
        require(len(decoded['considered'])==len(set(decoded['considered'])) and set(decoded['considered'])==set(request['required_considered']),'Synthesis omitted input')
        product=BoundedProduct(ROOT,ROOT/WORK/('diagnostic-validation-'+q),NoCalls(),
            read(ROOT/program['prerequisite_repair']['source']['path']),encode,limits=limits,maximum_calls=8100,active_questions=[q])
        product.citations(decoded,request['records']);validate_correction(request,decoded)
        require(decoded['support'] or decoded['unresolved'],'Unsupported settled synthesis')
        save(ROOT/WORK/('diagnostic-decoded-'+q+'.json'),decoded)
        row.update(verdict='PASS',decoded=ref(ROOT,WORK/('diagnostic-decoded-'+q+'.json')),
            manifest=ref(ROOT,directory/'manifest.json'),original_binding=ref(ROOT,original/'reference-binding.json'),
            source_gaps=len(decoded['source_gaps']),support=len(decoded['support']),unresolved=len(decoded['unresolved']))
    except Exception as exc:
        row.update(verdict='FAIL',error=getattr(exc,'code',type(exc).__name__),reason=str(getattr(exc,'details',None) or exc))
    out.append(row)
require(ref(ROOT,BASE/'live-calls.json')==ledger_ref,'Audit modified global ledger')
result=dict(plan=ref(ROOT,WORK/'diagnostic-response-review.md'),rows=out,provider_calls=0,ledger_unchanged=True,
    legal_acceptance=False,production_promoted=False,wall_seconds=time.monotonic()-began)
save(ROOT/WORK/'diagnostic-response-validation.json',result);print(json.dumps(result,indent=2))
