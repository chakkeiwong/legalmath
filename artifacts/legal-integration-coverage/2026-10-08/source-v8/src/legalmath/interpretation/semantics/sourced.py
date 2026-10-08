"""Source-bound adapter for the existing typed criticism profile.

The abstract graph is conditional on proposed premises and inferences. No model
status or preference becomes an established source interpretation.
"""
from dataclasses import asdict
import json
from .arguments import Argument, Attack, Theory, evaluate
from .reconciliation import spans
from ...canonical import digest, loads, canonical
from ...errors import LegalMathError
from ..assurance.arguments import evaluate_criticism

def context(criticism=None, reconciliation=None):
    return {"criticism":criticism, "reconciliation":reconciliation}

def check_context(value):
    if value is None:
        return context()
    if not isinstance(value,dict) or set(value)!={"criticism","reconciliation"}:
        raise LegalMathError("E_SCHEMA", details="Unknown source reasoning context")
    return value

def evaluate_sourced(packet, candidates, questions, branches, value, settings):
    value=check_context(value)
    proposal=value["criticism"]
    warrants=[]; arguments=[]; attacks=[]; covered=set(); questions_open=[]
    evaluation=None
    if proposal is not None:
        evaluation=evaluate_criticism(proposal,packet,candidates)
        for a in proposal["arguments"]:
            cid=a["candidate_id"]; covered.add(cid)
            warrants.append({"argument_id":a["argument_id"], "candidate_id":cid,
                "inference":a["inference"], "inference_kind":a["inference_kind"],
                "sources":[s.model_dump(mode="json") for s in spans(packet,questions[cid],a["evidence"])],
                "premises":[{**p, "sources":[s.model_dump(mode="json") for s in spans(packet,questions[cid],p["evidence"])]}
                            for p in a["premises"]],
                "parents":a["parents"],"legal_support":"NOT_ESTABLISHED"})
        if evaluation["status"]=="CYCLIC_SUPPORT_UNRESOLVED":
            theory=Theory((),(),"incomplete",tuple(sorted(a["argument_id"] for a in proposal["arguments"])))
        else:
            blocked=set(evaluation["blocked_arguments"])
            for a in proposal["arguments"]:
                if a["argument_id"] in blocked: continue
                arguments.append(Argument(a["argument_id"],digest(a["conclusion"]),
                    tuple(a["parents"]),a["inference_id"],a["inference_kind"].lower()))
            # Existing validator checks signed conclusions, target components and
            # parent closure. It applies no proposed preference without an explicit grant.
            for source,target in evaluation["defeats"]:
                attacks.append(Attack(source,target,"checked-typed-defeat",target))
            theory=Theory(tuple(arguments),tuple(attacks))
        questions_open=evaluation["questions"]
    else:
        theory=Theory((),())
    # Keep undeclared relations explicit. Missing criticism does not erase a reading.
    fallback=[]
    for cid in sorted(set(candidates)-covered):
        b=branches[cid]; reading=candidates[cid]
        aid="retained-warrant."+digest({"candidate":cid,"reading":reading})
        arguments.append(Argument(aid,cid,(),aid,"defeasible"))
        fallback.append(Argument(aid,cid,(),aid,"defeasible"))
        warrants.append({"argument_id":aid,"candidate_id":cid,"inference":reading["distinction"],
            "inference_kind":"DEFEASIBLE","sources":[s.model_dump(mode="json") for s in spans(packet,questions[cid],reading["citations"])],
            "premises":[p.model_dump(mode="json") for p in b.assumptions],
            "parents":[],"legal_support":"NOT_ESTABLISHED"})
        questions_open.append("No typed objections supplied for "+cid+"; prose questions remain unencoded.")
    theory=Theory(theory.arguments+tuple(fallback),theory.attacks,theory.completion,theory.frontier)
    result=evaluate(theory,settings.semantics,settings.max_arguments,settings.max_extensions,settings.timeout_seconds)
    extension_ids=[digest({"settings":settings.identity(),"context":digest(value),"extension":list(e)}) for e in result.extensions]
    membership={}
    for cid in candidates:
        ids={w["argument_id"] for w in warrants if w["candidate_id"]==cid}
        contained=[i for i,e in enumerate(result.extensions) if ids.intersection(e)]
        membership[cid]={"argument_ids":sorted(ids),"extension_ids":[extension_ids[i] for i in contained],
            "acceptance":("unfinished" if result.completion!="complete" else
                "none" if not contained else "all" if len(contained)==len(result.extensions) else "some"),
            "conditional_on_proposed_warrants":True,
            "meaning":"Membership of arguments assigned to this candidate; does not establish its formula or legal interpretation."}
    return loads(canonical({"profile":"source-bound-typed-criticism.v1","context_hash":digest(value),
        "theory":json.loads(json.dumps(asdict(theory))),"evaluation":json.loads(json.dumps(asdict(result))),"extensions":extension_ids,
        "candidate_membership":membership,"warrants":warrants,"criticism_evaluation":evaluation,
        "unencoded_candidates":sorted(set(candidates)-covered),"questions":sorted(set(questions_open)),
        "legal_acceptance":"NOT_ESTABLISHED","candidate_pruning_authorized":False}))
