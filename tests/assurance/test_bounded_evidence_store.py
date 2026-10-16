from pathlib import Path
import json
import pytest
from legalmath.canonical import MAX_BYTES, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.phased.evidence_store import save_exact, load_exact
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def test_verified_consumer_reads_large_exact_evidence(tmp_path):
    value = {'outputs': [{'text': '法' * 100000, 'verdict': 'REJECT'} for _ in range(72)]}
    path = tmp_path / 'investigation.json'
    save_exact(path, value)
    assert path.stat().st_size < MAX_BYTES
    assert read_evidence(evidence_file(path, tmp_path), tmp_path) == value
    assert load_exact(path) == value
    manifest = json.loads(path.read_text())
    leaf = tmp_path / manifest['record_directory'] / (manifest['root'] + '.json')
    leaf.write_text('{}')
    with pytest.raises(LegalMathError):
        read_evidence(evidence_file(path, tmp_path), tmp_path)


def test_product_dependency_restarts_without_provider_calls(tmp_path):
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path / 'product', provider, envelope(), list, limits=limits())
    initial = product.investigate()
    calls = len(provider.requests)
    retained = product.investigate()
    assert retained == initial and len(provider.requests) == calls
    directory = product.directory / 'dependency-outcomes'
    assert len(list(directory.glob('*.json'))) == len(initial['discovered_dependencies'])


def test_small_values_remain_ordinary_json(tmp_path):
    path = tmp_path / 'small.json'
    value = {'status': 'FAILED', 'reason': 'Retained'}
    save_exact(path, value)
    assert json.loads(path.read_text()) == value == load_exact(path)
