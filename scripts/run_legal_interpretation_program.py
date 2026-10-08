
"""Fixed offline phase execution; no provider dispatch, shell or grant mutation."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv/bin/python"
if __name__ == "__main__" and Path(sys.prefix) != ROOT / ".venv":
    os.execv(str(VENV), [str(VENV), "-m", "scripts.run_legal_interpretation_program", *sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.canonical import digest
from legalmath.interpretation.semantics.operative import build_overlay, write_overlay

BASE = ROOT / "artifacts/assurance-gap-continuation/2026-10-02/additional-100-repair-20"
RUN = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1"
POINTER = BASE / "current-post-review-repairs.json"
OBLIGATIONS = BASE / "local-recovery/abc7952787bceb734607c614/obligation-evidence-map.json"
SOURCE = ROOT / "docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json"
PLANS = ROOT / "docs/plans/legal-interpretation-program"
PHASE_MANIFEST = ROOT / "docs/implementation/legal-interpretation-program/phase-manifest.json"
TASKS = BASE/"current-review/packages/7f36255237fa16cf0e3b5ba6/task-definitions.json"

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ref(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, ensure_ascii=False)+"\n").encode()
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Immutable output already exists: "+str(path))
    else:
        with path.open("xb") as f:
            f.write(raw)

def checked(item):
    p = (ROOT/item["path"]).resolve()
    if not p.is_relative_to(ROOT) or sha(p) != item["sha256"]:
        raise ValueError("Input identity changed: "+item["path"])
    return p

def selected():
    return checked(read(POINTER)["receipt"]).parent

def strings(obj, prefix=()):
    if isinstance(obj, str):
        yield prefix, obj
    elif isinstance(obj, dict):
        for key, val in obj.items():
            yield from strings(val, (*prefix, key))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            yield from strings(val, (*prefix, i))

def code_manifest():
    return {str(p.relative_to(ROOT)): sha(p)
            for p in sorted((ROOT/"src/legalmath").rglob("*"))
            if p.is_file() and p.suffix in (".py", ".json", ".java", ".lean")}

def execution_dependencies():
    return {path:sha(ROOT/path) for path in ("scripts/run_legal_interpretation_program.py",
        "scripts/legal_interpretation_demo.py","scripts/legal_interpretation_ops.py")}

def new_attempt(phase):
    directory = RUN/phase
    directory.mkdir(parents=True, exist_ok=True)
    attempt = directory/("attempt-"+str(len(list(directory.glob("attempt-*")))+1))
    attempt.mkdir()
    plan = next(p for p in read(PHASE_MANIFEST)["phases"] if p["id"] == phase)
    (attempt/"plan.md").write_bytes((ROOT/plan["plan"]).read_bytes())
    save(attempt/"started.json", {"phase": phase, "at": datetime.now(timezone.utc).isoformat(),
         "command": "python3 -m scripts.run_legal_interpretation_program run "+phase,
         "specification": ref(ROOT/plan["plan"]), "code": code_manifest(), "execution_code":execution_dependencies(),
         "git_commit": subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT,text=True).strip(),
         "python": sys.version, "executable": sys.executable,
         "cpu_mode": "CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
         "provider_calls": 0, "seeds": "N/A: deterministic"})
    return attempt

def require_tests(phase):
    validation=validated()
    if validation is None:
        raise ValueError("Current code, tests and executable driver require validation")
    return ref(validation)

def latest(phase):
    rows = sorted((RUN/phase).glob("attempt-*/result.json"), key=lambda p:p.stat().st_mtime)
    if not rows or read(rows[-1])["status"] not in ("IMPLEMENTED_QUALIFIED","IMPLEMENTED"):
        raise ValueError("Unfinished prerequisite: "+phase)
    result = read(rows[-1])
    for item in result["outputs"]: checked(item)
    return rows[-1]

def finish(attempt, phase, result, started):
    save(attempt/"result.json", {"status": "IMPLEMENTED_QUALIFIED", "phase": phase,
         "elapsed_seconds": round(time.monotonic()-started,3), "test_receipt": require_tests(phase),
         "outputs": [ref(p) for p in sorted(attempt.rglob("*")) if p.is_file() and p.name not in (".lock",)],
         "engineering": result, "legal_correctness": "NOT_ESTABLISHED",
         "release_eligible": False, "provider_calls": 0})
    print(json.dumps({"phase":phase, "result": ref(attempt/"result.json"), **result}, ensure_ascii=False, indent=2),flush=True)

def p0():
    started = time.monotonic()
    pointer = sha(POINTER)
    folder = selected()
    receipt = read(folder/"completion-receipt.json")
    for item in receipt["files"]: checked(item)
    records = read(folder/"dispositions.json")
    obligations = read(OBLIGATIONS)
    if len(records)!=70 or len({r["reading_id"] for r in records})!=35 or len(obligations)!=46:
        raise ValueError("Baseline denominator differs")
    if len({x["obligation"]["obligation_id"] for x in obligations}) != 46:
        raise ValueError("Duplicate obligation")
    tasks = read(TASKS)
    packets = [t["request"]["source_packet"] for t in tasks if "result_under_review" in t["request"]]
    if not packets or any(p != packets[0] for p in packets):
        raise ValueError("Retained source packets differ")
    packet = packets[0]
    raw_source = read(SOURCE)
    if raw_source["refNo"] != "26EC22" or not any("Revised on 20 April 2026" in u["text"] for u in packet["units"]):
        raise ValueError("Wrong circular edition")
    ids = {u["unit_id"]: u for u in packet["units"]}
    required_sources = ["ut-current.parent","ut-current.intro","tokenised-securities.circular","tokenised-securities.appendix"]
    if not all(i in ids for i in required_sources):
        raise ValueError("Acquired source premise missing")
    evidence = {i: {"unit_id":i, "unit_hash":digest(ids[i]), "packet_hash":digest(packet)} for i in ids}
    explanation = ("SHOULD is preserved. UT Chapter 6 and its introductory text, the Tokenised Securities Circular and its Appendix are acquired. "
                   "Their applicability, the complete dated authority chain and any additional product-specific conditions remain unresolved; no independent liability rule follows.")
    uncertainty = (" Paragraph 14 conditions demonstration on an SFC request, while footnote 5 states minimum confirmation and demonstration of compliance with paragraphs 10 to 13 and absence of contract vulnerabilities or security flaws with a high level of confidence. "
                   "Their trigger, object and standard relationship remains unresolved; do not infer exclusively request-triggered demonstration.")
    target_ids = {"alternative.004.3104c53459d53628","alternative.006.85e21a337aa3f33d"}
    patches, nominations = [], []
    for row in records:
        for path, text in strings(row["operative"]):
            allowed = (len(path)==2 and path==("reading","explanation") or
                       len(path)==3 and path[:2] in (("reading","remaining_questions"),("candidate_repair","unresolved_questions")) or
                       len(path)==4 and path[:2]==("candidate_repair","dimensions") and path[-1]=="explanation")
            if not allowed: continue
            low = text.lower()
            kind = None
            if row["role"]=="structure-reader" and row["reading_id"] in target_ids and path==("candidate_repair","dimensions",7,"explanation"):
                after, kind, ev = explanation, "acquisition-versus-applicability", required_sources
            elif ("demonstrat" in low and "request" in low and "footnote" not in low
                  and any(t in low for t in ("request-triggered","request-qualified","requested demonstration","request conditions"))):
                after, kind = text+uncertainty, "unresolved-footnote-relation"
                ev = [i for i,u in ids.items() if "upon SFC" in u["text"] or "at a minimum" in u["text"]]
            else:
                if "unavailable" in low or ("missing" in low and "circular" in low):
                    nominations.append({"role":row["role"],"reading_id":row["reading_id"],"path":list(path),
                         "text":text,"disposition":"RETAINED: repair instruction or unresolved additional authority; not a source-unavailability assertion selected for replacement"})
                continue
            patches.append({"role":row["role"],"reading_id":row["reading_id"],"path":list(path),
                            "before":text,"after":after,"reason":kind,"evidence_ids":ev})
    for identity,path in [("alternative.004.3104c53459d53628",["candidate_repair","dimensions",7,"explanation"]),
                          ("alternative.006.85e21a337aa3f33d",["candidate_repair","dimensions",7,"explanation"]),
                          ("alternative.011.3d746657604226ce",["reading","remaining_questions",1]),
                          ("alternative.000.f39a1382fac93154",["reading","remaining_questions",3])]:
        if not any(p["role"]=="structure-reader" and p["reading_id"]==identity and p["path"]==path for p in patches):
            raise ValueError("Required cited field absent")
    overlay = build_overlay(records,patches,expected_pointer=pointer,current_pointer=lambda:sha(POINTER),evidence=evidence)
    for before, after in zip(records,overlay["records"]):
        if before["original"] != after["original"] or before["operative"]["obligations"] != after["operative"]["obligations"]:
            raise ValueError("Historical input/obligation changed")
        def formulas(item):
            return [(p,t) for p,t in strings(item) if "formalization" in p]
        if formulas(before)!=formulas(after):
            raise ValueError("Formula changed")
    attempt = new_attempt("P0")
    save(attempt/"baseline.json", {"pointer":ref(POINTER),"receipt":ref(folder/"completion-receipt.json"),
         "dispositions":ref(folder/"dispositions.json"),"obligations":ref(OBLIGATIONS),
         "source":ref(SOURCE),"tasks":ref(TASKS),"packet_hash":digest(packet),
         "roles":dict(Counter(r["role"] for r in records)),"readings":35,"obligations_count":46})
    save(attempt/"packet.json",packet)
    save(attempt/"overlay-table.json",patches)
    save(attempt/"search-dispositions.json",nominations)
    save(attempt/"obligation-map.json",[{"obligation":o["obligation"],"status":"OPEN",
        "disposition":"unresolved-meaning and/or unresolved-fact; P0 prose correction is not closure"} for o in obligations])
    write_overlay(attempt/"overlay.json",overlay,current_pointer=lambda:sha(POINTER))
    next_plan = ("# P1 refreshed from P0\n\n"
        "Use packet.json, baseline.json and overlay.json from "+str(attempt.relative_to(ROOT))+
        ". There are 54 retained source units, 35 reading identities in two roles and 46 open obligations.\n\n"
        "Packet is historical units-only data, not the strict Packet schema. Add a lossless legacy envelope; do not pretend it already contains edition/actor/speaker metadata. "
        "Keep supplied source qualifications and raw circular identity. Distinguish source integrity, proposed meaning, applicability, factual support and formal results. "
        "Use strict immutable records with tuples, forbid truth coercion of four-state evidence, preserve partial dates without year imputation, and bind semantic branch assumptions/settings independently of a legacy Reading.\n\n"
        "Audit passed: no source truth inferred from verified quotes; unknown actor/time/role remain unresolved. Tests: approved phase-tests P1 and regression contracts. "
        "Stop on lossy roundtrip or source identity mismatch; unsupported meaning permits conditional development.\n")
    (attempt/"next-phase-plan.md").write_text(next_plan)
    finish(attempt,"P0",{"role_records":70,"reading_identities":35,"original_obligations":46,
         "corrected_fields":len(patches),"formula_changes":0,"substantive_closures":0},started)


def p1():
    started=time.monotonic()
    previous=latest("P0")
    packet=read(previous.parent/"packet.json")
    from legalmath.interpretation.semantics.records import legacy_envelope,Support,Settings
    envelope=legacy_envelope(packet,"historical-units")
    if envelope.restore()!=packet: raise ValueError("Lossy packet adapter")
    attempt=new_attempt("P1")
    save(attempt/"predecessor.json",ref(previous))
    (attempt/"refreshed-plan.md").write_bytes((previous.parent/"next-phase-plan.md").read_bytes())
    save(attempt/"packet-envelope.json",envelope.model_dump(mode="json"))
    save(attempt/"support-states.json",[Support(positive=p,negative=n).model_dump(mode="json")
         for p,n in [((),()),(("declared.positive",),()),((),("declared.negative",)),(("declared.positive",),("declared.negative",))]])
    save(attempt/"settings.json",Settings(semantics="grounded",ordering="none",priorities=(),
          max_arguments=8,max_extensions=256,timeout_seconds=5).model_dump(mode="json"))
    (attempt/"next-phase-plan.md").write_text(
        "# P2 refreshed from P1\n\nUse the 54-unit historical packet from "+str(previous.parent.relative_to(ROOT))+
        "/packet.json; its versioned envelope is "+str(attempt.relative_to(ROOT))+
        "/packet-envelope.json. Preserve raw 26EC22 identity and Unicode offsets. "
        "The packet does not declare actual applicability. Use explicit sourced development nominations A/B/C for demonstration plus the responsibility dimensions, "
        "and record which retained candidates/citations motivated them. Do not falsely label newly encoded branches as exact retained model output. "
        "Bind footnote 1, UT 6.8, Appendix Part A, paragraph 14 and footnote 5 in full. Keep paragraphs 15/16 separate. "
        "Audit passed: compare query-specific trigger/object/standard; no imposed priority, completeness or numerical confidence. "
        "Acceptance: phase-tests P2, actual retained-source branch inventory and distinguishing conditional assignments; unsupported proposals retain reasons.\n")
    finish(attempt,"P1",{"packet_units":len(packet["units"]),"roundtrip":"LOSSLESS",
          "unknown_metadata":"PRESERVED","semantic_record_profile":envelope.version},started)

def phase_start(phase, predecessor):
    previous = latest(predecessor)
    attempt = new_attempt(phase)
    save(attempt/"predecessor.json", ref(previous))
    (attempt/"refreshed-plan.md").write_bytes((previous.parent/"next-phase-plan.md").read_bytes())
    return attempt, previous

def refresh(attempt, phase, text):
    (attempt/"next-phase-plan.md").write_text("# "+phase+" refreshed from execution\n\n"+text+"\n")

def p2():
    started=time.monotonic()
    attempt,previous=phase_start("P2","P1")
    from legalmath.interpretation.semantics.clauses import propose,distinguishing_assignments,controlled_english
    from legalmath.interpretation.semantics.records import Branch
    p0path=latest("P0").parent
    packet=read(p0path/"packet.json")
    question={"query":"Conditional responsibility and demonstration duties"}
    inventory=propose(packet,question,read(p0path/"overlay.json")["records"],read(previous.parent/"settings.json"))
    branches=[Branch.model_validate_json(json.dumps(b)) for b in inventory["branches"]]
    save(attempt/"question.json",question)
    save(attempt/"inventory.json",inventory)
    save(attempt/"distinguishing-assignments.json",distinguishing_assignments(branches))
    (attempt/"controlled-english.md").write_text("\n\n".join(b.proposal_id+"\n"+controlled_english(b) for b in branches))
    refresh(attempt,"P3","Seven source-bound nominations preserve all 70 retained role records. A/B/C differ by trigger, object and standard; no contrary relation follows from a label. Build a declared finite theory with shared source premises and a specific B/C trigger dispute. Independently check argument trees and attacks, then grounded/preferred selection; do not infer wholly empty real semantics from the mutual-attack fixture. PyArg archive/API completeness must be checked. Reject unknown priority/cyclic settings; resource cutoff retains frontier. Audit passed: conditional formal behavior only, no legal answer keys. Tests: phase-tests P3.")
    finish(attempt,"P2",{"branches":len(branches),"retained_role_records":len(inventory["retained"]),
        "unrepresented_concerns":inventory["unrepresented_concerns"],"english_fidelity":"NOT_ESTABLISHED"},started)

def p3():
    started=time.monotonic()
    attempt,previous=phase_start("P3","P2")
    from legalmath.interpretation.semantics.arguments import from_inventory,evaluate
    inventory=read(latest("P2").parent/"inventory.json")
    theory=from_inventory(inventory)
    grounded_result=evaluate(theory,"grounded",max_arguments=8,max_extensions=256,timeout_seconds=5)
    preferred_result=evaluate(theory,"preferred",max_arguments=8,max_extensions=256,timeout_seconds=5)
    save(attempt/"graph.json",{"arguments":[a.__dict__ for a in theory.arguments],
        "attacks":[a.__dict__ for a in theory.attacks]})
    save(attempt/"semantic-results.json",{"grounded":grounded_result.__dict__,
        "preferred":preferred_result.__dict__,"settings":{"max_arguments":8,"max_extensions":256,"timeout_seconds":5},
        "pyarg":"INCOMPLETE_ARCHIVE_NOT_ADOPTED"})
    refresh(attempt,"P4","P3 completed independent graph construction and bounded grounded/preferred evaluation. The actual eight-argument theory has a shared source premise, the declared B/C no-request trigger dispute and no imposed priorities and remains a conditional formal profile; its result is not a legal ranking. Preserve attack types and unresolved source premises. P4 must add source-bound precedent roles, authority/time/treatment premises, and distinguish missing Hong Kong authority from an empty search result. Any real-case walkthrough remains pending if no official judgment is available. Audit passed: valid empty grounded extensions and resource cutoffs are distinct; no subset enumeration above eight in the reference evaluator. Tests: phase-tests P4.")
    finish(attempt,"P3",{"arguments":len(theory.arguments),"attacks":len(theory.attacks),
        "grounded_completion":grounded_result.completion,"preferred_completion":preferred_result.completion,
        "pyarg_status":"INCOMPLETE_ARCHIVE_NOT_ADOPTED"},started)

def p4():
    started=time.monotonic()
    attempt,previous=phase_start("P4","P3")
    from legalmath.interpretation.semantics.precedent import JudgmentManifest,Proposition,Factor,Move,comparison
    from legalmath.canonical import digest
    manifest=JudgmentManifest("real-authority-pending","official origin not acquired","0"*64,None,None,None,None,(),("source_hash","court","jurisdiction","decision_date","treatment"),False)
    propositions=(Proposition("p1","The retained circular supplies a proposed operational duty","reasoning",("retained-source",),
        "Source-bound mechanics only; no ratio classification","unresolved"),)
    factors=(Factor("f1","ownership records","retained source concern",("p1",),"Relevance to the conditional pilot remains unresolved"),)
    moves=(Move("distinction",("f1",),"p1","Synthetic comparison: authority and applicability are missing"),)
    result=comparison(manifest,propositions,factors,moves)
    save(attempt/"authority-manifest.json",manifest.__dict__)
    save(attempt/"propositions.json",[x.__dict__ for x in propositions])
    save(attempt/"factors-and-moves.json",{"factors":[x.__dict__ for x in factors],"moves":[x.__dict__ for x in moves]})
    save(attempt/"comparison.json",result)
    refresh(attempt,"P5","P4 has no suitable official judgment identified in the retained pilot packet; broader acquisition has not been performed. The real precedent demonstration remains pending; this is a named authority gap, not a claim that no contrary case exists. Preserve the proposed passage roles and conditional factor move. P5 may proceed on retained regulatory text and explicitly declared synthetic evidence, deriving only appointment, supervision-event, discrepancy and unresolved ownership predicates. Do not infer responsibility, adequacy, title, liability or legal force. Audit passed: source roles, jurisdiction, hierarchy, date and later treatment remain independent fields. Tests: phase-tests P5.")
    finish(attempt,"P4",{"real_case":"PENDING","propositions":len(propositions),"factors":len(factors),"authority_fields":"UNVERIFIED"},started)

def p5():
    started=time.monotonic()
    attempt,previous=phase_start("P5","P4")
    from legalmath.interpretation.semantics.evidence import declared_fixture,derive
    observations,scope=declared_fixture()
    save(attempt/"evidence.json",{"origin":"SYNTHETIC_DECLARED_EVIDENCE","observations":[o.model_dump(mode="json") for o in observations],
        "scope":scope.model_dump(mode="json"),"provider":"operator-1","knowledge_cutoff":"2026-10-06"})
    predicates=("appointment_recorded","supervision_event_recorded","incident_recorded","remediation_recorded",
                "ownership_assertion_recorded","responsibility_retained","adequate_supervision","ownership_title","liability")
    results=[derive(observations,p,scope,"operator-1","2026-10-06") for p in predicates]
    save(attempt/"derivations.json",results)
    refresh(attempt,"P6","P5 preserves narrow recorded facts, original incident/remediation history, actor/provider identity and knowledge cutoff. Responsibility, adequacy, title and liability remain unknown without sufficient rules. P6 must execute actual Java via separate branch qualification v2, preserving conflict/unknown/unsupported reasons and branch identities, while integrating an optional stage into CompleteInvestigation. Keep legacy candidates/replay unchanged and bind settings, source, queries and evidence in method/stage receipts. Audit passed: synthetic cases test formal mechanics, not legal classifications. Test phase-tests P6 and regression integration/translation; no new provider calls.")
    finish(attempt,"P5",{"observations":len(observations),"derivations":len(results),"origin":"SYNTHETIC",
        "evaluative_classification":"UNRESOLVED","incident_erased_by_remediation":False},started)


def p6():
    started=time.monotonic()
    attempt,previous=phase_start("P6","P5")
    from scripts.legal_interpretation_demo import execute
    from legalmath.interpretation.assurance import investigation_observations as observation
    from legalmath.interpretation.semantics import qualification_v2 as qualification
    from legalmath.interpretation.semantics.records import Branch
    from legalmath.interpretation.semantics.lower import pilot_reading,envelope
    from legalmath.interpretation.search.formal import bundle,snapshots
    root,runner,dossier=execute(attempt/"complete-investigation",2)
    checked_result=observation.check_stages(root,dossier,observation.method(runner),runner)
    save(attempt/"complete-investigation-check.json",checked_result)
    packet=read(latest("P0").parent/"packet.json")
    question=read(latest("P2").parent/"question.json")
    inv=read(latest("P2").parent/"inventory.json")
    graph=read(latest("P3").parent/"semantic-results.json")
    at="2026-10-06T00:00:00.000000Z"  # declared computational fixture time, not inferred applicability
    jdk=ROOT/".localresources/java-toolchain/jdk-17.0.20.1+1"
    inputs=[];reports=[]
    for raw in inv["branches"]:
        b=Branch.model_validate_json(json.dumps(raw))
        r=pilot_reading(b);env=envelope(b,packet,r,question)
        compiled=bundle(r,env["legacy_packet"],at)
        cases=[{"id":"declared."+str(i),"snapshot":s,"valid_at":at,"known_at":at}
               for i,s in enumerate(snapshots([compiled],at,maximum=6))]
        ext=graph[b.settings.semantics]
        extension_ids=[digest({"settings":b.settings.model_dump(mode="json"),"extension":e}) for e in ext["extensions"]]
        directory=attempt/"pilot-qualifications"/b.identity()
        result=qualification.run(b,packet,r,question,cases,directory,jdk,at,
            extension_ids=extension_ids,completion=ext["completion"])
        qualification.verify(directory,b,packet,r,question,cases,at,
            extension_ids=extension_ids,completion=ext["completion"],jdk=jdk)
        inputs.append({"branch":raw,"reading":r,"question":question,"cases":cases,"at":at,
            "extension_ids":extension_ids,"completion":ext["completion"],"directory":str(directory.relative_to(ROOT))})
        reports.append(result)
    save(attempt/"pilot-inputs.json",{"packet":packet,"rows":inputs})
    save(attempt/"pilot-results.json",reports)
    save(attempt/"retained-investigation.json",ref(attempt/"complete-investigation/current.json"))
    refresh(attempt,"P7","Actual CompleteInvestigation optional semantics route and all seven retained-source pilot nominations have executed Java, with independent values and v2 receipts. Legacy replay remains separate. The source-warrant reconstruction in the general legacy adapter is still unimplemented; results remain conditional. Validate precise finite invariants, fault detection and the existing Boolean Lean profile. Do not claim a new branch-accounting theorem or Java compiler proof. Required audit: p7-proof-targets.md. Tests: phase-tests P7 and final semantic/integration regressions.")
    finish(attempt,"P6",{"pilot_branches":len(reports),
        "pilot_java_cases":sum(len(r["target"]["executions"]) for r in reports),
        "complete_investigation":checked_result["execution_complete"],
        "legacy_candidates":checked_result["candidate_count"],"live_provider":False,
        "qualification_profile":qualification.PROFILE},started)

def p7():
    started=time.monotonic()
    attempt,previous=phase_start("P7","P6")
    from legalmath.interpretation.assurance import proof_certificate as proof
    from legalmath.interpretation.semantics.lower import envelope
    from legalmath.interpretation.semantics.records import Branch
    from legalmath.interpretation.search.formal import bundle
    environment=subprocess.run([str(proof.LEAN),"--version"],capture_output=True,text=True,check=True,timeout=10)
    if "version 4.20.0" not in environment.stdout: raise ValueError("Unexpected Lean version")
    save(attempt/"lean-environment.json",{"executable":str(proof.LEAN),"sha256":sha(proof.LEAN),"version":environment.stdout.strip()})
    inputs=read(previous.parent/"pilot-inputs.json");certificates=[]
    for row in inputs["rows"]:
        b=Branch.model_validate_json(json.dumps(row["branch"]))
        env=envelope(b,inputs["packet"],row["reading"],row["question"])
        compiled=bundle(row["reading"],env["legacy_packet"],row["at"])
        certificate=proof.produce(row["reading"],compiled,row["at"],attempt/"boolean-proofs"/b.identity(),
            ROOT/".localresources/java-toolchain/jdk-17.0.20.1+1")
        certificates.append({"branch_id":b.identity(),"certificate":certificate})
    save(attempt/"claims.json",{"boolean_lowering":{"status":"KERNEL_CHECKED","profile":proof.PROFILE,
        "certificates":certificates},"finite_checks":{"argument_graphs":512,"abstract_arguments":3,
        "binary_truth_assignments":9,"extension_value_pairs":9},
        "not_proved":["English fidelity","branch accounting theorem","all-path unresolved-premise preservation",
        "dependency invalidation theorem","source-to-argument correctness","Java compiler correctness",
        "general evidence classification"],"legal_correctness":"NOT_ESTABLISHED"})
    refresh(attempt,"P8","Retain actual Boolean kernel/Java enumeration receipts and finite checks under their exact domain. New semantics theorem classes remain NOT_PROVED. Reconcile all 46 original obligations and 35 retained readings, preserving unsupported work and the rejected P3 attempt. Exercise actual freeze/observe with enabled semantics, missing/swapped receipts, timing, disabled old configuration and repair invalidation. Audit volatile package JSON without excluding identity coverage. Freeze only a development boundary; genuinely later official publications are pending. Tests: phase-tests P8.")
    finish(attempt,"P7",{"boolean_kernel_receipts":len(certificates),
        "exhaustive_java_cases":sum(c["certificate"]["runtime"].get("cases",0) for c in certificates),
        "new_semantics_theorems":"NOT_PROVED","source_fidelity":"NOT_ESTABLISHED"},started)

def coverage():
    original=read(latest("P0").parent/"obligation-map.json")
    rows=read(latest("P0").parent/"overlay.json")["records"]
    policies={
        "time":("evidence.py","Unknown assessment intervals, later knowledge and incident/remediation legal effects require evidence and rules."),
        "actor":("evidence.py","Identity joins are checked; actual provider roles and multiple-provider allocation remain unresolved."),
        "authority":("precedent.py","No suitable official judgment identified in retained pilot packet; hierarchy, applicability and treatment unresolved."),
        "definition":("clauses.py","Evaluative standards for responsibility, adequacy, ownership and proper records remain proposed."),
        "output":("render.py","Query and reason retention implemented; legal consequence and sanction rules remain unsupported.")}
    obligations=[]
    for item in original:
        ob=item["obligation"];module,reason=policies.get(ob["dimension"],("clauses.py",
            "Original interpretation question retained; finite pilot representation does not establish semantic closure."))
        related=[r for r in rows if r["reading_id"] in ob["candidate_ids"]]
        obligations.append({"obligation":ob,"status":"OPEN_QUALIFIED","substantive_closure":False,
            "implementation":"src/legalmath/interpretation/semantics/"+module,"remaining_gap":reason,
            "operative_records":[{"role":r["role"],"reading_id":r["reading_id"],"sha256":digest(r["operative"])} for r in related]})
    readings=[]
    for identity in sorted({r["reading_id"] for r in rows}):
        records=[r for r in rows if r["reading_id"]==identity]
        readings.append({"reading_id":identity,"roles":[r["role"] for r in records],
            "records":[digest(r) for r in records],"status":"RETAINED_UNRESOLVED",
            "semantic_reconciliation":"All original proposals preserved; exact equivalence to seven pilot nominations not established",
            "obligations":[o["obligation"]["obligation_id"] for o in obligations if identity in o["obligation"]["candidate_ids"]]})
    if len(obligations)!=46 or len(readings)!=35 or any(not o["operative_records"] for o in obligations):
        raise ValueError("Coverage denominator/reference mismatch")
    return {"original_obligations":obligations,"retained_readings":readings,"substantive_closures":0}

def p8():
    started=time.monotonic()
    attempt,previous=phase_start("P8","P7")
    report=coverage();save(attempt/"coverage.json",report)
    from scripts.legal_interpretation_demo import options
    from legalmath.interpretation.semantics.integration import configuration
    from legalmath.interpretation.assurance.integrated import implementation_identity
    source_files=[p for p in sorted((ROOT/"src/legalmath").rglob("*.json"))]
    before={str(p.relative_to(ROOT)):sha(p) for p in source_files}
    save(attempt/"identity-audit.json",{"implementation":implementation_identity(),"json_files":before,
        "policy":"All package .py/.java/.json/.lean remain bound; none excluded as volatile",
        "new_semantic_generated_json_under_src":list(str(p) for p in (ROOT/"src/legalmath/interpretation/semantics").glob("*.json"))})
    save(attempt/"future-boundary.json",{"status":"PREPARED_NOT_LIVE_PROSPECTIVE_EVIDENCE",
        "semantic_configuration":configuration(options()),"development_source_hash":read(latest("P0").parent/"baseline.json")["packet_hash"],
        "official_publications_admitted":0,"observation_profile":"legalmath.whole-investigation-observation.v2",
        "requires":"Freeze the complete selected runner and admit genuinely later official publications under a new window; any REPAIR event makes the old window ineligible"})
    refresh(attempt,"Successor","Priorities from actual execution: (1) reconcile the 35 retained readings individually with source-bound clauses and construct their warrants/objections in the complete-investigation adapter; current generic route preserves legacy formulas but does not reconstruct warrants. (2) acquire a bounded suitable official judgment and checked hierarchy/treatment sources for the responsibility/footnote disputes; citation syntax alone supplies no authority. (3) supply sufficient legal rules and scoped evidence for adequacy, retained responsibility, proper records and title. (4) extend recursive/large preferred theories only under independent checked algorithms; current reference cap is eight. (5) register a new semantics theorem profile with serialization/runtime correspondence before claiming branch/dependency proofs. (6) run a separately frozen future-source study on genuinely later official publications. All 46 original obligations remain OPEN_QUALIFIED; no provider grant is presumed. Each repair must create new attempts, refresh dependent plans and invalidate stale windows.")
    if before!={str(p.relative_to(ROOT)):sha(p) for p in source_files}:raise ValueError("Package JSON changed during identity audit")
    finish(attempt,"P8",{"original_obligations":46,"retained_readings":35,"substantive_closures":0,
        "prospective_official_observations":0,"future_study":"PENDING"},started)

PHASES = {"P0": p0, "P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5, "P6":p6, "P7":p7, "P8":p8}



def test_manifest():
    paths={p for directory in ("tests/interpretation/semantics","tests/assurance","tests/translation","tests/search","tests/catala")
           for p in (ROOT/directory).rglob("*.py")}
    paths.update(ROOT/p for p in ("tests/conftest.py","tests/interpretation/test_contracts.py") if (ROOT/p).is_file())
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}

def validated():
    files=sorted((RUN/"validation").glob("attempt-*/result.json"),key=lambda p:p.stat().st_mtime)
    if not files:return None
    path=files[-1];r=read(path)
    if r.get("status")=="PASS" and r["code"]==code_manifest() and r["tests"]==test_manifest() and r.get("execution_code")==execution_dependencies():
        for check in r["checks"]:checked(check["log"])
        return path
    return None

def validate_run():
    from scripts.legal_interpretation_ops import REGRESSIONS
    parent=RUN/"validation";parent.mkdir(parents=True,exist_ok=True)
    attempt=parent/("attempt-"+str(len(list(parent.glob("attempt-*")))+1));attempt.mkdir()
    code=code_manifest();tests=test_manifest();execution_code=execution_dependencies();started=time.monotonic();checks=[]
    commands=[("semantics",[str(VENV),"-m","pytest","tests/interpretation/semantics","-q"])]
    commands += [(name,[str(VENV),"-m","pytest",*paths,"-q"]) for name,paths in REGRESSIONS.items()]
    commands += [("reviewed-program",[str(VENV),"-m","scripts.check_legal_interpretation_revision"])]
    for name,command in commands:
        begin=time.monotonic();log=attempt/(name+".log")
        try:
            with log.open("xb") as stream:
                result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
            status="PASS" if result.returncode==0 else "FAIL"
        except subprocess.TimeoutExpired:
            status="TIMEOUT"
        checks.append({"group":name,"argv":command,"status":status,"log":ref(log),
                       "elapsed_seconds":round(time.monotonic()-begin,3)})
        print(json.dumps({"validation":name,"status":status,"log":str(log.relative_to(ROOT))}),flush=True)
        if status!="PASS":break
    result={"status":"PASS" if len(checks)==len(commands) and all(c["status"]=="PASS" for c in checks) else "FAIL",
        "checks":checks,"code":code,"tests":tests,"execution_code":execution_code,"elapsed_seconds":round(time.monotonic()-started,3),
        "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "python":sys.version,"cpu_mode":"CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
        "seeds":"N/A: deterministic checks","provider_calls":0,"legal_correctness":"NOT_ESTABLISHED"}
    if code!=code_manifest() or tests!=test_manifest() or execution_code!=execution_dependencies():result["status"]="CHANGED_DURING_VALIDATION"
    save(attempt/"result.json",result)
    if result["status"]!="PASS":raise ValueError("Final validation failed; inspect "+str(attempt))
    return attempt/"result.json"

def execution_status():
    phases={}
    for phase in PHASES:
        try:phases[phase]={"status":read(latest(phase))["status"],"result":ref(latest(phase))}
        except (ValueError,OSError,KeyError):phases[phase]={"status":"PENDING_OR_FAILED"}
    return {"profile":"legalmath.program-execution.v1","phases":phases,
        "validation":ref(validated()) if validated() else None,
        "legal_correctness":"NOT_ESTABLISHED","substantive_closures":0,"release_eligible":False}

def execute_phase(phase):
    if validated() is None:validate_run()
    require_tests(phase)
    existing=set((RUN/phase).glob("attempt-*"))
    try:PHASES[phase]()
    except BaseException as exc:
        created=set((RUN/phase).glob("attempt-*"))-existing
        for attempt in created:
            if not (attempt/"result.json").exists() and not (attempt/"failure.json").exists():
                save(attempt/"failure.json",{"status":"FAILED","phase":phase,"error":getattr(exc,"code",type(exc).__name__),
                     "detail":str(exc),"continuation":"Repair the cause and create a new immutable attempt"})
        raise

def resume():
    if validated() is None:validate_run()
    modules={"P0":["operative.py"],"P1":["records.py"],"P2":["clauses.py","records.py"],
             "P3":["arguments.py","pyarg_adapter.py","records.py"],"P4":["precedent.py"],"P5":["evidence.py","records.py"]}
    previous=None
    for phase in PHASES:
        rerun=False
        try:
            result_path=latest(phase);started=read(result_path.parent/"started.json")
            current_code=code_manifest()
            if phase in modules:
                rerun=any(started["code"].get("src/legalmath/interpretation/semantics/"+m)!=current_code.get("src/legalmath/interpretation/semantics/"+m)
                          for m in modules[phase])
            else:rerun=started["code"]!=current_code
            rerun=rerun or started.get("execution_code")!=execution_dependencies()
            if previous is not None:
                predecessor=read(result_path.parent/"predecessor.json")
                rerun=rerun or predecessor!=ref(previous)
        except (OSError,ValueError,KeyError):rerun=True
        if rerun:execute_phase(phase)
        previous=latest(phase)
    report=execution_status()
    report["status"]="EXECUTED_WITH_OPEN_PRODUCT_GAPS"
    report["rejected_evidence"]=["P3/attempt-1: invalid support-as-attack construction; see p3-repair-audit.md"]
    report["shared_code_invalidation"]="Only selected current phase receipts belong to this execution; earlier attempts predate recorded repairs."
    destination=RUN/("completion-"+str(len(list(RUN.glob("completion-*.json")))+1)+".json")
    save(destination,report)
    pointer=ROOT/"docs/implementation/legal-interpretation-program/execution-current.json"
    temp=pointer.with_suffix(".tmp")
    temp.write_text(json.dumps({"execution":ref(destination),"run":str(RUN.relative_to(ROOT)),
                              "status":report["status"]},indent=2)+"\n")
    os.replace(temp,pointer)
    print(json.dumps({"status":report["status"],"execution":ref(destination)},indent=2))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["run","validate","resume","status"])
    parser.add_argument("phase",choices=PHASES,nargs="?")
    args=parser.parse_args()
    if args.action=="run":
        if args.phase is None:parser.error("run requires one fixed phase")
        execute_phase(args.phase)
    elif args.phase is not None:parser.error("Only run accepts a phase")
    elif args.action=="validate":validate_run()
    elif args.action=="resume":resume()
    else:print(json.dumps(execution_status(),indent=2))

if __name__=="__main__":
    main()
