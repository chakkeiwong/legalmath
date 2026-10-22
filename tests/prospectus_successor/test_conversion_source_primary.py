"""Discriminating source thresholds and honest temporal source-admission fixtures."""
from copy import deepcopy
from decimal import Decimal

import pytest
from legalmath.prospectus import closure_mechanisms as kernels
from legalmath.prospectus.successor import financial_profiles, source_graph
from legalmath.prospectus.successor.contracts import digest
from tests.prospectus_successor.test_conversion_admission import scenario


@pytest.mark.parametrize('bank,group', [
    ('0.1', '0.06'), ('0.05125', '0.08'),
    ('0.05124999', '0.1'), ('0.05125', '0.1'), ('0.05125001', '0.1'),
    ('0.1', '0.07999999'), ('0.1', '0.08'), ('0.1', '0.08000001'),
    ('0.05', '0.079'), ('0.1', '0.05'), ('0.1', '0.1'),
])
def test_separate_bank_and_group_trigger_thresholds(bank, group):
    supplied = scenario('seb-at1-usd-2024')
    supplied.update(bank_cet1_ratio=bank, group_cet1_ratio=group)
    original = deepcopy(supplied)
    # Independent source proposition: page65 gives different strict thresholds.
    expected = Decimal(bank) < Decimal('0.05125') or Decimal(group) < Decimal('0.08')
    result = kernels.seb(supplied)
    assert result['conversion'] is expected
    assert supplied == original
    if expected:
        assert result['conversion_price_usd'] == '3'
        assert result['holder_entitlements'][0]['shares'] == 3
    else:
        assert result['principal_after_conversion'] is None


def source_fixture(tmp_path, monkeypatch, issue='seb-at1-usd-2024', changes=None):
    """A real small text file; its test hash never purports to identify a PDF."""
    text = 'Explicit test source. This fixture is not the original offering document.'
    path = tmp_path / 'fixture.txt'
    path.write_text(text)
    source_hash = digest(path.read_bytes())
    profile = {'document': 'text-fixture', 'sha256': source_hash, 'pages': [1]}
    monkeypatch.setitem(kernels.PROFILES, issue, profile)
    doc = {'id': 'text-fixture', 'sha256': source_hash, 'path': 'fixture.txt', 'format': 'text',
           'language': 'en', 'authority': 'Explicit test fixture',
           'document_date': '2024-01-01T00:00:00Z', 'known_from': '2024-01-01T00:00:00Z',
           'valid_from': '2024-01-01T00:00:00Z', 'valid_until': '2026-01-01T00:00:00Z'}
    doc.update(changes or {})
    bundle = {'instrument_id': issue, 'purpose': 'issue_formation',
              'issue_date': '2024-01-01T00:00:00Z', 'effective_at': '2024-01-01T00:00:00Z',
              'known_at': '2024-01-01T00:00:00Z', 'documents': [doc]}
    supplied = scenario(issue)
    supplied['source_sha256'] = source_hash
    return bundle, supplied, source_graph.build(bundle, tmp_path)


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025', 'seb-at1-usd-2024'])
@pytest.mark.parametrize('changes,reason', [
    ({'document_date': '2024-01-02T00:00:00Z'}, 'post-issue'),
    ({'known_from': '2024-01-02T00:00:00Z'}, 'not known'),
    ({'valid_from': '2024-01-02T00:00:00Z'}, 'not yet effective'),
    ({'valid_until': '2024-01-01T00:00:00Z'}, 'outside recorded'),
])
def test_named_primary_refuses_each_real_source_graph_exclusion(tmp_path, monkeypatch, issue, changes, reason):
    bundle, supplied, graph = source_fixture(tmp_path, monkeypatch, issue, changes)
    assert not graph['documents'][0]['visible']
    original = deepcopy((bundle, supplied, graph))
    result = financial_profiles.assess(bundle, supplied, graph)
    assert result['status'] == 'UNSUPPORTED'
    assert reason in ' '.join(result['unresolved'])
    assert (bundle, supplied, graph) == original


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025', 'seb-at1-usd-2024'])
def test_visible_temporal_boundaries_preserve_named_calculation(tmp_path, monkeypatch, issue):
    bundle, supplied, graph = source_fixture(tmp_path, monkeypatch, issue)
    assert graph['documents'][0]['visible']
    assert financial_profiles.assess(bundle, supplied, graph)['status'] == 'CONDITIONAL'
    assert financial_profiles.assess(bundle, supplied)['status'] == 'CONDITIONAL'


@pytest.mark.parametrize('mutation', ['bundle', 'instrument', 'edition', 'no-document',
                                      'no-units', 'hidden-unit', 'wrong-unit-edition', 'missing-page'])
def test_supplied_primary_graph_cannot_silently_lose_source_binding(tmp_path, monkeypatch, mutation):
    bundle, supplied, graph = source_fixture(tmp_path, monkeypatch)
    assert financial_profiles.assess(bundle, supplied, graph)['status'] == 'CONDITIONAL'
    if mutation == 'bundle':
        graph['bundle_sha256'] = '0' * 64
    elif mutation == 'instrument':
        graph['instrument_id'] = 'different-instrument'
    elif mutation == 'edition':
        graph['documents'][0]['sha256'] = '0' * 64
    elif mutation == 'no-document':
        graph['documents'] = []
    elif mutation == 'no-units':
        graph['units'] = []
    elif mutation == 'hidden-unit':
        graph['units'][0]['visible'] = False
    elif mutation == 'wrong-unit-edition':
        graph['units'][0]['source_sha256'] = '0' * 64
    else:
        kernels.PROFILES[supplied['issue_id']]['pages'] = [1, 2]
    assert financial_profiles.assess(bundle, supplied, graph)['status'] == 'UNSUPPORTED'
