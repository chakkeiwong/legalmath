"""The successor uses one existing allowance and enforces phase dependencies."""
import importlib.util
from pathlib import Path
import sys
import pytest
from legalmath.canonical import loads,digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.issue_search import validate_issue


def runner(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('issue_private_supervisor',root/'scripts/run_interpretation_plan.py')
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    monkeypatch.setitem(sys.modules,'run_interpretation_plan',supervisor)
    spec=importlib.util.spec_from_file_location('issue_runner_test',root/'scripts/run_issue_plan.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,supervisor


def test_fixed_commands_and_admitted_increment(monkeypatch,tmp_path,root):
    module,_=runner(monkeypatch)
    assert module.commands('F3',tmp_path)[0][1][1:]==[
        'scripts/run_issue_phase.py','--phase','F3','--out',str(tmp_path/'live')]
    doc=root/'docs/implementation/interpretation-round8'
    auth=loads((doc/'authorization.json').read_bytes())
    contracts=[loads((doc/'contracts'/f'{p}.json').read_bytes()) for p in ('F1','F2','F3','F4')]
    assert sum(c['maximum_actions'] for c in contracts)==87
    assert max(c['reservation_ceiling'] for c in contracts)==auth['used_before']+87<=500
    assert auth['ledger']=='artifacts/interpretation/round7/live-allowance.json'
    assert module.protect()['new_allowance']['maximum']==500


def test_unreviewed_execution_and_overwrite_fail(monkeypatch,tmp_path):
    module,supervisor=runner(monkeypatch);supervisor.OUT=tmp_path
    state=supervisor.state()
    with pytest.raises(ValueError,match='Missing/stale'):module.run('F0',state)
    with pytest.raises(ValueError,match='Predecessor'):module.run('F2',state)
    state['phases']['F0']['status']='PASSED'
    with pytest.raises(ValueError,match='already passed'):module.run('F0',state)


def test_actual_issues_have_exact_source_quotes_and_parallel_text_is_added_separately(root):
    doc=root/'docs/implementation/interpretation-round8'
    source=loads((doc/'source.json').read_bytes());packet=source['packet']
    for name in ('trigger-issue','qualification-issue'):
        issue=loads((doc/(name+'.json')).read_bytes());assert validate_issue(issue,packet)==issue
        assert len(issue['facts'])==3
    other=loads((doc/'parallel-source.json').read_bytes())
    assert other['english_parent_hash']==digest(packet)
    assert other['packet']['units'][:-1]==packet['units']
    assert other['packet']['units'][-1]['unit_id']=='parallel.tc.body'
    assert len(source['trigger_claims'])==8


def test_critique_cannot_substitute_a_different_source_or_question():
    from tests.assurance.test_issue_search import data,response
    from legalmath.interpretation.assurance.issue_search import merge_hypotheses,audit_request
    from tests.assurance.test_output_semantics import AT
    p,r,issue=data();merged=merge_hypotheses({'syntax-reader':response(r)},issue,p,AT)
    comparisons={'issue_hash':digest(issue),'source_packet_hash':digest(p),'candidates_hash':digest(merged['candidates']),
        'outputs':{},'ranked_scenarios':[]}
    comparisons['source_packet_hash']='0'*64
    with pytest.raises(LegalMathError):audit_request(issue,p,merged['candidates'],comparisons,'source-critic')


def test_completed_live_summary_uses_canonical_integer_timing(monkeypatch,tmp_path,root):
    from legalmath.interpretation.assurance.monitor import save
    spec=importlib.util.spec_from_file_location('issue_phase_test',root/'scripts/run_issue_phase.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'OUT',tmp_path/'out')
    ledger=tmp_path/'allowance.json';monkeypatch.setattr(module,'LEDGER',ledger)
    grant={'maximum':500,'calls':[]};save(ledger,grant)
    study=module.Study.__new__(module.Study)
    study.phase='F1';study.directory=tmp_path/'attempt';study.directory.mkdir()
    study.before=grant;study.used_before=0;study.began=module.monotonic()-0.123
    study.contract={'maximum_actions':54}
    study.finish({'status':'CHECKS_COMPLETED'})
    summary=loads((study.directory/'summary.json').read_bytes())
    assert type(summary['wall_milliseconds'])is int and summary['wall_milliseconds']>=123
    assert (study.directory/'manifest.json').exists() and summary['new_calls']==0
