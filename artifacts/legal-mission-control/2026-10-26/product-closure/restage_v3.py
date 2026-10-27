"""Rebuild failed staging from its frozen baseline; never change active files."""
from pathlib import Path
from copy import deepcopy
from xml.etree import ElementTree as ET
import hashlib,importlib.util,json,shutil,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=Path('artifacts/legal-mission-control/2026-10-26/product-closure')
TREE=Path('/tmp/legalmath-product-closure-20261026')
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,save,ref,require,digest,verify
from scripts.legal_integration_master import PROGRAM,STATE,BASE,DOC,PLAN
spec=importlib.util.spec_from_file_location('closure_deploy',ROOT/WORK/'deploy.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
deploy.transaction.assert_unchanged(ROOT,read(ROOT/WORK/'baseline.json'));deploy.idle()
prior=read(ROOT/WORK/'local-result-v2.json')
testpath=WORK/'final-verified-v3-tests.xml';test=ET.parse(ROOT/testpath).getroot()
require(not list(test.iter('failure')) and not list(test.iter('error')),'Candidate tests failed')
rows=[]
for item in prior['sources']:
    name=item['path'];target=WORK/'source-v3'/name
    require(not (ROOT/target).exists(),'Candidate version already retained')
    (ROOT/target).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(TREE/name,ROOT/target)
    rows.append(dict(path=name,candidate=ref(ROOT,target),before=item['before']))
evidence=[ref(ROOT,p) for p in [testpath,WORK/'candidate-history-validation.json',
    WORK/'canonical-baseline.py',WORK/'p14-current-disposition-result-v3.json',
    WORK/'p14-residual-proof.json',WORK/'corpus-independent-result.json']]
result=dict(verdict='PASS',test_executions=len(list(test.iter('testcase'))),provider_calls=0,legal_acceptance=False,
    sources=rows,evidence=evidence,predecessor=ref(ROOT,WORK/'local-result-v2.json'),
    failed_test_evidence=ref(ROOT,WORK/'final-v3-tests.xml'),limits=[
        'All original P14 objections accounted for; fresh acceptance reviews remain',
        'Corpus components do not establish final qualification',
        'Full staged and installed master validation still required'])
save(ROOT/WORK/'local-result-v3.json',result)
stage=WORK/'registration-stage'
archive=ROOT/WORK/'failed-staging-v2';require(not archive.exists(),'Prior stage archive exists')
shutil.copytree(ROOT/stage,archive)
r=deepcopy(read(ROOT/stage/'program.json')['product_closure'])
r.update(review=ref(ROOT,deploy.REVIEW),result=ref(ROOT,WORK/'local-result-v3.json'),
    implementation={x['path']:dict(path=x['path'],sha256=x['candidate']['sha256']) for x in rows},
    arm_checkpoints={'p14':{'baseline':ref(ROOT,WORK/'p14-checkpoint-v3.json')}})
r['substantive_evidence'].update(p14_dispositions=ref(ROOT,WORK/'p14-current-dispositions-v3.json'),
    p14_review=ref(ROOT,WORK/'p14-current-disposition-result-v3.json'),
    p14_proof=ref(ROOT,WORK/'p14-residual-proof.json'))
baseline=read(ROOT/WORK/'baseline.json');held={x['previous']['path']:x['archive'] for x in baseline['archived']}
deploy.imports()
from scripts import legal_product_closure as closure
from scripts.legal_integration_acceptance_revision import historical_projection
old=read(ROOT/r['prior_program']['path']);program=closure.expected_program(old,r,ROOT)
save(ROOT/stage/'program.json',program);pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
state=read(ROOT/stage/'state.json');state['program_hash']=digest(program)
state['events'][-1]['review']=r['review'];save(ROOT/stage/'state.json',state)
mapping=closure.aliases(baseline);mapping[(str(PROGRAM),r['prior_program']['sha256'])]=r['prior_program']
binding=read(ROOT/r['prior_binding']['path'])
binding['bindings']=historical_projection(binding['bindings'],mapping)
binding.update(program=pointer,product_closure=r,predecessor=r['prior_binding'],phase_service_predecessor=r['prior_binding'])
binding['bindings'] += [pointer,r['master_plan'],r['review'],r['result'],*r['implementation'].values(),
    *r['substantive_evidence'].values(),*r['corpus_components'].values(),r['arm_checkpoints']['p14']['baseline']]
known={(x['previous']['path'],x['previous']['sha256']) for x in binding['historical_archives']}
binding['historical_archives'] += [x for x in baseline['archived'] if (x['previous']['path'],x['previous']['sha256']) not in known]
save(ROOT/stage/'binding.json',binding)
successor=read(ROOT/WORK/'successor-stage.json');successor['binding_hash']=digest(binding)
save(ROOT/WORK/'successor-stage.json',successor);save(ROOT/stage/'current-stage.json',ref(ROOT,WORK/'successor-stage.json'))
mission=historical_projection(read(ROOT/held[str(DOC/'mission.json')]['path']),mapping)
mission['integration_master'].update(program=pointer,plan=r['master_plan'],product_closure=r)
event=read(ROOT/stage/'mission.json')['history'][-1];event['result_evidence']=[pointer,r['review'],r['result']]
mission['next_task_reason']=event['next_task_reason'];mission['history'].append(event)
save(ROOT/stage/'mission.json',mission)
require(program['protected_evidence'][-1]==r['master_plan'],'Plan reference ordering failed')
require(program==closure.expected_program(old,r,ROOT),'Projection mismatch')
require(program['tasks']==old['tasks'],'Changed task graph')
require(set(r['implementation'])==set(baseline['implementation_paths']),'Changed source population')
require(state['tasks']==read(ROOT/r['prior_state']['path'])['tasks'],'Changed attempts')
save(ROOT/WORK/'restaging-v3-result.json',dict(verdict='PASS',provider_calls=0,
    tests=result['test_executions'],preserved_graph=True,preserved_attempts=True,master_plan_last=True))
print(json.dumps(dict(staged=True,tests=result['test_executions'],provider_calls=0)))
