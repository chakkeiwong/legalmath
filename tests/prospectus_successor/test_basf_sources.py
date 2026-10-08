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
    assert "Bundesrepublik Deutschland Berechnungsstelle: [Name und bezeichnete Geschäftsstelle]" in text
    assert "Bundesrepublik Deutschland Zahlstelle:" not in text


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


def test_basf_notice_uses_listed_branch_and_exchange_condition(construction):
    text = " ".join(construction["candidate_text"].split())
    assert "(1) Bekanntmachung." in text
    assert "(2) Mitteilungen an das Clearing System." in text
    assert "Soweit die Regeln der Luxemburger Börse dies zulassen" in text
    assert "(1) Mitteilungen an das Clearing System." not in text
    assert "Die Emittentin wird alle die Schuldverschreibungen betreffenden Mitteilungen" not in text
    rule = next(r for r in construction["scope_review"]["decisions"] if r["id"] == "notice-unlisted")
    assert "bungen, die nicht an einer Börse notiert sind" in " ".join(s["quote"] for s in rule["governing"])
    assert {s["unit"].split(":")[1] for s in rule["premises"]} == {"p7", "p13"}


def test_basf_issuer_variants_preserve_successor_guarantee(construction):
    text = " ".join(construction["candidate_text"].split())
    assert text.count("(1) Kündigungsgründe.") == 1
    assert text.count("(2) Quorum.") == 1
    assert text.count("(1) Ersetzung.") == 1
    assert "(d) sichergestellt ist, dass sich die Verpflichtungen der Emittentin aus der Garantie" in text
    assert "Schuldverschreibungen der Nachfolgeschuldnerin erstrecken; und" in text
    assert "Änderung der Garantie." not in text
    assert "Bestellung von Zustellungsbevollmächtigten." not in text
    assert "auf die Schuldverschreibungen oder unter der Garantie zu zahlenden" not in text


def test_basf_holder_put_is_distinct_from_change_of_control(construction):
    text = " ".join(construction["candidate_text"].split())
    assert "(3) Kontrollwechsel." in text
    assert "Wahl-Rückzahlungsbetrag (Put)" not in text
    assert "Der Emittentin steht dieses Wahlrecht nicht" not in text
    assert "Vorzeitige Rückzahlung nach Wahl des Gläubigers" not in text
    assert "Vorzeitige Rückzahlung nach Wahl der Emittentin" in text


def test_basf_ngn_and_temporary_note_body_survives_instruction_removal(construction):
    text = " ".join(construction["candidate_text"].split())
    assert text.count("Die teilweise Rückzahlung wird in den Registern von CBL und Euroclear") == 2
    assert "Falls die Schuldverschreibungen in Form einer NGN begeben werden" not in text
    assert "Die Zahlung von Zinsen auf Schuldverschreibungen, die durch die vorläufige" in text
    assert "(3) Erfüllung." in text
    assert "USD-Gegenwert" not in text
    assert "kanadische(n) Fiscal Agent" not in text


def test_basf_values_are_exact_source_substrings(construction):
    text = " ".join(construction["candidate_text"].split())
    assert "EUR 500.000.000" in text and "EUR fünfhundert Millionen" in text
    assert "vom 8. März 2023 (einschließlich)" in text
    assert "am 8. März eines jeden Jahres" in text
    assert "8. Dezember 2031 – 7. März 2032" in text
    assert "0,300%" in text
    assert "0,300%%" not in text and "in jedem Jahr eines jeden Jahres" not in text
    for edit in construction["operations"]:
        if edit.get("scope_rule") and edit["new"]:
            assert edit["new"] == edit["basis"]["quote"]


def test_basf_missing_office_and_numbering_remain_visible(construction):
    text = " ".join(construction["candidate_text"].split())
    assert "Berechnungsstelle: [Name und bezeichnete Geschäftsstelle]" in text
    assert "[(iv)] eine Berechnungsstelle unterhalten" in text
    assert "Gesamtnennbetrag [ ]" not in text  # only the completed call row survives
    assert construction["annual_range_discrepancy"]
    assert construction["status"] == "PARTIAL"
    assert construction["scope_review"]["independent_legal_review"] is False


def test_basf_unselected_rate_table_caption_does_not_duplicate_definition(construction):
    raw = " ".join(construction["raw_body"].split())
    text = " ".join(construction["candidate_text"].split())
    phrase = '(jeweils ein "Zinszahlungstag")'
    assert raw.count(phrase) == 2 and text.count(phrase) == 1
    assert 'am 8. März eines jeden Jahres zahlbar (jeweils ein "Zinszahlungstag").' in text
    assert "Die erste Zinszahlung erfolgt am 8. März 2024" in text
    edit = next(e for e in construction["operations"]
                if e.get("scope_rule") == "different-rate-table-caption")
    assert edit["source_units"] == [basf.KEY + ":p111:l54", basf.KEY + ":p111:l55"]
    assert edit["new"] == "" and "different_rates" == edit["attachment"]["decision"]


