"""Conditional Boolean lowering; source meaning stays in the semantic envelope."""
from copy import deepcopy
import re
from .records import Branch,Clause,Premise,Scope,Interval,SourceSpan,Outcome,Support
from ...canonical import digest
from ...errors import LegalMathError
from ..contracts import Packet,parse
from ..search.models import Reading

def legacy_packet(packet,reading=None):
    if "source_key" in packet:
        return parse(Packet,packet)
    selected={c["unit_id"] for c in reading["citations"]} if reading else {u["unit_id"] for u in packet["units"]}
    if reading and reading.get("formalization"):
        selected.update(i for f in reading["formalization"]["facts"] for i in f["source_unit_ids"])
    units=[u for u in packet["units"] if u["unit_id"] in selected]
    if any(len(u["text"])>20000 for u in units):
        raise LegalMathError("E_UNSUPPORTED_PROFILE",details="Referenced historical unit exceeds legacy text bound")
    return parse(Packet,{"source_key":"semantic.retained","authority":"RETAINED_SOURCE",
        "selected_slice":"Conditional projection; complete original packet retained in semantic envelope",
        "units":[{"unit_id":u["unit_id"],"text":u["text"],"locator":u["unit_id"],"normative":False,"span":None} for u in units],
        "dependencies":[{"dependency_id":u["unit_id"],"source_hash":digest(u)} for u in packet["units"] if u["unit_id"] not in selected],
        "family_ids":["scope"]})

def from_legacy(packet,reading,question,settings):
    parse(Reading,reading)
    sources=[]
    for cite in reading["citations"]:
        unit=next(u for u in packet["units"] if u["unit_id"]==cite["unit_id"])
        start=unit["text"].find(cite["quote"])
        if start<0 or unit["text"].count(cite["quote"])!=1: raise LegalMathError("E_REFERENCE")
        sources.append(SourceSpan(source_hash=digest(packet),edition="retained packet; applicability unresolved",
            unit_id=unit["unit_id"],unit_hash=digest(unit["text"]),locator=unit.get("locator",unit["unit_id"]),
            start=start,end=start+len(cite["quote"]),quote=cite["quote"],request_hash=digest(question),role="unknown"))
    p=Premise(id="meaning",statement="Legacy formula and question are proposed interpretations",status="unresolved",dependencies=())
    f=reading["formalization"]
    c=Clause(id="formal",actor=question["actor"],action="evaluate declared formal proposal",modality="UNCERTAIN",
        trigger=f["scope"] if f else "unsupported",object=f["result"] if f else reading["subject"],
        standard="Meaning and evaluative predicates remain proposed",scope=Scope(actor=question["actor"],
        activity=None,product=None,component=None,interval=Interval(start=None,end=None)),
        sources=tuple(sources),relations=(),assumptions=(),warrant=reading["distinction"])
    return Branch(proposal_id=reading["local_id"],source_hash=digest(packet),question_hash=digest(question),
        legacy_reading_hash=digest(reading),clauses=(c,),settings=settings,assumptions=(),
        origin="retained-proposal",unresolved=(p,))

def pilot_reading(branch):
    cites={(s.unit_id,s.quote) for c in branch.clauses for s in c.sources}
    if branch.proposal_id.startswith("demonstration."):
        c=next(c for c in branch.clauses if c.id=="demonstration")
        names=["in_scope","sfc_request"]; expression="sfc_request" if c.trigger=="sfc_request" else "true"
        subject="Conditional demonstration trigger; object and standard remain separate"
    elif branch.proposal_id.startswith("responsibility."):
        names=["in_scope"]+[c.id for c in branch.clauses]
        expression=names[1] if len(names)==2 else "(and "+" ".join(names[1:])+")"
        subject="Conditional responsibility reading; evaluative values are declared inputs"
    else: raise LegalMathError("E_UNSUPPORTED_PROFILE")
    return parse(Reading,{"local_id":"semantic."+digest(branch.proposal_id)[:12],"family":"scope","subject":subject,
        "statement":subject,"distinction":"A formal conditional nomination, not established legal meaning",
        "citations":[{"unit_id":u,"quote":q} for u,q in sorted(cites)],
        "assumptions":[p.statement for p in branch.assumptions],
        "questions":[p.statement for p in branch.unresolved],
        "formalization":{"facts":[{"name":n,"type":"bool","meaning":"Declared "+n+" for one assessment",
           "unit":"conditional Boolean input","source_unit_ids":sorted({u for u,q in cites}),"requires_judgment":True} for n in names],
           "scope":"in_scope","result":expression,"result_type":"bool"}})

