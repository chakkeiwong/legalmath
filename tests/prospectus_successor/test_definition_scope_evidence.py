"""Discriminate printed boundary checks from supplied scope and legal authority."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import definition_scope_evidence as scope
from legalmath.prospectus.successor import definition_applications as applications
from legalmath.prospectus.successor.definition_scopes import specification as sources
from scripts import prospectus_explicit_scope_trial as prep

ROOT = Path(__file__).resolve().parents[2]


def source(request):
    return {k: deepcopy(v) for k, v in request.items() if k != 'rules'}


def example():
    return source(prep.cases()['cases'][0]['request'])


def selected():
    return prep.read(prep.PREP / 'request.json')


def summarize(report):
    return [{k: row[k] for k in ('start', 'end', 'status', 'extent', 'section')}
            for row in report['restrictions']]


def explicit_piece(request):
    return next(p for p in request['source_pieces'] if p['text'].startswith('Für die Zwecke'))


def unresolved(request):
    report = scope.discover(request)
    assert report['restrictions'][0]['status'] == 'REVIEW_REQUIRED'
    assert report['restrictions'][0]['extent'] is None


def test_original_independent_scope_and_unresolved_purposes():
    request = selected()
    report = scope.discover(source(request))
    assert summarize(report) == prep.read(prep.PREP / 'expected.json')['restrictions']
    assert scope.check_rules(request['text'], request['source_pieces'], request['rules'])['checked'] == [
        {'rule': 'affiliate', 'restriction_start': 34003, 'extent': [32176, 34657]}]
    explicit = report['restrictions'][3]
    assert explicit['label_roles'] == explicit['boundary_roles'] == ['HEADER']
    assert explicit['legal_scope_established'] is report['legal_scope_established'] is False


@pytest.mark.parametrize('structural', [False, True])
def test_original_registered_profiles_still_admit(structural):
    req = selected()
    report = applications.admit(req['text'], applications.packet(structural), sources(structural))
    assert len(report['rules']) == 5
    assert len(report['applications']) == 25
    assert report['automatic_legal_interpretation_established'] is False


@pytest.mark.parametrize('case', prep.cases()['cases'], ids=lambda row: row['id'])
def test_frozen_independent_examples(case):
    assert summarize(scope.discover(source(case['request']))) == case['expected']


def test_arbitrary_section_numbers_and_nonconsecutive_boundary():
    text = '§ 527\nFür die Zwecke dieses §527 bedeutet "Bank" eine Bank.\n§ 610\nEnde'
    report = scope.discover(source(prep.fixture(text)))
    assert report['restrictions'][0]['extent'] == [0, text.index('§ 610')]
    assert report['restrictions'][0]['section'] == '527'


def test_unknown_label_role_does_not_become_header_authority():
    req = example()
    for piece in req['source_pieces']:
        if piece['text'].startswith('§ '):
            piece['assembly_uses'][0]['role'] = 'UNKNOWN'
    report = scope.discover(req)
    assert report['restrictions'][0]['status'] == 'EXPLICIT_SECTION'
    assert report['restrictions'][0]['label_roles'] == ['UNKNOWN']
    assert report['restrictions'][0]['legal_scope_established'] is False


def test_raw_and_assembly_offsets_are_distinct_coordinate_systems():
    req = example()
    piece = req['source_pieces'][0]
    piece['raw_binding']['start'] += 7
    piece['raw_binding']['end'] += 7
    piece['assembly_uses'][0]['source'] = deepcopy(piece['raw_binding'])
    assert scope.discover(req)['restrictions'][0]['status'] == 'EXPLICIT_SECTION'


@pytest.mark.parametrize('text', [
    'Für die Zwecke dieses § 37 bedeutet "Linde" eine Firma.\n§ 38\nEnde',
    '§ 37\nFür die Zwecke dieses § 37 bedeutet "Linde" eine Firma.',
    '§ 36\nFür die Zwecke dieses § 37 bedeutet "Linde" eine Firma.\n§ 38\nEnde',
    'Text § 37\nFür die Zwecke dieses § 37 bedeutet "Linde" eine Firma.\n§ 38\nEnde',
    '§ 37\n§ 37\nFür die Zwecke dieses § 37 bedeutet "Linde" eine Firma.\n§ 38\nEnde',
    '§ 37\nFür die Zwecke dieses § 37 bedeutet "Linde" eine Firma.\n§ 38\n§ 37',
])
def test_missing_wrong_duplicate_or_inline_labels_do_not_prove_boundary(text):
    unresolved(source(prep.fixture(text)))


@pytest.mark.parametrize('change', ['missing-use', 'duplicate-use', 'unknown-context', 'foreign-context',
                                    'foreign-document', 'foreign-hash', 'altered-raw', 'altered-use',
                                    'missing-raw', 'transformed', 'nonheader-role', 'nonoperative-purpose',
                                    'invalid-use-length', 'negative-use-offset', 'boolean-use-offset'])
def test_adverse_provenance_cannot_prove_scope(change):
    req = example()
    label = req['source_pieces'][0]
    middle = next(p for p in req['source_pieces'] if p['text'] == 'TEXT')
    if change == 'missing-use':
        label['assembly_uses'] = []
    elif change == 'duplicate-use':
        label['assembly_uses'] *= 2
    elif change == 'unknown-context':
        label['assembly_uses'][0]['context'] = None
    elif change == 'foreign-context':
        middle['assembly_uses'][0]['context'] = 'another-contract'
    elif change in ('foreign-document', 'foreign-hash'):
        key, value = ('document', 'another-document') if change == 'foreign-document' else ('source_sha256', 'a' * 64)
        middle['raw_binding'][key] = value
        middle['assembly_uses'][0]['source'][key] = value
    elif change == 'altered-raw':
        label['raw_binding']['quote'] = '§ 99'
    elif change == 'altered-use':
        label['assembly_uses'][0]['source']['quote'] = '§ 99'
    elif change == 'missing-raw':
        label['raw_binding'] = None
    elif change == 'transformed':
        label['kind'] = 'SUPPLIED_OR_TRANSFORMED'
    elif change == 'nonheader-role':
        label['assembly_uses'][0]['role'] = 'OPERATIVE'
    elif change == 'nonoperative-purpose':
        explicit_piece(req)['assembly_uses'][0]['role'] = 'UNKNOWN'
    elif change == 'invalid-use-length':
        label['assembly_uses'][0]['end'] += 1
    elif change == 'negative-use-offset':
        label['assembly_uses'][0]['start'] = -1
        label['assembly_uses'][0]['end'] -= 1
    elif change == 'boolean-use-offset':
        label['assembly_uses'][0]['start'] = False
    unresolved(req)


@pytest.mark.parametrize('change', ['hash', 'gap', 'overlap', 'altered-copy', 'rules-leaked'])
def test_invalid_source_request_is_refused(change):
    req = example()
    if change == 'hash':
        req['text_sha256'] = 'a' * 64
    elif change == 'gap':
        req['source_pieces'].pop(1)
    elif change == 'overlap':
        req['source_pieces'][1]['start'] -= 1
    elif change == 'altered-copy':
        req['source_pieces'][0]['text'] = '§ 99'
    else:
        req['rules'] = [{'extents': [[0, len(req['text'])]]}]
    with pytest.raises(ValueError):
        scope.discover(req)


@pytest.mark.parametrize('extents', [[[32176, 34658]], [[34003, 34124]], [[0, 46365]],
                                     [[32176, 34657], [0, 100]], []])
def test_conflicting_supplied_extents_are_refused(extents):
    req = selected()
    req['rules'][3]['extents'] = extents
    with pytest.raises(ValueError, match='conflicts with printed self-section'):
        scope.check_rules(req['text'], req['source_pieces'], req['rules'])


def test_omitted_or_duplicated_explicit_premise_is_refused():
    req = selected()
    for rules in ([r for r in req['rules'] if r['id'] != 'affiliate'],
                  req['rules'] + [deepcopy(req['rules'][3])]):
        with pytest.raises(ValueError, match='missing or duplicated'):
            scope.check_rules(req['text'], req['source_pieces'], rules)


def test_real_admit_path_invokes_source_guard(monkeypatch):
    def refuse(*args):
        raise ValueError('guard reached in real admission')
    monkeypatch.setattr(scope, 'check_rules', refuse)
    req = selected()
    with pytest.raises(ValueError, match='guard reached in real admission'):
        applications.admit(req['text'], applications.packet(True), sources(True))


def test_consistent_occurrence_relabeling_cannot_evade_source_guard(monkeypatch):
    req = selected()
    spec = applications.specification(True)
    spec['rules'][3]['extents'] = [[34003, 34124]]
    for occurrence in spec['occurrences']:
        if occurrence['group'] == 'affiliate' and not 34003 <= occurrence['start'] < occurrence['end'] <= 34124:
            occurrence['role'] = 'STATUTORY_REFERENT'
    # Even a newly pinned internal profile must pass the independent invariant.
    monkeypatch.setattr(applications, 'specification', lambda structural=False: spec)
    with pytest.raises(ValueError, match='conflicts with printed self-section'):
        applications.admit(req['text'], applications.packet(True), sources(True))


def test_cli_uses_source_only_request(tmp_path):
    from legalmath.cli import main
    import sys
    from unittest.mock import patch
    request, output = tmp_path / 'source.json', tmp_path / 'scope.json'
    req = example()
    request.write_text(json.dumps(req))
    with patch.object(sys, 'argv', ['legalmath', 'prospectus', 'discover-definition-scope',
                                   '--request', str(request), '--output', str(output)]):
        main()
    report = json.loads(output.read_text())
    assert report['restrictions'][0]['extent'] == [0, req['text'].index('§ 38')]
    assert report['legal_scope_established'] is False
