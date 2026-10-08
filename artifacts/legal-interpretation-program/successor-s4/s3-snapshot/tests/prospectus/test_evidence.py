from copy import deepcopy
import json
import pytest
from legalmath.prospectus import archive, evidence
from legalmath.prospectus.common import sha, write


def document(text):
    return {"source_sha256": sha(text.encode()), "pages": [{"page": 1, "text": text}], "preliminary_indicator": False}


ROW = dict(id="synthetic", role="issue", instrument="synthetic")


def test_negation_other_referents_and_principal_ambiguity():
    doc = document("The Notes are not perpetual. Other securities are subordinated. The principal may be written down by a resolution authority.")
    claims = evidence.observations(ROW, doc)
    report = evidence.describe(ROW, doc, claims)
    assert report["candidate_facts"]["perpetual"] is None
    assert report["candidate_facts"]["subordinated"] is None
    assert report["candidate_facts"]["contractual_write_down"] is None
    assert report["spi_eligibility"]["decision"] == "UNDETERMINED"


def test_quotation_tampering_and_amendment_invalidates_binding():
    doc = document("The Notes are perpetual subordinated securities.")
    claim = evidence.observations(ROW, doc)[0]
    assert evidence.quote_check(claim, doc)
    changed = deepcopy(doc); changed["pages"][0]["text"] += " Amended terms."
    assert not evidence.quote_check(claim, changed)
    changed = deepcopy(claim); changed["quote"] += " not"
    assert not evidence.quote_check(changed, doc)


def test_issuer_rename_cannot_change_candidate_features():
    reports = []
    for issuer in ("Swiss Example", "UK Example", "Previously Unseen Issuer"):
        doc = document(issuer + ": The AT1 Capital Notes are perpetual and subordinated. The Notes are converted into ordinary shares on a Trigger Event.")
        reports.append(evidence.describe(ROW, doc, evidence.observations(ROW, doc)))
    assert all(r["candidate_facts"] == reports[0]["candidate_facts"] for r in reports)


def test_base_programme_is_not_a_specific_issue():
    doc = document("The AT1 Capital Notes are perpetual and subordinated.")
    row = {**ROW, "role": "base-programme"}
    result = evidence.describe(row, doc, evidence.observations(row, doc))
    assert all(v is None for v in result["candidate_facts"].values())
    assert result["classification"] == "UNDETERMINED"


@pytest.mark.parametrize("payload", ["", "into Settlement Shares "])
def test_no_holder_option_does_not_deny_trigger_conversion(payload):
    doc = document("The AT1 Capital Notes are perpetual. The Notes are not convertible " + payload + "at the option of the holders at any time. "
                   "Upon a Trigger Event the Notes automatically convert into ordinary shares.")
    result = evidence.describe(ROW, doc, evidence.observations(ROW, doc))
    assert result["candidate_facts"]["contingent_conversion"] is True
    assert result["classification"] == "COMPLEX_BOND_UNDER_CANDIDATE_PREMISES"


def test_final_html_not_marked_draft_by_historical_reference(tmp_path):
    path = tmp_path / "filing.html"
    path.write_text("<p>Final prospectus supplement.</p>" + "<p>Terms of this issue apply.</p>"*250 +
                    "<p>An earlier preliminary prospectus was superseded.</p>")
    assert not archive.extract(path, "html")["preliminary_indicator"]


def test_reusing_source_id_for_an_amendment_is_rejected(tmp_path):
    archive_fixture(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    row = {"id": "test", "url": "https://example.com/original", "kind": "html", "instrument": "test", "role": "issue"}
    manifest["documents"]["test"].update(row)
    write(tmp_path / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Source identity changed"):
        archive.acquire([{**row, "url": "https://example.com/amendment"}], tmp_path / "attempt", root=tmp_path)


def archive_fixture(tmp_path):
    original = b"<html><body><p>Instrument terms state the amount and conditions. These are fictional terms for a deterministic integrity control, not an actual offering.</p></body></html>"
    (tmp_path / "originals").mkdir()
    source = tmp_path / "originals/test.html"; source.write_bytes(original)
    write(tmp_path / "manifest.json", {"documents": {"test": {"file": "originals/test.html", "sha256": sha(original), "kind": "html"}}})
    write(tmp_path / "text/test.json", archive.extract(source, "html"))
    return source


def test_repair_derivative_but_never_replace_corrupt_original(tmp_path):
    source = archive_fixture(tmp_path)
    (tmp_path / "text/test.json").write_text('{"broken":true}')
    assert archive.derivative_repairs(root=tmp_path)
    assert archive.derivative_repairs(root=tmp_path, execute=True)[0]["executed"]
    assert not archive.derivative_repairs(root=tmp_path)
    source.write_bytes(b"changed original")
    with pytest.raises(ValueError, match="original changed"):
        archive.derivative_repairs(root=tmp_path, execute=True)


def test_html_error_page_is_not_pdf(tmp_path):
    path = tmp_path / "response"; path.write_text("<html>Download error</html>")
    with pytest.raises(ValueError, match="not a PDF"):
        archive.extract(path, "pdf")
