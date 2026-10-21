import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import json,sys,time,itertools
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_synthesis_continuation import WORK
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_campaign import provider
from legalmath.interpretation.assurance.bounded_product import BoundedProduct,NOTE
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.phased import downstream_instructions
from legalmath.errors import LegalMathError
began=time.monotonic();program=read(ROOT/PROGRAM);ledger=ref(ROOT,BASE/'live-calls.json')
source=Path(program['settled_recovery']['common_directories']['evidence'])/'reduction-evidence-3.json'
rows=read(ROOT/source);service=provider()
def forbidden(*a,**kw):raise AssertionError('No model call in capacity diagnostic')
service.complete=forbidden;service.allowance.reserve=forbidden
product=BoundedProduct(ROOT,ROOT/WORK/'evidence-capacity-product',service,
    read(ROOT/program['prerequisite_repair']['source']['path']),tokenizer(ROOT/TOKENIZER),
    limits=Limits(),maximum_calls=8100,active_questions=['evidence'],
    downstream_input_profile=program['repair_execution']['downstream_input_profile'])
question=next(q for q in product.route.envelope['original_questions'] if q['question_id']=='evidence')
results=[]
for size in (1,2):
    for members in itertools.combinations(rows,size):
        members=list(members)
        request=product.request('SYNTHESIZE_FINDINGS',question,product.source_records(members),
            payload=members,expected=[r['id'] for r in members])
        request['synthesis_scope']=('Produce a bounded source-supported synthesis for the original '
            'question, preserving operative conditions, exceptions, supported alternatives and '
            'unresolved dependencies. A single member is normalized once for subsequent combination. '
            'This summary is a proposal: complete original accounts and sources remain separately '
            'retained for independent answer review. Do not equate considered-ID coverage with '
            'semantic completeness. State any unfinished analysis explicitly in unresolved.')
        request=downstream_instructions.annotate(request)
        try:
            measurement=product.dispatch.measure(request,NOTE)
            row=dict(fits=True,measurement=measurement)
        except LegalMathError as exc:
            require(exc.code=='E_RESOURCE_LIMIT','Unexpected capacity diagnostic failure')
            row=dict(fits=False,error=exc.code,reason=exc.details)
        results.append(dict(ids=[r['id'] for r in members],**row))
require(ref(ROOT,BASE/'live-calls.json')==ledger,'Diagnostic changed live ledger')
out=dict(source=ref(ROOT,source),plan=ref(ROOT,WORK/'evidence-capacity-audit.md'),rows=results,
    provider_calls=0,ledger_unchanged=True,legal_acceptance=False,wall_seconds=time.monotonic()-began)
save(ROOT/WORK/'evidence-capacity-diagnosis.json',out);print(json.dumps(out,indent=2))
