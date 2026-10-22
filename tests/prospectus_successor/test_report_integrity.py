"""Resealed report claims still need their original selection and supplied facts."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from test_report_scope import fixture, products

CONSUMER_CASES = ("missing-p2", "changed-p2", "unsupplied-readings", "missing-p3", "changed-p3",
                  "unsupplied-scope", "changed-input", "withdrawn-scope", "empty-scope")
INTERPRETATION_CASES = ("changed-p2", "unsupplied-readings")


def reseal(values):
    request = values["P1"]["payload"]["request"]
    values["P1"] = service.seal("P1", request["bundle"], {"request": digest(request)}, values["P1"]["payload"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")),
                           ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        values[phase] = service.seal(phase, request["bundle"],
            {p: values[p]["sha256"] for p in parents}, values[phase]["payload"])
    return values


def changed(values, mutation):
    bad = deepcopy(values)
    request = bad["P1"]["payload"]["request"]
    selected, semantic = bad["P2"]["payload"], bad["P3"]["payload"]
    if mutation == "missing-p2":
        del selected["source_report_readings"]
    elif mutation == "changed-p2":
        # Plausible complete selection with valid hashes and facts but false page.
        readings = selected["source_report_readings"]
        reading = readings["reports"][0]
        reading["pages"][0]["page"] += 9
        reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
        scope = semantic["interpretation_input"]["source_report_scope"]
        scope["readings_sha256"] = digest(readings)
        scope["reports"][0]["reading_sha256"] = reading["sha256"]
        semantic["source_report_scope"] = report_scope.admit(readings, scope)
    elif mutation == "unsupplied-readings":
        del request["source_report_readings"]
    elif mutation == "missing-p3":
        del semantic["source_report_scope"]
    elif mutation == "changed-p3":
        semantic["source_report_scope"]["reports"][0]["facts"]["report_date"]["spans"][0]["quote"] = "Lisbon, 1 January 2099."
    elif mutation == "unsupplied-scope":
        semantic["interpretation_input"] = None
    elif mutation == "changed-input":
        semantic["interpretation_input"]["source_report_scope"]["reports"][0]["facts"]["conclusion"] = {
            "status": "UNKNOWN", "reason": "Conclusion no longer supplied"}
    elif mutation == "withdrawn-scope":
        semantic["interpretation_input"]["source_report_scope"] = None
    elif mutation == "empty-scope":
        semantic["interpretation_input"]["source_report_scope"] = {}
    else:
        raise AssertionError("Unknown counterexample: " + mutation)
    return reseal(bad)


@pytest.mark.parametrize("mode", ["frozen", "current"])
@pytest.mark.parametrize("mutation", CONSUMER_CASES)
def test_resealed_report_claims_require_source_and_scope_evidence(tmp_path, mode, mutation):
    _, p1, p2, scope = fixture(tmp_path)
    bad = changed(products(p1, p2, scope), mutation)
    # Every phase has a valid content hash and its correct new parent hashes.
    for phase in bad:
        service.verify(bad[phase], phase)
    with pytest.raises(ValueError):
        service.consume(bad, tmp_path, mode=mode)


@pytest.mark.parametrize("mutation", (*INTERPRETATION_CASES, "missing-p2"))
def test_interpretation_reconstructs_selection_before_admitting_scope(tmp_path, mutation):
    _, p1, p2, scope = fixture(tmp_path)
    bad = changed(products(p1, p2, scope), mutation)
    with pytest.raises(ValueError, match="[Rr]eport"):
        service.interpretation_product(bad["P1"], bad["P2"], bad["P3"]["payload"]["interpretation_input"])


@pytest.mark.parametrize("boundary", ["interpretation", "frozen", "current"])
def test_selection_is_checked_even_without_scope(tmp_path, boundary):
    _, p1, p2, _ = fixture(tmp_path)
    values = products(p1, p2)
    del values["P2"]["payload"]["source_report_readings"]
    reseal(values)
    with pytest.raises(ValueError):
        if boundary == "interpretation":
            service.interpretation_product(values["P1"], values["P2"])
        else:
            service.consume(values, tmp_path, mode=boundary)


@pytest.mark.parametrize("mode", ["frozen", "current"])
@pytest.mark.parametrize("override", ["none", "unknown", "absent"])
def test_request_scope_and_legal_interpretation_overrides_are_preserved(tmp_path, mode, override):
    req, p1, _, scope = fixture(tmp_path)
    req["source_report_scope"] = scope
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    supplied = None
    expected = scope
    if override == "unknown":
        expected = deepcopy(scope)
        expected["reports"][0]["facts"]["conclusion"] = {"status": "UNKNOWN", "reason": "No opinion supplied"}
        supplied = {"source_report_scope": expected}
    elif override == "absent":
        expected = None
        supplied = {"source_report_scope": None}
    p3 = service.interpretation_product(p1, p2, supplied)
    values = {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
              "P5": service.financial_product(p1, p2, p3)}
    answer = service.consume(values, tmp_path, mode=mode)
    if expected is None:
        assert "source_reports" not in answer
    else:
        assert answer["source_reports"] == report_scope.explain(report_scope.admit(p2["payload"]["source_report_readings"], expected))


@pytest.mark.parametrize("mode", ["frozen", "current"])
def test_request_scope_cannot_be_dropped_from_saved_semantics(tmp_path, mode):
    req, _, _, scope = fixture(tmp_path)
    req["source_report_scope"] = scope
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    values = products(p1, p2)
    del values["P3"]["payload"]["source_report_scope"]
    reseal(values)
    with pytest.raises(ValueError):
        service.consume(values, tmp_path, mode=mode)


@pytest.mark.parametrize("mode", ["frozen", "current"])
def test_valid_selection_without_scope_remains_consumable(tmp_path, mode):
    _, p1, p2, _ = fixture(tmp_path)
    assert "source_reports" not in service.consume(products(p1, p2), tmp_path, mode=mode)
