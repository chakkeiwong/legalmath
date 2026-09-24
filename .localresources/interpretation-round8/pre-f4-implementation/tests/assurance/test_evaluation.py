from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.evaluation import (ARMS,freeze,load_frozen,admit,summarize,
                                                         source_packet,execute_study)
from .support import reading
from .test_integration import source,responder
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT


def contract():
    return {'version':'paired-evaluation.v1','study_id':'controlled-gift','task':'CONTROLLED_SEMANTIC_TESTS',
        'call_cap':8,'seconds_per_arm':180,'bytes_per_input':200000,'bytes_per_output':200000,'seed':617,
        'development_families':['gift.fixture'],'minimum_families':2,'iid_family_sampling_attested':False,
        'confidence_error_ppm':50000,'maximum_coverage_loss_ppm':0,
        'criterion_basis':'Engineering fixture: no family sampling or legal-error threshold claim.'}


def cases():
    result=[]
    for variant in ('CLEAN','ALTERED'):
        doc=source()
        if variant=='ALTERED':doc['data']=b'A distributor should not offer gifts.'
        c={'case_id':variant.lower(),'family_id':'gift.fixture','variant':variant,
            'roots':[{'url':doc['url'],'media_type':doc['media_type'],'raw_hex':doc['data'].hex(),'sha256':raw_digest(doc['data'])}],
            'selected_slice':'Gift control','at':AT,'reference':{}}
        p=source_packet(c);uid=p['units'][0]['unit_id'];r=reading(variant=='ALTERED')
        r['citations']=[{'unit_id':uid,'quote':p['units'][0]['text']}]
        for fact in r['formalization']['facts']:fact['source_unit_ids']=[uid]
        facts={name:{'type':'bool','status':'known','value':True,'evidence_ids':['hidden.scenario'],
               'valid_from':AT,'valid_until':None,'recorded_at':AT} for name in ('gift','discount')}
        c['reference']={'basis':'DEVELOPER_FIXTURE','evidence':r['citations'],'binding_reading':r,
            'snapshots':[{'subject_id':'fixture','facts':facts}],
            'accepted':[[{'status':'TRUE' if variant=='ALTERED' else 'FALSE','type':'bool','value':variant=='ALTERED'}]],
            'limitations':['Controlled exception edit; complete legal correctness is not labelled.']}
        result.append(c)
    return result


def rows(study,status='ABSTAIN'):
    by_id={c['case_id']:c for c in study['cases']}
    return [{**j,'packet_hash':by_id[j['case_id']]['packet_hash'],'budget':study['contract']['call_cap'],'calls':1,
             'outcome':{'status':status,'signature':by_id[j['case_id']]['reference']['accepted'][0] if status=='ACCEPTED' else None}}
            for j in study['jobs']]


