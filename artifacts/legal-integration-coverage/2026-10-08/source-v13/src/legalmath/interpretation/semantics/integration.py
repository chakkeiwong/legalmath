"""Optional CompleteInvestigation semantic stage, separate from legacy candidates."""
import json
import time
from pathlib import Path
from ...canonical import canonical,digest,loads
from ...errors import LegalMathError
from ..search.formal import bundle,snapshots
from .records import Settings,Branch,Outcome,Premise
from .lower import from_legacy,legacy_packet
from .sourced import context as source_context,check_context,evaluate_sourced
from .reconciliation import validate_entry,enrich
from . import qualification_v2 as qualification
from .render import render,decision_set

PROFILE="legalmath.semantic-investigation.v2"
SCOPED_PROFILE="legalmath.semantic-investigation.v3"
CONTEXT_PROFILE="legalmath.semantic-context.v3"
CONDITIONAL_PROFILE="legalmath.semantic-investigation.v4"
CONDITIONAL_CONTEXT="legalmath.semantic-context.v4"
SCOPED_PROFILES=(SCOPED_PROFILE,CONDITIONAL_PROFILE)


def investigation_context(options,criticism,standards_input=None):
    """Build the same data envelope during execution and both verification routes."""
    if options and options.get("profile") in SCOPED_PROFILES:
        profile=CONDITIONAL_CONTEXT if options["profile"]==CONDITIONAL_PROFILE else CONTEXT_PROFILE
        return context_for(options,{"profile":profile,"source":source_context(criticism),
                                    "standards":standards_input})
    if standards_input is not None:
        raise LegalMathError("E_SCHEMA",details="Standards input requires semantic v3 or v4")
    return source_context(criticism)

def context_for(options,value):
    if options and options.get("profile") in SCOPED_PROFILES:
        from .scoped_standards import parse
        profile=CONDITIONAL_CONTEXT if options["profile"]==CONDITIONAL_PROFILE else CONTEXT_PROFILE
        if not isinstance(value,dict) or set(value)!={"profile","source","standards"} or value["profile"]!=profile:
            raise LegalMathError("E_SCHEMA",details="Scoped semantics requires its versioned context")
        return {"profile":profile,"source":check_context(value["source"]),
                "standards":parse(value["standards"]).model_dump(mode="json")}
    return check_context(value)

def source_part(context):
    return context["source"] if context and context.get("profile") in (CONTEXT_PROFILE,CONDITIONAL_CONTEXT) else context

def configuration(options):
    if options is None: return None
    if not isinstance(options,dict) or set(options)!={"profile","settings","case_limit"} or options["profile"] not in (PROFILE,*SCOPED_PROFILES):
        raise LegalMathError("E_SCHEMA",details="Unknown semantics configuration")
    if not isinstance(options["settings"],list) or not 1<=len(options["settings"])<=64:
        raise LegalMathError("E_RESOURCE_LIMIT")
    settings=[Settings.model_validate_json(json.dumps(s)) for s in options["settings"]]
    if len({s.identity() for s in settings})!=len(settings): raise LegalMathError("E_REFERENCE",details="Duplicate settings")
    if any(s.priorities for s in settings):
        raise LegalMathError("E_UNSUPPORTED_PROFILE",details="Source reasoning does not establish priorities; use an explicit structured theory")
    if type(options["case_limit"]) is not int or not 1<=options["case_limit"]<=4: raise LegalMathError("E_RESOURCE_LIMIT")
    extra={}
    if options["profile"]==CONDITIONAL_PROFILE:
        from . import conditional_runtime
        extra={"conditional_runtime":{"profile":conditional_runtime.PROFILE,"method":conditional_runtime.method(),
            "lean_sha256":conditional_runtime.raw_digest(conditional_runtime.LEAN.read_bytes())}}
    return {"profile":options["profile"],"records":"legalmath.semantic-records.v1",
        "adapter":("source-bound-warrants-and-typed-criticism.v1" if options["profile"]==PROFILE else "scoped-standards-and-typed-criticism.v1"),
        "evaluator":"local-finite-acyclic.v1","settings":[s.model_dump(mode="json") for s in settings],
        "case_limit":options["case_limit"],"implementation":digest(qualification.methods()),**extra}

