"""Immutable semantic identity around actual Java execution of supported branches."""
from pathlib import Path
from ...canonical import canonical,digest,loads,raw_digest
from ...errors import LegalMathError
from ...qualification.assurance import check_cases,method_manifest
from ...java.manifest import build_candidate,run_java
from ...ir.trace import verify_result
from ..search.formal import bundle,RULE
from .records import Branch
from .lower import envelope,reference

PROFILE="legalmath.investigation-qualification.v2"

def methods():
    return {"semantic":{p.name:raw_digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))},
            "machine":method_manifest()}

def targets(jdk):
    return {name:{"path":str((Path(jdk)/"bin"/name).resolve()),"sha256":raw_digest((Path(jdk)/"bin"/name).read_bytes())}
            for name in ("java","javac")}

def write(path,value):
    path=Path(path)
    with path.open("xb") as f: f.write(canonical(value))

def identity(inputs,target):
    return {"profile":PROFILE,"inputs":digest(inputs),"branch":digest(inputs["branch"]),
            "method":digest(methods()),"target":target}

def expected(inputs):
    branch=Branch.model_validate_json(canonical(inputs["branch"]))
    env=envelope(branch,inputs["packet"],inputs["reading"],inputs["question"])
    outcomes=[reference(branch,inputs["reading"],case,tuple(inputs["extension_ids"]),inputs["completion"])
              for case in inputs["cases"]]
    if env["legacy_packet"] is None:
        outcomes=[o.model_copy(update={"lowering":"unsupported",
            "reasons":tuple(sorted(set(o.reasons)|{"unsupported-lowering"}))}) for o in outcomes]
    return env,outcomes

def run(branch,packet,reading,question,cases,directory,jdk,at,*,extension_ids=(),completion="complete"):
    check_cases(cases)
    if not cases: raise LegalMathError("E_REFERENCE",details="Semantic qualification needs explicit cases")
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    inputs={"branch":branch.model_dump(mode="json"),"packet":packet,"reading":reading,"question":question,
            "cases":cases,"at":at,"extension_ids":list(extension_ids),"completion":completion}
    env,outcomes=expected(inputs);bound=identity(inputs,targets(jdk))
    write(directory/"inputs.json",inputs);write(directory/"envelope.json",env)
    supported=[(case,o) for case,o in zip(cases,outcomes) if o.lowering=="supported"]
    build=None;executions=[];target_status="UNSUPPORTED"
    if supported:
        b=bundle(reading,env["legacy_packet"],at)
        build=build_candidate(b,directory/"java",jdk)
        requests=[{**case,"bundle":b,"rule_id":RULE} for case,o in supported]
        actual=run_java(build["jar"],requests,jdk,build["class_name"])
        for (case,o),result in zip(supported,actual):
            verify_result(b,case["snapshot"],RULE,result)
            status={"TRUE":"true","FALSE":"false","UNKNOWN":"unknown","CONFLICT":"conflict","OUT_OF_SCOPE":"out-of-scope"}.get(result["status"])
            if status!=o.value: raise LegalMathError("E_INTEGRITY",details="Independent semantic/Java mismatch")
            executions.append({"case_id":case["id"],"result":result,"independent_value":o.value})
        build={**build,"jar":str(Path(build["jar"]).relative_to(directory))}
        target_status="EXECUTED"
    if bound!=identity(inputs,targets(jdk)): raise LegalMathError("E_STALE_REVIEW")
    report={"profile":PROFILE,"identity":bound,"outcomes":[o.model_dump(mode="json") for o in outcomes],
        "target":{"java":target_status,"catala":"NOT_SELECTED","build":build,"executions":executions},
        "source_meaning":"NOT_ESTABLISHED","release_eligible":False}
    report["report_hash"]=digest(report)
    write(directory/"qualification.json",report)
    return report

def verify(directory,branch,packet,reading,question,cases,at,*,extension_ids=(),completion="complete",jdk=None,target=None):
    directory=Path(directory)
    inputs={"branch":branch.model_dump(mode="json"),"packet":packet,"reading":reading,"question":question,
            "cases":cases,"at":at,"extension_ids":list(extension_ids),"completion":completion}
    report=loads((directory/"qualification.json").read_bytes())
    wanted=targets(jdk) if jdk else target
    if wanted is None: raise LegalMathError("E_REFERENCE")
    if report["identity"]!=identity(inputs,wanted): raise LegalMathError("E_STALE_REVIEW")
    if loads((directory/"inputs.json").read_bytes())!=inputs: raise LegalMathError("E_INTEGRITY")
    env,outcomes=expected(inputs)
    if loads((directory/"envelope.json").read_bytes())!=env: raise LegalMathError("E_INTEGRITY")
    base={k:v for k,v in report.items() if k!="report_hash"}
    if report["report_hash"]!=digest(base) or report["profile"]!=PROFILE or report["release_eligible"] is not False:
        raise LegalMathError("E_INTEGRITY")
    if report["source_meaning"]!="NOT_ESTABLISHED" or report["outcomes"]!=[o.model_dump(mode="json") for o in outcomes]:
        raise LegalMathError("E_INTEGRITY")
    supported=[(c,o) for c,o in zip(cases,outcomes) if o.lowering=="supported"]
    execution=report["target"];build=execution["build"]
    if set(execution)!={"java","catala","build","executions"} or execution["catala"]!="NOT_SELECTED":
        raise LegalMathError("E_INTEGRITY")
    if not supported:
        if execution!={"java":"UNSUPPORTED","catala":"NOT_SELECTED","build":None,"executions":[]}:
            raise LegalMathError("E_INTEGRITY")
    else:
        if not build or execution["java"]!="EXECUTED" or len(execution["executions"])!=len(supported):
            raise LegalMathError("E_REFERENCE")
        jar=(directory/build["jar"]).resolve()
        if not jar.is_relative_to(directory.resolve()) or raw_digest(jar.read_bytes())!=build["manifest"]["jar_sha256"]:
            raise LegalMathError("E_INTEGRITY")
        b=bundle(reading,env["legacy_packet"],at)
        if build["manifest"]["bundle_hash"]!=digest(b) or build["manifest_hash"]!=digest(build["manifest"]):
            raise LegalMathError("E_INTEGRITY")
        if loads((jar.parent/"build-manifest.json").read_bytes())!=build["manifest"]:
            raise LegalMathError("E_INTEGRITY")
        requests=[{**c,"bundle":b,"rule_id":RULE} for c,o in supported]
        actual=run_java(jar,requests,jdk,build["class_name"]) if jdk else None
        for index,((c,o),row) in enumerate(zip(supported,execution["executions"])):
            verify_result(b,c["snapshot"],RULE,row["result"])
            if row["case_id"]!=c["id"] or row["independent_value"]!=o.value:
                raise LegalMathError("E_INTEGRITY")
            value={"TRUE":"true","FALSE":"false","UNKNOWN":"unknown","CONFLICT":"conflict","OUT_OF_SCOPE":"out-of-scope"}.get(row["result"]["status"])
            if value!=o.value or (actual is not None and actual[index]!=row["result"]):
                raise LegalMathError("E_INTEGRITY")
    return report
