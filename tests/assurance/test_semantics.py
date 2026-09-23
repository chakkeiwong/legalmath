from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.semantics import (
    inventory_request, validate_inventory, merge_inventories, inventory_findings,
    fidelity_request, validate_fidelity, fidelity_findings, representation)
from .support import packet, inventory, reading, fidelity


def test_inventories_are_blind_and_union_preserves_disagreement():
    request = inventory_request(packet(), 'qualification-reader')
    assert 'candidates' not in request and 'readings' not in request and 'peers' not in request
    a = validate_inventory(inventory(), packet()); b = deepcopy(a); b['claims'][0]['modality'] = 'MUST_NOT'
    combined = merge_inventories({'atomic-reader': a, 'qualification-reader': b})
    assert len(combined) == 2
    assert len(merge_inventories({'atomic-reader': a, 'qualification-reader': a})) == 1


def test_shared_omission_is_visible_even_when_candidates_agree():
    inv = inventory(); claims = merge_inventories({'atomic-reader': inv, 'qualification-reader': inv})
    candidates = {'a': reading(True), 'b': reading(True), 'c': reading(True)}
    checks = validate_fidelity(fidelity(claims, candidates, {k: 'NOT_ESTABLISHED' for k in candidates}), packet(), claims, candidates)
    assert len(fidelity_findings(checks)) == 3
    assert 'discount' not in representation(reading(True))  # unused fact cannot masquerade as implemented exception
    assert all(f['stage'] == 'FORMALIZATION' for f in fidelity_findings(checks))


def test_both_inventory_readers_omitting_exception_triggers_separate_cue_check():
    bad = inventory(); bad['claims'][0]['exceptions'] = []
    result = inventory_findings(packet(), {'atomic-reader': bad, 'qualification-reader': bad})
    assert len([f for f in result if f['kind'] == 'UNACCOUNTED_EXCEPTION_CUE']) == 2


def test_authentic_quote_cannot_turn_unknown_into_supported_without_executable_anchor():
    inv = inventory(); claims = merge_inventories({'atomic-reader': inv}); candidates = {'a': reading(True)}
    proposed = fidelity(claims, candidates); proposed['checks'][0]['representation_quotes'] = ['not discount']
    with pytest.raises(LegalMathError): validate_fidelity(proposed, packet(), claims, candidates)
    proposed['checks'][0]['representation_quotes'] = []
    with pytest.raises(LegalMathError): validate_fidelity(proposed, packet(), claims, candidates)


def test_every_claim_candidate_pair_must_be_checked():
    inv = inventory(); claims = merge_inventories({'atomic-reader': inv}); candidates = {'a': reading(), 'b': reading()}
    value = fidelity(claims, candidates); value['checks'].pop()
    with pytest.raises(LegalMathError): validate_fidelity(value, packet(), claims, candidates)


def test_contradiction_requires_positive_evidence_absence_remains_unknown():
    claims = merge_inventories({'atomic-reader': inventory()}); candidates = {'a': reading()}
    value = fidelity(claims, candidates, {'a': 'CONTRADICTED'}); value['checks'][0]['source_evidence'] = []
    with pytest.raises(LegalMathError): validate_fidelity(value, packet(), claims, candidates)
    value['checks'][0]['label'] = 'NOT_ESTABLISHED'
    assert validate_fidelity(value, packet(), claims, candidates)['checks'][0]['label'] == 'NOT_ESTABLISHED'


def test_clean_control_can_pass_diagnostics_without_legal_certification():
    inv = validate_inventory(inventory(), packet()); inventories = {'atomic-reader': inv, 'qualification-reader': inv}
    claims = merge_inventories(inventories); candidates = {'a': reading()}
    assert not inventory_findings(packet(), inventories)
    assert not fidelity_findings(validate_fidelity(fidelity(claims, candidates), packet(), claims, candidates))


def test_remote_qualification_and_modality_are_retained_not_silently_dropped():
    p = packet(); p['units'].append({'unit_id': 'footnote', 'text': 'This exception applies only from 1 June.', 'locator': 'footnote', 'normative': True, 'span': None})
    inv = inventory()
    with pytest.raises(LegalMathError): validate_inventory(inv, p)
    inv['claims'][0]['evidence'].append({'unit_id': 'footnote', 'quote': p['units'][1]['text']})
    inv['claims'][0]['temporal'] = ['Only from 1 June']
    inv['units'].append({'unit_id': 'footnote', 'disposition': 'CLAIMS', 'claim_ids': ['gift'], 'rationale': 'Remote qualification'})
    result = validate_inventory(inv, p)
    assert result['claims'][0]['modality'] == 'SHOULD_NOT' and result['claims'][0]['temporal']


def test_fabricated_source_and_unaccounted_claim_are_rejected():
    inv = inventory(); inv['claims'][0]['evidence'][0]['quote'] = 'Everyone is exempt.'
    with pytest.raises(LegalMathError): validate_inventory(inv, packet())
    inv = inventory(); inv['units'][0].update(disposition='CONTEXT', claim_ids=[])
    with pytest.raises(LegalMathError): validate_inventory(inv, packet())


def test_batched_fidelity_checks_cannot_silently_skip_or_add_a_pair():
    claims=merge_inventories({'atomic-reader':inventory()});candidates={'a':reading(),'b':reading()}
    pairs=[(claims[0]['claim_id'],'a')]
    request=fidelity_request(packet(),claims,candidates,pairs)
    assert request['required_pairs']==[{'claim_id':claims[0]['claim_id'],'candidate_id':'a'}]
    good=fidelity(claims,{'a':reading()})
    validate_fidelity(good,packet(),claims,candidates,pairs)
    with pytest.raises(LegalMathError):validate_fidelity(fidelity(claims,candidates),packet(),claims,candidates,pairs)


@pytest.mark.parametrize('unformalized',[False,True])
def test_invalid_expression_cannot_be_certified_by_quoting_its_error_message(unformalized):
    bad=reading();bad['formalization']['scope']='Selected control in English prose.'
    if unformalized:bad['formalization']=None
    claims=merge_inventories({'atomic-reader':inventory()})
    assert representation(bad).startswith('UNAVAILABLE_EXECUTABLE_MEANING:')
    value=fidelity(claims,{'a':bad});value['checks'][0]['representation_quotes']=[representation(bad)]
    with pytest.raises(LegalMathError):validate_fidelity(value,packet(),claims,{'a':bad})
