"""Truth tables, time/scope changes and source-tampering checks for legal rules."""
from copy import deepcopy
from itertools import product
import json
import pytest
from legalmath.prospectus.common import sha
from legalmath.prospectus.external_law import expression, evaluate_rule, investigate
from tests.prospectus.test_loss_absorption import fixture, ORDINARY


@pytest.mark.parametrize("a,b", product([True,False,None], repeat=2))
def test_three_valued_conjunction(a,b):
    value=expression({"all":[{"fact":"a"},{"fact":"b"}]},{"a":[a],"b":[b]})
    expected=False if a is False or b is False else True if a is True and b is True else None
    assert value is expected


def test_conflicting_observations_and_missing_fact_stay_unknown():
    assert expression({"fact":"a"},{"a":[True,False]}) is None
    assert expression({"fact":"a"},{}) is None


def legal_fixture(tmp_path):
    original=tmp_path/"law.pdf";original.write_bytes(b"retained primary source fixture")
    text=tmp_path/"text.txt";text.write_text("1\nThe measure preceded proceedings.\n2\nAn appeal is not a suspension.")
    key="law"
    sources={key:{"original":str(original),"sha256":sha(original.read_bytes()),
                  "text":str(text),"text_sha256":sha(text.read_bytes())}}
    rule={"id":"recognition", "anchors":[{"source_key":key,"source_sha256":sources[key]["sha256"],
          "paragraph":1,"quote":"The measure preceded proceedings."}],
          "scope":{"claim_type":["bond"],"forum":["ES"]},"source_date":"2024-09-05",
          "stage":"recognition","conclusion":"pre_suit_recognition_under_reviewed_premises",
          "condition":{"all":[{"before":["measure","suit"]},{"not":{"fact":"suspended"}}]}}
    context={"claim_type":"bond","forum":"ES","known_at":"2026-10-04","requested_stage":"recognition",
             "facts":{"measure":["2015-12-29"],"suit":["2017-01-01"],"suspended":[False]}}
    return rule,context,sources


def test_valid_rule_then_later_measure_changes_result(tmp_path):
    rule,ctx,sources=legal_fixture(tmp_path)
    assert evaluate_rule(rule,ctx,sources,tmp_path)["value_under_declared_premises"] is True
    ctx["facts"]["measure"]=["2018-01-01"]
    assert evaluate_rule(rule,ctx,sources,tmp_path)["value_under_declared_premises"] is False


@pytest.mark.parametrize("field,value",[
    ("claim_type","shares"),("forum","UK"),("known_at","2023-01-01"),
    ("requested_stage","debt_discharge"),("claim_type",None)])
def test_wrong_scope_or_stage_cannot_inherit_holding(tmp_path,field,value):
    rule,ctx,sources=legal_fixture(tmp_path);ctx[field]=value
    result=evaluate_rule(rule,ctx,sources,tmp_path)
    assert result["status"]=="UNRESOLVED"
    assert result["value_under_declared_premises"] is None


@pytest.mark.parametrize("what",["original","text","quote","paragraph"])
def test_rejects_changed_or_mislocated_source(tmp_path,what):
    rule,ctx,sources=legal_fixture(tmp_path)
    if what in ("original","text"):
        from pathlib import Path
        Path(sources["law"][what]).write_bytes(b"changed")
    elif what=="quote":rule["anchors"][0]["quote"]="The debt was discharged."
    else:rule["anchors"][0]["paragraph"]=2
    with pytest.raises(ValueError):evaluate_rule(rule,ctx,sources,tmp_path)


def test_challengeability_does_not_supply_unsuspended_premise(tmp_path):
    rule,ctx,sources=legal_fixture(tmp_path)
    ctx["facts"].pop("suspended")
    ctx["facts"]["challengeable"]=[True]
    assert evaluate_rule(rule,ctx,sources,tmp_path)["status"]=="UNRESOLVED"


def test_join_keeps_contract_and_law_separate(tmp_path):
    issue,documents,_=fixture(tmp_path,[ORDINARY])
    rule,ctx,sources=legal_fixture(tmp_path)
    result=investigate(issue,documents,{"rules":[rule],"context":ctx,"sources":sources},tmp_path)
    assert result["contractual"]["answer"] is False
    assert result["external_law"][0]["value_under_declared_premises"] is True
    assert result["certified_legal_answer"] is None and not result["may_execute_transaction"]


def test_exact_haircut_complement_and_not_final_recovery(tmp_path):
    rule,ctx,sources=legal_fixture(tmp_path)
    rule["arithmetic"]={"remaining_percent":"remaining"}
    ctx["facts"]["remaining"]=["46.02"]
    result=evaluate_rule(rule,ctx,sources,tmp_path)
    assert result["implied_reduction_percent"]=="2699/50"
    assert result["ultimate_recovery"]=="NOT_ESTABLISHED"

@pytest.mark.parametrize("end,expected",[("2011-04-30",False),("2011-05-01",True),("2011-05-02",True)])
def test_execution_delay_boundary(end,expected):
    assert expression({"elapsed_days_at_least":["notice","execution",120]},
                      {"notice":["2011-01-01"],"execution":[end]}) is expected
    assert expression({"elapsed_days_at_least":["notice","execution",120]},
                      {"execution":[end]}) is None

def test_pdf_page_anchor_cannot_use_unbound_derivative(tmp_path):
    rule,ctx,sources=legal_fixture(tmp_path)
    rule["anchors"][0].pop("paragraph")
    rule["anchors"][0]["page"]=2
    # An attacker supplies a pages.json with the wanted quote at a wrong page.
    (tmp_path/"pages.json").write_text(json.dumps({"pages":[{"text":""},{"text":rule["anchors"][0]["quote"]}]}))
    with pytest.raises(ValueError):
        evaluate_rule(rule,ctx,sources,tmp_path)

def test_pdf_anchor_on_bound_text_page(tmp_path):
    rule,ctx,sources=legal_fixture(tmp_path)
    rule["anchors"][0].pop("paragraph")
    rule["anchors"][0]["page"]=2
    from pathlib import Path
    path=Path(sources["law"]["text"])
    path.write_text("Unrelated first page.\fThe measure preceded proceedings.\f")
    sources["law"]["text_sha256"]=sha(path.read_bytes())
    assert evaluate_rule(rule,ctx,sources,tmp_path)["status"]=="CONDITIONAL"
    rule["anchors"][0]["page"]=0
    with pytest.raises(ValueError):evaluate_rule(rule,ctx,sources,tmp_path)

