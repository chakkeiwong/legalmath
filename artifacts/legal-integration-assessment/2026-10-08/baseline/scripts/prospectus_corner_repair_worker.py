"""Candidate-only worker; all evidence inputs come from the preserved source checkout."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, os, sys, time
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-corner-repair-2026-10-04"
CANDIDATE = OUT / "candidate"
DATA = ROOT / "docs/prospectus/corner-cases-2026-10-04"
OLD = ROOT / "docs/implementation/prospectus-corner-cases-2026-10-04"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.path.insert(0, str(CANDIDATE / "src"))
from legalmath.prospectus import loss_absorption_reader as reader
from legalmath.prospectus.document_intake import validate_bundle
assert Path(reader.__file__).is_relative_to(CANDIDATE / "src")


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")


def intake(folder):
    sources = {s["key"]: s for s in read(DATA/"source-index.json")["sources"]}
    old_sources = read(ROOT/"docs/prospectus/jurisdiction-2026-10-04/source-index.json")["sources"]
    sources.update({s["key"]:s for s in old_sources})
    issuer = "Banco Espírito Santo, S.A."
    programme = [issuer, "BES Finance Ltd."]
    editions = {
        "1217215": ("2010-11-03","base_prospectus",None),
        "1221003": ("2010-11-15","supplement","1217215"),
        "1272291": ("2011-03-03","supplement","1217215"),
        "1260978": ("2011-04-19","supplement","1217215"),
        "1286398": ("2011-06-06","supplement","1217215"),
        "1297141": ("2011-06-17","supplement","1217215"),
        "1347380": ("2011-07-13","supplement","1217215"),
        "1774077": ("2013-07-17","base_prospectus",None),
        "1774113": ("2013-09-02","supplement","1774077"),
        "1843910": ("2013-11-06","supplement","1774077"),
        "1949460": ("2014-02-24","supplement","1774077"),
        "2001058": ("2014-04-23","supplement","1774077")}
    documents = {}
    for code,(date,role,base) in editions.items():
        key = "jur-more-bes-" + code
        source = sources[key]
        documents[key] = {**source, "id":key, "role":role, "edition_date":date,
                          "base_id":"jur-more-bes-"+base if base else None,
                          "programme_issuers":programme}
    rows = []
    for series,terms_date,issued,isin,key,base,supplements in [
        ("23","2011-07-14","2011-07-15","PTBEQBOM0010","jur-more-bes-1315263","1217215",
         ["1221003","1272291","1260978","1286398","1297141","1347380"]),
        ("35","2014-01-20","2014-01-21","PTBENKOM0012","jur-more-bes-1922255","1774077",
         ["1774113","1843910"]),
        ("36","2014-05-06","2014-05-08","PTBEQKOM0019","jur-bes-2014-ptbeqkom0019","1774077",
         ["1774113","1843910","1949460","2001058"])]:
        source = sources[key]
        documents[key] = {**source, "id":key, "role":"final_terms","edition_date":terms_date,
                          "base_id":"jur-more-bes-"+base, "programme_issuers":[issuer],
                          "issuer":issuer,"security_class":"senior","identifiers":[isin]}
        keys = [key, "jur-more-bes-"+base] + ["jur-more-bes-"+s for s in supplements]
        issue = {"id":"bes-series-"+series,"issuer":issuer,"title":"BES Series "+series,
                 "security_class":"senior","terms_date":terms_date,"issue_date":issued,"identifiers":[isin],
                 "documents":[{"id":k} for k in keys],
                 "document_contract":{"issuer":issuer,"security_class":"senior","issue_date":issued,
                     "required_documents":[{f:documents[k].get(f) for f in
                         ("id","sha256","role","edition_date","base_id")} for k in keys],
                     "precedence_reviewed":False,
                     "unresolved_dependencies":["incorporated financial reports and complete version/precedence review"],
                     "provenance":"Retained covers and reviewed final-terms images; conditional metadata, independent adjudication pending"}}
        result = validate_bundle(issue, documents, ROOT)
        assert result["status"] == "UNRESOLVED"
        assert not any("MISMATCH" in p or "SOURCE_CHANGED" in p for p in result["issues"])
        rows.append({"issue":issue,"binding":result})
    write(folder/"bes-bundles.json", {"issues":rows,"documents":documents})
    metadata = read(OLD/"run-001/reader-documents.json")
    selection = read(DATA/"reader-selection.json")
    extraction=[]
    for case in selection["offering_documents"]:
        key=case["source_key"]
        document=reader.load_document(metadata[key],ROOT)
        report=reader.extraction_coverage(document, {})
        extraction.append({"id":case["id"],**report})
    write(folder/"extraction.json",extraction)
    return {"status":"PASS","bes_issues":len(rows),"bundle_statuses":dict(Counter(r["binding"]["status"] for r in rows)),
            "extraction_statuses":dict(Counter(r["status"] for r in extraction)),
            "ocr_performed":False,"source_completeness":"OPEN","independent_adjudication":False}


def compare(folder):
    selections=read(DATA/"reader-selection.json")
    metadata=read(OLD/"run-001/reader-documents.json")
    comparisons=[]
    for mode, cases in [("whole_document",selections["offering_documents"]),("clause_probe",selections["probes"])]:
        for case in cases:
            key=case["source_key"];meta=metadata[key]
            selection={"id":key,"operative_pages":case.get("operative_pages",[[1,meta["pages"]]]),
                       "scope_basis":case.get("scope_basis","Whole-PDF diagnostic; not complete legal scope")}
            issue={k:case[k] for k in ("id","issuer","title","identifiers") if k in case}
            issue.update(security_type="debt",documents=[selection])
            start=time.monotonic()
            result=reader.analyze_issue(issue,{key:meta},ROOT)
            doc=reader.load_document(meta,ROOT)
            assert all(reader.quote_valid(e,doc) for e in result["evidence"])
            assert result["certified_legal_answer"] is None
            write(folder/(case["id"]+".json"),result)
            original=read(OLD/"run-001"/(case["id"]+".json"))
            comparisons.append({"id":case["id"],"mode":mode,"baseline_answer":original["answer"],
                "candidate_answer":result["answer"],"baseline_unresolved":sum(e["disposition"].startswith("unresolved") for e in original["evidence"]),
                "candidate_unresolved":sum(e["disposition"].startswith("unresolved") for e in result["evidence"]),
                "extraction":result.get("extraction"),"wall_seconds":round(time.monotonic()-start,4)})
    prior_data=ROOT/"docs/prospectus/difficulty-2026-10-04"
    prior_out=ROOT/"docs/implementation/prospectus-difficulty-2026-10-04/run-001"
    prior_sources={r["key"]:r for r in read(prior_data/"sources.json")}
    paired=[]
    for case in read(prior_data/"cases.json")["cases"]:
        if case["id"] not in {"case-105635287"}:continue
        meta=prior_sources[case["source_key"]]["document"]
        selection={"id":meta["id"],"operative_pages":case.get("operative_pages",[[1,meta["pages"]]]),
                   "scope_basis":case.get("scope_basis","Whole-document diagnostic stress input; legal applicability not established")}
        if case.get("shelf_pages"):selection["shelf_pages"]=case["shelf_pages"]
        issue={k:case[k] for k in ("id","issuer","title","identifiers") if k in case}
        issue.update(security_type=case.get("security_type","debt"),documents=[selection])
        result=reader.analyze_issue(issue,{meta["id"]:meta},ROOT)
        original=read(prior_out/(case["id"]+".json"))
        doc=reader.load_document(meta,ROOT)
        assert all(reader.quote_valid(e,doc) for e in result["evidence"])
        write(folder/(case["id"]+".json"),result)
        for e in original["evidence"]:
            if e["kind"]!="principal_write_down":continue
            assert reader.quote_valid(e,doc)
            features=reader.clause_features(e["quote"])
            paid=any(f["disposition"]=="principal_repaid_in_partial_redemption" for f in features)
            loss=any(f["kind"]=="principal_write_down" and f["disposition"]=="applicable" for f in features)
            new_e=[n for n in result["evidence"] if n["start"]<e["end"] and e["start"]<n["end"]]
            not_lost=any(n["disposition"]=="principal_repaid_in_partial_redemption" for n in new_e)
            paired.append({"baseline_id":e["id"],"baseline":e,"candidate_features":features,
                           "candidate_document_evidence":new_e,
                           "status":"PASS" if paid and not loss and not_lost else "FAIL"})
        comparisons.append({"id":case["id"],"mode":"prior_paid_amortisation_control",
            "baseline_answer":original["answer"],"candidate_answer":result["answer"],
            "baseline_unresolved":sum(e["disposition"].startswith("unresolved") for e in original["evidence"]),
            "candidate_unresolved":sum(e["disposition"].startswith("unresolved") for e in result["evidence"]),
            "extraction":result["extraction"]})
    write(folder/"paid-controls.json",paired)
    findings=[]
    for check in read(OLD/"regression-findings.json")["findings"]:
        row=read(folder/(check["run"]+".json"))
        found=[e for e in row["evidence"] if " ".join(check["quote"].split()) in " ".join(e["quote"].split())]
        losses=[e for e in found if e.get("semantic_witness",{}).get("rule")=="unpaid_cancellation"]
        passed=bool(losses) and all(e["disposition"]!="repurchase_or_redemption_cancellation" for e in found)
        findings.append({"id":check["id"],"status":"PASS" if passed else "FAIL",
                         "conditions":[e["semantic_witness"] for e in losses],
                         "final_answer":row["answer"]})
    write(folder/"classification-checks.json",findings)
    write(folder/"comparisons.json",comparisons)
    return {"status":"PASS" if all(r["status"]=="PASS" for r in findings+paired) and len(paired)==2 else "FAIL",
            "paid_controls":len(paired),"paid_controls_passed":sum(r["status"]=="PASS" for r in paired),
            "whole_documents":7,"probes":3,"classification_checks":len(findings),
            "classification_passed":sum(r["status"]=="PASS" for r in findings),
            "answers":dict(Counter(str(r["candidate_answer"]) for r in comparisons if r["mode"]=="whole_document")),
            "legal_accuracy":"NOT_MEASURED","reader_module":reader.__file__}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("phase",choices=("intake","compare","legal"))
    p.add_argument("folder")
    a=p.parse_args();folder=Path(a.folder).resolve()
    assert folder.is_relative_to(OUT) and folder.is_dir()
    if a.phase=="legal":
        from scripts.prospectus_corner_repair_legal import run
        result=run(folder)
    else:result=globals()[a.phase](folder)
    write(folder/"result.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(1 if result["status"]=="FAIL" else 0)


if __name__=="__main__":main()
