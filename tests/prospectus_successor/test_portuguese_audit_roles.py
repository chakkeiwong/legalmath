"""Finite inspected Portuguese reports: source roles, coverage and rebinding."""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from legalmath.prospectus.successor import report_scope
from legalmath.prospectus.successor.contracts import digest

BASE = Path(__file__).resolve().parents[2] / 'docs/implementation/prospectus-execution-authority/attempts/portuguese-2008'
READINGS = json.loads((BASE / 'attempt-001/selected-reading.json').read_text())
SCOPE = json.loads((BASE / 'attempt-002/positive-v2-scope.json').read_text())
AUDITS = ('consolidated-2008-pt', 'individual-2008-pt')
UNKNOWN = {'status': 'UNKNOWN', 'reason': 'Not established in this control'}


def fixture(rid):
    selected = deepcopy(READINGS)
    selected['reports'] = [r for r in selected['reports'] if r['id'] == rid]
    scope = deepcopy(SCOPE)
    scope['reports'] = [r for r in scope['reports'] if r['id'] == rid]
    scope['readings_sha256'] = digest(selected)
    scope['context_profile'] = 'portuguese-report-context.v2'
    return selected, scope


def direct(selected, scope):
    report, = report_scope.explain(report_scope.admit(selected, scope))
    return report


def rehash(selected, scope):
    reading, = selected['reports']
    reading['sha256'] = digest({k: v for k, v in reading.items() if k != 'sha256'})
    scope['reports'][0]['reading_sha256'] = reading['sha256']
    scope['readings_sha256'] = digest(selected)


def span(text, a, b):
    return {'start': a, 'end': b, 'quote': text[a:b]}


@pytest.mark.parametrize('rid', (*AUDITS, 'committee-2008-pt'))
def test_full_inspected_readings_preserve_report_kind_and_unknown_authority(rid):
    selected, scope = fixture(rid)
    report = direct(selected, scope)
    assert report['status'] == 'CONDITIONAL_SUPPLIED_READING'
    assert not report['unresolved_context_fields']
    assert not report['independent_legal_acceptance']
    assert not report['context_review']['general_semantic_truth_established']
    assert all(report['facts'][f]['status'] == 'UNKNOWN' for f in report_scope.EXTERNAL)
    if rid.startswith('committee'):
        assert report['use_assessment']['committee_concurrence'] == 'SUPPLIED_SOURCE_SUPPORT'
        assert report['use_assessment']['financial_statement_audit_opinion'] == 'NOT_ESTABLISHED_BY_THIS_READING'
        assert report['facts']['assurance_level']['status'] == 'UNKNOWN'
    else:
        assert report['use_assessment']['financial_statement_audit_opinion'] == 'SUPPLIED_SOURCE_SUPPORT'
        roles = report['context_review']['distinct_source_statements']
        assert roles['board_responsibilities']['quote'].startswith('É da responsabilidade do Conselho')
        assert roles['auditor_responsibility']['quote'].startswith('A nossa responsabilidade')
        assert roles['audit_scope']['quote'].startswith('O exame a que procedemos')
        assert roles['management_report_concordance']['quote'].startswith('O nosso exame abrangeu ainda')
        assert roles['opinion_basis']['quote'].startswith('Entendemos que o exame efectuado')
        assert 'Em nossa opinião' in ' '.join(roles['financial_statement_opinion']['quote'].split())
        assert 'em todos os aspectos materialmente relevantes' in ' '.join(roles['opinion_materiality']['quote'].split())
        reading, = selected['reports']
        for role in roles.values():
            a, b = role['start'], role['end']
            assert role['quote'] == reading['text'][a:b]
            assert role['source_characters'] == [c for c in reading['characters'] if a <= c['output'] < b]


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('quote', [
    'É da responsabilidade do Conselho de Administração:',
    'A nossa responsabilidade consiste em verificar a informação financeira',
    'O exame a que procedemos foi efectuado',
    'O nosso exame abrangeu ainda a verificação da concordância',
    'Entendemos que o exame efectuado proporciona uma base aceitável',
])
def test_literal_words_from_other_roles_are_not_the_audit_opinion(rid, quote):
    selected, scope = fixture(rid)
    text = selected['reports'][0]['text']
    a = text.index(quote)
    scope['reports'][0]['facts']['conclusion']['spans'] = [span(text, a, a + len(quote))]
    before_scope = deepcopy(scope)
    before_scope['context_profile'] = 'portuguese-report-context.v1'
    before, after = direct(selected, before_scope), direct(selected, scope)
    assert before['status'] == 'CONDITIONAL_SUPPLIED_READING'
    assert after['status'] == 'INCOMPLETE_SOURCE_READING'
    assert after['facts'] == before['facts']
    assert after['unresolved_context_fields'] == ['conclusion']


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('field,append', [
    ('conclusion', True), ('assurance_level', True), ('assurance_level', False)])
