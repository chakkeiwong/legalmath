"""Fixed paths and retained evidence for the round-14 execution."""
from pathlib import Path
import json
import shutil
from collections import Counter
from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.controls import validate_plan
from legalmath.errors import LegalMathError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round14'
DOC=ROOT/'docs/implementation/interpretation-round14'
OLD=ROOT/'artifacts/interpretation/round13'
PY=ROOT/'.venv/bin/python'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
LEDGER=ROOT/'artifacts/interpretation/round7/live-allowance.json'
AT='2026-09-26T00:00:00.000000Z'
CEILING=480

from legalmath.interpretation.assurance.control_investigation import BoundedReader

class CircuitReader(BoundedReader):
    """Transport/environment failures stop dispatch, not interpretation search."""
    def call(self, request, model, validate):
        result=super().call(request,model,validate)
        if result is None and not self.stopped_reason:
            actions=self.provider.journal.report()['actions']
            if actions:
                last=actions[-1]
                if last['status'] in ('FAILED','INTERRUPTED') and last.get('error') in ('E_DEPENDENCY','E_RESOURCE_LIMIT'):
                    self.stopped_reason='DISPATCH_BLOCKED: '+str(last.get('details',last.get('error')))
        return result

def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return raw_digest(Path(path).read_bytes())
def used(): return len(read(LEDGER)['calls'])
def case(cid):
    from decision_live import load_case
    return load_case(cid)
def previous(cid):
    return OLD/'complete-live'/('26ec2-completion' if cid=='26ec2' else cid)/'checks'

def baseline():
    path=DOC/'baseline.json'
    if path.exists():
        value=read(path)
        for name,h in value['retained_inputs'].items():
            if sha(ROOT/name)!=h:raise LegalMathError('E_INTEGRITY',details=name)
        return value
    m=read(OLD/'delivery-manifest.json')
    for name,h in m['files'].items():
        if sha(OLD/name)!=h:raise LegalMathError('E_INTEGRITY',details=name)
    for name,h in m['external_files'].items():
        if sha(ROOT/name)!=h:raise LegalMathError('E_INTEGRITY',details=name)
    files=[OLD/'delivery-manifest.json',OLD/'final-report.json',OLD/'evaluation.json',
           OLD/'post-execution-review.json',ROOT/'docs/plans/assurance-after-round13.md']
    for cid in ('26ec2','23ec46'):
        files += [previous(cid)/'result.json',previous(cid)/'routing-plan.json',
                  ROOT/'docs/implementation/interpretation-round13/inputs'/(cid+'.json')]
    value={'retained_inputs':{str(p.relative_to(ROOT)):sha(p) for p in files},
           'ledger_start':used(),'ledger_prefix':read(LEDGER),
           'monograph':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'docs/monograph/chapters').glob('*.tex'))},
           'monograph_pages':265,'existing_source_verified':True}
    DOC.mkdir(parents=True,exist_ok=True);save(path,value)
    # Protected copies allow textual preservation checks after adding the new unit.
    for path in (ROOT/'docs/monograph/chapters').glob('*.tex'):
        dest=OUT/'manuscript-baseline'/path.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    return value

def inventory(out):
    baseline();rows=[];unencoded=[];pairs=[]
    for cid in ('26ec2','23ec46'):
        data=case(cid);p=read(previous(cid)/'routing-plan.json');r=read(previous(cid)/'result.json')
        validate_plan(p,data['packet'],data['claims'],data['candidates'])
        full={(c['claim_id'],k) for c in data['claims'] for k in data['candidates']}
        checks={(c['claim_id'],c['candidate_id']):c for c in r['checks']}
        excluded={(c['claim_id'],c['candidate_id']):c for c in r['excluded_pairs']}
        if set(checks)&set(excluded) or set(checks)|set(excluded)!=full or len(checks)!=len(r['checks']):
            raise LegalMathError('E_INTEGRITY')
        if r['pending_pairs'] or not r['execution_complete']:raise LegalMathError('E_JOB_STATE')
        for key in sorted(full):
            pairs.append({'case_id':cid,'claim_id':key[0],'candidate_id':key[1],
                          'original':checks.get(key) or excluded[key],
                          'disposition':'EXCLUDED' if key in excluded else
                            'ENCODING_FAILURE' if key[1] in r['unsupported_candidates'] else 'MODEL_ASSESSMENT'})
        for ident,error in r['unsupported_candidates'].items():
            unencoded.append({'case_id':cid,'candidate_id':ident,'error':error,
                              'original':data['candidates'][ident]})
        rows.append({'case_id':cid,'full_pairs':len(full),'required_pairs':len(checks),'excluded_pairs':len(excluded),
                     'label_counts':dict(Counter(c['label'] for c in r['checks'])),
                     'concerns':r['additional_concerns'],'missing_questions':r['missing_questions']})
    pdf=read(OLD/'execution-reviewed/action-0002/pdf/result.json')
    issues=[i for row in pdf['rows'] for i in row['reconciliation']['remaining']]
    if len(pairs)!=1155 or len(unencoded)!=8 or len(issues)!=339:raise LegalMathError('E_INTEGRITY')
    result={'status':'BOUND_AND_ACCOUNTED','cases':rows,'pairs':pairs,'unencoded':unencoded,'pdf_issues':issues,
            'counts':{'full_pairs':len(pairs),'unencoded':len(unencoded),'pdf_issues':len(issues),
                      **dict(Counter(r['disposition'] for r in pairs))},'release_eligible':False}
    save(out/'result.json',result);save(OUT/'issue-inventory.json',result);return result
