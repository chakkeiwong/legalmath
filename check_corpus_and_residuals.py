"""Actual corpus-handler missing-evidence check and retained P14 target audit."""
from pathlib import Path
import importlib.util
import json
import sys
sys.path[:0]=[str(Path(__file__).parent/'src'),'/home/chakwong/python/legalmath',str(Path(__file__).parent)]
from replay_baselines import ROOT, OUT, BASE, read, ref, save, outcome
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require

def main():
    module_path=Path(__file__).parent/'scripts/legal_integration_qualification_continuation.py'
    spec=importlib.util.spec_from_file_location('candidate_corpus_handler',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    directory=OUT/'corpus-handler-missing-evidence'; directory.mkdir(exist_ok=True)
    result=module.corpus(directory)
    require(result['_node_status']=='BLOCKED','Missing real corpus reviews incorrectly qualified')
    current=read(directory/'corpus-reconciliation.json')
    retained=read(ROOT/'artifacts/legal-mission-control/2026-10-13/master/corpus-qualification/attempt-6/corpus-reconciliation.json')
    require(current==retained,'Historical corpus fidelity changed')
    sources={}
    for region in ('2023','2025','handbook'):
        receipt=read(ROOT/f'artifacts/legal-mission-control/2026-10-13/master/ownership-{region}/attempt-3/evidence.json')
        ownership=read(ROOT/receipt['ownership']['path'])
        sources[region]={'source':ownership['source'],'fidelity':receipt['ownership'],
            'applicability':'MISSING_REVIEW','later_treatment':'MISSING_REVIEW'}
    state=read(ROOT/'artifacts/legal-mission-control/2026-10-13/master/execution-state.json')
    duties={'declared_product_as_of':'2026-10-15T00:00:00+08:00',
        'as_of_provenance':'scripts/legal_integration_phased_live.py product_route argument; not current-law certification',
        'sources':sources,'answers':{q:{'owner':'baseline-'+q,'status':state['tasks']['baseline-'+q]['status'],
        'source_use_review':'MISSING_COMPLETE_REVIEW','proposition_inventory':'Requires fixed actual answer'}
        for q in ('p10','p14','evidence','gatecoin')},
        'required_controls':['positive','wrong_source','false_attribution'],
        'consumer_status':result['_node_status'],'fidelity_exactly_preserved':True,
        'legal_acceptance':False,'provider_calls':0}
    save('corpus-missing-duties.json',duties)
    # A syntactically exact selected quote is not evidence that the objection is true.
    rows=[]
    replay=read(OUT/'p14-warrant-replay-final.json')
    for row in replay['rows']:
        folder=ROOT/row['request']['path']; request=read(folder); answer=request['payload']['answer']
        raw=read(ROOT/row['raw']['path'])['value']
        rows.append({'call':row['call'],'request':row['request'],'raw':row['raw'],
            'mechanical_status':row['simulation']['status'],
            'original_issue_texts':request['payload']['issues'],
            'answer_hash':digest(answer),'review_target_must_be_reassessed':True,
            'reason':'Exact-field identity cannot show that this criticism describes the answer. '
                'The retained failed quotations are not substring matches; some allege an absence '
                'that the delivered conclusion does not assert. Use a fresh scoped assessment; '
                'do not promote the replay to a supported correction warrant.'})
    save('p14-warrant-semantic-reassessment.json',{'rows':rows,'auto_promote':False,'provider_calls':0})
    print(json.dumps({'corpus_status':result['_node_status'],'fidelity_preserved':True,
        'pending_p14_semantic_assessments':len(rows),'provider_calls':0}))

if __name__=='__main__':main()
