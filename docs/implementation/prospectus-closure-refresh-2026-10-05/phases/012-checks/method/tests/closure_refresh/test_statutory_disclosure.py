"""Adverse controls for the reviewed statutory disclosure annotation."""
import pytest
from scripts import prospectus_refresh as m
from scripts.prospectus_refresh_sources import norm, region_extract
from scripts.prospectus_refresh_semantics import passage, recognize
from scripts.prospectus_refresh_admission import review

@pytest.fixture
def english():
    record=review()
    row=next(r for r in record["source_pages"] if r["document"]=="deutsche-at1-2025" and r["page"]==37)
    result=region_extract((m.ROOT/row["bbox"]).read_text(),page_number=37,split=304,body_end=775)
    return result["columns"]["en"]["text"]

def test_reviewed_full_passage_preserves_offsets_and_possibility(english):
    p=passage(english)
    assert norm(english)[p["start"]:p["end"]]==p["quote"]
    result=recognize(p["quote"])
    assert result is not None
    assert result["principal_write_down_power_disclosed"] is True
    assert result["ordinary_share_conversion_alternative_disclosed"] is True
    assert result["other_cet1_ownership_alternative_disclosed"] is True
    assert result["mandatory_common_share_only_conversion"] is None
    assert result["current_legal_applicability"] is None
    assert result["actual_resolution_measure"] is None and result["certified_legal_answer"] is None

@pytest.mark.parametrize("old,new",[
 ("may be subject","may not be subject"),
 ("competent resolution authority","Issuer"),
 ("principal amount, the interest amount","interest amount"),
 ("including writing down to zero","excluding writing down to zero"),
 ("ordinary shares","preference shares"),
 ("or other instruments of ownership qualifying as Common Equity Tier 1 instruments",""),
 ("shall not constitute an event of default","shall constitute an event of default"),
 ("from time to time","as at issue only"),
 ("these claims","unrelated claims"),
 ("the exclusion of any other agreements","the inclusion of any other agreements"),
])
def test_changed_legal_relation_abstains(english,old,new):
    text=passage(english)["quote"]
    assert old in text
    assert recognize(text.replace(old,new)) is None

def test_added_exception_abstains(english):
    text=passage(english)["quote"]
    assert recognize(text+" The foregoing does not apply to these Notes.") is None
    assert recognize(text.replace("(a) write down","provided that these Notes are excluded, (a) write down")) is None

@pytest.mark.parametrize("mutation",["no_heading","repeated_heading","no_next_section"])
def test_incomplete_passage_rejected(english,mutation):
    if mutation=="no_heading":english=english.replace("(7)","(8)",1)
    elif mutation=="repeated_heading":english=english+"\n"+english
    else:english=english.replace("Interest","Other")
    with pytest.raises(ValueError):passage(english)

def test_unreviewed_synonym_does_not_claim_general_entailment(english):
    assert recognize(passage(english)["quote"].replace("may be subject","could be subject")) is None