def expression(text,names):
    tokens=re.findall(r"\(|\)|[^\s()]+",text); index=0
    def go(depth=0):
        nonlocal index
        if index>=len(tokens) or depth>64: raise LegalMathError("E_UNSUPPORTED_PROFILE")
        token=tokens[index]; index+=1
        if token!="(":
            if token not in names|{"true","false"}: raise LegalMathError("E_UNSUPPORTED_PROFILE")
            return token
        if index>=len(tokens): raise LegalMathError("E_UNSUPPORTED_PROFILE")
        op=tokens[index];index+=1;args=[]
        while index<len(tokens) and tokens[index]!=")": args.append(go(depth+1))
        if index>=len(tokens): raise LegalMathError("E_UNSUPPORTED_PROFILE")
        index+=1
        if not ((op=="not" and len(args)==1) or (op=="if" and len(args)==3) or (op in ("and","or") and args)):
            raise LegalMathError("E_UNSUPPORTED_PROFILE")
        return (op,*args)
    tree=go()
    if index!=len(tokens): raise LegalMathError("E_UNSUPPORTED_PROFILE")
    return tree

def boolean(tree,values):
    if isinstance(tree,str): return {"true":"true","false":"false"}.get(tree,values.get(tree,"unknown"))
    op,*args=tree
    if op=="if":
        condition=boolean(args[0],values)
        return boolean(args[1 if condition=="true" else 2],values) if condition in ("true","false") else condition
    vals=[boolean(a,values) for a in args]
    if "conflict" in vals: return "conflict"
    if op=="not": return {"true":"false","false":"true","unknown":"unknown"}[vals[0]]
    if op=="and": return "false" if "false" in vals else "unknown" if "unknown" in vals else "true"
    return "true" if "true" in vals else "unknown" if "unknown" in vals else "false"

def reference(branch,reading,case,extension_ids=(),completion="complete"):
    reasons={"unknown-interpretation"}  # formal readings and pilot nominations are proposals
    formal=reading.get("formalization")
    witnesses=[p.id for p in (*branch.assumptions,*branch.unresolved)]
    lowering="supported";value="unknown"
    facts=case["snapshot"]["facts"]
    states={}
    for name,f in facts.items():
        status=f.get("status")
        if status=="conflict":
            states[name]="conflict";reasons.add("conflicting-evidence")
        elif (status=="known" and type(f.get("value")) is bool and f.get("complete",True) is True
              and f.get("valid_from") is not None and f.get("recorded_at") is not None
              and f["valid_from"]<=case["valid_at"] and (f.get("valid_until") is None or case["valid_at"]<f["valid_until"])
              and f["recorded_at"]<=case["known_at"]):
            states[name]=str(f["value"]).lower()
        else: states[name]="unknown";reasons.add("unknown-fact")
    try:
        if not formal or formal["result_type"]!="bool" or any(f["type"]!="bool" for f in formal["facts"]):
            raise LegalMathError("E_UNSUPPORTED_PROFILE")
        names={f["name"] for f in formal["facts"]}
        if set(facts)!=names: raise LegalMathError("E_REFERENCE")
        scope=boolean(expression(formal["scope"],names),states)
        result=boolean(expression(formal["result"],names),states)
        if scope=="false": value="out-of-scope"
        elif scope=="true": value=result
        else:
            value=scope
            reasons.add("unknown-applicability")
        if "conflicting-evidence" in reasons: lowering="unsupported"
    except LegalMathError as exc:
        if exc.code!="E_UNSUPPORTED_PROFILE": raise
        lowering="unsupported"
    if lowering=="unsupported": reasons.add("unsupported-lowering")
    if completion!="complete": reasons.add("unfinished")
    return Outcome(query_id=digest({"question":branch.question_hash,"case":case["id"]}),branch_id=branch.identity(),
        extension_ids=tuple(extension_ids),value=value,completion=completion,lowering=lowering,
        reasons=tuple(sorted(reasons)),witnesses=tuple(sorted(set(witnesses))))

def envelope(branch,packet,reading,question):
    if branch.source_hash!=digest(packet) or branch.question_hash!=digest(question):
        raise LegalMathError("E_REFERENCE")
    if branch.legacy_reading_hash is not None and branch.legacy_reading_hash!=digest(reading):
        raise LegalMathError("E_REFERENCE")
    units={u["unit_id"]:u["text"] for u in packet["units"]}
    for c in branch.clauses:
        for s in c.sources: s.verify(units[s.unit_id],branch.source_hash,branch.question_hash)
    if branch.legacy_reading_hash is None and reading!=pilot_reading(branch):
        raise LegalMathError("E_REFERENCE",details="Pilot formula differs from the semantic clause")
    try:
        projected=legacy_packet(packet,reading);projection_reason=None
    except LegalMathError as exc:
        if exc.code!="E_UNSUPPORTED_PROFILE": raise
        projected=None;projection_reason=str(exc.details)
    return {"profile":"legalmath.semantic-lowering.v1","branch":branch.model_dump(mode="json"),
            "packet":packet,"legacy_packet":projected,"legacy_projection_reason":projection_reason,
            "reading":deepcopy(reading),"question":question,
            "provenance":"declared_semantic_branch","legacy_basis":"reviewer_interpretation",
            "meaning":"proposed; reviewer_interpretation is a legacy enum, not approval",
            "unknown_packet_metadata":"retained in original packet; adapter does not infer authority or applicability"}
