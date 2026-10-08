"""Check retained engine evidence against source-reviewed unpaid-cancellation expectations."""
import argparse, json, re
from scripts import prospectus_corner_cases as c
def norm(text):return re.sub(r"\s+"," ",text).strip()
EXPECTED=[
    {"id":"CC29-final","run":"probe-lease-final-cancellation","source":"jur-more-hypo-1314069","page":140,
     "quote":"If the Issuer has insufficient Issuer Available Funds to repay the Senior Notes in full",
     "exception":"unless payment of such amounts is being improperly withheld or refused",
     "explanation":"Condition8.1.3 cancels unpaid amounts on insufficient funds, subject to improper-withholding exception."},
    {"id":"CC29-exhaustion","run":"probe-lease-exhaustion","source":"jur-more-hypo-1314069","page":145,
     "quote":"the Noteholders shall have no further claim against the Issuer",
     "exception":"the Representative of the Noteholders has given notice",
     "explanation":"Condition9.2.3 extinguishes unpaid claims after a certificate and notice; this is not cancellation after payment."},
    {"id":"CC28-cancellation","run":"probe-adriatica-cancellation","source":"jur-more-hypo-843665","page":121,
     "quote":"If the Notes cannot be redeemed in full on the Maturity Date",
     "exception":"in the absence of gross negligence (colpa grave) or wilful misconduct (dolo)",
     "explanation":"Condition7(b) preserves unpaid claims until the later CancellationDate, with a misconduct exception."}
]
def main():
    p=argparse.ArgumentParser();p.add_argument("--run-directory",default=str(c.OUT/"run-001"));a=p.parse_args()
    folder=c.Path(a.run_directory).resolve()
    assert folder.is_relative_to(c.OUT.resolve())
    sources={s["key"]:s for s in c.j.read(c.DATA/"source-index.json")["sources"]}
    rows=[]
    for expected in EXPECTED:
        source=sources[expected["source"]]
        assert c.j.sha(c.ROOT/source["original"])==source["sha256"]
        pages=c.j.read(c.DATA/"sources"/source["key"]/"pages.json")["pages"]
        page=norm(pages[expected["page"]-1]["text"])
        assert norm(expected["quote"]) in page and norm(expected["exception"]) in page
        result=c.j.read(folder/(expected["run"]+".json"))
        evidence=[e for e in result["evidence"] if norm(expected["quote"]) in norm(e["quote"])]
        accepted=[e for e in evidence if (e["kind"]=="principal_write_down" and e["disposition"]=="applicable") or e["disposition"].startswith("unresolved")]
        ordinary=[e for e in evidence if e["disposition"]=="repurchase_or_redemption_cancellation"]
        # A minimal safety criterion: do not discard this unpaid cancellation as repayment.
        passed=bool(accepted) and not ordinary
        rows.append({**expected,"source_sha256":source["sha256"],"status":"PASS" if passed else "FAIL",
            "criterion":"Retain as unpaid principal loss or unresolved meaning, not ordinary post-payment cancellation.",
            "matching_evidence":[{"id":e["id"],"kind":e["kind"],"disposition":e["disposition"]} for e in evidence],
            "final_answer":result["answer"],"certified_legal_answer":result["certified_legal_answer"],
            "scope":"Minimum clause classification screen; pass does not certify exception logic or issue-level legal result."})
    failed=sum(r["status"]=="FAIL" for r in rows)
    report={"status":"GAPS_REPRODUCED" if failed else "MINIMUM_SCREEN_PASS","checked":len(rows),"failed":failed,"findings":rows,
            "engine_fix_applied":False,"legal_adjudication":"PENDING","baseline":"Unchanged 293-file reader"}
    c.j.write(c.OUT/"regression-findings.json",report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(1 if failed else 0)
if __name__=="__main__":main()
