from copy import deepcopy
from pathlib import Path

import pytest

from scripts.legal_integration_accounts import source_quote, conditional_account, graph_proposal, SOURCE
from scripts.legal_integration_master import ROOT
from scripts.legal_integration_post_review import finish_transaction
from scripts.legal_mission_execution import Refused, read, ref, save
from legalmath.interpretation.assurance.arguments import evaluate_criticism


@pytest.fixture
def envelope():
    return read(ROOT/SOURCE)


def test_long_source_returns_actual_matched_quote():
    text='unrelated '*600+'Operative rule.'+' trailing '*600
    packet={'source_packet':{'units':[{'unit_id':'right','text':text,'locator':'right document'}]}}
    hit=source_quote(packet,'Operative rule.',unit_id='right')
    assert hit['start']>1800
    assert text[hit['start']:hit['end']]==hit['quote']=='Operative rule.'
    with pytest.raises(Refused):source_quote(packet,'Operative rule.',unit_id='wrong')
    packet['source_packet']['units'].append({'unit_id':'other','text':text})
    with pytest.raises(Refused):source_quote(packet,'Operative rule.')


def test_duplicate_within_unit_is_ambiguous():
    packet={'source_packet':{'units':[{'unit_id':'u','text':'Rule. Rule.'}]}}
    with pytest.raises(Refused):source_quote(packet,'Rule.')


def test_register_rule_is_not_generic_handbook_6_8(envelope):
    answer=conditional_account('p10',envelope)
    rule=answer['sources']['UT-Code:6.8']
    assert 'maintain a register of holders' in rule['quote']
    assert rule['start']>1800
    with pytest.raises(Refused):
        source_quote(envelope,rule['quote'],unit_id='handbook.oct2024.page17')


@pytest.mark.parametrize('qid',['p10','p14','evidence','gatecoin'])
def test_accounts_have_bound_sources_and_keep_fulfillment_open(envelope,qid):
    account=conditional_account(qid,envelope)
    for paragraph in account['reasoning']:
        assert set(paragraph['source_keys'])<=set(account['sources'])
    for quote in account['sources'].values():
        assert source_quote(envelope,quote['quote'],unit_id=quote['unit_id'])['start']==quote['start']
    assert account['original_inventory_fulfilled'] is False
    assert account['actual_product_answer'] is False


@pytest.mark.parametrize('case',['SUPPORTED','ADVERSE','UNKNOWN'])
def test_gatecoin_exception_undercuts_without_reversing_legal_conclusion(envelope,case):
    proposal,expected=graph_proposal('gatecoin',case,envelope)
    evaluation=evaluate_criticism(proposal,envelope['source_packet'],
                                  [a['candidate_id'] for a in proposal['arguments']])
    assert evaluation['semantics']['grounded']==expected
    assert not any(a['conclusion']=={'atom':'ncc','negative':True} for a in proposal['arguments'])
    assert all('unless there is evidence' in a['evidence'][0]['quote'] for a in proposal['arguments'])
    assert all('7th scenario' not in a['evidence'][0]['quote'] for a in proposal['arguments'])
    if case=='ADVERSE':
        assert evaluation['defeats']==[['access','default']]
    if case=='UNKNOWN':assert evaluation['blocked_arguments']==['default']


def test_gatecoin_refuses_scenario_seven_in_place_of_exception(envelope):
    corrupted=deepcopy(envelope)
    unit=next(u for u in corrupted['source_packet']['units'] if u['unit_id']=='dbccd54bdabce.u0.0')
    unit['text']=unit['text'].replace(
        'The customers should be regarded as NCCs unless there is evidence to show that they have accessed or used the Platform to effect the transactions;',
        'The transactions described in the 7th scenario did not exist and the customers should not be regarded as NCC.')
    with pytest.raises(Refused):graph_proposal('gatecoin','ADVERSE',corrupted)


@pytest.mark.parametrize('case',['NO_REQUEST_RIVALS','REQUEST_INADEQUATE','REQUEST_ADEQUATE','UNKNOWN'])
def test_p14_controls_preserve_hypotheses_and_unknowns(envelope,case):
    proposal,expected=graph_proposal('p14',case,envelope)
    evaluation=evaluate_criticism(proposal,envelope['source_packet'],
                                  [a['candidate_id'] for a in proposal['arguments']])
    assert evaluation['semantics']['grounded']==expected
    assert not proposal['preferences']
    assert all(any(p['kind']=='ASSUMPTION' for p in a['premises']) for a in proposal['arguments'])
    assert evaluation['legal_premises_verified'] is False
    if case=='NO_REQUEST_RIVALS':
        assert len({a['candidate_id'] for a in proposal['arguments']})==2
        assert evaluation['semantics']['undecided_grounded']==['footnote','main']
    if case=='UNKNOWN':assert evaluation['blocked_arguments']==['main']


def transaction(root):
    for name,value in [('a','old-a'),('b','old-b'),('new-a','next-a'),('new-b','next-b')]:
        (root/name).write_text(value)
    save(root/'journal.json',{'status':'PREPARED','writes':[
        {'path':p,'before':ref(root,p),'replacement':ref(root,'new-'+p)} for p in ('a','b')]})


def test_registration_resumes_partial_replacement(tmp_path):
    transaction(tmp_path)
    (tmp_path/'a').write_bytes((tmp_path/'new-a').read_bytes())
    finish_transaction(tmp_path,Path('journal.json'))
    assert (tmp_path/'b').read_text()=='next-b'
    assert read(tmp_path/'journal.json')['status']=='COMMITTED'
    finish_transaction(tmp_path,Path('journal.json'))


def test_registration_preserves_unrelated_concurrent_edit(tmp_path):
    transaction(tmp_path)
    (tmp_path/'b').write_text('other worker')
    with pytest.raises(Refused,match='Concurrent edit'):
        finish_transaction(tmp_path,Path('journal.json'))
    assert (tmp_path/'a').read_text()=='old-a'
    assert (tmp_path/'b').read_text()=='other worker'


def test_master_verify_selects_current_revision(tmp_path,monkeypatch,capsys):
    from scripts import legal_integration_master as master
    from scripts import legal_integration_substantive_verify as current
    monkeypatch.setattr(master,'ROOT',tmp_path)
    save(tmp_path/master.PROGRAM,{'remaining_work_revision':True,'substantive_continuation_revision':True})
    monkeypatch.setattr(current,'check',lambda:{'current_revision':True})
    monkeypatch.setattr('sys.argv',['master','verify'])
    master.main()
    assert 'current_revision' in capsys.readouterr().out


def test_approval_packet_refuses_stale_current_implementation(tmp_path,monkeypatch):
    from scripts import legal_integration_post_review as review
    (tmp_path/'implementation.py').write_text('original')
    save(tmp_path/'proposal.json',{'implementation':[ref(tmp_path,'implementation.py')]})
    save(tmp_path/review.PROGRAM,{})
    monkeypatch.setattr(review,'ROOT',tmp_path)
    monkeypatch.setattr(review,'latest_evidence',lambda tid:{'proposal':ref(tmp_path,'proposal.json')})
    (tmp_path/'implementation.py').write_text('changed after preparation')
    with pytest.raises(Refused,match='Changed evidence'):review.approval_packet()
