"""Adverse planning controls; these do not execute the future ODRL feature."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.check_odrl_master_program import completion, frontier, safe_file, validate

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def program():
    return json.loads((ROOT/'docs/implementation/odrl-master/program.json').read_text())


def task(program, name):
    return next(t for t in program['tasks'] if t['id']==name)


def test_actual_program_has_bound_inputs_and_no_execution_grant(program):
    result=validate(program)
    assert result['status']=='PASS', result['errors']
    assert frontier(program)['ready']==[]


@pytest.mark.parametrize('defect',['missing_node','unknown_dependency','cycle','duplicate','unbounded','fake_success','live_grant'])
def test_bad_plans_cannot_pass(program,defect):
    if defect=='missing_node':program['tasks']=[t for t in program['tasks'] if t['id']!='T03']
    elif defect=='unknown_dependency':task(program,'X07')['requires_success'].append('absent')
    elif defect=='cycle':task(program,'S00')['requires_success'].append('K17')
    elif defect=='duplicate':program['tasks'].append(deepcopy(task(program,'F06')))
    elif defect=='unbounded':task(program,'V08')['max_attempts']=1000
    elif defect=='fake_success':task(program,'Q10')['status']='SUCCEEDED'
    elif defect=='live_grant':program['authority']['external_model_calls']=400
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_stale_source_binding_blocks_adoption(program):
    name=next(iter(program['evidence_bindings']))
    program['evidence_bindings'][name]='0'*64
    result=validate(program)
    assert result['status']=='FAIL' and any('changed evidence' in x for x in result['errors'])


def test_oval_failure_releases_bounded_recovery_and_independent_duties(program):
    states={name:'SUCCEEDED' for name in ['S00','S01','N02','T03','E04','P05','F06','X07']}
    states['V08']='FAILED'
    result=frontier(program,states,{'local_implementation'},
                    {'V08':'SUPPORTED_FRAGMENT_INCOMPATIBILITY'})
    assert 'R08' in result['ready']
    assert 'D11' in result['ready']
    assert 'Q10' not in result['ready']
    states['C09']='SUCCEEDED';states['R08']='SUCCEEDED'
    assert 'Q10' in frontier(program,states,{'local_implementation'})['ready']


def test_successful_primary_engine_does_not_run_recovery(program):
    result=frontier(program,{'V08':'SUCCEEDED'},{'local_implementation'})
    assert 'R08' not in result['ready'] and result['recovery_not_needed']==['R08']


def test_unclassified_or_source_failure_does_not_authorize_evaluator_recovery(program):
    states={name:'SUCCEEDED' for name in ['S00','S01','N02','T03','E04','P05','F06','X07']}
    states['V08']='FAILED'
    result=frontier(program,states,{'local_implementation'})
    assert result['blocked']['R08']==['failure class not qualified']
    result=frontier(program,states,{'local_implementation'}, {'V08':'SOURCE_INVALID'})
    assert 'R08' not in result['ready'] and 'R08' in result['recovery_not_needed']


@pytest.mark.parametrize('name,dependency',[('F06','P05'),('X07','T03')])
def test_implementation_cannot_precede_its_contract_or_independent_cases(program,name,dependency):
    task(program,name)['requires_success'].remove(dependency)
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_late_model_authority_does_not_block_manual_release(program):
    states={t['id']:'SUCCEEDED' for t in program['tasks']}
    states['R08']='SKIPPED';states['G16']='NOT_STARTED'
    result=frontier(program,states,{'local_implementation'})
    assert 'G16' not in result['ready']
    assert result['blocked']['G16']==['authority: bounded_generation']
    assert completion(program,states)['manual_release']
    assert not completion(program,states)['full_program_complete']
    assert 'G16' in frontier(program,states,{'local_implementation','bounded_generation'})['ready']


def test_completion_review_runs_after_failure_without_promoting_feature(program):
    states={t['id']:'SUCCEEDED' for t in program['tasks']}
    states.update({'V08':'FAILED','R08':'FAILED','Q10':'BLOCKED','Q13':'BLOCKED',
                   'G16':'BLOCKED','K17':'BLOCKED','A18':'BLOCKED','L19':'NOT_STARTED'})
    assert 'L19' in frontier(program,states,{'local_implementation'})['ready']
    states['L19']='SUCCEEDED'
    result=completion(program,states)
    assert not result['manual_release'] and not result['full_program_complete']


def test_alternative_pass_completes_without_falsifying_primary_failure(program):
    states={t['id']:'SUCCEEDED' for t in program['tasks']}
    states['V08']='FAILED'
    assert completion(program,states)['full_program_complete']
    states['R08']='FAILED'
    assert not completion(program,states)['full_program_complete']


def test_unrun_optional_branch_requires_an_explicit_disposition(program):
    states={t['id']:'SUCCEEDED' for t in program['tasks']}
    states['C09C']='NOT_STARTED'
    result=completion(program,states)
    assert not result['manual_release'] and not result['full_program_complete']
    assert result['manual_release_pending_completion']==['C09C']
    states['C09C']='BLOCKED'
    assert completion(program,states)['manual_release']
    assert completion(program,states)['full_program_complete']
    states['R08']='NOT_STARTED'
    assert not completion(program,states)['full_program_complete']


def test_release_label_cannot_hide_a_failed_semantic_dependency(program):
    states={t['id']:'SUCCEEDED' for t in program['tasks']}
    states['F06']='FAILED'
    result=completion(program,states)
    assert not result['manual_release'] and not result['full_program_complete']
    assert 'A18' in result['missing_required']


def test_required_task_and_success_edge_cannot_be_dropped_together(program):
    task(program,'Q13')['mandatory_for_full_program']=False
    program['completion']['full_program_requires'].remove('Q13')
    task(program,'K17')['requires_success'].remove('Q13')
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_acceptance_inventory_retains_source_correction_mutants(program):
    program['acceptance_inventory']['mutations'].remove('M15')
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_recovery_is_not_an_unconditional_extra_attempt(program):
    task(program,'R08')['on_failure']=[]
    assert validate(program,check_bindings=False)['status']=='FAIL'
    task(program,'R08')['on_failure']=['V08']
    task(program,'Q10')['requires_success'].append('V08')
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_recovery_cannot_bypass_authority_or_invalid_evidence(program):
    task(program,'R08')['failure_trigger']['accepted_failure_classes'].append('AUTHORITY_INVALID')
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_required_generation_cannot_disappear_from_full_completion(program):
    task(program,'G16')['mandatory_for_full_program']=False
    program['completion']['full_program_requires'].remove('G16')
    assert validate(program,check_bindings=False)['status']=='FAIL'


def test_paths_cannot_escape_bound_worktree(tmp_path):
    (tmp_path/'ok').write_text('evidence')
    outside=tmp_path.parent/(tmp_path.name+'-outside')
    outside.write_text('outside evidence')
    (tmp_path/'link').symlink_to(outside)
    for name in ['../'+outside.name,'link','/etc/passwd','.git/config']:
        with pytest.raises(ValueError):safe_file(tmp_path,name)
    assert safe_file(tmp_path,'ok').read_text()=='evidence'
