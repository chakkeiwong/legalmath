from copy import deepcopy
import json
from pathlib import Path
import subprocess
import pytest
from legalmath.canonical import loads,canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.engine import Assurance,AssuranceSettings
from legalmath.interpretation.search.models import Settings,DIMENSIONS
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .support import packet,reading,inventory,fidelity


def source():
    return {'url':'https://www.sfc.hk/test/assurance','media_type':'text/plain','data':packet()['units'][0]['text'].encode()}


def settings(repairs=0):
    return AssuranceSettings(total_model_calls=18 if repairs else 12,semantic_repair_rounds=repairs,
        max_derived_comparisons=0,run_formula_challenges=False,
        search=Settings(max_model_calls=3,max_rounds=1,reconstruction_required=False))


def responder(omitted=False):
    def respond(request):
        task=request.get('original_task',request['task']);p=request['source_packet'];uid=p['units'][0]['unit_id']
        if task=='SOURCE_INVENTORY':
            inv=inventory();inv['claims'][0]['evidence'][0].update(unit_id=uid,quote=p['units'][0]['text'])
            inv['units'][0]['unit_id']=uid
            return inv
        if task in ('GENERATE','SEMANTIC_REPAIR','REFINE'):
            r=reading(omitted and task=='GENERATE')
            r['citations'][0].update(unit_id=uid,quote=p['units'][0]['text'])
            for fact in r['formalization']['facts']:fact['source_unit_ids']=[uid]
            return {'readings':[r],'dimensions':[{'dimension':d,'status':'PROPOSED','source_unit_ids':[uid],'explanation':'Controlled fixture'} for d in DIMENSIONS],
                    'coverage':[{'unit_id':uid,'status':'INTERPRETED','reason':'Selected rule'}],'questions':[]}
        if task=='SOURCE_FIDELITY':
            checks=[]
            for c in request['claims']:
                for candidate in request['candidates']:
                    if request.get('required_pairs') is not None and {'claim_id':c['claim_id'],'candidate_id':candidate['candidate_id']} not in request['required_pairs']:continue
                    missing='not the case' not in candidate['representation']
                    checks.append({'claim_id':c['claim_id'],'candidate_id':candidate['candidate_id'],
                        'label':'NOT_ESTABLISHED' if missing else 'ENTAILED','source_evidence':c['evidence'],
                        'representation_quotes':[] if missing else [candidate['representation']],
                        'rationale':'Synthetic diagnostic labels only','failing_stage':'FORMALIZATION' if missing else 'NONE',
                        'question':'Where is the exception?' if missing else None})
            return {'checks':checks,'additional_concerns':[]}
        if task=='STRUCTURED_CRITICISM':
            return {'arguments':[{'argument_id':'arg.'+str(i),'candidate_id':cid,'premises':[], 'parents':[],
                'inference_id':'rule.'+str(i),'inference_kind':'DEFEASIBLE','inference':'Proposed direct source reading',
                'conclusion':{'atom':'supported.'+str(i),'negative':False},
                'evidence':[{'unit_id':uid,'quote':p['units'][0]['text']}]} for i,cid in enumerate(request['candidates'])],
                'attacks':[],'preferences':[],'cases':[],'case_queries':[],'questions':[]}
        raise AssertionError(task)
    return respond


def test_integrated_clean_path_is_replayable_and_source_inventories_precede_generation(root,tmp_path):
    provider=FunctionProvider(responder());engine=Assurance(tmp_path/'run',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings())
    result=engine.drive([source()],'Selected gift control')
    assert result['status']=='NO_ISSUE_DETECTED_IN_PROFILE',result
    assert result['model_calls']==7 and not result['release_eligible']
    assert [r['task'] for r in provider.requests[:3]]==['SOURCE_INVENTORY','SOURCE_INVENTORY','GENERATE']
    assert engine.verify()==result
    assert engine.drive([source()],'Selected gift control')==result
    assert len(provider.requests)==7
    with pytest.raises(LegalMathError):engine.drive([source()],'Changed control')


def test_unanimous_omission_is_repaired_and_failed_parent_remains_archived(root,tmp_path):
    provider=FunctionProvider(responder(True));engine=Assurance(tmp_path/'run',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings(1))
    result=engine.drive([source()],'Selected gift control')
    assert result['status']=='NO_ISSUE_DETECTED_IN_PROFILE',result
    assert len(result['repairs'])==1 and result['superseded_by_checked_repair']
    assert len(result['candidate_ids'])==2 and len(result['active_candidate_ids'])==1
    assert any(c['label']=='NOT_ESTABLISHED' for c in result['fidelity']['checks'])
    history=loads((tmp_path/'run/stage-history.json').read_bytes())
    assert any(not r['valid'] for r in history)
    assert not result['release_eligible']


def test_exhaustion_reports_shared_error_without_consultancy_requirement(root,tmp_path):
    provider=FunctionProvider(responder(True));engine=Assurance(tmp_path/'run',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings(0))
    result=engine.drive([source()],'Selected gift control')
    assert result['status']=='UNRESOLVED' and result['residual_questions']
    assert any(f['kind']=='SOURCE_NOT_ESTABLISHED' for f in result['findings'])
    assert all(not q['external_consultancy_required'] for q in result['residual_questions'])


def test_cli_has_executable_assurance_and_monitor_commands(root):
    for command in ('interpretation-assurance','assurance-monitor'):
        result=subprocess.run([str(root/'.venv/bin/python'),'-m','legalmath.cli',command,'--help'],capture_output=True,text=True)
        assert result.returncode==0 and '--allowance' in result.stdout


