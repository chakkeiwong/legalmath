"""Retained development cases; hypothetical predicates are not observed legal facts."""
from datetime import date
from fractions import Fraction
import re
from .contracts import digest, read, bound_path
from .predicates import decide
from . import financial_profiles
from ..closure_mechanisms import PROFILES
from .jobs import LEGAL, INVENTORY


def checked_anchor(anchor, sources, root):
    s=sources[anchor["source_key"]]
    original=bound_path(root,s["original"]); extraction=bound_path(root,s["text"])
    if digest(original.read_bytes()) != anchor["source_sha256"] or s["sha256"] != anchor["source_sha256"]:
        raise ValueError("Changed primary source")
    if digest(extraction.read_bytes()) != s["text_sha256"]:
        raise ValueError("Changed source extraction")
    full=extraction.read_text(); text=full; base=0
    if "page" in anchor:
        pages=full.split("\f")
        page=anchor["page"]
        if type(page) is not int or not 1 <= page <= len(pages):
            raise ValueError("Invalid case source page")
        base=sum(len(p)+1 for p in pages[:page-1]);text=pages[page-1]
    elif "paragraph" in anchor:
        pattern=re.compile(r"(?m)^"+str(anchor["paragraph"])+r"\n")
        matches=list(pattern.finditer(full))
        if len(matches)!=1:
            raise ValueError("Ambiguous or missing paragraph")
        base=matches[0].end()
        end=re.search(r"(?m)^\d+\n",full[base:])
        text=full[base:base+end.start()] if end else full[base:]
    words=list(re.finditer(r"\S+",text))
    normalized=" ".join(m.group() for m in words)
    quote=" ".join(anchor["quote"].split())
    starts=[m.start() for m in re.finditer(re.escape(quote),normalized)]
    if len(starts)!=1:
        raise ValueError("Exact unique case source occurrence required")
    start=starts[0];end=start+len(quote); offsets=[];cursor=0
    for m in words:
        offsets.extend(range(m.start(),m.end()));offsets.append(m.end());cursor+=len(m.group())+1
    a,b=base+offsets[start],base+offsets[end-1]+1
    return {**anchor,"extraction_sha256":s["text_sha256"],"start":a,"end":b,"raw_quote":full[a:b],
            "normalization":"whitespace only","edition_verified":True}


def compile_expression(node,facts,observations):
    if type(node) is bool:
        return node
    if not isinstance(node,dict) or len(node)!=1:
        raise ValueError("One typed rule operator required")
    op,args=next(iter(node.items()))
    if op in {"all","any"}:
        return {op:[compile_expression(x,facts,observations) for x in args]}
    if op=="not":
        return {"not":compile_expression(args,facts,observations)}
    if op=="fact":
        values=facts.get(args,[])
        if not isinstance(values,list) or any(type(v) is not bool and v is not None for v in values):
            raise ValueError("Boolean observation list required")
        present=set(v for v in values if v is not None)
        observations[args]=next(iter(present)) if len(present)==1 else "conflict" if present else None
        return args
    if op not in {"before","on_or_after","elapsed_days_at_least"} or not isinstance(args,list):
        raise ValueError("Unsupported dated predicate")
    if len(args)!=(3 if op=="elapsed_days_at_least" else 2):
        raise ValueError("Wrong dated predicate arity")
    key="date_"+digest(node)[:16];dates=[];conflict=False
    for name in args[:2]:
        values=facts.get(name,[])
        if not isinstance(values,list):
            raise ValueError("Dated observations must be lists")
        present=set(v for v in values if v is not None)
        conflict |= len(present)>1
        dates.append(date.fromisoformat(next(iter(present))) if len(present)==1 else None)
    if conflict:
        value="conflict"
    elif None in dates:
        value=None
    elif op=="before":
        value=dates[0]<dates[1]
    elif op=="on_or_after":
        value=dates[0]>=dates[1]
    else:
        if type(args[2]) is not int or args[2]<0:
            raise ValueError("Nonnegative integer day count required")
        value=(dates[1]-dates[0]).days>=args[2]
    observations[key]=value
    return key


