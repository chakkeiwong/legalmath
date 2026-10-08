from legalmath.interpretation.semantics.clauses import distinguishing_assignments

def test_no_request_agreement_is_query_specific(branches):
    rows = distinguishing_assignments(branches)
    absent = {r["proposal_id"]: r for r in rows if not r["sfc_request"]}
    assert [absent["demonstration."+k]["demonstration_trigger"] for k in "ABC"] == [False, True, False]
    present = {r["proposal_id"]: r for r in rows if r["sfc_request"]}
    assert all(r["demonstration_trigger"] for r in present.values())
    assert present["demonstration.A"]["object"] != present["demonstration.C"]["object"]
    assert present["demonstration.A"]["standard"] != present["demonstration.C"]["standard"]

def test_confirmation_verification_opinion_remain_separate(branches):
    for b in branches[:3]:
        assert {c.id for c in b.clauses} == {"confirmation", "verification", "opinion", "demonstration"}
        assert next(c for c in b.clauses if c.id == "confirmation").trigger == "standing"
    assert len(branches) == 7
