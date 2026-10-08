#!/usr/bin/env python3
"""Frozen, resumable three-arm source conversion development comparison."""
import argparse
import math
from pathlib import Path
import subprocess
import sys
import time
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.catala.native.contracts import Candidate, validate_candidate
from legalmath.catala.native.converter import Limits, convert, generation_request as native_request
from legalmath.catala.native.runtime import build, verify_cases, verify_build
from legalmath.catala.native.source_review import admit_heldout
from legalmath.interpretation.search.models import Generation, validate_generation, generation_request as ir_request
from legalmath.interpretation.search.providers import Allowance, CodexProvider, verify_allowance_checkpoint
from legalmath.interpretation.search.formal import bundle, RULE
from legalmath.java.manifest import build_candidate, verify_candidate

ROOT=Path(__file__).resolve().parents[1]
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
TOOLCHAIN={'compiler':ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
           'upstream':ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
           'lock':ROOT/'docs/implementation/catala/toolchain-lock.json'}
LEDGER=Path('/home/chakwong/python/legalmath/artifacts/interpretation/round7/live-allowance.json')
ARMS=('ruleir-generation','native-minimal','native-reviewed')
TYPES={'boolean':'bool','integer':'integer','money':'money_hkd','date':'date'}


def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_bytes(canonical(value));temp.replace(path)


def inputs():
    paths=[*sorted((ROOT/'src/legalmath/catala/native').glob('*.py')),*sorted((ROOT/'src/legalmath/catala/native').glob('*.java')),
           ROOT/'scripts/catala_gap_study.py',ROOT/'scripts/prepare_catala_source_packet.py',
           ROOT/'docs/plans/catala-gap-closure.md',ROOT/'docs/implementation/catala/gap-closure/trace-toolchain.json',
           ROOT/'src/legalmath/interpretation/search/models.py',ROOT/'src/legalmath/interpretation/search/formal.py',
           ROOT/'src/legalmath/interpretation/search/providers.py',ROOT/'src/legalmath/java/manifest.py']
    return {str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in paths}


class Recorded:
    def __init__(self, provider, directory, max_calls=2):
        self.provider=provider;self.directory=directory;directory.mkdir(parents=True,exist_ok=True)
        self.provider_id=provider.provider_id;self.routing=provider.routing;self.live=True;self.max_calls=max_calls
    def complete(self,request,schema,settings):
        commitment={'request':request,'schema':schema,'limits':settings.__dict__}
        saved=sorted(self.directory.glob('*.request.json'))
        for prior in saved:
            if loads(prior.read_bytes())!=commitment:continue
            p=self.directory/prior.name.split('.')[0]
            answer=p.with_suffix('.response.json')
            if answer.exists():
                from legalmath.interpretation.search.providers import Completion
                old=loads(answer.read_bytes());return Completion(old['value'],old['provenance'])
            error=p.with_suffix('.failure.json')
            if error.exists():
                old=loads(error.read_bytes());raise LegalMathError(old['code'],details=old['details'])
            raise LegalMathError('E_JOB_STATE',details='Interrupted call remains counted; do not redispatch')
        if len(saved)>=self.max_calls:raise LegalMathError('E_RESOURCE_LIMIT')
        p=self.directory/str(len(saved)+1)
        write(p.with_suffix('.request.json'),commitment)
        print(str(self.directory)+': dispatch '+str(len(saved)+1),flush=True)
        try:
            result=self.provider.complete(request,schema,settings)
            write(p.with_suffix('.response.json'),{'value':result.value,'provenance':result.provenance})
            return result
        except LegalMathError as e:
            write(p.with_suffix('.failure.json'),{'code':e.code,'details':e.details});raise


def check_native(directory,cases):
    return verify_cases(directory,cases,JDK,compiler=TOOLCHAIN['compiler'])


def native_minimal(row,out,provider):
    task=row['task'];previous=feedback=None
    for attempt in range(4):
        try:
            proposal=provider.complete(native_request(task,previous,feedback),Candidate.model_json_schema(),Limits()).value
            previous=proposal;c=validate_candidate(task,proposal)
            directory=out/('build-'+str(attempt))
            if (directory/'build.json').exists():verify_build(directory)
            else:build(task,c,directory,JDK,**TOOLCHAIN)
            if c['unresolved']:return {'status':'ABSTAIN','questions':c['unresolved']}
            return {'status':'BUILT','directory':directory.name}
        except LegalMathError as e:
            feedback={'kind':'VALIDATION_OR_COMPILER_FAILURE','code':e.code,'details':e.details}
            write(out/('failure-'+str(attempt)+'.json'),feedback)
    return {'status':'REJECTED'}


