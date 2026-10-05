"""Run the frozen candidate through reviewed derivative admission."""
import json,sys
from scripts import run_prospectus_closure_next as m
from scripts.prospectus_reviewed_extraction import load
from scripts.prospectus_closure_intake import analyze
def run():
    candidate=m.ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04/candidate"
    sys.path.insert(0,str(candidate/"src"))
    from legalmath.prospectus import loss_absorption_reader as r
    assert str(candidate) in r.__file__
    metadata=m.read(m.DATA/"reviewed-extractions.json")
    old=m.read(m.ROOT/"docs/implementation/prospectus-corner-cases-2026-10-04/run-001/reader-documents.json")
    cases=m.read(m.ROOT/"docs/prospectus/corner-cases-2026-10-04/reader-selection.json")["offering_documents"]
    results=[]
    folder=m.OUT/"validated-reader-v2";folder.mkdir(exist_ok=True)
    for case in cases:
        key=case["source_key"]
        meta=metadata.get(key,old[key])
        doc=load(meta,m.ROOT) if key in metadata else r.load_document(meta,m.ROOT)
        issue={k:case[k] for k in ("id","issuer","title","identifiers") if k in case}
        issue.update(security_type="debt",documents=[{"id":key,"operative_pages":[[1,meta["pages"]]],
            "scope_basis":"Fixed full-document engineering comparison; dependency completeness not established"}])
        value,raw=analyze(r,issue,{key:meta},m.ROOT)
        assert all(r.quote_valid(e,doc) for e in value["evidence"])
        assert value["certified_legal_answer"] is None
        m.write(folder/(case["id"]+".json"),value)
        m.write(folder/(case["id"]+"-frozen-output.json"),raw)
        results.append({"id":case["id"],"answer":value["answer"],"extraction":value["extraction"],
            "validated_ocr":doc.get("automatic_ocr_performed",False),
            "unresolved":sum(e["disposition"].startswith("unresolved") for e in value["evidence"])})
    m.write(m.OUT/"validated-reader-results-v2.json",results)
    print(json.dumps([{"id":v["id"],"answer":v["answer"],
        "extraction":[e["status"] for e in v["extraction"]],"ocr":v["validated_ocr"]} for v in results],indent=2))
