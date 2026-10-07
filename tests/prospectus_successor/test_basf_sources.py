"""Pinned source regressions; these do not certify the full German contract."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_order, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read


@pytest.fixture(scope="module")
def basf_graph():
    root = Path(__file__).resolve().parents[2]
    request = jobs.basf_request(root)
    return source_graph.build(request["bundle"], root)


@pytest.fixture(scope="module")
def construction(basf_graph):
    root = Path(__file__).resolve().parents[2]
    return basf.construct(basf_graph, read(root / jobs.BASF))


@pytest.fixture
def body_lines(basf_graph, construction):
    selected = {r["unit"] for r in construction["unit_accounting"] if r["role"] == "BODY_CANDIDATE"}
    return deepcopy([u for u in basf_graph["units"] if u["id"] in selected])


def test_icma_common_definition_survives_unselected_optional_period(construction):
    text = construction["candidate_text"]
    assert '"Bezugsperiode" bezeichnet den Zeitraum ab dem Verzinsungsbeginn' in text
    assert "Fiktive Zinszahlungstag" not in text and "Fiktiver Zinszahlungstag" not in text
    assert "die tatsächliche Anzahl von Tagen in der jeweiligen Zinsperiode." in " ".join(text.split())


def test_malformed_unselected_coupon_and_source_character_map(construction):
    assert construction["source_defects"][0]["source_page"] == 112
    assert not construction["unbalanced_offsets"]
    assert "[die Summe aus:" not in construction["candidate_text"]
    maps = construction["character_map"]
    assert maps[0]["start"] == 0 and maps[-1]["end"] == len(construction["candidate_text"])
    assert all(a["end"] == b["start"] for a,b in zip(maps,maps[1:]))
    for m in maps:
        if m["operation"] == "COPY":
            assert construction["candidate_text"][m["start"]:m["end"]] == construction["raw_body"][m["raw_start"]:m["raw_end"]]
        else:
            assert m["basis"]["source_sha256"] == "34c23622c9c9ede54d254ca191bc0c827e748fa0289f0ebd50fa3d8fbcd83085"


def test_basf_reading_order_matches_printed_prose(construction):
    raw = " ".join(construction["raw_body"].split())
    assert "Fälligkeitstag (ausschließlich) belaufen sich auf [abschließenden" in raw
    passage = "des betreffenden Clearing Systems ausgewählt. [Falls die Schuldverschreibungen in Form einer NGN"
    for page in (120, 121):
        spans = [s for s in construction["source_map"] if s["page"] == page]
        page_text = " ".join(" ".join(construction["raw_body"][s["start"]:s["end"]] for s in spans).split())
        assert page_text.count(passage) == 1
        assert "[Falls des betreffenden Clearing Systems" not in page_text


def test_basf_table_cells_are_complete_before_branch_exclusion(construction):
    raw = " ".join(construction["raw_body"].split())
    assert "[Fiscal Agent und Zahlstelle: Deutsche Bank Aktiengesellschaft Trust & Agency Services" in raw
    assert "[Fiscal Agent und Zahlstelle: [Name und bezeichnete Geschäftsstelle des/der Kanadischen Fiscal Agent und Zahlstelle]]" in raw
    deletion = next(e for e in construction["operations"] if e["reason"] == "canadian_agent")
    assert "Zahlstelle:" in deletion["old"]
    assert deletion["old"].rstrip().endswith("Zahlstelle]]")
    assert deletion["new"] == ""
    text = " ".join(construction["candidate_text"].split())
    assert "Bundesrepublik Deutschland] [Berechnungsstelle:" in text
    assert "Bundesrepublik Deutschland] Zahlstelle:" not in text


def test_basf_permutations_preserve_every_source_occurrence(basf_graph, construction):
    by_id = {u["id"]: u for u in basf_graph["units"]}
    selected = {r["unit"] for r in construction["unit_accounting"] if r["role"] == "BODY_CANDIDATE"}
    spans = construction["source_map"]
    assert len(spans) == len(selected)
    assert {s["unit"] for s in spans} == selected
    assert spans[0]["start"] == 0 and spans[-1]["end"] + 1 == len(construction["raw_body"])
    for span in spans:
        assert construction["raw_body"][span["start"]:span["end"]] == by_id[span["unit"]]["raw"]
        assert construction["raw_body"][span["end"]] == "\n"
    assert all(a["end"] + 1 == b["start"] for a, b in zip(spans, spans[1:]))
    assert construction["interval_accounting"]["gaps"] == []
    assert not construction["interval_accounting"]["complete"]
    assert not construction["full_german_contract_constructed"]


@pytest.mark.parametrize("change", ["text", "geometry", "edition", "missing", "duplicate", "intruding"])
def test_basf_order_rejects_changed_source_span(body_lines, change):
    unit = next(u for u in body_lines if u["id"] == basf.KEY + ":p120:l74")
    if change == "text":
        unit["raw"] = "[Nicht falls"
        unit["text_sha256"] = digest(unit["raw"].encode())
    elif change == "geometry":
        unit["bbox"][2] += 0.01
    elif change == "edition":
        unit["source_sha256"] = "0" * 64
    elif change == "missing":
        body_lines.remove(unit)
    elif change == "duplicate":
        body_lines.append(deepcopy(unit))
    else:
        extra = deepcopy(unit)
        extra["id"] += ":unexpected"
        extra["bbox"][0] += 0.1
        body_lines.append(extra)
    with pytest.raises(ValueError):
        basf_order.reviewed_order(body_lines)


def test_basf_order_does_not_change_unreviewed_occurrences(body_lines):
    before = deepcopy(body_lines)
    legacy = sorted(body_lines, key=lambda u: (u["page"], round(u["bbox"][1], 1), u["bbox"][0]))
    corrected, decisions = basf_order.reviewed_order(body_lines)
    changed = {key for row in decisions for key in row["before"]}
    assert [u for u in corrected if u["id"] not in changed] == [u for u in legacy if u["id"] not in changed]
    assert body_lines == before
    assert {u["id"]: u for u in corrected} == {u["id"]: u for u in legacy}
