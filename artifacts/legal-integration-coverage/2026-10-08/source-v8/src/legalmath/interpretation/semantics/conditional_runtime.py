"""Regenerated Lean certificates for actual decoded conditional Java results."""
import json
from pathlib import Path
import subprocess
import tempfile
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from .conditional_ir import decode, witnesses, lower, reference
from ..assurance.proof_certificate import LEAN
from .qualification_v2 import targets

HERE=Path(__file__).parent
PRELUDE=HERE/"ConditionalHorn.lean"
JAVA=HERE/"ConditionalHorn.java"
JSON_SOURCE=HERE.parents[1]/"java/runtime/Json.java"
PROFILE="legalmath.conditional-runtime.v1"
SCOPE={
    "proved":"For the exact decoded numeric program and fixed evidence codes, the returned head set contains exactly the inductively derivable positive heads.",
    "assumptions":["The fixed-evidence positive Horn semantics in ConditionalHorn.lean.",
        "Source-to-rule interpretation, evidence admission and code/identity mapping are supplied premises."],
    "excludes":["English fidelity","Evidence truth","General recursive defeasible argumentation",
        "Universal Python/Java/codec/compiler correctness","Legal discharge","Unrestricted future generalization"]}


def write(path,value):
    with Path(path).open("xb") as f:f.write(canonical(value))


def method():
    return {p.name:raw_digest(p.read_bytes()) for p in (PRELUDE,JAVA,JSON_SOURCE,
        Path(__file__),HERE/"conditional_ir.py")}


def compile_java(directory,jdk):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    classes=directory/"classes";classes.mkdir(exist_ok=True)
    cmd=[str(Path(jdk)/"bin/javac"),"-encoding","UTF-8","-d",str(classes),str(JSON_SOURCE),str(JAVA)]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
    (directory/"javac.log").write_text(result.stdout+result.stderr)
    if result.returncode:raise LegalMathError("E_DEPENDENCY",details="Conditional Java build failed: "+result.stderr[:1000])
    return {"target":targets(jdk),"sources":{str(p):raw_digest(p.read_bytes()) for p in (JAVA,JSON_SOURCE)},
        "classes":{str(p.relative_to(classes)):raw_digest(p.read_bytes()) for p in sorted(classes.rglob("*.class"))}}


def java_raw(lines,directory,jdk):
    if len(lines)>4096 or sum(len(x.encode())+1 for x in lines)>20*1024*1024:
        raise LegalMathError("E_RESOURCE_LIMIT")
    cmd=[str(Path(jdk)/"bin/java"),"-cp",str(Path(directory)/"classes"),"hk.legalmath.ConditionalHorn"]
    proc=subprocess.run(cmd,input="\n".join(lines)+"\n",capture_output=True,text=True,timeout=60)
    if proc.returncode:raise LegalMathError("E_DEPENDENCY",details=proc.stderr[:1000])
    output=proc.stdout.splitlines()
    if len(output)!=len(lines):raise LegalMathError("E_INTEGRITY",details="Missing/extra runtime output")
    return [loads(line.encode()) for line in output]


def checked_java(programs,directory,jdk):
    values=[p.model_dump(mode="json") for p in programs]
    output=java_raw([canonical(v).decode() for v in values],directory,jdk)
    for p,v,r in zip(programs,values,output):
        if set(r)!={"status","decoded","program_hash","derived"} or r["status"]!="OK":
            raise LegalMathError("E_INTEGRITY",details="Valid conditional input rejected")
        if r["decoded"]!=v or r["program_hash"]!=digest(v):
            raise LegalMathError("E_REFERENCE",details="Requested and Java-decoded programs differ")
        # This reconstructs the object from the actual decoded wire response.
        decoded=decode(canonical(r["decoded"]))
        witnesses(decoded,r["derived"])
        if reference(p)!=r["derived"]:raise LegalMathError("E_INTEGRITY")
    return output


def lean_list(xs):
    return "["+", ".join(str(x) for x in xs)+"]"


def lean_rule(r):
    return "{ facts := "+lean_list(r.facts)+", parents := "+lean_list(r.parents)+", head := "+str(r.head)+" }"


