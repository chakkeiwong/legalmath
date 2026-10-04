"""Specification counterexamples, never human-labelled real legal outcomes."""
from datetime import datetime, timedelta, timezone
import hashlib
from itertools import product

import pytest

from legalmath.prospectus.legal_review import (
    AUTHORITY_FACTS, DIRECT_DEBT_FACTS, HKMA_SALE_FACTS, SALE_FACTS,
    LegalVersion, authority_preconditions, hkma_direct_debt_scope,
    hkma_pi_restriction, judgment_result, sale_preconditions,
    verify_source_dependencies,
    required_articles, dossier_files, verify_dossier,
)


def test_authority_cannot_be_inferred_from_any_subset_of_necessary_premises():
    complete = dict.fromkeys(AUTHORITY_FACTS, True)
    for key in AUTHORITY_FACTS:
        assert authority_preconditions({**complete, key: None})["decision"] == "UNDETERMINED"
        assert authority_preconditions({**complete, key: False})["decision"] == "FALSE"
        assert authority_preconditions({**complete, key: "conflict"})["decision"] == "CONFLICT"
    assert "order_issued" not in authority_preconditions(complete)


def test_generic_bail_in_warning_neither_establishes_nor_defeats_product_scope():
    for debt, qualifying, excluded in product((True, False, None), repeat=3):
        fixed = dict(zip(DIRECT_DEBT_FACTS[:3], (debt, qualifying, excluded)))
        results = {hkma_direct_debt_scope({**fixed, "bail_in_possible": v})["decision"]
                   for v in (True, False, None)}
        assert len(results) == 1
    assert hkma_direct_debt_scope({"debt_legal_form": True, "bail_in_possible": True,
                                  "plain_debt_or_deposit": False})["decision"] == "UNDETERMINED"


def test_equity_and_plain_debt_exclusions_are_not_general_sale_permissions():
    for facts in ({"debt_legal_form": False}, {"plain_debt_or_deposit": True}):
        assert hkma_direct_debt_scope(facts)["decision"] == "FALSE"
        assert sale_preconditions({})["decision"] == "UNDETERMINED"


def test_pi_restriction_all_partial_inputs_against_forbidden_complete_states():
    # Independent relational specification: exactly one complete state violates
    # this requirement. Compare intersection of evidence with that relation.
    worlds = list(product((False, True), repeat=4))
    forbidden = {(True, True, False, False)}
    for values in product((False, True, None, "conflict"), repeat=4):
        facts = dict(zip(HKMA_SALE_FACTS, values))
        actual = hkma_pi_restriction(facts)
        if "conflict" in values:
            assert actual["decision"] == "CONFLICT"
            assert actual["worlds"] == 0
            continue
        compatible = {w for w in worlds if all(v is None or v == x for v, x in zip(values, w))}
        good, bad = compatible - forbidden, compatible & forbidden
        expected = "UNDETERMINED" if good and bad else "TRUE" if good else "FALSE"
        assert actual["decision"] == expected


def test_unknown_faq9_exception_is_not_assumed_absent_or_established():
    facts = dict(registered_institution=True, in_scope_product=True, professional_investor=False)
    assert hkma_pi_restriction(facts)["decision"] == "UNDETERMINED"
    assert hkma_pi_restriction({**facts, "faq9_exception_established": False})["decision"] == "FALSE"
    assert hkma_pi_restriction({**facts, "faq9_exception_established": True})["decision"] == "TRUE"


def test_sale_all_partial_states_and_spi_cannot_override_any_failed_requirement():
    # The independent conjunction relation admits only the all-true complete
    # tuple. Every partial state is classified by whether it can include it and
    # whether it also permits another tuple. No court/user answer labels enter.
    for values in product((False, True, None, "conflict"), repeat=len(SALE_FACTS)):
        expected = ("CONFLICT" if "conflict" in values else "FALSE" if False in values
                    else "UNDETERMINED" if None in values else "TRUE")
        facts = dict(zip(SALE_FACTS, values))
        assert sale_preconditions(facts, spi_eligible=True)["decision"] == expected
    complete = dict.fromkeys(SALE_FACTS, True)
    for key in SALE_FACTS:
        for spi in (True, False, None):
            assert sale_preconditions({**complete, key: False}, spi_eligible=spi)["decision"] == "FALSE"


def test_no_quality_label_or_inferred_country_fact_is_accepted():
    for fn in (sale_preconditions, authority_preconditions, hkma_direct_debt_scope, hkma_pi_restriction):
        for key in ("human_verified", "expected_answer", "swiss_issuer"):
            with pytest.raises(ValueError):
                fn({key: True})


