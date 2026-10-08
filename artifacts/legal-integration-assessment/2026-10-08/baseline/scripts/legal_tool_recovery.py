"""Retained local runtime repair and one final transport retry."""
from scripts.legal_tool_program import OUT,DOC,LIMITS,read,save,ref,used_repairs

def direct_folder(question,arm):
    folder=OUT/"live-trials"/(question+"-"+arm)
    row=folder/"row.json"
    if row.exists() and read(row)["status"]=="FAILED":
        if (question,arm)!=("p10","baseline"):
            return folder,1
        retry=folder.with_name(folder.name+"-retry-1")
        ledger=read(OUT/"repairs.json")
        identifier="transport-retry-r3"
        if not any(r["id"]==identifier for r in ledger["repairs"]):
            if used_repairs(read(OUT/"state.json"))>=LIMITS["repair_attempts"]:
                raise RuntimeError("Repair budget exhausted")
            ledger["repairs"].append({"id":identifier,
                "review":ref(DOC/"t3-transport-repair.md"),"failed_arm":ref(row),
                "reason":"One unchanged-route retry after a transport timeout"})
            save(OUT/"repairs.json",ledger)
        return retry,2
    return folder,1

def repair_logical_english(work):
    from scripts.legal_tool_native import logical_english
    row=OUT/"logical-english-repair/result.json"
    if row.exists():
        save(work/"component-repairs.json",{"logical-english":ref(row)})
        return
    state=read(OUT/"state.json")
    if used_repairs(state)>=LIMITS["repair_attempts"]:
        save(work/"component-repairs.json",{"logical-english":{"status":"DEFER_REPAIR_BUDGET"}})
        return
    ledger=read(OUT/"repairs.json")
    ledger["repairs"].append({"id":"logical-english-r2","review":ref(DOC/"t3-review.md"),
        "reason":"Rebuild unpacked SWI autoload index and declare optional R syntax operator; pinned source is preserved"})
    save(OUT/"repairs.json",ledger)
    row.parent.mkdir(parents=True,exist_ok=True)
    try:result=logical_english(row.parent)
    except Exception as exc:
        result={"status":"TRIAL_FAILED","error":str(exc),"decision":"DEFER_RUNTIME"}
    if result.get("status")!="PASS":result["decision"]="DEFER_RUNTIME"
    save(row,result)
    save(work/"component-repairs.json",{"logical-english":ref(row)})