def test_required_role_plus_board_duties_does_not_clear_the_role_check(rid, field, append):
    selected, scope = fixture(rid)
    text = selected['reports'][0]['text']
    quote = 'É da responsabilidade do Conselho de Administração:'
    a = text.index(quote)
    fact = scope['reports'][0]['facts'][field]
    if not append:
        fact['spans'].clear()
    fact['spans'].append(span(text, a, a + len(quote)))
    report = direct(selected, scope)
    assert report['unresolved_context_fields'] == [field]
    assert report['use_assessment']['financial_statement_audit_opinion'] == 'NOT_ESTABLISHED_BY_THIS_READING'


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('field,omission', [
    ('conclusion', 'materialmente'), ('conclusion', 'Normas'),
    ('assurance_level', 'aceitável'), ('assurance_level', 'materialmente')])
def test_missing_materiality_criteria_or_assurance_words_withhold_support(rid, field, omission):
    selected, scope = fixture(rid)
    text = selected['reports'][0]['text']
    fact = scope['reports'][0]['facts'][field]
    original, = fact['spans']
    a, b = original['start'], original['end']
    cut = text.index(omission, a, b)
    fact['spans'] = [span(text, a, cut), span(text, cut + len(omission), b)]
    report = direct(selected, scope)
    assert report['status'] == 'INCOMPLETE_SOURCE_READING'
    assert report['unresolved_context_fields'] == [field]


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('field', ['conclusion', 'assurance_level'])
def test_complete_fragmented_nonspace_coverage_is_sufficient(rid, field):
    selected, scope = fixture(rid)
    text = selected['reports'][0]['text']
    fact = scope['reports'][0]['facts'][field]
    original, = fact['spans']
    a, b = original['start'], original['end']
    fact['spans'] = [span(text, a + m.start(), a + m.end()) for m in re.finditer(r'\S+', text[a:b])]
    assert direct(selected, scope)['status'] == 'CONDITIONAL_SUPPLIED_READING'


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('field', ['conclusion', 'assurance_level'])
def test_unknown_required_role_stays_unknown(rid, field):
    selected, scope = fixture(rid)
    scope['reports'][0]['facts'][field] = deepcopy(UNKNOWN)
    report = direct(selected, scope)
    assert field in report['missing_essential_facts']
    assert field in report['unresolved_context_fields']


@pytest.mark.parametrize('rid', (*AUDITS, 'committee-2008-pt'))
@pytest.mark.parametrize('change', ['new_edition', 'reordered_pages', 'missing_page', 'other_mode',
                                   'changed_text', 'derivative_text'])
def test_rehashing_cannot_transfer_inspected_support_to_another_reading(rid, change):
    selected, scope = fixture(rid)
    reading, = selected['reports']
    if change == 'new_edition':
        reading['source_sha256'] = '0' * 64
    elif change == 'reordered_pages':
        reading['pages'].reverse()
    elif change == 'missing_page':
        reading['pages'].pop()
    elif change == 'other_mode':
        reading['pages'][0]['mode'] = 'layout'
    else:
        addition = '\nCom reserva adicional não examinada.'
        offset = len(reading['text'])
        reading['text'] += addition
        reading['characters'] += [{'output': offset + i, 'unit': 'changed-source',
                                  'source_offset': i, 'character': c} for i, c in enumerate(addition)]
        if change == 'derivative_text':
            reading['source_sha256'] = digest(reading['text'].encode())
    rehash(selected, scope)
    report = direct(selected, scope)
    assert report['status'] == 'INCOMPLETE_SOURCE_READING'
    assert 'source_structure' in report['unresolved_context_fields']
    assert report['context_review']['checks']['source_structure']['status'] == 'UNRECOGNIZED_OR_CHANGED_SOURCE_READING'


@pytest.mark.parametrize('rid', AUDITS)
@pytest.mark.parametrize('change', ['missing', 'duplicate', 'wrong_character', 'negative_offset', 'repeated_origin'])
def test_rehashing_cannot_hide_corrupt_source_character_ownership(rid, change):
    selected, scope = fixture(rid)
    chars = selected['reports'][0]['characters']
    if change == 'missing':
        chars.pop(0)
    elif change == 'duplicate':
        chars.append(deepcopy(chars[0]))
    elif change == 'wrong_character':
        chars[0]['character'] = 'X'
    elif change == 'negative_offset':
        chars[0]['source_offset'] = -1
    else:
        chars[1]['unit'] = chars[0]['unit']
        chars[1]['source_offset'] = chars[0]['source_offset']
    rehash(selected, scope)
    with pytest.raises(ValueError, match='provenance|unmapped'):
        direct(selected, scope)


@pytest.mark.parametrize('rid', AUDITS)
def test_coherently_reclassified_audit_cannot_become_a_committee_report(rid):
    selected, scope = fixture(rid)
    facts = scope['reports'][0]['facts']
    facts['identity']['value'] = 'COMMITTEE_REPORT'
    for field, value in report_scope.PROFILES['COMMITTEE_REPORT'].items():
        facts[field]['value'] = value
    facts['assurance_level'] = deepcopy(UNKNOWN)
    with pytest.raises(ValueError, match='Portuguese report contradicts'):
        direct(selected, scope)


@pytest.mark.parametrize('profile', [None, [], {}, 'automatic-portuguese-truth'])
def test_profile_selection_requires_an_explicit_supported_name(profile):
    selected, scope = fixture(AUDITS[0])
    scope['context_profile'] = profile
    with pytest.raises(ValueError, match='profile'):
        direct(selected, scope)
