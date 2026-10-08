from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import challenge_contract as c
from .support import packet, reading


def inputs():
    p = packet(); candidates = {'candidate.a': reading()}
    q = {'control_id':'gift.control', 'question':'Is this offer prohibited?',
        'unit_of_assessment':'one offer', 'actor':'distributor', 'temporal_basis':'declared time',
        'result_kind':'PROHIBITED', 'true_means':'prohibited gift', 'false_means':'prohibition not established',
        'source_evidence':deepcopy(candidates['candidate.a']['citations'])}
    questions = {'candidate.a':q}
    return p, candidates, questions, c.build(p, candidates, questions)


def answer(contract, packet, selected=None, status='UNRESOLVED'):
    selected = selected or [o['obligation_id'] for o in contract['obligations']]
    return {'binding_hash':contract['binding_hash'], 'answers':[
        {k:o[k] for k in ('obligation_id','candidate_hash','question_hash')} |
        {'status':status, 'evidence':[{'unit_id':packet['units'][0]['unit_id'],'quote':packet['units'][0]['text']}],
         'rationale':'Mathematical fixture; no legal label', 'followup_question':'Does the exemption qualify this question?'}
        for o in contract['obligations'] if o['obligation_id'] in selected],
        'alternative_readings':[], 'unrepresented_concerns':[], 'proposed_formal_premises':[]}


def test_all_dimensions_exist_even_without_lexical_cues():
    p, candidates, questions, _ = inputs(); p['units'][0]['text']='甲乙丙'
    for r in candidates.values(): r['citations'][0]['quote']='甲乙丙'
    questions['candidate.a']['source_evidence'][0]['quote']='甲乙丙'
    contract=c.build(p,candidates,questions)
    assert len(contract['obligations'])==len(c.DIMENSIONS)==9
    assert not contract['source_cues']['cues'] and not contract['legal_coverage_complete']


def test_source_cues_are_exact_and_do_not_supply_elimination():
    p,_,_,contract=inputs(); cues=contract['source_cues']['cues']
    assert any(x['dimension']=='exception' for x in cues)
    for row in cues:
        assert p['units'][0]['text'][row['start_codepoint']:row['end_codepoint']]==row['quote']
    assert 'pruned_candidates' not in contract


@pytest.mark.parametrize('part',['source','question','candidate','missing','duplicate'])
def test_changed_inputs_or_denominator_reject(part):
    p,r,q,contract=inputs()
    if part=='source': p['selected_slice']+=' amended'
    elif part=='question': q['candidate.a']['actor']='another actor'
    elif part=='candidate': r['candidate.a']['formalization']['result']='gift'
    elif part=='missing': contract['obligations'].pop()
    else: contract['obligations'].append(contract['obligations'][0])
    with pytest.raises(LegalMathError): c.validate_contract(contract,p,r,q)


@pytest.mark.parametrize('defect',['missing','duplicate','wrong-question','wrong-candidate','quote','missing-question','foreign'])
def test_answer_accounting_and_original_identities_are_checked(defect):
    p,r,q,contract=inputs(); selected=[o['obligation_id'] for o in contract['obligations']]
    value=answer(contract,p)
    if defect=='missing': value['answers'].pop()
    elif defect=='duplicate': value['answers'][-1]=deepcopy(value['answers'][0])
    elif defect=='wrong-question': value['answers'][0]['question_hash']='a'*64
    elif defect=='wrong-candidate': value['answers'][0]['candidate_hash']='a'*64
    elif defect=='quote': value['answers'][0]['evidence'][0]['quote']='Invented exemption'
    elif defect=='missing-question': value['answers'][0]['followup_question']=None
    else: value['answers'][0]['obligation_id']='foreign'
    with pytest.raises(LegalMathError): c.validate_response(value,contract,p,selected)


def test_first_round_is_blind_and_full_context_survives_output_selection():
    p,r,q,contract=inputs(); selected=[contract['obligations'][0]['obligation_id']]
    request=c.request(contract,p,r,q,selected,'exception-challenger')
    assert request['source_packet']==p and request['candidates']==r and request['questions']==q
    assert len(request['obligations'])==9 and 'prior_round_evidence' not in request
    prior={'structure-reader':answer(contract,p)}
    assert c.request(contract,p,r,q,selected,'exception-challenger',prior=prior)['prior_round_evidence']==prior


def test_renamed_candidate_does_not_create_new_substantive_issue():
    p,r,q,old=inputs(); renamed=deepcopy(r['candidate.a']); renamed['local_id']='renamed'
    new=c.build(p,{'renamed':renamed},{'renamed':q['candidate.a']})
    assert {o['obligation_id'] for o in old['obligations']}=={o['obligation_id'] for o in new['obligations']}
    assert old['binding_hash']!=new['binding_hash']
