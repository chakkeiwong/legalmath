"""Expectations follow declared formal constructions, not human legal labels."""
from copy import deepcopy
from itertools import product

import pytest

from legalmath.prospectus.common import sha, write
from legalmath.prospectus.loss_absorption import FACTS, decide, explain
from legalmath.prospectus.loss_absorption_checks import reference
from legalmath.prospectus.loss_absorption_reader import analyze_issue, clause_features, quote_valid


def features(text, **kwargs):
    return {(f['kind'], f['disposition']) for f in clause_features(text, **kwargs)}


@pytest.mark.parametrize('values', list(product((False, True, None, 'conflict'), repeat=4)))
def test_finite_known_unknown_conflict_semantics(values):
    assert decide(dict(zip(FACTS, values)))['answer'] is reference(values)


@pytest.mark.parametrize('text,kind', [
    ('Upon a Trigger Event the principal amount of the Notes shall be permanently written down to zero.', 'principal_write_down'),
    ('The Notes may be temporarily written down by reducing the principal amount.', 'principal_write_down'),
    ('The resolution authority may reduce or cancel the principal amount of the Notes under its bail-in power.', 'principal_write_down'),
    ('Upon a Trigger Event the Notes will automatically convert into ordinary shares.', 'mandatory_common_conversion'),
    ('The Issuer may convert the Notes into common shares without the consent of holders.', 'mandatory_common_conversion'),
])
def test_actual_mechanism_constructions(text, kind):
    assert (kind, 'applicable') in features(text)


@pytest.mark.parametrize('text,disposition', [
    ('The Notes are unsubordinated obligations.', None),
    ('The Notes are perpetual and deeply subordinated obligations.', None),
    ('Interest on the Notes may be cancelled at the Issuer\'s discretion.', 'distribution_only'),
    ('The Notes purchased or redeemed shall be cancelled.', 'repurchase_or_redemption_cancellation'),
    ('The Notes convert the interest basis from fixed rate to floating rate.', 'interest_rate_conversion'),
    ('The Notes may be converted from one currency into another currency.', 'currency_conversion'),
    ('The resolution authority with jurisdiction over the administrator for the SOFR Benchmark may discontinue the benchmark for the Notes.', 'benchmark_administrator'),
    ('At the option of the holders, the Notes may convert into common shares.', 'holder_optional_conversion'),
    ('The Notes will convert into preferred shares on the specified date.', 'preferred_share_conversion'),
    ('Other securities will automatically convert into ordinary shares.', 'other_security'),
    ('An Extraordinary Resolution passed by a majority of holders may reduce the principal amount of the Notes.', 'creditor_amendment'),
])
def test_confounding_constructions(text, disposition):
    found = features(text)
    assert ('principal_write_down', 'applicable') not in found
    assert ('mandatory_common_conversion', 'applicable') not in found
    if disposition:
        assert ('candidate', disposition) in found


def fixture(tmp_path, pages, *, title='Example senior notes', operative=None):
    original = tmp_path / 'original.pdf'; original.write_bytes(b'controlled-source-fixture')
    document = {'source_sha256': sha(original.read_bytes()), 'preliminary_indicator': False,
                'pages': [{'page': i + 1, 'text': t} for i, t in enumerate(pages)]}
    text = tmp_path / 'text.json'; write(text, document)
    row = {'id': 'document', 'original': str(original), 'text': str(text),
           'sha256': sha(original.read_bytes()), 'text_sha256': sha(text.read_bytes()), 'pages': len(pages),
           'identity_markers': ['Example issuer']}
    selection = {'id': 'document', 'required_markers': [title]}
    if operative is not None: selection['operative_pages'] = operative
    issue = {'id': 'example', 'title': title, 'documents': [selection]}
    return issue, {'document': row}, document


ORDINARY = ('Example issuer. Example senior notes. The Notes are direct, unsecured and unsubordinated obligations. '
            'The Notes will be redeemed at maturity at 100% of their principal amount.')


def test_negative_requires_affirmative_terms_and_reason(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY])
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is False
    assert result['classification'] == 'non loss absorption'
    assert 'cash principal repayment' in result['summary_reason']
    assert 'document, PDF p.1' in result['summary_reason']


def test_no_keyword_hit_is_not_a_negative(tmp_path):
    issue, docs, _ = fixture(tmp_path, ['Example issuer. Example senior notes. No operative terms supplied.'])
    assert analyze_issue(issue, docs, tmp_path)['answer'] is None


def test_late_page_clause_changes_answer_and_reason(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY] + ['Routine information.'] * 9 +
        ['On a Trigger Event the Notes shall automatically convert into ordinary shares.'])
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is True
    assert 'compulsorily converted' in result['summary_reason']
    assert 'p.11' in result['summary_reason']


def test_cross_page_clause_keeps_both_pages_and_classification(tmp_path):
    issue, docs, document = fixture(tmp_path, [ORDINARY + ' On a Trigger Event the Notes shall automatically',
                                              'convert into ordinary shares.'])
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is True
    witness = next(e for e in result['evidence'] if e['kind'] == 'mandatory_common_conversion')
    assert witness['page'] == 1 and witness['end_page'] == 2
    assert quote_valid(witness, document)


