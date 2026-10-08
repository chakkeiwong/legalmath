"""Formal construction contrasts; no issuer-specific expected-answer labels."""
from copy import deepcopy
from itertools import product

import pytest

from legalmath.prospectus.common import digest
from legalmath.prospectus.loss_absorption_derivation import check
from legalmath.prospectus.loss_absorption_reader import analyze_issue, joined, quote_valid
from tests.prospectus.test_loss_absorption import fixture, ORDINARY


def read_clause(tmp_path, clause, definitions=''):
    issue, docs, document = fixture(tmp_path, [ORDINARY+' '+clause+' '+definitions])
    return analyze_issue(issue, docs, tmp_path), document


@pytest.mark.parametrize('security,force,target', product(
    ['Notes', 'Preferred Securities'], ['mandatorily', 'compulsorily'],
    ['ordinary shares', 'newly issued common shares']))
def test_copular_mandatory_relation(tmp_path, security, force, target):
    row, document = read_clause(tmp_path,
        f'Upon a Trigger Event, the {security} are {force} and irrevocably convertible into {target}.')
    assert row['answer'] is True
    e = next(e for e in row['evidence'] if e['kind']=='mandatory_common_conversion')
    assert quote_valid(e, document)
    assert security in e['semantic_witness']['slots']['subject']['text']
    assert row['certified_legal_answer'] is None


@pytest.mark.parametrize('clause', [
    'The Notes are not mandatorily convertible into ordinary shares.',
    'The Notes are convertible into ordinary shares.',
    'Other Preferred Securities are mandatorily convertible into ordinary shares.',
    'Interest on the Notes is mandatorily convertible into ordinary shares.',
    'The issuer shall report whether the Notes are mandatorily convertible into ordinary shares.',
    'Hypothetically, the Notes are mandatorily convertible into ordinary shares.',
    'The Notes are mandatorily convertible into ordinary shares at the option of holders.',
    'The Notes are mandatorily convertible into preference shares.',
])
def test_copular_polarity_actor_and_class_contrasts(tmp_path, clause):
    row, _ = read_clause(tmp_path, clause)
    assert row['answer'] is not True


def numbered_conversion(action='irrevocably and mandatorily convert all the Notes into Common Shares',
                        actor='the Bank', modal='will', lead='notify the Regulator'):
    return ('If the Trigger Event occurs at any time on or after the Issue Date, then '
            f'{actor} {modal}: (a) {lead}; (b) not make any further distribution; and (c) {action}.')


@pytest.mark.parametrize('modal,target,consent', product(
    ['will', 'shall', 'must'], ['ordinary shares', 'Common Shares'],
    ['', '(and without any requirement for the consent or approval of Holders) ']))
def test_numbered_action_inherits_only_its_governing_modal(tmp_path, modal, target, consent):
    row, document = read_clause(tmp_path,
        numbered_conversion('irrevocably and mandatorily '+consent+
                            'convert all the Preferred Securities into '+target, modal=modal),
        '“Common Shares” means ordinary shares in the capital of the Bank.')
    assert row['answer'] is True
    e = next(e for e in row['evidence'] if e['kind']=='mandatory_common_conversion')
    slots = e['semantic_witness']['slots']
    assert slots['subject']['text']=='the Bank'
    assert slots['modal']['text']==modal
    assert slots['trigger']['text'].startswith('If the Trigger Event occurs')
    assert quote_valid(e, document)


@pytest.mark.parametrize('action,actor,lead', [
    ('not convert the Notes into Common Shares', 'the Bank', 'notify the Regulator'),
    ('report whether the Notes convert into Common Shares', 'the Bank', 'notify the Regulator'),
    ('the holders may elect to convert the Notes into Common Shares', 'the Bank', 'notify the Regulator'),
    ('convert other Notes into Common Shares', 'the Bank', 'notify the Regulator'),
    ('convert the Notes into preference shares', 'the Bank', 'notify the Regulator'),
    ('convert the Notes into Common Shares at the option of holders', 'the Bank', 'notify the Regulator'),
    ('convert the Notes into Common Shares', 'the Holders', 'notify the Regulator'),
    ('consider whether to convert the Notes into Common Shares', 'the Bank', 'notify the Regulator'),
])
def test_numbered_list_action_contrasts(tmp_path, action, actor, lead):
    row, _ = read_clause(tmp_path, numbered_conversion(action, actor=actor, lead=lead),
                         'Common Shares means ordinary shares.')
    assert row['answer'] is not True