def inventory(packet,candidates,questions,options,at,context=None):
    config=configuration(options);rows=[]
    context=context_for(options,context)
    reconciliation=source_part(context)["reconciliation"]
    if reconciliation is not None and (
            reconciliation["packet_hash"]!=digest(packet) or
            reconciliation["questions_hash"]!=digest(questions) or
            set(reconciliation["entries"])!=set(candidates)):
        raise LegalMathError("E_REFERENCE",details="Reconciliation input changed")
    if set(questions)!=set(candidates) or not candidates: raise LegalMathError("E_REFERENCE")
    if len(candidates)*len(config["settings"])>64: raise LegalMathError("E_RESOURCE_LIMIT",details="No semantic branches silently dropped")
    for cid,reading in sorted(candidates.items()):
        for raw in config["settings"]:
            branch=from_legacy(packet,reading,questions[cid],Settings.model_validate_json(json.dumps(raw)))
            entry=validate_entry(reconciliation["entries"][cid],packet,cid,reading,questions[cid]) if reconciliation else None
            branch=enrich(branch,reading,entry)
            branch=branch.model_copy(update={"proposal_id":cid,
                "assumptions":branch.assumptions+(Premise(id="reasoning-context",
                    statement="Argument evaluation is conditional on the retained source context",
                    status="declared",dependencies=(digest(context),)),)})
            try:
                b=bundle(reading,legacy_packet(packet,reading),at)
                cases=[{"id":"declared."+str(i),"snapshot":s,"valid_at":at,"known_at":at}
                       for i,s in enumerate(snapshots([b],at,maximum=config["case_limit"]))]
            except LegalMathError as exc:
                if exc.code not in ("E_UNSUPPORTED_PROFILE","E_SCHEMA"): raise
                cases=[{"id":"unsupported","snapshot":{"subject_id":"unresolved","facts":{}},"valid_at":at,"known_at":at}]
            rows.append({"candidate_id":cid,"branch":branch.model_dump(mode="json"),"cases":cases})
    if len({digest(r["branch"]) for r in rows})!=len(rows): raise LegalMathError("E_REFERENCE")
    return rows

def reasoning(rows,packet,candidates,questions,context=None):
    groups={}
    for row in rows:
        branch=Branch.model_validate_json(canonical(row["branch"]))
        groups.setdefault(branch.settings.identity(),{})[row["candidate_id"]]=branch
    return {key:evaluate_sourced(packet,candidates,questions,branches,source_part(context),next(iter(branches.values())).settings)
            for key,branches in groups.items()}

def decisions(rows,reports):
    groups={}
    for row,report in zip(rows,reports):
        b=Branch.model_validate_json(canonical(row["branch"]))
        for outcome in report["outcomes"]:
            o=Outcome.model_validate_json(canonical(outcome))
            groups.setdefault(o.query_id,[]).append((b,o))
    return {q:decision_set([b for b,o in items],[o for b,o in items],[b.identity() for b,o in items])
            for q,items in sorted(groups.items())}

