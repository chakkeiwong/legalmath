"""Exercise real successor product entry without model calls or active writes."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import json,os,sys,time
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import legal_window_continuation as a
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts.legal_mission_execution import read,save,ref,require,digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition as context,capacity_checkpoint

class Captured(BaseException): pass

def main():
    started=time.monotonic();folder=a.WORK/'offline-resume-registered'
    program=deepcopy(read(ROOT/a.WORK/'registration-stage/program.json'))
    program[a.KEY]['runtime']=str(folder/'runtime')
    service=campaign.provider();captured={}
    def forbidden(*args,**kwargs): raise AssertionError('Offline replay attempted provider work')
    service.complete=service.check_service=forbidden
    ledger=ref(ROOT,a.BASE/'live-calls.json')
    service.check=lambda:read(ROOT/a.BASE/'live-calls.json')
    def capture(product,qid,question,answer,details,**kwargs):
        captured.update(product=product,qid=qid,question=question,answer=answer)
        save(ROOT/folder/'captured.json',dict(qid=qid,question=question,answer=answer,answer_hash=digest(answer)))
        print(json.dumps(dict(stage='production_answer_captured',answer_hash=digest(answer))),flush=True)
        raise Captured()
    original_read=live.read
    print(json.dumps(dict(stage='production_reconstruction',runtime=program[a.KEY]['runtime'])),flush=True)
    def local_read(path): return program if Path(path)==ROOT/a.PROGRAM else original_read(path)
    with patch.object(live,'read',local_read),patch.object(live,'phase_admit',lambda owner:forbidden),patch.object(PhasedProduct,'audit_answer',capture):
        try: live.product_route('p14',None,service)
        except Captured: pass
    require(captured.get('qid')=='p14','Wrong production entry')
    product,answer=captured['product'],captured['answer']
    source=ROOT/a.SOURCE/'arms/p14/baseline'
    receipts=[(p,read(p)) for p in sorted(source.glob('context-review-*.json'))]
    require(len(receipts)==696,'Wrong retained context census')
    chosen=[]
    for kind,predicate in (('success',lambda r:r['result']['status']=='VALIDATED'),
        ('invalid_quote',lambda r:'Invalid response answer quotation' in str(r['result'].get('reason',''))),
        ('dropped_need',lambda r:r['result'].get('reason')=='Necessary original context need was lost'),
        ('deadline',lambda r:r['result'].get('reason')=='Phase exceeds original global window')):
        path,receipt=next((p,r) for p,r in receipts if predicate(r))
        require(receipt['answer_hash']==digest(answer),'Answer changed')
        request,schema,rows,_,failures=context.prepare(product,'p14',captured['question'],answer,receipt['item'],receipt['original_review'])
        key='audit-context-disposition-p14-'+digest([receipt['item']['id'],receipt['original_review']['value'],answer])[:24]
        call=dict(key=key,request=request,schema=schema,validate=lambda value:context.validate(product,'p14',value,answer,receipt['item'],rows,request['records'],failures))
        # Production capacity.phase prepares calls before checkpoint matching.
        call=product.prepare_calls([call])[0]
        checkpoint=read(ROOT/product.capacity_checkpoint['path'])
        previous=checkpoint['calls'].get(key)
        save(ROOT/folder/(kind+'-comparison.json'),dict(key=key,
            request=call['request'],schema=call['schema'],
            checkpoint_row=previous,
            exact_request=None if previous is None else read(ROOT/previous['request']['path'])==call['request'],
            exact_schema=None if previous is None else read(ROOT/previous['schema']['path'])==call['schema']))
        retained=capacity_checkpoint.retained(product,call)
        if kind=='deadline': require(retained is None,'Unsent deadline refusal was imported')
        elif kind=='success': require(retained['status']=='VALIDATED' and retained['value']==receipt['result']['value'],'Success changed')
        else: require(retained==receipt['result'],'Invalid response lost or resampled')
        chosen.append(dict(kind=kind,receipt=ref(ROOT,path),key=key,status=None if retained is None else retained['status']))
        print(json.dumps(dict(stage='checked',**chosen[-1])),flush=True)
    require(ref(ROOT,a.BASE/'live-calls.json')==ledger,'Offline replay changed charges')
    journal=product.directory/'calls/dispatch.json'
    require(not journal.exists() or not read(journal)['calls'],'Offline replay reserved a call')
    result=dict(verdict='PASS',provider_calls=0,unchanged_answer=True,checks=chosen,ledger=ledger,
        legal_acceptance=False,wall_seconds=time.monotonic()-started)
    save(ROOT/folder/'result.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__': main()
