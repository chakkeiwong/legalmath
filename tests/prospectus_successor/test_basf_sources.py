"""Pinned source regressions; these do not certify the full German contract."""
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, jobs, source_graph
from legalmath.prospectus.successor.contracts import read


@pytest.fixture(scope="module")
def construction():
    root = Path(__file__).resolve().parents[2]
    request = jobs.basf_request(root)
    graph = source_graph.build(request["bundle"], root)
    return basf.construct(graph, read(root / jobs.BASF))


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