@pytest.mark.parametrize('definition', ['', 'Common Shares means preference shares.',
    'Common Shares means ordinary shares. Common Shares means preference shares.'])
def test_numbered_list_requires_consistent_share_definition(tmp_path, definition):
    row, _ = read_clause(tmp_path, numbered_conversion(), definition)
    assert row['answer'] is None


def test_denial_of_holder_option_does_not_negate_separate_mandatory_relation(tmp_path):
    row, _ = read_clause(tmp_path,
        numbered_conversion()+' The Notes are not convertible into Common Shares at the option of Holders.',
        'Common Shares means ordinary shares.')
    assert row['answer'] is True
    assert not any(e['kind']=='no_conversion' and e['disposition']=='applicable' for e in row['evidence'])


def test_absolute_prohibition_still_conflicts_with_mandatory_relation(tmp_path):
    row, _ = read_clause(tmp_path, numbered_conversion()+' The Notes are not convertible.',
                         'Common Shares means ordinary shares.')
    assert row['answer'] is None
    assert row['facts']['mandatory_common_conversion']=='conflict'


def test_list_crosses_page_without_losing_context(tmp_path):
    clause=numbered_conversion()
    split=clause.index('(c)')
    issue, docs, document=fixture(tmp_path,[ORDINARY+' '+clause[:split],
        clause[split:]+' Common Shares means ordinary shares.'])
    row=analyze_issue(issue,docs,tmp_path)
    assert row['answer'] is True
    e=next(e for e in row['evidence'] if e['kind']=='mandatory_common_conversion')
    assert (e['page'],e['end_page'])==(1,2)
    assert quote_valid(e,document)


@pytest.mark.parametrize('suffix', [
    ' subject to the consent of Holders',
    ' only with the approval of Holders',
    ' if the Holders elect to convert',
])
@pytest.mark.parametrize('construction', ['copular','numbered'])
def test_holder_consent_condition_cannot_establish_compulsion(tmp_path,suffix,construction):
    clause=('The Notes are mandatorily convertible into ordinary shares'+suffix+'.'
            if construction=='copular' else
            numbered_conversion('convert the Notes into ordinary shares'+suffix))
    row,_=read_clause(tmp_path,clause)
    assert row['answer'] is not True


def test_numbered_context_cannot_cross_foreign_section(tmp_path):
    clause=numbered_conversion();split=clause.index('(c)')
    issue,docs,_=fixture(tmp_path,[ORDINARY+' '+clause[:split],
        clause[split:]+' Common Shares means ordinary shares.'],operative=[[1,1]])
    assert analyze_issue(issue,docs,tmp_path)['answer'] is not True


@pytest.mark.parametrize('prefix', ['The issuer shall report whether ', 'Hypothetically, '])
def test_list_is_not_evidence_when_embedded_in_reporting_or_hypothesis(tmp_path,prefix):
    row,_=read_clause(tmp_path,prefix+numbered_conversion(),'Common Shares means ordinary shares.')
    assert row['answer'] is not True


@pytest.mark.parametrize('slot', ['subject','modal','trigger','action','target'])
def test_numbered_witness_tampering_is_rejected(tmp_path, slot):
    row, document=read_clause(tmp_path,numbered_conversion(),'Common Shares means ordinary shares.')
    assert row['answer'] is True
    damaged=deepcopy(row)
    e=next(e for e in damaged['evidence'] if e['kind']=='mandatory_common_conversion')
    e['semantic_witness']['slots'][slot]['text']='forged slot'
    old=e['id'];e['id']=digest({k:v for k,v in e.items() if k!='id'})[:24]
    damaged['derivation']['evidence_ids']=[e['id'] if i==old else i for i in damaged['derivation']['evidence_ids']]
    damaged['summary_evidence_ids']=damaged['derivation']['evidence_ids'][:1]
    damaged['derivation']['sha256']=digest({k:v for k,v in damaged['derivation'].items() if k!='sha256'})
    with pytest.raises(ValueError):
        check(damaged,{'document':{'text':joined(document)[0],'sha256':document['source_sha256']}})
