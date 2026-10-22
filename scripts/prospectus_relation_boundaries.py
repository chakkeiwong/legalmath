"""Execute the admitted optional boundary repair in short retained stages."""
from copy import deepcopy
import argparse
import gzip
from pathlib import Path
import json
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import read,write,file_hash
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.relation_boundaries import discover_bounded,consume_with_suggestions

BASE=ROOT/'docs/implementation/prospectus-execution-authority/attempts/relation-discovery'
HERE=BASE/'attempt-004'
PLAN='docs/plans/prospectus-relation-boundaries-2026-10-15.md'
METHODS=['src/legalmath/prospectus/relation_boundaries.py',
         'tests/prospectus/test_relation_boundaries.py','scripts/prospectus_relation_boundaries.py']


def save(name,value):write(HERE/name,value,exclusive=True)


def bindings():
    changed=[p for p,h in read(HERE/'admission.json')['binding'].items() if file_hash(ROOT/p)!=h]
    if changed:raise ValueError('Admitted input changed: '+repr(changed))


def tests():
    import pytest
    xml='tests-repaired.xml' if (HERE/'tests.xml').exists() else 'tests.xml'
    code=pytest.main(['-q','tests/prospectus/test_relation_boundaries.py',
         'tests/prospectus_successor/test_relation_discovery.py',
         'tests/prospectus_successor/test_relation_scope.py','--junitxml='+str(HERE/xml)])
    if code:raise ValueError('Boundary tests failed: '+str(code))
    return {'pytest_exit':int(code)}


def evaluate():
    products=json.load(gzip.open(BASE/'attempt-002/v2-products.json.gz'))
    original=json.load(gzip.open(BASE/'attempt-002/v2-answer.json.gz'))
    protected=read(BASE/'attempt-001/protected-targets.json')['bes']
    ledger=read(BASE/'attempt-003/review-ledger.json')
    before=digest(products)
    output=consume_with_suggestions(products,ROOT)
    with gzip.open(HERE/'consumer.json.gz','wt') as stream:json.dump(output,stream)
    answer=output['answer'];result=output['suggestions']
    old={c['id']:c for c in original['relation_candidates']['candidates']}
    new={c['id']:c for c in result['candidates']}
    lineage={r['original_id']:r for r in result['lineage']}
    expected_excess={r['candidate_id']:r['excess'] for r in ledger['reviews'] if r['disposition']=='WRONG_PRINTED_SCOPE'}
    abstained=next(k for k in old if k.split(':')[1].startswith('f81c9c687311'))
    comparisons=[]
    for key,c in old.items():
        row=lineage.get(key,{})
        if key in expected_excess:
            candidate=new.get(row.get('candidate_id'),{})
            excess=expected_excess[key]
            check=(row.get('status')=='BOUNDED' and row['removed']==[a for side in ('from','to') for a in c[side] if a in excess]
                and all(candidate.get(side)==[a for a in c[side] if a not in excess] for side in ('from','to')))
            comparisons.append({'original_id':key,'expected':'EXACT_SCOPE_REPAIR','pass':check})
        elif key==abstained:
            comparisons.append({'original_id':key,'expected':'DISCONNECTED_VALUE_ABSTENTION',
                'pass':row.get('status')=='ABSTAINED' and row.get('candidate_id') is None})
        else:
            comparisons.append({'original_id':key,'expected':'UNCHANGED',
                'pass':row.get('status')=='UNCHANGED' and new.get(key)==c})
    normalized=deepcopy(answer);normalized['assessment_mode']=original['assessment_mode']
    normalized['report_sha256']=digest({k:v for k,v in normalized.items() if k!='report_sha256'})
    target_checks={t['id']:sum(all(c[k]==t[k] for k in ('kind','from','to')) for c in result['candidates'])==1 for t in protected}
    checks={'all24_lineages':set(lineage)==set(old) and len(result['lineage'])==24,
            'exact_each_candidate':all(c['pass'] for c in comparisons),
            'eight_targets':all(target_checks.values()),'three_bounded':sum(r['status']=='BOUNDED' for r in lineage.values())==3,
            'one_abstention':sum(r['status']=='ABSTAINED' for r in lineage.values())==1,
            'twenty_unchanged':sum(r['status']=='UNCHANGED' for r in lineage.values())==20,
            'products_unchanged':digest(products)==before,
            'full_answer_preserved_after_mode_normalization':normalized==original,
            'no_admission':result['accepted_relations']==[] and result['legal_scope_inferred'] is False and output['relation_admission_performed'] is False}
    report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
            'candidate_comparisons':comparisons,'protected_targets':target_checks,
            'baseline_candidates':len(old),'bounded_candidates':len(new),
            'actual_mode':answer['assessment_mode'],'normalized_mode':original['assessment_mode'],
            'native_starts':0,'fresh_assessment':False,'whole_program_complete':False}
    save('comparison.json',report)
    save('candidate-output.json',result)
    save('method-identities.json',{p:file_hash(ROOT/p) for p in METHODS})
    for path in METHODS:
        target=HERE/'method'/path;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write((ROOT/path).read_bytes())
    if not all(checks.values()):raise ValueError('Finite boundary comparison failed; inspect retained comparison')
    return {k:v for k,v in report.items() if k not in {'candidate_comparisons','protected_targets'}}


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['tests','tests-repaired','evaluate']);args=p.parse_args()
    def expired(signum,frame):raise TimeoutError('120-second stage bound; no automatic retry')
    signal.signal(signal.SIGALRM,expired);signal.alarm(120)
    if (HERE/'outputs.json').exists():raise ValueError('Attempt is sealed')
    bindings()
    folder=HERE/'invocations'/args.stage;folder.mkdir(parents=True,exist_ok=False)
    write(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_relation_boundaries',args.stage],
         'environment':sys.executable,'plan':PLAN,'cpu_gpu':'CPU only; no GPU framework imported',
         'git_commit':read(HERE/'admission.json')['git_commit']},exclusive=True)
    start=time.monotonic()
    try:result={'status':'PASS','stage':args.stage,'result':(tests if args.stage=='tests-repaired' else globals()[args.stage])()}
    except BaseException as error:
        result={'status':'FAIL','stage':args.stage,'error':repr(error)};raise
    finally:
        result['wall_seconds']=time.monotonic()-start
        write(folder/'result.json',result,exclusive=True);signal.alarm(0)
    print(json.dumps(result))


if __name__=='__main__':main()
