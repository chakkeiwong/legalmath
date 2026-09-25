"""Verify the frozen public interfaces and authored reference execution before dispatch."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from legalmath.canonical import digest,loads
from legalmath.interpretation.assurance.declared_evaluation import score_declared
from legalmath.interpretation.assurance.issue_search import merge_hypotheses,distinguish
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.checkpoints import seal
from legalmath.interpretation.search.formal import Comparisons
from legalmath.errors import LegalMathError

ROOT=Path(__file__).resolve().parents[1]


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    frozen=loads((ROOT/'docs/implementation/interpretation-round9/study.json').read_bytes());results=[]
    jdk=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    for case in frozen['study']['cases']:
        public=frozen['public_interfaces'][case['case_id']];packet,issue,at=(public[k] for k in ('packet','issue','at'))
        r=deepcopy(case['reference']['binding_reading'])
        r['statement']='[TRUE_IS_SATISFIED] The proposed applicability condition holds under the declared supplied classifications.'
        answer={'readings':[r],'vocabulary_concerns':[],'questions':[]}
        merged=merge_hypotheses({'reference':answer},issue,packet,at)
        result={'status':'COMPLETE','source_packet_hash':digest(packet),'public_hash':digest(public),
            'merged':merged,'reviews':{},'invalid_proposals':{'records':[]}}
        score=score_declared(result,case,public,Comparisons(out/case['case_id']/'reference',jdk,at))
        if score['status']!='ACCEPTED' or not score['reference_in_candidate_set']:raise LegalMathError('E_INTEGRITY')
        finite=distinguish(issue,packet,merged['candidates'],Comparisons(out/case['case_id']/'finite',jdk,at))
        wrong=deepcopy(r);wrong['formalization']['result']='(not '+wrong['formalization']['result']+')'
        merged_bad=merge_hypotheses({'mutant':{'readings':[wrong],'vocabulary_concerns':[],'questions':[]}},issue,packet,at)
        bad=score_declared({**result,'merged':merged_bad},case,public,Comparisons(out/case['case_id']/'mutant',jdk,at))
        if bad['reference_in_candidate_set']:raise LegalMathError('E_INTEGRITY',details='Mutation not detected')
        results.append({'case_id':case['case_id'],'reference':score,'mutant':bad,'java_cases':finite['java_cases'],
            'legal_reference_independently_verified':False})
    save(out/'result.json',{'cases':results,'status':'REFERENCE_ENGINEERING_CHECKS_PASSED',
        'call_reservation':frozen['study']['required_call_reservation'],'release_eligible':False})
    seal(out);print({'cases':len(results),'status':'REFERENCE_ENGINEERING_CHECKS_PASSED'},flush=True)


if __name__=='__main__':
    p=ArgumentParser();p.add_argument('--out',required=True);run(p.parse_args().out)
