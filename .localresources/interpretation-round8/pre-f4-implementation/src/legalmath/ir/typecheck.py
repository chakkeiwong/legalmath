"""All branches are checked before any rule can run."""
from ..canonical import canonical
from ..domain import scalar, interval, timestamp
from ..errors import BoundaryError, diagnostic
from .graph import children, walk
from .load import schema_errors


def validate_bundle(bundle):
    canonical(bundle)
    errors = schema_errors("rule-bundle", bundle, "/bundle")
    if errors:
        return errors
    invalid_spans = [diagnostic("E_SCHEMA", f"/bundle/source_spans/{i}/end") for i, span in enumerate(bundle["source_spans"]) if span["start"] >= span["end"]]
    if invalid_spans:
        return invalid_spans
    refs, types, cycles = [], [], []
    maps = {}
    for collection, key in (("facts", "name"), ("rules", "id"), ("source_spans", "id"), ("interpretations", "id")):
        seen = {}
        for i, item in enumerate(bundle[collection]):
            if item[key] in seen:
                refs.append(diagnostic("E_DUPLICATE_ID", f"/bundle/{collection}/{i}/{key}"))
            seen[item[key]] = item
        maps[collection] = seen
    facts, rules = maps["facts"], maps["rules"]
    nodes, node_types, pointers, edges = {}, {}, {}, {r: set() for r in rules}

    def citations(item, ptr, meaning=True):
        if meaning and item["interpretation_id"] not in maps["interpretations"]:
            refs.append(diagnostic("E_REFERENCE", ptr + "/interpretation_id"))
        for j, ident in enumerate(item["source_span_ids"]):
            if ident not in maps["source_spans"]:
                refs.append(diagnostic("E_REFERENCE", ptr + f"/source_span_ids/{j}"))

    for i, item in enumerate(bundle["interpretations"]):
        citations(item, f"/bundle/interpretations/{i}", False)
    for i, rule in enumerate(bundle["rules"]):
        rptr = f"/bundle/rules/{i}"
        citations(rule, rptr)
        for field in ("scope", "body"):
            for node, ptr in walk(rule[field], rptr + "/" + field):
                ident, op = node["node_id"], node["op"]
                if ident in nodes:
                    refs.append(diagnostic("E_DUPLICATE_ID", ptr + "/node_id"))
                nodes[ident], pointers[ident] = node, ptr
                if op in ("fact", "rule") and node["name"] not in (facts if op == "fact" else rules):
                    refs.append(diagnostic("E_REFERENCE", ptr + "/name"))
                elif op == "rule":
                    edges[rule["id"]].add(node["name"])
                if op == "default":
                    seen = set()
                    for j, ex in enumerate(node["exceptions"]):
                        ep = ptr + f"/exceptions/{j}"
                        if ex["exception_id"] in seen:
                            refs.append(diagnostic("E_DUPLICATE_ID", ep + "/exception_id"))
                        seen.add(ex["exception_id"])
                        citations(ex, ep)
    if refs:
        return sorted(refs, key=lambda d: (d["pointer"], d["code"]))
    if len(nodes) > 10000:
        return [diagnostic("E_RESOURCE_LIMIT", "/bundle/rules")]

    def infer(node):
        op, ident = node["op"], node["node_id"]
        vals = [infer(n) for _, n in children(node)]
        bad = False
        if op == "literal":
            typ = node["type"]
            bad = not scalar(typ, node["value"])
        elif op == "fact":
            typ = facts[node["name"]]["type"]
        elif op == "rule":
            target = rules[node["name"]]
            typ = target["type"]
            s = target["scope"]
            bad = not (s["op"] == "literal" and s["type"] == "bool" and s["value"] is True)
        elif op in ("all", "any", "not"):
            typ, bad = "bool", any(t != "bool" for t in vals)
        elif op in ("compare", "add", "sub"):
            typ = "bool" if op == "compare" else vals[0]
            bad = vals[0] != vals[1] or vals[0] not in (("integer", "money_hkd", "date") if op == "compare" else ("integer", "money_hkd"))
        elif op == "scale":
            typ, bad = vals[0], vals[0] not in ("integer", "money_hkd")
        elif op == "if":
            typ, bad = vals[1], vals[0] != "bool" or vals[1] != vals[2]
        else:
            typ = vals[0]
            bad = any(vals[i] != "bool" or vals[i + 1] != typ for i in range(1, len(vals), 2))
        if bad:
            types.append(diagnostic("E_TYPE", pointers[ident]))
        node_types[ident] = typ
        return typ
    for i, rule in enumerate(bundle["rules"]):
        for field, typ in (("scope", "bool"), ("body", rule["type"])):
            if infer(rule[field]) != typ:
                types.append(diagnostic("E_TYPE", f"/bundle/rules/{i}/{field}"))
    if types:
        return sorted({(d["pointer"], d["code"]): d for d in types}.values(), key=lambda d: d["pointer"])
    visited, visiting, order = set(), set(), []
    for i, rule in enumerate(bundle["rules"]):
        stack = [(rule["id"], False)]
        while stack:
            name, exiting = stack.pop()
            if exiting:
                visiting.remove(name)
                visited.add(name)
                order.append(name)
            elif name in visiting:
                return [diagnostic("E_CYCLE", f"/bundle/rules/{i}")]
            elif name not in visited:
                visiting.add(name)
                stack.append((name, True))
                stack.extend((target, False) for target in sorted(edges[name], reverse=True))
    # Bound the expanded call path, including references between shallow ASTs.
    # Counting nodes alone does not protect an evaluator from a long rule chain.
    depths = {}
    def depth(node):
        if node["op"] == "rule":
            return 1 + depths[node["name"]]
        return 1 + max((depth(n) for _, n in children(node)), default=0)
    for name in order:
        depths[name] = 2 + max(depth(rules[name][k]) for k in ("scope", "body"))
        if depths[name] > 128:
            return [diagnostic("E_RESOURCE_LIMIT", "/bundle/rules")]
    try:
        interval(bundle["valid_from"], bundle["valid_until"])
    except BoundaryError:
        return [diagnostic("E_TIME", "/bundle/valid_from")]
    return []


def validate_snapshot(bundle, snapshot):
    errors = schema_errors("fact-snapshot", snapshot, "/snapshot")
    if errors:
        return errors
    facts = {f["name"]: f["type"] for f in bundle["facts"]}
    for name in sorted(set(facts) | set(snapshot["facts"])):
        ptr = "/snapshot/facts/" + name
        if name not in facts or name not in snapshot["facts"]:
            errors.append(diagnostic("E_REFERENCE", ptr))
            continue
        entry = snapshot["facts"][name]
        if facts[name] != entry["type"] or (entry["status"] == "known" and not scalar(entry["type"], entry["value"])):
            errors.append(diagnostic("E_TYPE", ptr))
        if entry["status"] == "known":
            try:
                interval(entry["valid_from"], entry["valid_until"])
                timestamp(entry["recorded_at"])
            except BoundaryError:
                errors.append(diagnostic("E_TIME", ptr))
        if "evidence_ids" in entry and len(set(entry["evidence_ids"])) != len(entry["evidence_ids"]):
            errors.append(diagnostic("E_DUPLICATE_ID", ptr + "/evidence_ids"))
    if errors:
        stages = {"E_REFERENCE": 1, "E_DUPLICATE_ID": 1, "E_TYPE": 2, "E_TIME": 4}
        first = min(stages[d["code"]] for d in errors)
        errors = [d for d in errors if stages[d["code"]] == first]
    return sorted(errors, key=lambda d: (d["pointer"], d["code"]))
