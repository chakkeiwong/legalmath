from legalmath.interpretation.semantics.precedent import *
from legalmath.interpretation.semantics.records import Interval, SourceSpan
from legalmath.canonical import digest

def test_precedent_roles_and_transfer_stay_qualified():
    text="The provider should maintain a register."
    span=SourceSpan(source_hash="a"*64,edition="synthetic",unit_id="u",unit_hash=digest(text),
        locator="synthetic judgment",start=0,end=len(text),quote=text,request_hash="b"*64,role="finding")
    manifest=JudgmentManifest("synthetic-1","declared synthetic",digest(text),"Synthetic Court","synthetic",None,
        "mechanics fixture",("opinion-1",),("decision_date","treatment"),False)
    prop=Proposition("p","maintain a register","holding",("passage",),"source role supplied", "unresolved")
    factor=Factor("f","register","recorded",("p",),"conditional relevance")
    move=Move("distinction",("f",),"p","Different actor; relevance unresolved")
    result=comparison(manifest,(prop,),(factor,),(move,))
    assert result["status"]=="REAL_CASE_PENDING"
    assert prop.role=="holding" and prop.role_status=="unresolved"

def test_submission_cannot_be_promoted_to_holding_and_source_hash_is_checked():
    import pytest
    from dataclasses import replace
    packet={"units":[{"unit_id":"u","text":"Counsel argues that p."}]}
    text=packet["units"][0]["text"]
    span=SourceSpan(source_hash=digest(packet),edition="synthetic",unit_id="u",unit_hash=digest(text),
        locator="opinion 1",start=0,end=len(text),quote=text,request_hash="b"*64,role="submission")
    m=JudgmentManifest("synthetic","synthetic",digest(packet),"court","jurisdiction","2026-01-01","test",("opinion 1",),(),True)
    passage=Passage("s",span,"counsel","submission",text)
    prop=Proposition("p","p","holding",("s",),"proposed inference","source-backed")
    with pytest.raises(ValueError,match="submission"):
        validate_case(packet,"b"*64,m,(passage,),(prop,),(),())
    prop=replace(prop,role_status="proposed")
    assert validate_case(packet,"b"*64,m,(passage,),(prop,),(),())["ratio"]=="NOT_ESTABLISHED"
    with pytest.raises(ValueError,match="identity"):
        validate_case(packet,"b"*64,replace(m,source_hash="0"*64),(passage,),(prop,),(),())

def test_later_authority_and_empty_treatment_search_are_unresolved():
    m=JudgmentManifest("j","synthetic","a"*64,"c","HK","2027-01-01",None,(),(),True)
    p=Proposition("p","p","holding",("s",),"warrant")
    a=Authority("p","HK","unknown",None,None,Interval(start=None,end=None),(),"unknown")
    result=assess_authority(m,p,a,(),"2026-10-06")
    assert "unknown-or-later-decision" in result["reasons"]
    assert "subsequent-treatment-unresolved" in result["reasons"]
    assert result["binding_established"] is False
