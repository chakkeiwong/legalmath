"""Independent frozen readings of uses, printed purposes and source projections."""
import hashlib

from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_reference_address_projection_oracle import verify_projection

KEY = 'purpose_use_discovery'


def mapping(value, required):
    assert type(value) is dict and set(required) <= set(value), 'Missing or malformed report fields'
    return value


def span(value, wanted, text, pieces, raw, operations):
    mapping(value, ('start', 'end', 'raw', 'source_projection'))
    assert {k: value[k] for k in ('start', 'end', 'raw')} == wanted, 'Source span differs'
    assert type(value['start']) is int and type(value['end']) is int
    assert text[value['start']:value['end']] == value['raw']
    assert type(value['source_projection']) is list
    verify_projection(value['source_projection'], value['start'], value['end'], text, pieces, raw, operations)


def verify(actual, old, products, expected, profile):
    mapping(actual, (KEY, 'report_sha256'))
    assert {k: v for k, v in actual.items() if k not in (KEY, 'report_sha256')} == {
        k: v for k, v in old.items() if k != 'report_sha256'}, 'Previous answer changed'
    assert actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    report = mapping(actual[KEY], ('profile_sha256', 'products_sha256', 'ordinary_answer_sha256',
        'version', 'text_sha256', 'language', 'declarations', 'occurrences', 'unsupported_declarations',
        'scope_admitted', 'meaning_admitted', 'general_recall_established', 'automatic_legal_interpretation',
        'prior_answer_preserved', 'original_records_preserved', 'whole_task_complete', 'legal_truth_established',
        'reviewed_binding_reconciliation'))
    assert report['profile_sha256'] == digest(profile)
    assert report['products_sha256'] == digest(products) and report['ordinary_answer_sha256'] == digest(old)
    assert report['version'] == 'purpose-use-discovery.v1' and report['language'] == 'de'
    for name in ('scope_admitted', 'meaning_admitted', 'general_recall_established',
                 'automatic_legal_interpretation', 'whole_task_complete', 'legal_truth_established'):
        assert report[name] is False, name
    assert report['prior_answer_preserved'] is True and report['original_records_preserved'] is True
    assert report['unsupported_declarations'] == []
    assembly = products['P2']['payload']['assembly']
    text, operations = assembly['continuous_text'], assembly['operations']
    assert report['text_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    pieces = old['definition_sources']['source_pieces']
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    index = old['reference_addresses']['index']
    assert type(report['declarations']) is list and len(report['declarations']) == expected['declaration_count']
    declared = []
    for row, want in zip(report['declarations'], expected['scopes']):
        mapping(row, ('declaration_start', 'declaration_end', 'raw', 'term', 'restriction', 'value',
            'printed_scope_address', 'family', 'address_status', 'targets', 'source_projection'))
        assert row['declaration_start'] == want['declaration_start']
        original = next(r for r in old['unquoted_definitions']['candidates'] if r['start'] == want['declaration_start'])
        assert row['declaration_end'] == original['end'] and row['raw'] == original['raw']
        assert text[row['declaration_start']:row['declaration_end']] == row['raw']
        assert type(row['source_projection']) is list
        verify_projection(row['source_projection'], row['declaration_start'], row['declaration_end'],
                          text, pieces, raw, operations)
        assert row['printed_scope_address'] == {'section': want['section'], 'paragraph': want['path'][0]}
        assert row['family'] == {'adjective_stem': 'vorzeitig', 'noun': 'rückzahlungsbetrag'}
        assert row['address_status'] == 'EXACT_PRINTED_ADDRESS'
        assert type(row['targets']) is list and len(row['targets']) == 1
        target = mapping(row['targets'][0], ('section', 'path', 'printed_label', 'start', 'end'))
        assert target in index
        assert {k: target[k] for k in ('section', 'path', 'printed_label', 'start', 'end')} == {
            k: want[k] for k in ('section', 'path', 'printed_label', 'start', 'end')}
        assert target['text_sha256'] == digest(text[target['start']:target['end']].encode())
        assert target['legal_meaning_established'] is False
        verify_projection(target['source_projection'], target['start'], target['end'],
                          text, pieces, raw, operations)
        for name, source_name in (('term', 'term'), ('restriction', 'restriction'), ('value', 'value')):
            span(row[name], want[source_name], text, pieces, raw, operations)
        declared.append(want['declaration_start'])
    assert type(report['occurrences']) is list and len(report['occurrences']) == expected['candidate_count']
    for row, want in zip(report['occurrences'], expected['occurrences']):
        mapping(row, ('start', 'end', 'raw', 'role', 'status', 'region', 'family',
            'compatible_declaration_starts', 'selected_declaration_starts', 'review_required',
            'governing_scope', 'meaning', 'legal_meaning_established', 'source_projection'))
        assert {k: row[k] for k in ('start', 'end', 'raw', 'role', 'selected_declaration_starts')} == {
            k: want[k] for k in ('start', 'end', 'raw', 'role', 'selected_declaration_starts')}
        span(row, {k: want[k] for k in ('start', 'end', 'raw')}, text, pieces, raw, operations)
        assert row['family'] == {'adjective_stem': 'vorzeitig', 'noun': 'rückzahlungsbetrag'}
        assert row['region'] == 'selected-contract' and row['compatible_declaration_starts'] == declared
        status = ('SELF_DECLARATION' if want['role'] == 'DECLARATION_TERM' else
                  'NON_OPERATIVE_HEADING' if want['role'] == 'HEADING_CANDIDATE' else
                  'UNIQUE_PRINTED_PURPOSE' if want['selected_declaration_starts'] else 'UNRESOLVED_PRINTED_PURPOSE')
        assert row['status'] == status
        assert row['review_required'] is True and row['governing_scope'] is None and row['meaning'] is None
        assert row['legal_meaning_established'] is False
    recon = mapping(report['reviewed_binding_reconciliation'], ('declaration_rule_candidates', 'occurrences',
        'reviewed_matrix_used_to_select_occurrences', 'reviewed_matrix_changed', 'new_semantic_capability'))
    for name in ('reviewed_matrix_used_to_select_occurrences', 'reviewed_matrix_changed', 'new_semantic_capability'):
        assert recon[name] is False
    assert recon['declaration_rule_candidates'] == {'21343': ['tax'], '21487': ['makewhole']}
    assert type(recon['occurrences']) is list and len(recon['occurrences']) == len(expected['occurrences'])
    old_apps = {(r['start'], r['end']): r for r in old['definition_sources']['application_supplement']['applications']}
    for row, want in zip(recon['occurrences'], expected['occurrences']):
        mapping(row, ('start', 'end', 'reviewed_application_id', 'reviewed_role', 'reviewed_rule',
            'proposed_reviewed_rule_ids', 'status', 'meaning_derived', 'independent_legal_proof'))
        assert (row['start'], row['end']) == (want['start'], want['end'])
        app = old_apps.get((want['start'], want['end']))
        assert row['reviewed_application_id'] == (app['id'] if app else None)
        assert row['reviewed_role'] == (app['role'] if app else None)
        assert row['reviewed_rule'] == want['reviewed_rule']
        assert row['proposed_reviewed_rule_ids'] == ([want['reviewed_rule']] if want['reviewed_rule'] else [])
        status = ('NOT_PRESENT_IN_REVIEWED_APPLICATIONS' if app is None else
                  'AGREES_WITH_REVIEWED_CONDITIONAL_BINDING' if want['reviewed_rule'] else 'AGREES_ON_EXPLICIT_REMAINDER')
        assert row['status'] == status and row['meaning_derived'] is False and row['independent_legal_proof'] is False
    assert not any(n['section'] == '5' and n['path'] == ['10', 'a'] for n in index)
    return {'status': 'PASS', 'source_occurrences': 6, 'distinct_printed_purposes': 2,
        'broad_reference_unselected': True, 'heading_not_operative': True,
        'complete_prior_answer_equal': True, 'new_legal_meaning': False, 'whole_task_complete': False}
