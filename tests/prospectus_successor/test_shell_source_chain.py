from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import shell_source_chain as chain
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/finance-conventions/attempt-001/source-P1.json.gz'


@pytest.fixture
def original():
    value = json.loads(gzip.decompress(P1.read_bytes()))['payload']
    return value['graph'], value['request']['bundle']


def test_dated_history_and_restricted_precedence(original):
    graph, bundle = original
    before = digest(graph)
    result = chain.admit(graph, bundle, {'version': chain.VERSION})
    assert result['edition_link']['referenced_date'] == '2020-08-13'
    history = result['trustee_history']
    assert history['original_deed_date'] == '2005-07-22'
    assert history['original_deed_named_trustee'] == 'Citicorp Trustee Company Limited'
    assert history['programme_named_trustee'] == 'Deutsche Trustee Company Limited'
    assert history['successors_included_in_definition'] is True
    assert history['actual_succession_established'] is False
    assert history['contradiction_established'] is False
    assert result['precedence']['condition'] == 'ONLY_IN_THE_EVENT_OF_INCONSISTENCY'
    assert result['precedence']['mandatory_law_overridden'] is False
    assert result['legal_applicability_established'] is False
    assert result['financial_selections']['equal_amounts_make_triggers_equivalent'] is False
    assert digest(graph) == before


@pytest.mark.parametrize('defect', ['wrong-edition', 'wrong-date', 'wrong-instrument',
                                   'missing-document', 'duplicate-document', 'invisible-document',
                                   'wrong-bundle', 'path-mismatch', 'missing-qualifier',
                                   'duplicate-qualifier', 'invisible-qualifier', 'altered-qualifier'])
def test_source_chain_rejects_incomplete_or_changed_context(original, defect):
    graph, bundle = deepcopy(original)
    doc = next(d for d in graph['documents'] if d['id'] == 'shell-2020-base')
    unit = next(u for u in graph['units'] if u['id'] == 'shell-2020-base:p33:l19')
    if defect == 'wrong-edition':
        doc['sha256'] = '0' * 64
    elif defect == 'wrong-date':
        doc['document_date'] = '2021-08-13T00:00:00Z'
    elif defect == 'wrong-instrument':
        graph['instrument_id'] = 'another-note'
    elif defect == 'missing-document':
        graph['documents'].remove(doc)
    elif defect == 'duplicate-document':
        graph['documents'].append(deepcopy(doc))
    elif defect == 'invisible-document':
        doc['visible'] = False
    elif defect == 'wrong-bundle':
        graph['bundle_sha256'] = '0' * 64
    elif defect == 'path-mismatch':
        doc['path'] = 'another.pdf'
    elif defect == 'missing-qualifier':
        graph['units'].remove(unit)
    elif defect == 'duplicate-qualifier':
        graph['units'].append(deepcopy(unit))
    elif defect == 'invisible-qualifier':
        unit['visible'] = False
    elif defect == 'altered-qualifier':
        unit['raw'] = unit['raw'].replace('successor', 'previous')
    with pytest.raises(ValueError):
        chain.admit(graph, bundle, {'version': chain.VERSION})


@pytest.mark.parametrize('profile', [None, {}, [], {'version': 'generic'},
                                    {'version': chain.VERSION, 'authentic': True}])
def test_no_undeclared_profile_or_asserted_authenticity(original, profile):
    with pytest.raises(ValueError):
        chain.admit(*original, profile)


@pytest.mark.parametrize('defect', ['forged-succession', 'forged-publication', 'lost-agreement',
                                   'changed-precedence', 'false-as-zero', 'lost-source', 'omitted-review'])
def test_rehashed_review_corruption_is_rejected(original, defect):
    graph, bundle = original
    profile = {'version': chain.VERSION}
    report = chain.admit(graph, bundle, profile)
    if defect == 'forged-succession':
        report['trustee_history']['actual_succession_established'] = True
    elif defect == 'forged-publication':
        report['edition_link']['historical_publication'] = '2020-08-13'
    elif defect == 'lost-agreement':
        report['onward_documents'].pop()
    elif defect == 'changed-precedence':
        report['precedence']['rules'][0]['prevails'] = 'AGENCY_AGREEMENT'
    elif defect == 'false-as-zero':
        report['legal_applicability_established'] = 0
    elif defect == 'lost-source':
        report['sources']['conditions_and_agreements'].pop()
    selected = {} if defect == 'omitted-review' else {'contract_source_chain': report}
    with pytest.raises(ValueError):
        chain.verify(graph, bundle, {'contract_source_chain': profile}, selected)


def test_unsolicited_review_refused_and_absence_preserved(original):
    graph, bundle = original
    assert chain.verify(graph, bundle, {}, {}) is None
    with pytest.raises(ValueError):
        chain.verify(graph, bundle, {}, {'contract_source_chain': {}})


def test_returned_review_does_not_alias_selected_record(original):
    graph, bundle = original
    profile = {'version': chain.VERSION}
    selected = {'contract_source_chain': chain.admit(graph, bundle, profile)}
    value = chain.verify(graph, bundle, {'contract_source_chain': profile}, selected)
    value['onward_documents'].clear()
    assert len(selected['contract_source_chain']['onward_documents']) == 3


@pytest.mark.parametrize('defect', ['published', 'succession', 'whole-applicability', 'precedence', 'qualifier'])
def test_independent_evidence_checker_rejects_false_reading(original, defect):
    from scripts.prospectus_shell_source_chain_verify import report_check
    graph, bundle = original
    report = chain.admit(graph, bundle, {'version': chain.VERSION})
    report_check(report, graph)
    if defect == 'published':
        report['documents'][0]['first_publication'] = '2020-09-08'
    elif defect == 'succession':
        report['trustee_history']['actual_succession_established'] = True
    elif defect == 'whole-applicability':
        report['legal_applicability_established'] = 0
    elif defect == 'precedence':
        report['precedence']['rules'].pop()
    else:
        report['sources']['conditions_and_agreements'].pop()
    with pytest.raises(AssertionError):
        report_check(report, graph)
