"""Explicit contract construction with source maps and correlated choices.

This executes admitted construction decisions; it does not infer their legal meaning.
"""
from .anchors import bind, fields, in_period
from .contracts import digest, timestamp
from .predicates import decide

def render(graph, spec):
    fields(spec, {"version","root","nodes","selections","constraints"}, {"version","root","nodes"})
    if spec["version"] != "contract-ast.v1" or not isinstance(spec["nodes"], list):
        raise ValueError("Unsupported contract AST")
    nodes = {n["id"]:n for n in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("Duplicate construction node")
    selections = spec.get("selections", {})
    choices = {k:n for k,n in nodes.items() if n["kind"] == "Choice"}
    if set(selections) - set(choices):
        raise ValueError("Selection refers to unknown choice")
    unresolved, trace, coverage = [], [], {}
    observations = {}
    for key,n in choices.items():
        chosen = selections.get(key)
        if chosen is not None:
            fields(chosen, {"option","reason","source"}, {"option","reason","source"})
            if chosen["option"] not in n["options"] or not chosen["reason"]:
                raise ValueError("Unknown choice option or missing selection reason")
            bind(graph,chosen["source"])
        for option in n["options"]:
            observations[key + ":" + option] = option == chosen["option"] if chosen else None
    for constraint in spec.get("constraints", []):
        outcome = decide(constraint, observations)
        if outcome["status"] == "NO":
            raise ValueError("Correlated construction constraint violated")
        if outcome["status"] != "YES":
            unresolved.append("Unresolved correlated construction constraint")

    def visit(key, stack=()):
        if key in stack or key not in nodes or len(stack) > 64:
            raise ValueError("Cyclic, missing or overdeep construction reference")
        n = nodes[key]; kind = n["kind"]; common = {"id","kind"}
        if kind == "Text":
            fields(n, common | {"source"}, common | {"source"})
            source = bind(graph,n["source"])
            coverage.setdefault(source["unit"],set()).update(range(source["start"],source["end"]))
            return [{"text":source["quote"],"source":source,"node":key,"operation":"Text"}]
        if kind == "Sequence":
            fields(n, common | {"children"}, common | {"children"})
            return [p for child in n["children"] for p in visit(child, stack+(key,))]
        if kind == "Choice":
            fields(n, common | {"options"}, common | {"options"})
            chosen = selections.get(key)
            if not chosen:
                unresolved.append("Unselected choice: "+key)
                return []
            trace.append({"node":key,"operation":"Choice",**chosen,"excluded_options":sorted(set(n["options"])-{chosen["option"]})})
            return visit(n["options"][chosen["option"]],stack+(key,))
        if kind == "Field":
            fields(n, common | {"template","value","source","reason"}, common | {"template","source","reason","value"})
            template, source = bind(graph,n["template"]), bind(graph,n["source"])
            if not n["reason"] or not isinstance(n["value"],str) or not n["value"]:
                raise ValueError("Explicit field value and source-backed reason required")
            coverage.setdefault(template["unit"],set()).update(range(template["start"],template["end"]))
            trace.append({"node":key,"operation":"Field","template":template,"source":source,"reason":n["reason"]})
            return [{"text":n["value"],"source":source,"node":key,"operation":"Field","template":template}]
        if kind == "Reference":
            fields(n, common | {"target","source","reason"}, common | {"target","source","reason"})
            source=bind(graph,n["source"])
            if not n["reason"]:
                raise ValueError("Reference scope reason required")
            trace.append({"node":key,"operation":"Reference","source":source,"target":n["target"],"reason":n["reason"]})
            return visit(n["target"],stack+(key,))
        if kind == "Override":
            required=common | {"target","replacement","source","reason","valid_from","known_from"}
            fields(n,required | {"valid_until","known_until"},required)
            source=bind(graph,n["source"])
            if not n["reason"] or n["target"] not in nodes:
                raise ValueError("Amendment requires explicit target and precedence reason")
            ctx=graph.get("context",{})
            active=in_period(n,timestamp(ctx["effective_at"]),timestamp(ctx["known_at"]))
            trace.append({"node":key,"operation":"Override","source":source,"target":n["target"],
                          "replacement":n["replacement"],"active":active,"reason":n["reason"]})
            return visit(n["replacement"] if active else n["target"],stack+(key,))
        raise ValueError("Unsupported construction kind: "+str(kind))
    pieces=visit(spec["root"])
    text="";mapping=[]
    for p in pieces:
        if text:
            start=len(text);text+=" "
            mapping.append({"start":start,"end":len(text),"operation":"Sequence separator","source":None})
        start=len(text);text+=p["text"]
        mapping.append({**p,"start":start,"end":len(text)})
    return {"version":"rendered-contract.v1","ast_sha256":digest(spec),"text":text,"map":mapping,
            "operations":trace,"unresolved":unresolved,"covered":{k:sorted(v) for k,v in coverage.items()}}


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
        if u["role"] in {"HEADER","EXCLUDED","EXAMPLE","INSTRUCTION"}:
            continue
        if any(i not in covered and not ch.isspace() for i,ch in enumerate(raw)) or not raw.strip():
            units.append({**u,"role":"UNKNOWN","order":len(units),"reason":"Raw source not accounted for by construction"})
    unresolved=output["unresolved"]+[u["unit"] for u in units if u["role"]=="UNKNOWN"]
    return {**base,"version":"assembled-contract.v2","units":units,"rendered_ast":output,"unresolved":unresolved,
            "status":"PARTIAL" if unresolved else "COMPLETE_UNDER_SUPPLIED_DISPOSITIONS",
            "continuous_text":"\n".join(u["text"] for u in units)}
