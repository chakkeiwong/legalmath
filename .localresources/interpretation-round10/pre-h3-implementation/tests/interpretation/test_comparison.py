from copy import deepcopy
from legalmath.interpretation.comparison import compare_candidates
from legalmath.java.manifest import build_candidate

def test_interpretation_comparison_replays_witness(svc,run,proposal,case,root,tmp_path):
    old=deepcopy(case['bundle']);new=deepcopy(old);new['rules'][0]['body']['op']='all';new['bundle_id']='synthetic.mutant'
    candidates=[]
    for i,b in enumerate((old,new)):
        bh=svc.lc.create('author','b'+str(i),b)['bundle_hash']
        candidates.append(svc.propose('author','p'+str(i),run['run_id'],{**proposal,'bundle_hash':bh})['candidate_id'])
    jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1';jar=build_candidate(old,tmp_path/'java',jdk)['jar']
    domain={'portfolio':{'min':'0','max':'4000000001','allow_unknown':True},'net_assets_ex_home':{'min':'0','max':'8000000001','allow_unknown':True}}
    result=compare_candidates(svc,'author',run['run_id'],*candidates,case['rule_id'],domain,case['valid_at'],case['known_at'],java_jar=jar,jdk=jdk)
    assert result['evidence']['comparison_result']=='DIFFERENT' and len(result['result']['java_replays'])==2
    assert not result['evidence']['legal_source_commitment_resolved']
    domain['portfolio']={'min':'5','max':'4','allow_unknown':False}
    result=compare_candidates(svc,'author',run['run_id'],*candidates,case['rule_id'],domain,case['valid_at'],case['known_at'])
    assert result['evidence']['comparison_result']=='INCONSISTENT_DOMAIN'