def proof_text(program,derived):
    order=witnesses(program,derived)
    out=[PRELUDE.read_text(),"\nopen LegalMathConditional\n",
        "set_option maxRecDepth 8192\nset_option maxHeartbeats 4000000\n",
        "def inputCodes : List Nat := "+lean_list(program.codes)+"\n"]
    for i,r in enumerate(program.rules):
        out.append("def rule"+str(i)+" : Rule := "+lean_rule(r)+"\n")
    names=["rule"+str(i) for i in range(len(program.rules))]
    out.append("def inputRules : List Rule := ["+", ".join(names)+"]\n")
    out.append("def returned : List Nat := "+lean_list(derived)+"\n")
    for row in order:
        h,i=row["head"],row["rule"];r=program.rules[i]
        out.append(f"theorem head_{h} : Derivable inputRules inputCodes {h} := by\n")
        out.append(f"  apply Derivable.byRule (r := rule{i}) (by decide) (by unfold factsGood; decide)\n")
        out.append("  intro p hp\n")
        if not r.parents:
            out.append(f"  simp [rule{i}] at hp\n")
        else:
            out.append(f"  simp only [rule{i}, List.mem_cons, List.not_mem_nil, or_false] at hp\n")
            for j,parent in enumerate(r.parents):
                if j<len(r.parents)-1:
                    out.append("  rcases hp with hp | hp\n")
                    out.append(f"  · subst p; exact head_{parent}\n")
                else:out.append(f"  subst p; exact head_{parent}\n")
    out.append("theorem result_sound : Sound inputRules inputCodes returned := by\n")
    out.append("  intro h member\n")
    if not derived:out.append("  simp [returned] at member\n")
    else:
        out.append("  simp only [returned, List.mem_cons, List.not_mem_nil, or_false] at member\n")
        for j,h in enumerate(derived):
            if j<len(derived)-1:
                out.append("  rcases member with member | member\n")
                out.append(f"  · subst h; exact head_{h}\n")
            else:out.append(f"  subst h; exact head_{h}\n")
    out.append("theorem result_closed : Closed inputRules inputCodes returned := by\n  intro r member\n")
    if not program.rules:
        out.append("  simp [inputRules] at member\n")
    else:
        out.append("  simp only [inputRules, List.mem_cons, List.not_mem_nil, or_false] at member\n")
        for i,r in enumerate(program.rules):
            last=i==len(program.rules)-1
            if not last:
                out.append("  rcases member with member | member\n")
            pad="  " if last else "  · "
            out.append(pad+"subst r\n")
            indent="  " if last else "    "
            out.append(indent+"intro facts parents\n")
            if r.head in derived:
                out.append(indent+"exact (by decide)\n")
            elif any(program.codes[f]!=1 for f in r.facts):
                out.append(indent+"change false = true at facts\n"+indent+"cases facts\n")
            else:
                missing=next(p for p in r.parents if p not in derived)
                out.append(indent+f"have absent : {missing} ∉ returned := by decide\n")
                out.append(indent+f"exact False.elim (absent (parents {missing} (by decide)))\n")
    out.append("theorem actual_runtime_exact : ∀ h, h ∈ returned ↔ Derivable inputRules inputCodes h :=\n")
    out.append("  sound_closed_exact inputRules inputCodes returned result_sound result_closed\n")
    out.append("#print axioms actual_runtime_exact\n")
    return "".join(out)


