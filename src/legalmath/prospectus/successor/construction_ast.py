"""Explicit contract construction with source maps and correlated choices.

This executes admitted construction decisions; it does not infer their legal meaning.
"""
from .anchors import bind, fields, in_period
from .contracts import digest, timestamp
from .predicates import decide

def render(graph, spec):
    fields(spec, {"version","root","nodes","selections","constraints"}, {"version","root","nodes"})
    if spec["version"] not in {"contract-ast.v1", "contract-ast.v2"} or not isinstance(spec["nodes"], list):
        raise ValueError("Unsupported contract AST")
    nodes = {n["id"]:n for n in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("Duplicate construction node")
    selections = spec.get("selections", {})
    choices = {k:n for k,n in nodes.items() if n["kind"] == "Choice"}
    if set(selections) - set(choices):
        raise ValueError("Selection refers to unknown choice")
    unresolved, trace, coverage, dispositions = [], [], {}, []
    overrides = {}
    def account(source, disposition, use, reason, binding=None):
        bound = bind(graph, source)
        dispositions.append({"source": source, "disposition": disposition, "use": list(use),
                             "reason": reason, "binding": binding})
        coverage.setdefault(bound["unit"], set()).update(range(bound["start"], bound["end"]))
        return bound
    observations = {}
    for key,n in choices.items():
        chosen = selections.get(key)
        if chosen is not None:
            fields(chosen, {"option","reason","source"}, {"option","reason","source"})
            if chosen["option"] not in n["options"] or not chosen["reason"]:
                raise ValueError("Unknown choice option or missing selection reason")
            account(chosen["source"], "PREMISE", (key, "selection"), chosen["reason"])
        for option in n["options"]:
            observations[key + ":" + option] = option == chosen["option"] if chosen else None
    for constraint in spec.get("constraints", []):
        outcome = decide(constraint, observations)
        if outcome["status"] == "NO":
            raise ValueError("Correlated construction constraint violated")
        if outcome["status"] != "YES":
            unresolved.append("Unresolved correlated construction constraint")

    active_nodes = set()
    visits = 0
    def visit(key, stack=(), inactive=None):
        nonlocal visits
        visits += 1
        if visits > 100000:
            raise ValueError("Construction expansion limit exceeded")
        if key in active_nodes or key not in nodes or len(stack) > 128:
            raise ValueError("Cyclic, missing or overdeep construction reference")
        active_nodes.add(key)
        try:
            return visit_node(key, stack, inactive)
        finally:
            active_nodes.remove(key)

    def visit_node(key, stack, inactive):
        n = nodes[key]; kind = n["kind"]; common = {"id","kind"}
        use = stack + (key,)
        disposition, reason, binding = inactive or ("COPIED", "Selected text", None)
        if kind == "Text":
            fields(n, common | {"source"}, common | {"source"})
            source = account(n["source"], disposition, use, reason, binding)
            return [] if inactive else [{"text":source["quote"],"source":source,"node":key,"operation":"Text"}]
        if kind == "Sequence":
            fields(n, common | {"children"}, common | {"children"})
            return [p for i, child in enumerate(n["children"]) for p in visit(child, use+(str(i),), inactive)]
        if kind == "Choice":
            fields(n, common | {"options"}, common | {"options"})
            chosen = selections.get(key)
            if inactive:
                for option, child in n["options"].items():
                    visit(child, use+(option,), inactive)
                return []
            if not chosen:
                unresolved.append("Unselected choice: "+key)
                for option, child in n["options"].items():
                    visit(child, use+(option,), ("UNRESOLVED", "Unselected choice: " + key, {"choice": key}))
                return []
            trace.append({"node":key,"operation":"Choice",**chosen,"excluded_options":sorted(set(n["options"])-{chosen["option"]})})
            for option, child in n["options"].items():
                if option != chosen["option"]:
                    visit(child, use+(option,), ("EXCLUDED_BY_CHOICE", chosen["reason"],
                          {"choice": key, "option": option, "selected": chosen["option"], "source": chosen["source"]}))
            return visit(n["options"][chosen["option"]],use+(chosen["option"],))
        if kind == "Field":
            fields(n, common | {"template","value","source","reason"}, common | {"template","source","reason","value"})
            template = account(n["template"], disposition if inactive else "REPLACED_TEMPLATE", use,
                               reason if inactive else n["reason"], binding if inactive else {"field": key, "source": n["source"]})
            source = account(n["source"], disposition if inactive else "PREMISE", use+("value",),
                             reason if inactive else n["reason"], binding)
            if not n["reason"] or not isinstance(n["value"],str) or not n["value"]:
                raise ValueError("Explicit field value and source-backed reason required")
            if inactive:
                return []
            if n["value"] != source["quote"]:
                unresolved.append("Field value differs from source quotation; transformation unadmitted: " + key)
            trace.append({"node":key,"operation":"Field","template":template,"source":source,"reason":n["reason"]})
            return [{"text":n["value"],"source":source,"node":key,"operation":"Field","template":template}]
        if kind == "Reference":
            fields(n, common | {"target","source","reason"}, common | {"target","source","reason"})
            source=account(n["source"], disposition if inactive else "REFERENCE", use+("reference",), n["reason"], binding)
            if not n["reason"]:
                raise ValueError("Reference scope reason required")
            if not inactive:
                trace.append({"node":key,"operation":"Reference","source":source,"target":n["target"],"reason":n["reason"]})
            return visit(n["target"],use,inactive)
        if kind == "Override":
            required=common | {"target","replacement","source","reason","valid_from","known_from"}
            if spec["version"] == "contract-ast.v2":
                required.add("authority")
            fields(n,required | {"valid_until","known_until","authority"},required)
            source=account(n["source"], disposition if inactive else "PREMISE", use+("override",), n["reason"], binding)
            authority = n.get("authority", n["source"])
            account(authority, disposition if inactive else "PREMISE", use+("authority",), n["reason"], binding)
            if not n["reason"] or n["target"] not in nodes:
                raise ValueError("Amendment requires explicit target and precedence reason")
            ctx=graph.get("context",{})
            active=in_period(n,timestamp(ctx["effective_at"]),timestamp(ctx["known_at"]))
            if inactive:
                visit(n["target"],use+("target",),inactive)
                visit(n["replacement"],use+("replacement",),inactive)
                return []
            decision = {"override": key, "target": n["target"], "replacement": n["replacement"],
                        "authority": authority, "source": n["source"],
                        "valid_from": n["valid_from"], "known_from": n["known_from"],
                        "valid_until": n.get("valid_until"), "known_until": n.get("known_until"), "context": ctx}
            if active:
                prior = overrides.setdefault(n["target"], set())
                prior.add(n["replacement"])
                if len(prior) > 1:
                    unresolved.append("Conflicting active overrides: " + n["target"])
            visit(n["target"] if active else n["replacement"],use+("inactive",),
                  ("SUPERSEDED" if active else "INACTIVE_REPLACEMENT", n["reason"], decision))
            trace.append({"node":key,"operation":"Override","source":source,"target":n["target"],
                          "replacement":n["replacement"],"active":active,"reason":n["reason"]})
            return visit(n["replacement"] if active else n["target"],use)
        raise ValueError("Unsupported construction kind: "+str(kind))
    pieces=visit(spec["root"])
    text="";mapping=[]
    for p in pieces:
        if text:
            start=len(text);text+=" "
            mapping.append({"start":start,"end":len(text),"operation":"Sequence separator","source":None})
        start=len(text);text+=p["text"]
        mapping.append({**p,"start":start,"end":len(text)})
    from .intervals import check
    accounting = check(graph, dispositions)
    unresolved += ["Unaccounted source: " + r["unit"] for r in accounting["gaps"] + accounting["unresolved"]]
    return {"version":"rendered-contract.v2","ast_sha256":digest(spec),"text":text,"map":mapping,
            "operations":trace,"unresolved":sorted(set(unresolved)),"covered":{k:sorted(v) for k,v in coverage.items()},
            "dispositions":dispositions, "accounting":accounting}


def assemble(graph, spec, base):
    output=render(graph,spec)
    units=[]
    for i,piece in enumerate(output["map"]):
        if piece["source"] is None:
            continue
        source=piece["source"]
        units.append({"unit":"ast:"+str(i),"role":"UNKNOWN" if output["unresolved"] else "OPERATIVE",
                      "reason":"Admitted AST; legal interpretation remains a supplied premise","text":piece["text"],
                      "original_sha256":digest(piece["text"].encode()),"questions":["Q1","Q2"],"order":len(units),
                      "context":"ast:"+spec["root"],"language":"admitted",
                      "source":{"document":source["document"],"page":source["page"],"bbox":source["bbox"]},
                      "character_map":[piece]})
    # Unaccounted raw text stays visible. An AST cannot silently delete a distant exception.
    for u in base["units"]:
        covered=set(output["covered"].get(u["unit"],[]))
        raw=next(x["raw"] for x in graph["units"] if x["id"]==u["unit"])
        source_unit = next(x for x in graph["units"] if x["id"] == u["unit"])
        if not source_unit["visible"]:
            continue
        if any(i not in covered and not ch.isspace() for i,ch in enumerate(raw)) or not raw.strip():
            units.append({**u,"role":"UNKNOWN","order":len(units),"reason":"Raw source not accounted for by construction"})
    unresolved=output["unresolved"]+[u["unit"] for u in units if u["role"]=="UNKNOWN"]
    return {**base,"version":"assembled-contract.v2","units":units,"rendered_ast":output,"unresolved":unresolved,
            "status":"PARTIAL" if unresolved else "COMPLETE_UNDER_SUPPLIED_DISPOSITIONS",
            "continuous_text":"\n".join(u["text"] for u in units)}