def test_basf_spare_rows_do_not_add_redemption_choices(construction):
    edits = [e for e in construction["operations"] if e.get("scope_rule") in {"B24", "B25", "B26", "B27"}]
    assert len(edits) == 4 and all(e["old"] == "[\n]" and e["new"] == "" for e in edits)
    text = " ".join(construction["candidate_text"].split())
    assert "8. Dezember 2031 – 7. März 2032 Gesamtnennbetrag" in text
    assert "(iii) den Rückzahlungstag, der nicht weniger als 30 Tage" in text


@pytest.mark.parametrize("change", ["missing", "retained"])
def test_basf_caption_requires_actual_branch_exclusion(basf_graph, monkeypatch, change):
    original = basf.reviewed_edits

    def without_exclusion(graph, admission, raw, source_map, pairs, prior_edits):
        edits = deepcopy(prior_edits)
        if change == "missing":
            edits = [e for e in edits if e["reason"] != "different_rates"]
        else:
            next(e for e in edits if e["reason"] == "different_rates")["new"] = "retained"
        return original(graph, admission, raw, source_map, pairs, prior_edits=edits)

    monkeypatch.setattr(basf, "reviewed_edits", without_exclusion)
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="attached text"):
        basf.construct(basf_graph, read(root / jobs.BASF))


def test_basf_caption_cannot_delete_the_identical_single_rate_phrase(basf_graph, construction, monkeypatch):
    from legalmath.prospectus.successor import basf_scope
    data = basf_scope.review_data()
    rule = next(r for r in data["rules"] if r["id"] == "different-rate-table-caption")
    raw = construction["raw_body"]
    a = raw.index(rule["target"]["text"])
    b = a + len(rule["target"]["text"])
    assert a != rule["target"]["start"]
    units = {u["id"]: u for u in basf_graph["units"]}
    spans = []
    for span in construction["source_map"]:
        left, right = max(a, span["start"]), min(b, span["end"])
        if left < right:
            unit = units[span["unit"]]
            spans.append({"unit": unit["id"], "document": unit["document"],
                          "source_sha256": unit["source_sha256"], "start": left-span["start"],
                          "end": right-span["start"], "quote": raw[left:right]})
    rule["target"] = {"start": a, "end": b, "text": raw[a:b], "spans": spans}
    monkeypatch.setattr(basf_scope, "review_data", lambda: data)
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="attached text"):
        basf.construct(basf_graph, read(root / jobs.BASF))


def test_basf_assembly_consumes_reviewed_exclusions(basf_graph, construction):
    assembled = basf.as_assembly(basf_graph, construction)
    assert assembled["continuous_text"] == construction["candidate_text"]
    assert assembled["operations"] == construction["operations"]
    by_unit = {u["unit"]: u for u in assembled["units"]}
    rule = next(r for r in construction["scope_review"]["decisions"] if r["id"] == "notice-unlisted")
    for source in rule["target"]["spans"]:
        assert not by_unit[source["unit"]]["text"].strip()
        assert by_unit[source["unit"]]["role"] == "EXCLUDED"


@pytest.mark.parametrize("change", ["selected", "issuer", "issue"])
def test_basf_scope_rejects_changed_admission(basf_graph, change):
    root = Path(__file__).resolve().parents[2]
    admission = read(root / jobs.BASF)
    if change == "selected":
        next(r for r in admission["decisions"] if r["id"] == "holder_put")["selected"] = True
    elif change == "issuer":
        next(r for r in admission["issue_context"] if r["id"] == "issuer")["value"] = "BASF Finance Europe N.V."
    else:
        admission["issue_id"] = "another-issue"
    with pytest.raises(ValueError, match="BASF scope review"):
        basf.construct(basf_graph, admission)


def test_basf_scope_rejects_other_instrument_using_same_documents(basf_graph):
    graph = {**basf_graph, "instrument_id": "another-instrument"}
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="BASF scope review"):
        basf.construct(graph, read(root / jobs.BASF))


@pytest.mark.parametrize("change", ["body", "margin", "geometry", "edition", "missing", "duplicate",
                                    "added_margin", "checkbox", "label", "value", "value_position", "hidden"])
def test_basf_scope_rejects_changed_source_or_premise(basf_graph, change):
    graph = deepcopy(basf_graph)
    key = basf.KEY + ":p132:l15"
    if change == "body":
        key = basf.KEY + ":p129:l12"
    elif change in {"checkbox", "label"}:
        key = "basf-2032-final:p13:l47"
    elif change in {"value", "value_position", "hidden"}:
        key = "basf-2032-final:p7:l11"
    unit = next(u for u in graph["units"] if u["id"] == key)
    if change in {"body", "margin", "checkbox", "label", "value"}:
        unit["raw"] = unit["raw"] + " CHANGED"
        unit["text_sha256"] = digest(unit["raw"].encode())
    elif change in {"geometry", "value_position"}:
        unit["bbox"][1] += 0.01
    elif change == "edition":
        unit["source_sha256"] = "0" * 64
    elif change == "missing":
        graph["units"].remove(unit)
    elif change == "duplicate":
        graph["units"].append(deepcopy(unit))
    elif change == "added_margin":
        extra = deepcopy(unit)
        extra["id"] += ":extra"
        graph["units"].append(extra)
    else:
        unit["visible"] = False
    root = Path(__file__).resolve().parents[2]
    with pytest.raises(ValueError, match="BASF"):
        basf.construct(graph, read(root / jobs.BASF))
