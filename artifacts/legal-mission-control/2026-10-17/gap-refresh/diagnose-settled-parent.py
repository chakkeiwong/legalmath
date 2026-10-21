import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import read,save,ref
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_campaign import provider
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_recovery,account_contract,account_encoding,account_instructions,account_input,account_output,downstream_instructions
WORK=Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery')
p=read(ROOT/PROGRAM); service=provider()
def forbidden(*a,**kw):raise AssertionError('No live completion or admission')
service.complete=forbidden; service.allowance.reserve=forbidden
product=PhasedProduct(ROOT,ROOT/WORK/'parent-diagnostic',service,
    read(ROOT/p['prerequisite_repair']['source']['path']),tokenizer(ROOT/TOKENIZER),limits=Limits(),
    active_questions=['evidence'],phase_admit=forbidden,phase_identity='diagnosis',
    requirement_account_profile=account_contract.PROFILE,requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,requirement_account_recovery=ref(ROOT,WORK/'recovery-evidence.json'),
    downstream_input_profile=p['repair_execution']['downstream_input_profile'],downstream_instruction_profile=downstream_instructions.PROFILE)
original=account_recovery.restore_record_order
def diff(a,b,path=''):
    if type(a)!=type(b):return [{'path':path,'old':str(a)[:350],'new':str(b)[:350]}]
    if isinstance(a,dict):return [r for k in sorted(a.keys()|b.keys()) for r in diff(a.get(k),b.get(k),path+'/'+k)]
    if isinstance(a,list):return ([{'path':path+'/length','old':len(a),'new':len(b)}] if len(a)!=len(b) else [])+[r for i,(x,y) in enumerate(zip(a,b)) for r in diff(x,y,path+'/'+str(i))]
    return [] if a==b else [{'path':path,'old':str(a)[:350],'new':str(b)[:350]}]
def capture(old,new):
    try:return original(old,new)
    except Exception:
        save(ROOT/WORK/'parent-mismatch.json',{'differences':diff(old,new),'original':old,'actual':new,'provider_calls':0})
        print(json.dumps(diff(old,new),indent=2)[:12000],flush=True)
        raise SystemExit(0)
account_recovery.restore_record_order=capture
records=[r for r in product.route.records.values() if r['kind'] in ('obligation','reading','case')]
i=4; record=records[i]; scope=set(product.requirement_questions(record))
questions=[q for q in product.route.envelope['original_questions'] if q['question_id'] in scope]
sources=product.route.retrieve(canonical(record['value']).decode())['record_ids']
for question in questions:sources+=product.route.retrieve(question['text'])['record_ids']
sources=[rid for rid in dict.fromkeys(sources) if scope & product.acquisition_questions(product.route.records[rid])]
product.note('detail-4','ASSESS_ORIGINAL_REQUIREMENT',questions,[product.route.records[r] for r in sources],
    {**record,'coverage':'Delivered sources join requirement and applicable question retrieval. Absence from this local selection is not absence from the corpus or the law; identify incomplete coverage explicitly.'},[record['id']])
raise AssertionError('Mismatch did not reproduce')