@pytest.mark.parametrize('fault', ['original', 'text', 'identity', 'missing_document', 'page_count', 'preliminary', 'missing_terms'])
def test_invalid_evidence_never_defaults_to_negative(tmp_path, fault):
    issue, docs, document = fixture(tmp_path, [ORDINARY])
    row = docs['document']
    if fault == 'original': (tmp_path / 'original.pdf').write_bytes(b'changed source')
    elif fault == 'text': (tmp_path / 'text.json').write_text('{}')
    elif fault == 'identity': row['identity_markers'] = ['A different issuer']
    elif fault == 'missing_document': issue['documents'].append({'id': 'absent supplement'})
    elif fault == 'page_count': row['pages'] += 1
    elif fault == 'preliminary':
        document['preliminary_indicator'] = True; write(tmp_path / 'text.json', document)
        row['text_sha256'] = sha((tmp_path / 'text.json').read_bytes())
    elif fault == 'missing_terms': issue['unresolved_operative_dependencies'] = ['Missing applicable base prospectus']
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is None
    assert result['open_issues']
    assert 'No supported yes/no' in result['summary_reason']


def test_unknown_share_class_does_not_become_common_shares(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + ' The Notes shall convert into shares.'])
    assert analyze_issue(issue, docs, tmp_path)['answer'] is None


def test_qualifying_and_absolute_negative_clauses_conflict(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + ' The Notes are not convertible. '
        'On a Trigger Event the Notes shall automatically convert into ordinary shares.'])
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is None and result['status'] == 'conflicting evidence'


def test_foreign_scope_cannot_override_selected_terms(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY, 'Other securities will be written down to zero.'], operative=[[1, 1]])
    assert analyze_issue(issue, docs, tmp_path)['answer'] is False


def test_stale_quote_rejected_even_for_whitespace_change(tmp_path):
    issue, docs, document = fixture(tmp_path, [ORDINARY])
    quote = analyze_issue(issue, docs, tmp_path)['evidence'][0]
    changed = deepcopy(document); changed['source_sha256'] = sha(b'new bytes, same words')
    assert not quote_valid(quote, changed)


def test_positive_reason_cannot_be_supplied_without_its_witness():
    with pytest.raises(ValueError, match='witness'):
        explain({'status': 'qualified source reading', 'answer': True}, [])


@pytest.mark.parametrize('clause', [
    'A partial redemption of the Notes uses a pool factor corresponding to a reduction of the nominal amount redeemed.',
    'Upon partial repayment the debt securities will be canceled and new securities for the remaining principal amount issued.',
    'The consent of the holder of each debt security is required to reduce the principal amount.',
    'We may redeem the Notes at 100% of their principal amount plus interest, excluding interest cancelled at our discretion.',
    'The Volume Weighted Average Price of an Ordinary Share or other Security shall use the Conversion Price of the shares.',
    'The conversion of one class of capital stock into another class is permitted, including other convertible notes that rank equally with the Notes.',
    'The nominal amount of each Note shall be reduced by the Instalment Amount upon its payment.',
    'The Notes pay the principal amount only on winding up and we may cancel any interest payment.',
    'We would recognize a taxable credit if the principal amount of the Securities were written down.',
    'Shareholders passed a resolution to increase share capital for any securities that will convert into ordinary shares.',
])
def test_repayment_price_and_other_security_are_not_mechanisms(clause):
    found = features(clause)
    assert ('principal_write_down', 'applicable') not in found
    assert ('mandatory_common_conversion', 'applicable') not in found


@pytest.mark.parametrize('clause', [
    'Even if no Write-Down is made, the Notes may be Written -Down on another Trigger Event.',
    'Liabilities are not written down at the start of resolution but may be written down later.',
])
def test_conditional_or_temporal_negation_is_not_absolute_denial(clause):
    assert not any(f['kind'] in ('no_conversion','no_write_down') for f in clause_features(clause))


def test_section_boundary_cannot_hide_new_operative_clause(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY, 'An unfinished foreign sentence without a period',
        'The Notes shall automatically convert into ordinary shares.'], operative=[[1,1],[3,3]])
    result = analyze_issue(issue, docs, tmp_path)
    assert result['answer'] is True
    assert 'p.3' in result['summary_reason']


def test_issuer_country_and_rank_do_not_supply_answer(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY])
    baseline = analyze_issue(issue, docs, tmp_path)
    issue.update(issuer='A different issuer', jurisdiction='Switzerland', rank='additional tier 1')
    changed = analyze_issue(issue, docs, tmp_path)
    assert changed['answer'] is baseline['answer']
    assert changed['summary_reason'] == baseline['summary_reason']


def test_future_statutory_scope_does_not_become_established_mechanism():
    found=features('This condition is applicable only if the Notes are in the scope of future law as implemented. '
                   'The resolution authority may reduce the principal amount of the Notes under its bail-in power.')
    assert ('candidate','unresolved_statutory_scope') in found
    assert ('principal_write_down','applicable') not in found


def test_historical_date_mention_cannot_satisfy_selected_edition(tmp_path):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' Base Prospectus dated 18 June 2026.',
                                  'Previously issued under the Base Prospectus dated 13 June 2025.'])
    issue['documents'][0]['required_markers']=['13 June 2025']
    issue['documents'][0]['required_page_markers']=[{'page':1,'text':'13 June 2025'}]
    result=analyze_issue(issue,docs,tmp_path)
    assert result['answer'] is None
    assert 'required page' in result['summary_reason']


def test_correct_cover_edition_is_accepted(tmp_path):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' Base Prospectus dated 13 June 2025.'])
    issue['documents'][0]['required_page_markers']=[{'page':1,'text':'13 June 2025'}]
    assert analyze_issue(issue,docs,tmp_path)['answer'] is False
