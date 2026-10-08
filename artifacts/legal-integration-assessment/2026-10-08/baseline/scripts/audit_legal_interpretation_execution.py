"""Fixed read-only baseline/current-code audit; writes one local audit receipt."""
from pathlib import Path
import json
import subprocess
import os
import sys
AUDIT_ROOT=Path(__file__).resolve().parents[1]
if Path(sys.prefix)!=AUDIT_ROOT/".venv":
    os.execv(str(AUDIT_ROOT/".venv/bin/python"),[str(AUDIT_ROOT/".venv/bin/python"),"-m","scripts.audit_legal_interpretation_execution"])
from scripts.run_legal_interpretation_program import ROOT,RUN,latest,read,sha,checked,save,ref,validated

def main():
    baseline=read(RUN/"P0/attempt-1/started.json")["code"]
    allowed={"src/legalmath/interpretation/assurance/complete_investigation.py",
             "src/legalmath/interpretation/assurance/investigation_observations.py"}
    altered=[p for p,h in baseline.items() if sha(ROOT/p)!=h]
    unrelated=[p for p in altered if p not in allowed and not p.startswith("src/legalmath/interpretation/semantics/")]
    if unrelated:raise ValueError("Unrelated baseline file changed: "+repr(unrelated))
    original=read(latest("P0").parent/"baseline.json")
    for name in ("pointer","receipt","dispositions","obligations","source","tasks"):checked(original[name])
    v1="src/legalmath/interpretation/assurance/qualification_adapter.py"
    if baseline[v1]!=sha(ROOT/v1):raise ValueError("Legacy qualification v1 bytes changed")
    predecessor=None
    for phase in ("P0","P1","P2","P3","P4","P5","P6","P7","P8"):
        current=latest(phase)
        if predecessor is not None and read(current.parent/"predecessor.json")!=ref(predecessor):
            raise ValueError("Stale predecessor: "+phase)
        predecessor=current
    if validated() is None:raise ValueError("No validation receipt for current code/tests")
    paths=["src/legalmath/interpretation/semantics","tests/interpretation/semantics",
           *sorted(allowed),"scripts/run_legal_interpretation_program.py","scripts/legal_interpretation_demo.py"]
    diff=subprocess.run(["git","diff","--check","--",*paths],cwd=ROOT,capture_output=True,text=True,timeout=30)
    if diff.returncode:raise ValueError(diff.stdout+diff.stderr)
    status=subprocess.check_output(["git","status","--short","--",*paths],cwd=ROOT,text=True,timeout=30)
    result={"status":"PASS","baseline_package_files_checked":len(baseline),
        "preexisting_package_files_changed":altered,"unrelated_changes":unrelated,
        "legacy_qualification_v1":"BYTE_IDENTICAL","original_pointer_sources_dispositions_obligations":"HASH_IDENTICAL",
        "all_phase_predecessors":"CURRENT","validation":ref(validated()),"diff_check":"PASS",
        "worktree_changes":status.splitlines(),"commit_push":"NOT_PERFORMED"}
    destination=RUN/("preservation-audit-"+str(len(list(RUN.glob("preservation-audit*.json")))+1)+".json")
    save(destination,result)
    print(json.dumps({k:v for k,v in result.items() if k!="worktree_changes"},indent=2))

if __name__=="__main__":main()
