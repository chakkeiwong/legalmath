"""Finite live qualification boundaries exercised without dispatching a model."""
from copy import deepcopy
import pytest
from scripts import legal_mission_response_qualification as q
from scripts.legal_mission_execution import Refused,save,read,ref


def allowance(tmp_path,monkeypatch):
    old=tmp_path/'old';out=tmp_path/'qualification';old.mkdir();out.mkdir()
    prior={'maximum':400,'calls':[{'request_hash':str(i),'stage':'core','arm':'baseline'} for i in range(13)]}
    save(old/'allowance.json',prior);save(out/'allowance.json',prior)
    save(out/'protocol.json',{'bindings':[],'deadline_utc':q.DEADLINE,'global_maximum':400,'maximum_new_calls':4})
    monkeypatch.setattr(q,'OLD',old);monkeypatch.setattr(q,'OUT',out)
    monkeypatch.setattr(q,'ROOT',tmp_path)
    a=q.QualificationAllowance('primary');a.expected='request';a.stage='proposal'
    return a,prior


def test_same_stage_cannot_redispatch_and_history_cannot_be_refunded(tmp_path,monkeypatch):
    a,prior=allowance(tmp_path,monkeypatch)
    assert a.reserve('request')==14
    assert read(q.OLD/'allowance.json')==prior
    with pytest.raises(Refused):a.reserve('request')
    a.stage='review';a.reserve('request')
    with pytest.raises(Refused):a.reserve('request')
    state=read(a.path);state['calls'][0]['request_hash']='replaced';save(a.path,state)
    with pytest.raises(Refused,match='history'):a.check()


def test_unknown_request_and_changed_review_evidence_refuse_before_reservation(tmp_path,monkeypatch):
    a,_=allowance(tmp_path,monkeypatch)
    with pytest.raises(Refused):a.reserve('different')
    source=tmp_path/'source.txt';source.write_text('before')
    protocol=read(a.grant_path);protocol['bindings']=[ref(tmp_path,source)];save(a.grant_path,protocol)
    source.write_text('after')
    with pytest.raises(Refused,match='Changed evidence'):a.reserve('request')
    assert len(read(a.path)['calls'])==13


def test_exact_quotes_and_question_and_case_coverage_are_required():
    request={'source_packet':{'units':[{'unit_id':'u','text':'The original source.'}]},'cases':[{'case_id':'shared-error'}]}
    value={'answers':[{'question_id':k,'answer':'Conditional result','grounds':[{'unit_id':'u','quote':'original source','inference':'Reasoning'}],
             'rival_readings':['Contrary reading'],'unknowns':['Unknown standard']} for k in ('p10','evidence')],
           'case_assessments':[{'case_id':'shared-error','conclusion':'Conditional','reasons':'Reasoned'}],'limitations':['Source selection']}
    q.validate_proposal(value,request)
    for mutate in ('quote','question','case'):
        wrong=deepcopy(value)
        if mutate=='quote':wrong['answers'][0]['grounds'][0]['quote']='Invented'
        elif mutate=='question':wrong['answers'][1]['question_id']='p10'
        else:wrong['case_assessments']=[]
        with pytest.raises(Refused):q.validate_proposal(wrong,request)
