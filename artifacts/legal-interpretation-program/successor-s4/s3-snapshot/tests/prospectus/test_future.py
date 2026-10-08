from copy import deepcopy
import pytest
from legalmath.prospectus import future
from legalmath.prospectus.common import read
from legalmath.qualification import prospective
from .test_evidence import archive_fixture


def fixture(tmp_path, monkeypatch):
    root = tmp_path / "archive"; root.mkdir()
    archive_fixture(root)
    row = {"id": "test", "role": "issue", "instrument": "new-instrument"}
    directory = tmp_path / "window"
    monkeypatch.setattr(prospective, "now", lambda: "2030-01-01T00:00:00Z")
    frozen = prospective.freeze(directory, "a"*64, ["new_issuer"], ends_at="2030-12-31T00:00:00Z")
    monkeypatch.setattr(prospective, "now", lambda: "2030-03-01T00:00:00Z")
    item = {"task_id": "new", "family": "new_issuer", "published_at": "2030-02-01T00:00:00Z", "first_seen_at": "2030-02-02T00:00:00Z"}
    return root, row, directory, frozen["window_hash"], item


def test_future_observation_is_qualified_and_idempotent(tmp_path, monkeypatch):
    root, row, d, h, item = fixture(tmp_path, monkeypatch)
    r = future.observe(d, h, row, item, method_hash="a"*64, root=root)
    assert r["status"] == "OBSERVED_QUALIFIED" and not r["human_quality_evidence"]
    assert r["candidate_report"]["spi_eligibility"]["decision"] == "UNDETERMINED"
    assert future.observe(d, h, row, item, method_hash="a"*64, root=root) == r
    assert prospective.report(d, h)["observed"] == 1
    p = d / "observations/new.json"; p.write_text('{"forged":true}')
    with pytest.raises(ValueError, match="altered"):
        future.observe(d, h, row, item, method_hash="a"*64, root=root)


def test_changed_method_and_old_publications_are_retained(tmp_path, monkeypatch):
    root, row, d, h, item = fixture(tmp_path, monkeypatch)
    r = future.observe(d, h, row, item, method_hash="b"*64, root=root)
    assert r["status"] == "INELIGIBLE" and "METHOD_CHANGED" in r["reasons"]
    item = {**item, "task_id": "old", "published_at": "2029-01-01T00:00:00Z"}
    r = future.observe(d, h, row, item, method_hash="a"*64, root=root)
    assert r["status"] == "INELIGIBLE"
    assert prospective.report(d, h)["submitted"] == 2


def test_future_input_rejects_quality_authority(tmp_path, monkeypatch):
    root, row, d, h, item = fixture(tmp_path, monkeypatch)
    for field in ("human_label", "expected", "model_consensus", "reviewer"):
        with pytest.raises(ValueError, match="quality labels"):
            future.observe(d, h, row, {**item, field: True}, method_hash="a"*64, root=root)