def run(packet,candidates,questions,options,directory,jdk,at,*,context=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    context=context_for(options,context)
    inputs={"packet":packet,"candidates":candidates,"questions":questions,"options":options,"at":at,"context":context}
    config=configuration(options);rows=inventory(packet,candidates,questions,options,at,context)
    graph=reasoning(rows,packet,candidates,questions,context);started_ms=time.time_ns()//1000000
    qualification.write(directory/"inputs.json",inputs)
    qualification.write(directory/"branches.json",rows)
    reports=[]
    for row in rows:
        b=Branch.model_validate_json(canonical(row["branch"]));g=graph[b.settings.identity()]
        report=qualification.run(b,packet,candidates[row["candidate_id"]],questions[row["candidate_id"]],row["cases"],
            directory/"branches"/b.identity(),jdk,at,extension_ids=g["candidate_membership"][row["candidate_id"]]["extension_ids"],completion=g["evaluation"]["completion"])
        reports.append(report)
    scoped={}
    if config["profile"] in SCOPED_PROFILES:
        from .scoped_standards import compute
        scoped={"standards":compute(context["standards"],packet,candidates,questions,rows)}
    if config["profile"]==CONDITIONAL_PROFILE:
        from . import conditional_ir,conditional_runtime
        program,mapping=conditional_ir.lower(scoped["standards"])
        runtime=conditional_runtime.run(program,directory/"conditional-runtime",jdk)
        scoped["conditional_runtime"]={"lowering":mapping,**conditional_runtime.attach(scoped["standards"],runtime)}
    result={"profile":config["profile"],"configuration":config,"inputs_hash":digest(inputs),"inventory_hash":digest(rows),
        "started_ms":started_ms,"finished_ms":time.time_ns()//1000000,"reasoning":graph,
        "branch_reports":reports,"decisions":decisions(rows,reports),
        "explanations":[render(Branch.model_validate_json(canonical(row["branch"])),Outcome.model_validate_json(canonical(o)))
                        for row,report in zip(rows,reports) for o in report["outcomes"]],
        "execution_complete":all(g["evaluation"]["completion"]=="complete" for g in graph.values()),
        "legal_correctness":"NOT_ESTABLISHED","release_eligible":False,**scoped}
    # Normalize tuples before retaining/recomparing JSON.
    result=loads(canonical(result))
    qualification.write(directory/"result.json",result)
    return result

def verify(directory,packet,candidates,questions,options,at,*,jdk=None,target=None,context=None):
    directory=Path(directory)
    result=loads((directory/"result.json").read_bytes())
    config=configuration(options)
    if result["configuration"]!=config: raise LegalMathError("E_STALE_REVIEW")
    context=context_for(options,context)
    inputs={"packet":packet,"candidates":candidates,"questions":questions,"options":options,"at":at,"context":context}
    rows=inventory(packet,candidates,questions,options,at,context)
    graph=reasoning(rows,packet,candidates,questions,context)
    if loads((directory/"inputs.json").read_bytes())!=inputs or result["inputs_hash"]!=digest(inputs):
        raise LegalMathError("E_REFERENCE")
    if loads((directory/"branches.json").read_bytes())!=rows or result["inventory_hash"]!=digest(rows):
        raise LegalMathError("E_REFERENCE")
    if len(result["branch_reports"])!=len(rows): raise LegalMathError("E_REFERENCE")
    reports=[]
    for row,record in zip(rows,result["branch_reports"]):
        b=Branch.model_validate_json(canonical(row["branch"]));g=graph[b.settings.identity()]
        report=qualification.verify(directory/"branches"/b.identity(),b,packet,candidates[row["candidate_id"]],
            questions[row["candidate_id"]],row["cases"],at,extension_ids=g["candidate_membership"][row["candidate_id"]]["extension_ids"],completion=g["evaluation"]["completion"],
            jdk=jdk,target=target)
        if record!=report: raise LegalMathError("E_REFERENCE",details="Missing/swapped branch receipt")
        reports.append(report)
    scoped={}
    if config["profile"] in SCOPED_PROFILES:
        from .scoped_standards import compute
        scoped={"standards":compute(context["standards"],packet,candidates,questions,rows)}
    elif "standards" in result:
        raise LegalMathError("E_SCHEMA",details="v2 cannot carry scoped standards")
    if config["profile"]==CONDITIONAL_PROFILE:
        from . import conditional_ir,conditional_runtime
        program,mapping=conditional_ir.lower(scoped["standards"])
        runtime=conditional_runtime.verify(program,directory/"conditional-runtime",jdk=jdk,target=target)
        scoped["conditional_runtime"]={"lowering":mapping,**conditional_runtime.attach(scoped["standards"],runtime)}
    elif "conditional_runtime" in result:
        raise LegalMathError("E_SCHEMA",details="Conditional runtime requires v4")
    expected={"profile":config["profile"],"reasoning":graph,"decisions":decisions(rows,reports),
        "explanations":[render(Branch.model_validate_json(canonical(row["branch"])),Outcome.model_validate_json(canonical(o)))
                        for row,report in zip(rows,reports) for o in report["outcomes"]],
        "execution_complete":all(g["evaluation"]["completion"]=="complete" for g in graph.values()),
        "legal_correctness":"NOT_ESTABLISHED","release_eligible":False,**scoped}
    if config["profile"]==CONDITIONAL_PROFILE and set(result)!=set(expected)|{"configuration","inputs_hash","inventory_hash","started_ms","finished_ms","branch_reports"}:
        raise LegalMathError("E_SCHEMA",details="Unexpected/missing v4 result fields")
    if any(result.get(k)!=v for k,v in loads(canonical(expected)).items()): raise LegalMathError("E_INTEGRITY")
    if type(result["started_ms"]) is not int or type(result["finished_ms"]) is not int or result["finished_ms"]<result["started_ms"]:
        raise LegalMathError("E_INTEGRITY")
    return result