def test_freeze_precedes_dispatch_and_budget_admission_does_not_spend(tmp_path,root):
    study=freeze(contract(),cases(),tmp_path/'freeze');provider=FunctionProvider(lambda r:pytest.fail('Cannot dispatch under budget'))
    assert study['required_call_reservation']==64 and not study['heldout']
    result=execute_study(tmp_path/'freeze',tmp_path/'run',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',available_calls=22)
    assert result['status']=='UNDER_BUDGETED' and not provider.requests
    assert load_frozen(tmp_path/'freeze')==study
    (tmp_path/'freeze/study.json').write_text('{}')
    with pytest.raises(LegalMathError):load_frozen(tmp_path/'freeze')


def test_missing_pairs_unequal_budget_and_changed_source_are_vetoes(tmp_path):
    study=freeze(contract(),cases(),tmp_path/'freeze');data=rows(study)
    with pytest.raises(LegalMathError):summarize(study,data[:-1],live=False)
    data[0]['budget']=9
    with pytest.raises(LegalMathError):summarize(study,data,live=False)
    data=rows(study);data[0]['packet_hash']='0'*64
    with pytest.raises(LegalMathError):summarize(study,data,live=False)


def test_seeded_label_cannot_be_promoted_to_legal_outcome_and_clean_control_required(tmp_path):
    c=contract();c['task']='LEGAL_OUTCOMES'
    with pytest.raises(LegalMathError):freeze(c,cases(),tmp_path/'bad')
    with pytest.raises(LegalMathError):freeze(contract(),cases()[:1],tmp_path/'missing-clean')


def test_all_abstain_cannot_look_like_success_and_worse_treatment_visible(tmp_path):
    study=freeze(contract(),cases(),tmp_path/'freeze');data=rows(study)
    result=summarize(study,data,live=False)
    assert not result['ranking_supported'] and all(v['abstain']==2 and v['correct_accepted']==0 for v in result['counts'].values())
    assert {'DEVELOPMENT_FAMILY_OVERLAP','SCRIPTED_FIXTURE_NOT_LIVE_EVIDENCE','INSUFFICIENT_FAMILY_REPLICATION'}<=set(result['promotion_vetoes'])
    data=rows(study,'ACCEPTED')
    for row in data:
        if row['arm']=='assurance':row['outcome']['signature']=[{'status':'UNKNOWN','type':'bool'}]
    result=summarize(study,data,live=True)
    assert result['counts']['assurance']['unsafe_accepted']==2
    assert float(result['comparisons'][-1]['metrics']['unsafe']['mean_difference'])==1
    assert not result['ranking_supported']


def provider():
    normal=responder()
    def respond(request):
        assert 'reference' not in request and 'accepted' not in request and 'binding_reading' not in request
        if request['task']=='RECONSTRUCT':
            # The controlled reconstruction stub is isolated and explicitly labelled.
            r=reading('not the case' not in request['result_text']);r['formalization']['facts']=request['fact_definitions']
            return {'formalization':r['formalization'],'uncertainty':['Scripted fixture reconstruction']}
        result=normal(request)
        if request['task'] in ('GENERATE','REFINE','SEMANTIC_REPAIR') and 'other than' not in request['source_packet']['units'][0]['text']:
            result['readings'][0]['formalization']['result']='gift'
        return result
    return FunctionProvider(respond)


def test_all_four_real_method_adapters_receive_blinded_public_input(root,tmp_path):
    freeze(contract(),cases(),tmp_path/'freeze');p=provider()
    result=execute_study(tmp_path/'freeze',tmp_path/'run',p,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',available_calls=64)
    assert set(result['counts'])==set(ARMS)
    assert all(v['missing']==0 for v in result['counts'].values()),loads((tmp_path/'run/results.json').read_bytes())
    assert not result['ranking_supported']
    rows_=loads((tmp_path/'run/results.json').read_bytes())
    assert len(rows_)==8 and all(r['calls']<=8 for r in rows_)
    assert any(r['arm']=='search' and r['calls']>3 for r in rows_)
    assert {r['task'] for r in p.requests}>={'SOURCE_INVENTORY','GENERATE','SOURCE_FIDELITY','STRUCTURED_CRITICISM'}


@pytest.mark.parametrize('defect',['wrong','boolean-as-integer','unwitnessed-alternative'])
def test_reference_labels_must_match_explicit_executable_witnesses(tmp_path,defect):
    data=cases()
    if defect=='wrong':data[0]['reference']['accepted'][0][0]={'status':'TRUE','type':'bool','value':True}
    elif defect=='boolean-as-integer':data[0]['reference']['accepted'][0][0]['value']=0
    else:data[0]['reference']['accepted'].append([{'status':'TRUE','type':'bool','value':True}])
    with pytest.raises(LegalMathError) as exc:freeze(contract(),data,tmp_path/'freeze')
    assert exc.value.code=='E_REFERENCE'
    assert not (tmp_path/'freeze').exists()


def test_multiple_reference_answers_need_comparable_programs(tmp_path):
    data=cases();alternative=deepcopy(data[0]['reference']['binding_reading'])
    alternative['formalization']['result']='gift'
    data[0]['reference']['alternate_readings']=[alternative]
    data[0]['reference']['accepted'].append([{'status':'TRUE','type':'bool','value':True}])
    study=freeze(contract(),data,tmp_path/'freeze')
    assert len(study['cases'][0]['reference']['accepted'])==2
    alternative['formalization']['facts'][0]['meaning']='A different legal fact'
    with pytest.raises(LegalMathError) as exc:freeze(contract(),data,tmp_path/'bad')
    assert exc.value.code=='E_REFERENCE'


@pytest.mark.parametrize('field',['required_call_reservation','jobs','heldout','packet_hash','families'])
def test_rehashed_study_cannot_forge_derived_budget_or_assignments(tmp_path,field):
    directory=tmp_path/'freeze';study=freeze(contract(),cases(),directory)
    if field=='required_call_reservation':study[field]=1
    elif field=='jobs':study[field]=study[field][:-1]
    elif field=='heldout':study[field]=True
    elif field=='packet_hash':study['cases'][0][field]='0'*64
    else:study[field]=['fake.family']
    (directory/'study.json').write_bytes(canonical(study))
    (directory/'manifest.json').write_bytes(canonical({'study_hash':digest(study),
        'files':{'study.json':raw_digest((directory/'study.json').read_bytes())}}))
    with pytest.raises(LegalMathError):load_frozen(directory)


def test_same_source_cannot_be_relabelled_as_an_independent_family(tmp_path):
    data=cases();extra=deepcopy(data)
    for c in extra:c.update(case_id='copy.'+c['case_id'],family_id='copy.family')
    with pytest.raises(LegalMathError) as exc:freeze(contract(),data+extra,tmp_path/'bad')
    assert exc.value.code=='E_REFERENCE'


@pytest.mark.parametrize('value',['NaN','inf','-1'])
def test_invalid_elapsed_time_cannot_evade_the_resource_check(tmp_path,value):
    study=freeze(contract(),cases(),tmp_path/'freeze');data=rows(study)
    data[0]['wall_seconds']=value
    with pytest.raises(LegalMathError):summarize(study,data,live=True)


def test_selected_source_keeps_full_raw_bytes_and_checked_regions(tmp_path):
    from legalmath.interpretation.assurance.sources import extract_document
    data=cases();doc=data[0]['roots'][0];raw=bytes.fromhex(doc['raw_hex'])
    full=b'Navigation\n'+raw+b'\nFooter';extracted=extract_document({'data':full,'media_type':'text/plain'})
    a=extracted['text'].index(raw.decode());b=a+len(raw.decode())
    doc.update(raw_hex=full.hex(),sha256=raw_digest(full),selection={'raw_sha256':raw_digest(full),
        'text_sha256':raw_digest(extracted['text'].encode()),'ranges':[[a,b]],
        'regions':[{'anchor':{'start':a,'end':b,'quote':raw.decode()}}]})
    p=source_packet(data[0]);reference=data[0]['reference'];uid=p['units'][0]['unit_id']
    reference['binding_reading']['citations']=[{'unit_id':uid,'quote':raw.decode()}]
    reference['evidence']=deepcopy(reference['binding_reading']['citations'])
    for f in reference['binding_reading']['formalization']['facts']:f['source_unit_ids']=[uid]
    study=freeze(contract(),data,tmp_path/'freeze')
    assert bytes.fromhex(study['cases'][0]['roots'][0]['raw_hex'])==full
    assert len(p['units'])==1 and p['units'][0]['text']==raw.decode()
    doc['selection']['regions'][0]['anchor']['quote']='Different quotation'
    with pytest.raises(LegalMathError):freeze(contract(),data,tmp_path/'bad')


def test_shared_polarity_tag_cannot_hide_a_different_output_question():
    from legalmath.interpretation.assurance.evaluation import score
    c=cases()[0];r=deepcopy(c['reference']['binding_reading'])
    r['statement']='[TRUE_IS_PROHIBITED] True means a different control prohibits this.'
    class NoReplay:
        def replay(self,*a):pytest.fail('Meaning mismatch must be reported before Java comparison')
    result=score({'status':'CANDIDATES','readings':[r]},c,NoReplay())
    assert result=={'status':'ABSTAIN','signature':None,'reason':'OUTPUT_MEANING_UNALIGNED'}
