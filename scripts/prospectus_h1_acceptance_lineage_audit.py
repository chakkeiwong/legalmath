"""Read-only diagnosis of current H1 dimensional evidence and acceptance schema."""
from copy import deepcopy
import json
import sys
import time

from scripts import prospectus_h1_reference_closure as trial
from scripts.prospectus_h1_unit_oracle import verify

common=trial.common
ROOT,BASE,AUTH=trial.ROOT,trial.BASE,trial.AUTH
read,save,sha,rel,require=common.read,common.save,common.sha,common.rel,common.require
TEMP=ROOT/'.localresources/prospectus-preparation/h1-acceptance-lineage'
PLAN='docs/plans/prospectus-h1-acceptance-lineage-2026-10-22.md'
LATER={'h1_individual_unit_review','h1_individual_unit_explanation',
    'h1_source_relationship_review','h1_source_relationship_explanation',
    'h1_reference_availability_review','h1_reference_availability_explanation'}
PRIOR={'answer','cash_flow_review','cash_flow_explanation','risk_table_review',
    'risk_table_explanation','h1_scope_review','h1_scope_explanation'}


def main():
    tick=time.monotonic()
    path=TEMP/'current-unit-066.json'
    require(not path.exists(),'Preserve completed audit; no unchanged retry')
    auth=common.authority()
    require(read(AUTH/'program.json')['revision']==429,'Expected revision429')
    manifest=trial.HERE/'outputs.json'
    require(any(e.get('attempt')==rel(trial.HERE) and e.get('outputs_sha256')==sha(manifest)
        for e in auth.events()),'Recorded066required')
    require(read(trial.HERE/'result.json')['status']=='PASS','Successful066required')
    require(all(sha(trial.HERE/n)==v for n,v in read(manifest).items()),'Changed sealed066')
    freeze=read(trial.PREP/'freeze.json')
    production=common.production()
    require(production==freeze['candidate_production'],'Current production differs from066')
    require(all(sha(ROOT/n)==v for n,v in freeze['bindings'].items()),'Current source or method binding changed')
    answers=[]
    for kind in ('ordinary','installed'):
        receipt=read(trial.HERE/(kind+'.json'))
        p=trial.HERE/(kind+'-answer.json.gz')
        require(receipt['status']=='PASS' and sha(p)==receipt['answer_file']['sha256'],'Current answer file changed')
        answer=read(p)
        require(common.digest(answer)==receipt['answer_sha256'],'Current answer content changed')
        answers.append(answer)
    require(answers[0]==answers[1],'Current ordinary/installed answers differ')
    answer=answers[0]
    require(set(answer)==PRIOR|LATER,'Unknown preceding-answer structure')
    preceding={k:answer[k] for k in PRIOR}
    profiles=read(BASE/'attempt-063/profiles.json.gz')
    graph=read(BASE/'attempt-063/products.json.gz')['P1']['payload']['graph']
    original=read(BASE/'attempt-016/profile.json')|{'full_units':read(BASE/'attempt-016/source-units.json')}
    profile=profiles['unit']
    actual=answer['h1_individual_unit_review']
    explanation=answer['h1_individual_unit_explanation']
    proof=verify(actual,explanation,profile,graph,preceding,original,ROOT)
    old=read(BASE/'attempt-017/answer-delta.json.gz')['h1_individual_unit_review']
    substantive=lambda obj:{k:v for k,v in obj.items() if k not in ('prior_sha256','profile_sha256')}
    require(substantive(actual)==substantive(old),'Historical unit meaning changed')
    require(actual['prior_sha256']!=old['prior_sha256'],'Expected later complete answer binding')
    controls=[]
    cases={
        'same-unit-equality':lambda a:a['comparisons'][0].update(same_unit_financial_equality=True),
        'scale-swapped':lambda a:a['pages'][0]['cells'][2].update(scale_to_EUR=1000),
        'unknown-dash-zero':lambda a:a['pages'][0]['cells'][1].update(value=0,status='SOURCE_NUMBER'),
        'official-correction':lambda a:a.update(official_unit_correction_established=True),
        'selected-incorporation':lambda a:a.update(selected_incorporation_reading='overall-range'),
        'wrong-source-identity':lambda a:a['pages'][0]['cells'][2]['source'].update(unit='bes-interim-h1-2010:p53:l223'),
    }
    for name,change in cases.items():
        bad=deepcopy(actual)
        change(bad)
        try:
            verify(bad,explanation,profile,graph,preceding,original,ROOT)
        except ValueError as exc:
            controls.append({'case':name,'refused':True,'reason':str(exc)})
        else: raise ValueError('Unit oracle accepted '+name)
    bad_profile=deepcopy(profile)
    bad_profile['prior_sha256']='0'*64
    try:
        verify(actual,explanation,bad_profile,graph,preceding,original,ROOT)
    except ValueError as exc:
        require(str(exc)=='Input context mismatch','Unexpected binding refusal')
        controls.append({'case':'stale-prior-binding','refused':True,'reason':str(exc)})
    else: raise ValueError('Unit oracle accepted stale prior')
    package=read(trial.HERE/'package.json')
    current={n.removeprefix('src/legalmath/'):v for n,v in production.items()}
    require(package['status']=='PASS' and package['files']==current,'Package map differs')
    task=next(t for t in read(AUTH/'program.json')['tasks'] if t['id']=='source-bes-dep-05')
    require(task['build_criteria_scope']==[],'Unexpected current submission scope')
    require(not (trial.HERE/'source-package.json').exists(),'Donor schema assumption changed')
    require(common.production()==production,'Audit changed production')
    result={'status':'CURRENT_UNIT_DERIVATION_PASSES_ACCEPTANCE_ROUTE_REQUIRES_REVIEW',
        'plan':PLAN,'method':common.ref(__file__),'oracle':common.ref(ROOT/'scripts/prospectus_h1_unit_oracle.py'),
        'actual_result':common.ref(trial.HERE/'result.json'),'actual_answer':common.ref(trial.HERE/'ordinary-answer.json.gz'),
        'original_map':common.ref(BASE/'attempt-016/profile.json'),'original_units':common.ref(BASE/'attempt-016/source-units.json'),
        'current_profiles':common.ref(BASE/'attempt-063/profiles.json.gz'),
        'current_products':common.ref(BASE/'attempt-063/products.json.gz'),
        'whole_current_answer_equal_installed':True,'historical_unit_meaning_preserved':True,
        'current_preceding_answer_binding':profile['prior_sha256'],'proof':proof,'controls':controls,
        'acceptance_route_gaps':[
            'The old donor loader requires source-package.json; current actual map is package.json/files.',
            'The current submission scope is empty; old preparation inherits it and would not submit the named criterion.',
            'The old evaluator replays007/017; current whole-answer binding was updated in063 and preserved through066.',
            'A reviewed current validator must distinguish source-unit derivation from unresolved intended unit and source authority.'],
        'original_requirements':{
            'conditional_unit_derivation':'Current saved actual result passes independent original-source dimensional oracle.',
            'explicit_reference_delivery':'Recorded066 finite availability, not complete source interpretation.',
            'source_authenticity_and_controlling_language':'NOT_ESTABLISHED',
            'intended_unit_and_clipped_values':'UNRESOLVED; no correction inferred',
            'legal_incorporation_and_effect':'CONDITIONAL; no alternative selected',
            'general_automatic_discovery':'NOT_ESTABLISHED',
            'original_task_acceptance':'NOT_ESTABLISHED'},
        'production_changed':False,'build_criterion_accepted':False,'original_task_complete':False,
        'seconds':time.monotonic()-tick}
    save(path,result)
    return {'status':result['status'],'proof':proof,'controls':len(controls),'seconds':result['seconds'],
        'output':rel(path),'bytes':path.stat().st_size}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    started=time.monotonic()
    try: print(json.dumps(main()),flush=True)
    except Exception as exc:
        p=TEMP/'failure.json'
        if not p.exists(): save(p,{'status':'FAIL','method':common.ref(__file__),
            'error':type(exc).__name__+': '+str(exc),'seconds':time.monotonic()-started})
        raise
