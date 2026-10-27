from copy import deepcopy

import pytest

from scripts import legal_context_failure_repair as repair


def inputs():
    request = {
        'records': [{'id': 'source:one', 'kind': 'source'},
                    {'id': 'assignment:two', 'kind': 'dependency'}],
        'available_source_indexes': [{'index_hash': 'doc-a'}, {'index_hash': 'doc-b'}],
        'payload': {'prior_needs': [{'need_id': 'fact', 'route': 'CLIENT_FACT'},
                                    {'need_id': 'text', 'route': 'SOURCE_TEXT'}],
                    'source_delivery_failures': {'text': {'status': 'FAILED'}}},
    }
    wire = {
        'review': {'verdict': 'UNRESOLVED', 'issues': ['Missing facts'], 'support': []},
        'reason': 'The missing evidence matters.', 'assertion_bindings': [], 'source_gaps': [],
        'context_needs': [
            {'kind': 'CLIENT_FACT', 'record_ids': ['source:one'],
             'locators': [{'index_hash': 'doc-a', 'locator': 'P1'}],
             'query': 'What actually happened?', 'reason': 'Not established.'},
            {'kind': 'SOURCE_TEXT', 'record_ids': ['r1'],
             'locators': [{'index_hash': 'typo', 'locator': 'P1'}],
             'query': 'Needed authority', 'reason': 'Unresolved.'}],
        'need_dispositions': [
            {'need_id': 'fact', 'disposition': 'SUPPLIED_SOURCE',
             'reason': 'Facts remain unknown.', 'support': []},
            {'need_id': 'text', 'disposition': 'SUPPLIED_SOURCE',
             'reason': 'Delivery failed.', 'support': []}],
    }
    aliases = {'r0': 'source:one', 'r1': 'assignment:two'}
    return request, wire, aliases