def law_cases(root,admission=None):
    scenarios=read(root/LEGAL/"rule-scenarios.json") if admission is None else admission
    sources=read(root/LEGAL/"source-registry.json")
    results=[]
    for scenario in scenarios:
        rule,context=scenario["rule"],scenario["context"]
        anchors=[checked_anchor(a,sources,root) for a in rule["anchors"]]
        problems=[]
        for k,allowed in rule["scope"].items():
            if context.get(k) not in allowed:
                problems.append("OUT_OF_SCOPE:"+k)
        if context.get("requested_stage")!=rule["stage"]:
            problems.append("STAGE_MISMATCH")
        if not context.get("known_at") or date.fromisoformat(context["known_at"])<date.fromisoformat(rule["source_date"]):
            problems.append("SOURCE_POSTDATES_KNOWLEDGE")
        observations={}
        expression=compile_expression(rule["condition"],context.get("facts",{}),observations)
        answer=decide(expression,observations)
        if problems:
            answer={**answer,"status":"UNKNOWN"}
        if admission is None:
            expected=scenario["expected"]
            observed_status="UNRESOLVED" if answer["status"] in {"UNKNOWN","CONFLICT"} else "CONDITIONAL"
            observed_value={"YES":True,"NO":False}.get(answer["status"])
            if observed_status!=expected["status"] or observed_value is not expected["value"]:
                raise ValueError("Retained scoped counterfactual changed: "+scenario["case"])
        amount=None
        if rule.get("arithmetic") and answer["status"]=="YES":
            name=rule["arithmetic"]["remaining_percent"];values=context["facts"].get(name,[])
            if len(values)!=1 or not isinstance(values[0],str):
                raise ValueError("Exact percentage observation required")
            remaining=Fraction(values[0])
            if not 0<=remaining<=100:
                raise ValueError("Invalid remaining percent")
            amount={"remaining_percent":str(remaining),"reduction_percent":str(100-remaining),
                    "ultimate_recovery":"NOT_ESTABLISHED"}
        results.append({"case":scenario["case"],"stage":rule["stage"],"requested_stage":context["requested_stage"],
                        "conclusion":rule["conclusion"],"predicate_result":answer,"scope_issues":problems,
                        "anchors":anchors,"arithmetic":amount,"rule_sha256":digest(rule),"context_sha256":digest(context),
                        "scenario":scenario,"premise_kind":"HYPOTHETICAL_DEVELOPMENT",
                        "law_currentness":"NOT_ESTABLISHED_BY_CORPUS_AVAILABILITY_DATE",
                        "actual_event":"NOT_ESTABLISHED","independent_adjudication":False,
                        "frozen_development_expectation":"PASS" if admission is None else "NOT_PREDECLARED",
                        "remaining":["Admit actual forum, instrument, effective law edition, event/procedure and suspension facts",
                                     "Independent source interpretation review"]})
    return results


def financial_cases(root,admission=None):
    original=read(root/"docs/prospectus/evidence-closure/scenarios.json")
    if admission is None:
        scenarios=original
        # Explicitly chosen synthetic identity; historical receipts remain untouched.
        for scenario in scenarios.values():
            for i,h in enumerate(scenario.get("holdings",[])):
                h.update(legal_holder_id="synthetic-holder-a",account_id="synthetic-account-"+str(i))
    else:
        scenarios=admission
    inventory=read(root/INVENTORY)["documents"]
    results=[]
    for key,scenario in scenarios.items():
        profile=PROFILES[key];meta=inventory[profile["document"]]
        if digest((root/meta["original"]).read_bytes())!=profile["sha256"]:
            raise ValueError("Financial source bytes changed")
        if digest((root/meta["text"]).read_bytes())!=meta["text_sha256"]:
            raise ValueError("Financial source text changed")
        document=read(root/meta["text"])
        pages=document["pages"]
        anchors=[{"page":p,"text_sha256":digest(pages[p-1]["text"].encode()),"source_sha256":profile["sha256"]} for p in profile["pages"]]
        result=financial_profiles.assess({"instrument_id":key,"documents":[{"sha256":profile["sha256"]}]},scenario)
        if admission is None:
            expected={"deutsche-at1-2025":{"write_down":"25"},
                      "bbva-at1-series15-2025":{"conversion_price":"501/100","shares":3},
                      "seb-at1-usd-2024":{"conversion_price_usd":"3","shares":3}}[key]
            calculation=result["value"]["calculation"]
            for k,v in expected.items():
                actual=calculation["holder_entitlements"][0]["shares"] if k=="shares" else calculation[k]
                if actual!=v:
                    raise ValueError("Independent hand calculation mismatch: "+key+":"+k)
        else:
            expected=None
        results.append({"instrument_id":key,"source_anchors":anchors,"question":result,
                        "scenario_sha256":digest(scenario),"hand_calculation_expected":expected,
                        "hand_calculation_review":"IMPLEMENTER; independent reviewer pending",
                        "identity_assumption":"Two synthetic accounts of one legal holder" if admission is None else "Admitted scenario",
                        "scope":"NAMED_SUBCALCULATION; not complete settlement or actual exercise"})
    return results