def ir_generation(row,out,provider):
    task=row['task'];feedback=[]
    expected={f['name']:TYPES[f['type']] for f in task['inputs']}
    for attempt in range(4):
        request=ir_request(task['packet'],'normative',diagnostics=feedback)
        request['selected_question']=task['question']
        request['fixed_factual_interface']=task['inputs']
        request['instructions']+=' For this component study, use exactly the supplied input names/types, retain their meanings, and give the first reading the selected output question. The output has type '+TYPES[task['outputs'][0]['type']]+'. Do not broaden the question to whole-circular compliance.'
        try:
            value=validate_generation(provider.complete(request,Generation.model_json_schema(),Limits()).value,task['packet'])
            write(out/('generation-'+str(attempt)+'.json'),value)
            reading=value['readings'][0];formal=reading['formalization']
            if formal is None:return {'status':'ABSTAIN','questions':value['questions']+reading['questions']}
            if {f['name']:f['type'] for f in formal['facts']}!=expected or formal['result_type']!=TYPES[task['outputs'][0]['type']]:
                raise LegalMathError('E_TYPE',details='Generated factual interface differs from supplied task')
            b=bundle(reading,task['packet'],task['valid_from'])
            built=build_candidate(b,out/('build-'+str(attempt)),JDK)
            write(out/'selected.json',{'reading':reading,'bundle':b,'build':built})
            if value['questions'] or reading['questions'] or any(x['status'] in ('DEFERRED','UNCERTAIN') for x in value['coverage']):
                return {'status':'ABSTAIN','questions':value['questions']+reading['questions']}
            return {'status':'BUILT','directory':'build-'+str(attempt)}
        except LegalMathError as e:
            feedback=[{'code':e.code,'details':e.details}];write(out/('failure-'+str(attempt)+'.json'),feedback)
    return {'status':'REJECTED'}


def check_ir(row,out):
    selected=loads((out/'selected.json').read_bytes());b=selected['bundle'];cases=[]
    for c in row['cases']:
        snap=c['snapshot'];facts={}
        for f in b['facts']:
            v=snap['facts'][f['name']]
            facts[f['name']]={'type':f['type'],'status':v['status'],'value':v['value'],'evidence_ids':snap['evidence']['/'+f['name']],
                              'valid_from':v['valid_from'],'valid_until':v['valid_until'],'recorded_at':v['recorded_at']}
        expected=c['expected']['value']['result'];typ=b['rules'][0]['type']
        cases.append({'id':c['id'],'bundle':b,'snapshot':{'subject_id':snap['subject_id'],'facts':facts},'rule_id':RULE,
                      'valid_at':snap['valid_at'],'known_at':snap['known_at'],
                      'expected':{'status':('TRUE' if expected else 'FALSE') if typ=='bool' else 'VALUE','value':expected}})
    write(out/'cases.json',cases)
    return verify_candidate(selected['build'],cases,JDK)


