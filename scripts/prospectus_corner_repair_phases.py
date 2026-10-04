"""Phase implementations for the isolated repair master."""
import sys
from scripts import run_prospectus_corner_repair as m


def worker(phase, folder):
    run=m.command([str(m.ROOT/".venv/bin/python"),"-m","scripts.prospectus_corner_repair_worker",
                   phase,str(folder)],folder,phase,timeout=180)
    path=folder/"result.json"
    result=m.read(path) if path.exists() else {"status":"FAIL","reason":"No worker result"}
    if run["exit_code"]:result["status"]="FAIL"
    return {**result,"run":run}


def finalize(folder,args):
    from scripts.prospectus_corner_repair_finalize import finalize as action
    return action(folder,args)


def verify(folder,args):
    from scripts.prospectus_corner_repair_finalize import verify as action
    return action(folder,args)


def intake(folder,args):return worker("intake",folder)
def legal(folder,args):return worker("legal",folder)
def compare(folder,args):return worker("compare",folder)

def fetch(folder,args):
    from scripts import prospectus_jurisdiction_study as j
    data=m.ROOT/"docs/prospectus/corner-repair-2026-10-04"
    j.DATA=data
    j.OUT=m.OUT
    policy=m.read(data/"acquisition-policy.json")
    assert policy["global_ceiling"]==212 and policy["max_new_requests"]==42
    before=len(j.receipts())
    m.write(data/"policy-snapshots"/(m.sha(data/"acquisition-policy.json")+".json"),policy)
    m.write(folder/"queue.json",m.read(data/"public-queue.json"))
    m.write(folder/"policy.json",policy)
    existing={m.read(p)["key"] for p in j.receipts()}
    results=[]
    for row in m.read(data/"public-queue.json"):
        if row["key"] in existing:continue
        result=j.fetch(row["key"]);results.append(result)
        print(__import__("json").dumps(result),flush=True)
    extracted=j.extract()
    m.write(folder/"source-index.json",m.read(data/"source-index.json"))
    after=len(j.receipts())
    records=[m.read(p) for p in j.receipts() if m.read(p)["key"] in {r["key"] for r in m.read(data/"public-queue.json")}]
    m.write(folder/"requests.json",records)
    return {"status":"PASS","before":before,"after":after,"new_requests":after-before,
            "remaining":212-after,"requests":results,"extraction":extracted,
            "legal_source_completeness":"REQUIRES_SOURCE_REVIEW"}

