"""Independent exact-source checks; reviewed meanings do not select candidates."""
import hashlib
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_reference_address_projection_oracle import verify_projection

KEY = 'unquoted_definitions'


def verify(actual, old, products, expected):
    assert {k: v for k, v in actual.items() if k not in (KEY, 'report_sha256')} == {
        k: v for k, v in old.items() if k != 'report_sha256'}
    assert actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    report = actual[KEY]
    assert report['products_sha256'] == digest(products) and report['ordinary_answer_sha256'] == digest(old)
    assert report['prior_answer_preserved'] is True and report['original_records_preserved'] is True
    for key in ('whole_task_complete', 'legal_truth_established', 'general_recall_established',
                'automatic_legal_interpretation', 'scope_admitted', 'meaning_admitted'):
        assert report[key] is False
    assert len(report['candidates']) == expected['count'] == 7
    assembly = products['P2']['payload']['assembly']
    text = assembly['continuous_text']
    assert report['version'] == 'unquoted-definitions.v1' and report['language'] == 'de'
    assert report['text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    pieces = old['definition_sources']['source_pieces']
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    for row, wanted in zip(report['candidates'], expected['candidates']):
        assert row['region'] == 'selected-contract'
        assert {k: row[k] for k in ('kind', 'start', 'end', 'raw', 'label')} == {
            k: wanted[k] for k in ('kind', 'start', 'end', 'raw', 'label')}
        for key in ('term', 'scope', 'value'):
            if wanted[key] is None:
                assert row[key] is None
            else:
                assert {k: row[key][k] for k in ('start', 'end', 'raw')} == wanted[key]
        if wanted['kind'] == 'REFERENCE_EXPANSION':
            condition = row['condition']
            assert isinstance(condition, dict)
            a = text.index('soweit', row['start'], row['end'])
            b = text.index(',', a, row['end'])
            assert {k: condition[k] for k in ('start', 'end', 'raw')} == {
                'start': a, 'end': b, 'raw': text[a:b]}
        else:
            assert row['condition'] is None
        address = {'section': '5', 'paragraph': '2' if wanted['review_record'] == 'U06-tax-early-amount' else '5'}
        assert row['printed_scope_address'] == (address if wanted['kind'] == 'PURPOSE_CONDITIONED_AMOUNT' else None)
        assert row['review_required'] is True and row['governing_scope'] is None and row['meaning'] is None
        assert row['legal_meaning_established'] is False
        for part in (row, row['term'], row['scope'], row['value'], row['condition']):
            if part is not None:
                assert text[part['start']:part['end']] == part['raw']
                verify_projection(part['source_projection'], part['start'], part['end'],
                                  text, pieces, raw, assembly['operations'])
    amount = [r for r in report['candidates'] if r['kind'] == 'PURPOSE_CONDITIONED_AMOUNT']
    assert len(amount) == 2 and amount[0]['label'] == amount[1]['label']
    assert amount[0]['scope']['raw'] != amount[1]['scope']['raw'] and amount[0]['value']['raw'] != amount[1]['value']['raw']
    assert all(r['label'] != 'Zinsperiode' for r in report['candidates'])
    assert any(r['kind'] == 'UNSUPPORTED_DEFINITION_CUE' for r in report['issues'])
    for issue in report['issues']:
        assert issue['region'] == 'selected-contract' and issue['kind'] == 'UNSUPPORTED_DEFINITION_CUE'
        assert text[issue['start']:issue['end']] == issue['raw']
    return {'status': 'PASS', 'source_definitions': 7, 'exact_term_scope_value_spans': True,
        'separate_conditioned_amounts': 2, 'invented_missing_definitions': 0,
        'complete_prior_answer_equal': True, 'general_recall_established': False}