def paired(rows,a,b):
    # Each source family contributes one joint pass outcome, avoiding pseudo-replication.
    families=sorted({r['lineage_family'] for r in rows});wins=losses=ties=0
    for family in families:
        subset=[r for r in rows if r['lineage_family']==family]
        x=all(r['arms'][a]['status']=='PASS' for r in subset);y=all(r['arms'][b]['status']=='PASS' for r in subset)
        wins+=x and not y;losses+=y and not x;ties+=x==y
    n=wins+losses
    p=min(1,2*sum(math.comb(n,i) for i in range(min(wins,losses)+1))/2**n) if n else 1
    # Hoeffding's bounded paired-difference interval, conditional on independent sampled families.
    mean=(wins-losses)/len(families);radius=(2*math.log(40)/len(families))**0.5
    return {'a':a,'b':b,'source_families':len(families),'a_only':wins,'b_only':losses,'ties':ties,
            'paired_difference':format(mean,'.6f'),'conditional_95_interval':[format(max(-1,mean-radius),'.6f'),format(min(1,mean+radius),'.6f')],
            'exact_discordant_sign_p':format(p,'.6f'),
            'assumptions':'Independent representative families for interval and exchangeable arm success under sign null; convenience selection does not establish these assumptions.',
            'ranking':'UNSUPPORTED; development sampling and independent adjudication veto promotion regardless of p-value'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--packet', type=Path, default=ROOT/'artifacts/catala/gap-closure/source-review/packet.json')
    args=parser.parse_args()
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    packet=loads(args.packet.read_bytes())
    # Keep witnesses and adjudication metadata for heldout admission. Generation
    # functions receive only row['task'], never the private reference cases.
    if args.freeze:
        if (out/'freeze.json').exists():raise RuntimeError('Already frozen')
        new_calls=24
        balance=loads(LEDGER.read_bytes());ceiling=min(balance['maximum'],len(balance['calls'])+new_calls)
        if ceiling-len(balance['calls'])<new_calls:raise RuntimeError('Insufficient remaining shared allowance for the declared ceiling')
        freeze={'packet_hash':digest(packet),'inputs':inputs(),'ledger':str(LEDGER),'checkpoint_hash':digest(balance),
                'start_calls':len(balance['calls']),'ceiling':ceiling,'max_per_arm':2,'declared_new_calls':new_calls,'arms':list(ARMS),
                'criterion':'Complete hidden reference success per task after bounded interface/compile repair; all failure/abstention outcomes counted.',
                'nonclaims':'No legal correctness, default promotion or comparison with the full RuleIR assurance/search algorithm.',
                'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
        write(out/'freeze.json',freeze);write(out/'packet.json',packet)
        for name in freeze['inputs']:
            p=out/'reviewed-sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        write(out/'admission.json',admit_heldout(packet,{r['lineage_family'] for r in packet['corpus']},{}))
        print(canonical(freeze).decode());return
    freeze=loads((out/'freeze.json').read_bytes())
    if freeze['inputs']!=inputs() or freeze['packet_hash']!=digest(packet):raise RuntimeError('Frozen implementation/source changed')
    verify_allowance_checkpoint(LEDGER,freeze['checkpoint_hash'])
    provider=CodexProvider(allowance=Allowance(LEDGER,500,reservation_ceiling=freeze['ceiling']))
    started=time.monotonic();rows=[]
    for i,row in enumerate(packet['corpus']):
        name=row['task']['task_id'];results={}
        for arm in ARMS[i%3:]+ARMS[:i%3]:
            directory=out/name/arm;directory.mkdir(parents=True,exist_ok=True)
            if (directory/'result.json').exists():results[arm]=loads((directory/'result.json').read_bytes());continue
            recorder=Recorded(provider,directory/'calls',freeze['max_per_arm']);before=time.monotonic()
            try:
                if arm=='ruleir-generation':state=ir_generation(row,directory,recorder)
                elif arm=='native-minimal':state=native_minimal(row,directory,recorder)
                else:
                    state=convert(row['task'],directory/'conversion',recorder,JDK,**TOOLCHAIN,resume=(directory/'conversion/state.json').exists())
                    if state['status']=='READY_FOR_BEHAVIOR_CHECK':state={'status':'BUILT','directory':'conversion/'+state['build_directory']}
                result={'generation':state,'status':'ABSTAIN_OR_REJECTED'}
                if state['status']=='BUILT':
                    verification=check_ir(row,directory) if arm=='ruleir-generation' else check_native(directory/state['directory'],row['cases'])
                    write(directory/'verification.json',verification)
                    result.update(status='PASS',reference_cases=len(row['cases']))
            except LegalMathError as e:result={'status':'FAIL','failure':{'code':e.code,'details':e.details}}
            result['wall_ms']=int((time.monotonic()-before)*1000)
            result['dispatches']=len(list((directory/'calls').glob('*.request.json')))
            write(directory/'result.json',result);results[arm]=result
            print(name+' '+arm+' '+result['status'],flush=True)
        rows.append({'task_id':name,'lineage_family':row['lineage_family'],'arms':results})
    end=loads(LEDGER.read_bytes())
    report={'rows':rows,'comparison':[paired(rows,'native-reviewed',a) for a in ('ruleir-generation','native-minimal')],
            'source_adjudication':'PENDING_INDEPENDENT_HUMAN','ranking':'UNSUPPORTED','default_readiness':False,
            'shared_start':freeze['start_calls'],'shared_end':len(end['calls']),'maximum':end['maximum']}
    report['own_dispatches']=sum(r['arms'][a]['dispatches'] for r in rows for a in ARMS)
    write(out/'results.json',report)
    write(out/'run-manifest.json',{'commit':freeze['git_commit'],'command':sys.argv,'python':sys.executable,'jdk':str(JDK),'compiler':str(TOOLCHAIN['compiler']),
          'CPU_GPU':'CPU; no GPU library imported','seed':'N/A provider samples unseeded; deterministic rotated arm order',
          'wall_ms':int((time.monotonic()-started)*1000),'data_version':freeze['packet_hash'],'freeze_hash':digest(freeze),
          'plan':'docs/plans/catala-gap-closure.md','result':'results.json'})
    print(canonical(report).decode())

if __name__=='__main__':main()