def test_cached_diagnostic_reduces_one_call_but_source_change_invalidates_reuse(root,tmp_path):
    provider=FunctionProvider(responder());jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    first=Assurance(tmp_path/'one',provider,jdk,AT,settings()).drive([source()],'Selected gift control')
    second=Assurance(tmp_path/'two',provider,jdk,AT,settings()).drive([source()],'Selected gift control')
    assert first['model_calls']==7 and second['model_calls']==6
    assert any(a['kind']=='REUSE_SUPPORTED_ANSWER' for a in second['actions'])
    changed=source();changed['data'] += b' '
    third=Assurance(tmp_path/'three',provider,jdk,AT,settings()).drive([changed],'Selected gift control')
    assert third['model_calls']==7


def test_failure_is_retained_and_never_reported_as_clean(root,tmp_path):
    def failed(request):raise LegalMathError('E_DEPENDENCY',details='Controlled unavailable provider')
    provider=FunctionProvider(failed)
    result=Assurance(tmp_path/'failed',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings()).drive([source()],'Selected gift control')
    assert result['status'] != 'NO_ISSUE_DETECTED_IN_PROFILE'
    assert result['failures'] and result['model_calls'] <= 12
    assert all(r['task']=='SOURCE_INVENTORY' for r in provider.requests)


def test_source_inventory_omission_triggers_source_repair_not_only_code_repair(root,tmp_path):
    normal=responder()
    def respond(request):
        if request['task']=='REPAIR_SOURCE_INVENTORY':return normal({**request,'task':'SOURCE_INVENTORY'})
        response=normal(request)
        if request['task']=='SOURCE_INVENTORY':response['claims'][0]['exceptions']=[]
        return response
    provider=FunctionProvider(respond)
    result=Assurance(tmp_path/'source-repair',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings(1)).drive([source()],'Selected gift control')
    assert result['status']=='NO_ISSUE_DETECTED_IN_PROFILE',result
    assert any(r['kind']=='SOURCE_INVENTORY' for r in result['repairs'])
    assert sum(r['task']=='REPAIR_SOURCE_INVENTORY' for r in provider.requests)==2


def test_fidelity_batches_preserve_all_claim_candidate_pairs(root,tmp_path):
    provider=FunctionProvider(responder());config=settings().model_copy(update={'max_fidelity_pairs_per_call':1})
    engine=Assurance(tmp_path/'batches',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,config)
    from legalmath.interpretation.assurance.semantics import merge_inventories
    result,findings=engine._fidelity(packet(),merge_inventories({'atomic-reader':inventory()}),{'a':reading(),'b':reading()})
    assert not findings and len(provider.requests)==2
    assert {c['candidate_id'] for c in result['checks']}=={'a','b'}
    assert all(len(r['required_pairs'])==1 for r in provider.requests)


def test_failed_search_reader_remains_a_top_level_issue(root,tmp_path):
    respond=responder();count=0
    def missing_reader(request):
        nonlocal count
        if request['task']=='GENERATE':
            count+=1
            if count==2:raise LegalMathError('E_DEPENDENCY',details='One reader unavailable')
        return respond(request)
    result=Assurance(tmp_path/'failed-reader',FunctionProvider(missing_reader),
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings()).drive([source()],'Selected gift control')
    assert result['status']=='UNRESOLVED'
    assert any(f['kind']=='SEARCH_ACTION_FAILED' for f in result['findings'])


def test_invalid_scope_remains_unresolved_while_valid_sibling_is_checked(root,tmp_path):
    provider=FunctionProvider(responder());engine=Assurance(tmp_path/'invalid-scope',provider,
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings())
    from legalmath.interpretation.assurance.semantics import merge_inventories
    bad=reading();bad['formalization']['scope']='Selected control in English prose.'
    result,findings=engine._fidelity(packet(),merge_inventories({'atomic-reader':inventory()}),{'bad':bad,'good':reading()})
    assert {c['candidate_id']:c['label'] for c in result['checks']}=={'bad':'NOT_ESTABLISHED','good':'ENTAILED'}
    assert len(provider.requests)==1
    assert [c['candidate_id'] for c in provider.requests[0]['candidates']]==['good']
    assert any(a['kind']=='UNSUPPORTED_EXECUTABLE_MEANING' for a in engine.actions)
    assert any(f['candidate_id']=='bad' for f in findings)


def test_legacy_deferred_valid_sibling_receives_assurance_checks(root,tmp_path):
    normal=responder()
    def respond(request):
        result=normal(request)
        if request['task']=='GENERATE' and request['role']=='normative':
            result['readings'][0]['formalization']['scope']='Selected control in English prose.'
        return result
    config=settings();config=config.model_copy(update={'search':config.search.model_copy(update={'max_candidates':6})})
    provider=FunctionProvider(respond)
    result=Assurance(tmp_path/'deferred',provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,config).drive([source()],'Selected gift control')
    assert result['execution_complete'] and result['status']=='UNRESOLVED'
    assert len(result['checked_deferred_candidate_ids'])==1
    cid=result['checked_deferred_candidate_ids'][0]
    assert any(c['candidate_id']==cid and c['label']=='ENTAILED' for c in result['fidelity']['checks'])
    assert any(a['kind']=='CHECK_DEFERRED_PROPOSAL' and a['search_registration_unchanged'] for a in result['actions'])
