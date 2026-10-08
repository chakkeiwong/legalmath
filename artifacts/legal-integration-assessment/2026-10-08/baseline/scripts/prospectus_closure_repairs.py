"""Execute the source-bound BES successor repairs on real reviewed terms."""
import json
from scripts import run_prospectus_closure_next as m
from scripts.prospectus_reviewed_extraction import load,norm
from scripts.prospectus_closure_dossiers import anchor
from scripts import prospectus_closure_finance as f

def reviewed_anchor(key,page,fragment):
    meta=m.read(m.DATA/"reviewed-extractions.json")[key];doc=load(meta,m.ROOT)
    text=doc["pages"][page-1]["text"];fragment=norm(fragment)
    if text.count(fragment)!=1:raise ValueError("Reviewed fragment missing or ambiguous")
    start=text.index(fragment)
    return {"document":key,"source_sha256":meta["sha256"],"text":meta["text"],"text_sha256":meta["text_sha256"],
        "review_sha256":meta["review_sha256"],"page":page,"start":start,"end":start+len(fragment),"quote":fragment}

def run():
    base="jur-more-bes-1774077"
    rules=[
        anchor(base,"the full nominal amount outstanding of the Fixed Rate Notes"),
        anchor(base,"and, in each case, multiplying such sum by the applicable Day Count Fraction, and rounding the resultant figure to the nearest sub-unit of the relevant Specified Currency, half of any such sub-unit being rounded upwards or otherwise in accordance with applicable market convention."),
        anchor(base,"the number of days in such Accrual Period divided by the product of (1) the number of days in such Determination Period and (2) the number of Determination Dates"),
        anchor(base,"the Accrual Period is longer than the Determination Period during which the Accrual Period ends, the sum of:"),
        anchor(base,"with respect to euro, means one cent.")]
    rows=[]
    for key,rate,printed_rate,start,end,expected in [
        ("jur-more-bes-1922255","0.04","4.00","2014-01-21","2015-01-21","30000000.00"),
        ("jur-bes-2014-ptbeqkom0019","0.02625","2.625","2014-05-08","2015-05-08","19687500.00")]:
        meta=m.read(m.DATA/"reviewed-extractions.json")[key];doc=load(meta,m.ROOT)
        quotes=[
            reviewed_anchor(key,1,"€750,000,000"),
        ] if doc["pages"][0]["text"].count("€750,000,000")==1 else []
        # Full page preserves repeated issue-size entries without choosing an arbitrary occurrence.
        quotes.append({"document":key,"source_sha256":meta["sha256"],"text":meta["text"],
            "text_sha256":meta["text_sha256"],"page":1,"start":0,"end":len(doc["pages"][0]["text"]),"quote":doc["pages"][0]["text"]})
        quotes += [
            reviewed_anchor(key,2,printed_rate+" per cent. per annum payable in arrear on each Interest Payment Date"),
            reviewed_anchor(key,2,"Actual/Actual (ICMA)"),
            reviewed_anchor(key,2,"Subject to any purchase and cancellation or early redemption, the Notes will be redeemed on the Maturity Date at 100 per cent. of their nominal amount"),
            reviewed_anchor(key,2,"Minimum period: 30 days Maximum period: 60 days"),
            reviewed_anchor(key,3,"Book-entry form registered Notes (Interbolsa Notes)"),
            reviewed_anchor(key,5,"the second business day after the day on which it was given to Interbolsa."),
            reviewed_anchor(key,5,"does not necessarily mean that the Notes will be recognised as eligible collateral"),
            reviewed_anchor(key,5,"Such recognition will depend upon satisfaction of the Eurosystem eligibility criteria.")]
        result=f.coupon("750000000",rate,start,end,[(start,end)],1,rounding="source_half_up")
        if result["amount"]!=expected:raise ValueError("Annual coupon disagrees with exact source arithmetic")
        eligibility=f.eurosystem_designation(doc["pages"][4]["text"])
        if eligibility["eligible_collateral"] is not None:raise ValueError("Conditional designation promoted")
        rows.append({"source":key,"anchors":quotes,"coupon":result,"eligibility":eligibility,
            "missing_calendar":f.deemed_notice(start,{}),
            "maturity_unknown_events":f.maturity_principal("750000000",purchased_and_cancelled=None,early_redeemed=None),
            "tax_notice_unknown_counting":f.tax_notice(start,end,legal_counting_confirmed=False),
            "scenario_assumptions":"Original issued nominal remains outstanding throughout first annual period; printed half-up convention selected. These are calculation premises, not evidenced payments or outstanding balances."})
    conflict=m.read(m.OUT/"dossier-review.json")["conflicts"][0]
    selected=f.select_section([{"number":"1.17","title":"FTT","source":"1843910"},
                               {"number":"1.17","title":"KPMG audit","source":"2001058"}],"1.17")
    assert selected["status"]=="UNRESOLVED" and len(selected["records"])==2
    result={"status":"PASS","formula_anchors":rules,"issues":rows,
        "duplicate_section":{"input_evidence":conflict,"result":selected},
        "tests":m.read(m.OUT/"closure-tests.json"),
        "production_promotion":False,"independent_legal_adjudication":False,
        "scope":"Optional source-bound successor calculations and qualification guards. Original-cohort S5 adapters and production reader are unchanged."}
    m.write(m.OUT/"repairs-results.json",result)
    print(json.dumps({"status":"PASS","source_issues":len(rows),"annual_coupon_amounts":[r["coupon"]["amount"] for r in rows],
        "eligibility_promoted":False,"missing_facts_abstain":True,"duplicate_sections_retained":2},indent=2))