def test_effective_time_is_distinct_from_publication_and_knowledge_time():
    # Synthetic dated premise, exercising the retained ordinance's exact time
    # boundary; these tests do not adjudicate its constitutional validity.
    start = datetime.fromisoformat("2023-03-19T20:00:00+01:00")
    end = datetime.fromisoformat("2023-09-15T00:00:00+02:00")
    known = start + timedelta(hours=1)
    version = LegalVersion(start, end, known)
    assert version.visible_and_in_period(start, known) == "IN_RECORDED_PERIOD"
    assert version.visible_and_in_period(start-timedelta(microseconds=1), known) == "OUT_OF_PERIOD"
    assert version.visible_and_in_period(end-timedelta(microseconds=1), known) == "IN_RECORDED_PERIOD"
    assert version.visible_and_in_period(end, known) == "OUT_OF_PERIOD"
    assert version.visible_and_in_period(start, known-timedelta(microseconds=1)) == "NOT_KNOWN"
    assert version.visible_and_in_period(start.astimezone(timezone.utc), known) == "IN_RECORDED_PERIOD"
    # The repeal was enacted on 6 September but entered into force on the 15th.
    assert version.visible_and_in_period(datetime.fromisoformat("2023-09-06T12:00:00+02:00"), known) == "IN_RECORDED_PERIOD"


def test_ambiguous_time_and_invalid_interval_are_rejected():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        LegalVersion(t, t, t)
    with pytest.raises(ValueError):
        LegalVersion(t.replace(tzinfo=None), None, t)
    with pytest.raises(ValueError):
        LegalVersion(t, None, t).visible_and_in_period(t.replace(tzinfo=None), t)


def test_procedural_decision_cannot_resolve_merits_or_infer_repayment():
    result = judgment_result(proceeding="procedural", disposition="inadmissible", final=True,
                             suspensive_effect=False, repayment_received=None)
    assert result["merits"] == "NOT_DECIDED"
    assert result["repayment_received"] is None
    for final, stay in ((False, True), (False, None), (True, False)):
        result = judgment_result(proceeding="merits", disposition="annulled", final=final,
                                 suspensive_effect=stay, repayment_received=None)
        assert result["repayment_received"] is None
    with pytest.raises(ValueError):
        judgment_result(proceeding="procedural", disposition="annulled", final=True,
                        suspensive_effect=False, repayment_received=None)


def test_changed_or_missing_source_invalidates_dependency_without_certifying_meaning(tmp_path):
    source = tmp_path / "law.txt"
    source.write_bytes(b"version one")
    expected = {source.name: hashlib.sha256(source.read_bytes()).hexdigest()}
    result = verify_source_dependencies(tmp_path, expected)
    assert result["status"] == "UNCHANGED"
    assert result["legal_currentness"] == result["source_entailment"] == "NOT_ESTABLISHED"
    source.write_bytes(b"version two")
    assert verify_source_dependencies(tmp_path, expected)["status"] == "STALE"
    source.unlink()
    assert verify_source_dependencies(tmp_path, expected)["changed"] == [source.name]
    with pytest.raises(ValueError):
        verify_source_dependencies(tmp_path, {"../escape": "0"*64})


def test_amendment_heading_omission_cannot_be_hidden_by_a_cover_date():
    text = "Stand am 1. Januar 2023\nArt. 30b127 Kapitalmassnahmen\nArt. 30c128 Sanierungsplan\n"
    assert required_articles(text, ["30b", "30c"])["status"] == "HEADINGS_PRESENT"
    changed = text.replace("Art. 30b127", "Removed article")
    assert required_articles(changed, ["30b", "30c"])["missing"] == ["30b"]
    # A cross-reference or a different article identifier is not its heading.
    assert required_articles("See Art. 30b\nArt. 30bb Other\n", ["30b"])["missing"] == ["30b"]


def test_real_dossier_dependencies_and_preserved_version_discrepancy():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    result = verify_dossier(root)
    checks = {r["source_key"]: r for r in result["amendment_checks"]}
    assert checks["swissbank2023"]["missing"] == ["30b", "30c"]
    assert checks["swissbank2023"]["use_for_applicable_law"] is False
    assert checks["swissbank2024"]["missing"] == []
    names = {str(p.relative_to(root)) for p in dossier_files(root)}
    assert "docs/prospectus/legal/manifest.json" in names
    assert "docs/prospectus/legal/originals/swiss-bank-amendment-as2022732.pdf" in names
