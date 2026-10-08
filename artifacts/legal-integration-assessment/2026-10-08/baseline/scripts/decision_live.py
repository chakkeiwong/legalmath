"""Execute bounded checks over complete frozen investigations and malformed outputs."""
from pathlib import Path
import json
from legalmath.canonical import digest,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import parse
from legalmath.interpretation.search.models import Reading
from legalmath.interpretation.search.formal import bundle
from legalmath.interpretation.search.providers import Allowance,CodexProvider
from legalmath.interpretation.assurance.control_investigation import BoundedReader,investigate
from legalmath.interpretation.assurance.lowering import SyntaxProposal,Correspondence,request,lower,review_request,check_review
from legalmath.interpretation.assurance.diversity import save

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/implementation/interpretation-round13'
AT='2026-09-25T00:00:00.000000Z'

def load_case(cid):
    p=DOC/'inputs'/(cid+'.json')
    if raw_digest(p.read_bytes())!=json.loads((DOC/'inputs-lock.json').read_text())[cid]:
        raise LegalMathError('E_INTEGRITY')
    value=json.loads(p.read_text())
    for name,sha in value['origin'].items():
        if raw_digest((ROOT/name).read_bytes())!=sha:raise LegalMathError('E_INTEGRITY')
    return value

def lowerings(provider,work):
    reader=BoundedReader(provider,work/'syntax',{'phase':'frozen-raw-lowering.v1','at':AT},maximum_actions=12)
    rows=[]
    for cid in ('25ec71','24ec50'):
        packet=load_case(cid)['packet']
        base=ROOT/'artifacts/interpretation/round12/P4/attempt-04/live'/cid/'model-evidence'
        chosen=[]
        for path in sorted(base.glob('action-*/result.json')):
            raw=json.loads(path.read_text())
            for item in raw.get('value',{}).get('proposals',[]):
                reading=item['reading']
                try:
                    parse(Reading,reading)
                    if reading['formalization'] is None:continue
                    bundle(reading,packet,AT)
                except LegalMathError:
                    if len(chosen)<2:chosen.append((path,reading))
        for path,reading in chosen:
            rid=digest(reading)
            proposal=reader.call(request(reading,packet),SyntaxProposal,
                                 lambda v:lower(reading,v,packet,AT))
            row={'case_id':cid,'original_path':str(path.relative_to(ROOT)),
                 'original_file_sha256':raw_digest(path.read_bytes()),'original':reading,'original_hash':rid}
            if proposal is None:
                row['status']='UNENCODED_READING_RETAINED'
            else:
                review=reader.call(review_request(proposal,packet),Correspondence,
                                   lambda v:check_review(proposal,v,packet))
                row['lowering']=review or proposal
                row['status']=(review or proposal)['status']
            rows.append(row);save(work/'lowering-results.json',rows)
    return rows

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    live_root=ROOT/'artifacts/interpretation/round13/complete-live'
    checkpoint=json.loads((DOC/'completion-checkpoint.json').read_text())
    for name,sha in checkpoint['prior_files'].items():
        if raw_digest((ROOT/name).read_bytes())!=sha:raise LegalMathError('E_INTEGRITY')
    ceiling=checkpoint['absolute_ceiling']
    if ceiling!=400 or checkpoint['calls_at_checkpoint']!=320:raise LegalMathError('E_RESOURCE_LIMIT')
    provider=CodexProvider(allowance=Allowance(ROOT/'artifacts/interpretation/round7/live-allowance.json',500,reservation_ceiling=ceiling))
    lowered=lowerings(provider,live_root)
    cases=[]
    for cid in ('26ec2','23ec46'):
        data=load_case(cid)
        prior=BoundedReader(provider,live_root/cid,{'case':cid,'at':AT,'input':digest(data)},maximum_actions=30)
        directory=live_root/cid
        if cid=='26ec2':
            directory=live_root/(cid+'-completion')
            reader=BoundedReader(provider,directory,{'case':cid,'at':AT,'input':digest(data),
                'completion_checkpoint':digest(checkpoint)},maximum_actions=80,reuse_from=[prior])
        else:reader=prior
        print('Full investigation '+cid+' claims='+str(len(data['claims']))+' candidates='+str(len(data['candidates'])),flush=True)
        result=investigate(data['packet'],data['claims'],data['candidates'],data['controls'],reader,directory/'checks',AT)
        cases.append({'case_id':cid,'result':result,'directory':str(directory),
                      'model_actions':reader.provider.journal.report()['consumed_actions']})
        save(out/'progress.json',cases)
    value={'cases':cases,'lowerings':lowered,'status':'EXECUTED_WITH_RESIDUALS',
           'call_ceiling':ceiling,'initial_increment_ceiling':320,'full_input_accounting':True,'independent_model_families':1,
           'legal_correctness_established':False,'release_eligible':False}
    save(out/'result.json',value)
    # Bind all raw model receipts/outputs and pending checks without claiming a
    # second independent observation from cached evidence.
    save(out/'live-evidence-manifest.json',{'files':{str(p.relative_to(ROOT)):raw_digest(p.read_bytes())
         for p in sorted(live_root.rglob('*')) if p.is_file() and p.name!='.lock'}})
    return value