def kernel(program,derived,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    code=proof_text(program,derived)
    path=directory/"ConditionalResult.lean";path.write_text(code)
    run=subprocess.run([str(LEAN),str(path.resolve())],capture_output=True,text=True,timeout=60,cwd=directory)
    log=run.stdout+run.stderr;(directory/"lean.log").write_text(log)
    import re
    used=set()
    for group in re.findall(r"depends on axioms: \[([^\]]*)\]",log):
        used.update(x.strip() for x in group.split(",") if x.strip())
    # Lean core logical axioms are explicit; no sorryAx or supplied axiom is accepted.
    printed=re.findall(r"'actual_runtime_exact' (?:depends on axioms: \[[^\]]*\]|does not depend on any axioms)",log)
    if run.returncode or len(printed)!=1 or "sorry" in log or used-{"propext","Quot.sound"}:
        raise LegalMathError("E_INTEGRITY",details="Conditional Lean proof rejected: "+log[-2500:])
    return {"status":"KERNEL_CHECKED","profile":PROFILE,"theorem":"actual_runtime_exact",
        "tool_sha256":raw_digest(LEAN.read_bytes()),"prelude_sha256":raw_digest(PRELUDE.read_bytes()),
        "certificate_sha256":raw_digest(code.encode()),"log_sha256":raw_digest(log.encode()),
        "program_hash":program.identity(),"derived":derived,"scope":SCOPE,"kernel_axioms":sorted(used)}


def run(program,directory,jdk):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    value=program.model_dump(mode="json")
    write(directory/"input.json",value)
    build=compile_java(directory/"java",jdk)
    reply=checked_java([program],directory/"java",jdk)[0]
    write(directory/"java-reply.json",reply)
    proof=kernel(decode(canonical(reply["decoded"])),reply["derived"],directory/"proof")
    report={"profile":PROFILE,"method":method(),"program_hash":program.identity(),
        "java":reply,"build":build,"kernel":proof,"scope":SCOPE,"legal_correctness":"NOT_ESTABLISHED",
        "release_eligible":False}
    write(directory/"result.json",report)
    return report


def verify(program,directory,*,jdk=None,target=None):
    directory=Path(directory)
    old=loads((directory/"result.json").read_bytes())
    if old.get("profile")!=PROFILE or old.get("method")!=method():
        raise LegalMathError("E_STALE_REVIEW")
    wanted=targets(jdk) if jdk else target
    if wanted is None or old["build"]["target"]!=wanted:raise LegalMathError("E_STALE_REVIEW")
    if loads((directory/"input.json").read_bytes())!=program.model_dump(mode="json"):
        raise LegalMathError("E_REFERENCE")
    if loads((directory/"java-reply.json").read_bytes())!=old["java"]:
        raise LegalMathError("E_INTEGRITY")
    for name,h in old["build"]["classes"].items():
        p=(directory/"java/classes"/name).resolve()
        if not p.is_relative_to((directory/"java/classes").resolve()) or raw_digest(p.read_bytes())!=h:
            raise LegalMathError("E_INTEGRITY")
    if raw_digest((directory/"proof/ConditionalResult.lean").read_bytes())!=old["kernel"]["certificate_sha256"]:
        raise LegalMathError("E_INTEGRITY")
    if raw_digest((directory/"proof/lean.log").read_bytes())!=old["kernel"]["log_sha256"]:
        raise LegalMathError("E_INTEGRITY")
    # Never execute receipt-provided proof code or class paths. Rebuild from checked data.
    actual_jdk=Path(jdk) if jdk else Path(wanted["java"]["path"]).parent.parent
    if targets(actual_jdk)!=wanted:raise LegalMathError("E_STALE_REVIEW")
    with tempfile.TemporaryDirectory(prefix="conditional-verify-") as td:
        rebuilt=run(program,Path(td)/"rebuilt",actual_jdk)
    if old!=rebuilt:raise LegalMathError("E_INTEGRITY",details="Conditional runtime receipt differs from recomputation")
    return old


def attach(scoped,report):
    branch_rows=[]
    indices={name:i for i,name in enumerate(report["java"]["decoded"]["heads"])}
    for b in scoped["branches"]:
        branch_rows.append({"branch_id":b["branch_id"],
            "rule_results":[{"rule_id":r["rule_id"],"head_index":indices[r["rule_id"]],
                "derived":indices[r["rule_id"]] in report["java"]["derived"]} for r in b["results"]],
            "runtime_hash":digest(report),"standards_lowering":PROFILE,
            "legacy_formula_relationship":"NOT_ESTABLISHED"})
    return {"profile":PROFILE,"runtime":report,"branches":branch_rows}