def test_choices_keep_source_aliases_separate_from_dependencies():
    req, wire, aliases = inputs()
    rows = {r['path']: r for r in repair.permitted_edits(req, wire, aliases)}
    assert rows['/context_needs/1/record_ids']['choices'] == [[]]
    assert rows['/context_needs/1/locators/0/index_hash']['choices'] == ['doc-a', 'doc-b']
    assert rows['/need_dispositions/0/disposition']['choices'] == [
        'STILL_REQUIRED', 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER']
    assert rows['/need_dispositions/1/disposition']['choices'] == ['STILL_REQUIRED']


def test_shape_repair_preserves_missing_need_and_every_other_field():
    req, wire, aliases = inputs()
    before = deepcopy(wire)
    rules = repair.permitted_edits(req, wire, aliases)
    changes = [{'path': r['path'], 'value': []} for r in rules
               if r['mode'] == 'DETERMINISTIC_IDENTIFIER_CLEARING']
    result = repair.apply_edits(wire, rules, changes)
    expected = deepcopy(wire)
    expected['context_needs'][0]['record_ids'] = []
    expected['context_needs'][0]['locators'] = []
    assert result == expected
    assert wire == before


@pytest.mark.parametrize('path,value', [
    ('/review/verdict', 'ACCEPT'), ('/review/issues', []), ('/review/support', ['invented']),
    ('/reason', 'Changed conclusion'), ('/source_gaps', ['changed']),
    ('/assertion_bindings', [{'invented': True}]), ('/context_needs', []),
    ('/context_needs/0/kind', 'SOURCE_TEXT'), ('/context_needs/0/query', 'Changed'),
    ('/context_needs/0/reason', 'Satisfied'), ('/need_dispositions/0/reason', 'Changed'),
    ('/need_dispositions/0/support', ['invented']),
])
def test_substantive_mutations_are_refused(path, value):
    req, wire, aliases = inputs()
    with pytest.raises(ValueError, match='Unauthorized'):
        repair.apply_edits(wire, repair.permitted_edits(req, wire, aliases),
                           [{'path': path, 'value': value}])


@pytest.mark.parametrize('path,value', [
    ('/context_needs/1/record_ids', ['r1']),
    ('/context_needs/1/locators/0/index_hash', 'doc-nearest'),
    ('/context_needs/0/record_ids', ['source:one']),
    ('/need_dispositions/0/disposition', 'SUPPLIED_SOURCE'),
    ('/need_dispositions/1/disposition', 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER'),
])
def test_unoffered_choices_and_delivery_waivers_are_refused(path, value):
    req, wire, aliases = inputs()
    with pytest.raises(ValueError, match='not an offered'):
        repair.apply_edits(wire, repair.permitted_edits(req, wire, aliases),
                           [{'path': path, 'value': value}])


def test_duplicate_stale_and_extra_fields_are_refused():
    req, wire, aliases = inputs()
    rules = repair.permitted_edits(req, wire, aliases)
    change = {'path': '/context_needs/0/record_ids', 'value': []}
    with pytest.raises(ValueError, match='duplicate'):
        repair.apply_edits(wire, rules, [change, change])
    with pytest.raises(ValueError, match='only path and value'):
        repair.apply_edits(wire, rules, [dict(change, reason='new prose')])
    wire['context_needs'][0]['record_ids'] = ['different']
    with pytest.raises(ValueError, match='Stale'):
        repair.apply_edits(wire, rules, [change])


def test_valid_fields_are_not_editable():
    req, wire, aliases = inputs()
    wire['context_needs'][1]['record_ids'] = ['r0']
    wire['context_needs'][1]['locators'][0]['index_hash'] = 'doc-a'
    rules = repair.permitted_edits(req, wire, aliases)
    assert not any(r['path'].startswith('/context_needs/1/') for r in rules)


def test_retained_output_cannot_be_replaced(tmp_path):
    path = tmp_path / 'receipt.json'
    repair.save_retained(path, {'status': 'REJECTED'})
    repair.save_retained(path, {'status': 'REJECTED'})
    with pytest.raises(ValueError, match='replace retained'):
        repair.save_retained(path, {'status': 'ACCEPT'})


def test_protocol_projection_is_explicit_and_does_not_mutate_wire():
    wire = {'need_dispositions': [{'answer_evidence': {'path': '/conclusion', 'quote': 'old'}}],
            'review': {'verdict': 'UNRESOLVED'}, 'context_needs': []}
    baseline = deepcopy(wire)
    projected = repair.protocol_wire(wire)
    assert projected['need_dispositions'][0]['answer_evidence'] == {'answer_field': '/conclusion'}
    assert projected['review'] == baseline['review']
    assert wire == baseline


def test_non_source_removal_preserves_real_sources_and_the_need():
    req, wire, aliases = inputs()
    wire['context_needs'][1]['record_ids'] = ['source:one', 'r1', 'r0']
    rules = repair.permitted_edits(req, wire, aliases)
    rule = next(r for r in rules if r['path'] == '/context_needs/1/record_ids')
    assert rule['choices'] == [['source:one', 'r0']]
    result = repair.apply_edits(wire, rules, [{'path': rule['path'], 'value': rule['choices'][0]}])
    expected = deepcopy(wire)
    expected['context_needs'][1]['record_ids'] = ['source:one', 'r0']
    assert result == expected
    with pytest.raises(ValueError, match='not an offered'):
        repair.apply_edits(wire, rules, [{'path': rule['path'], 'value': []}])


def test_unknown_alias_and_unidentified_need_cannot_be_cleared():
    req, wire, aliases = inputs()
    wire['context_needs'][1]['record_ids'] = ['unknown']
    rules = repair.permitted_edits(req, wire, aliases)
    rule = next(r for r in rules if r['path'].startswith('/context_needs/1/record_ids'))
    assert rule['mode'] == 'EXPLICIT_SOURCE_SELECTION'
    assert rule['choices'] == ['source:one', 'r0']
    wire['context_needs'][1].update(record_ids=['r1'], locators=[], query='')
    rules = repair.permitted_edits(req, wire, aliases)
    assert not any(r['mode'] == 'REMOVE_AUTHENTICATED_NON_SOURCE_IDS' for r in rules)
