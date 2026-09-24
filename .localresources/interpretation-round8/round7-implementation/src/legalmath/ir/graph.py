"""One structural traversal, without evaluating branches."""
def children(node):
    op = node["op"]
    if op in ("all", "any"):
        return [(f"args/{i}", n) for i, n in enumerate(node["args"])]
    if op in ("not", "scale"):
        return [("arg", node["arg"])]
    if op in ("compare", "add", "sub"):
        return [(k, node[k]) for k in ("left", "right")]
    if op == "if":
        return [(k, node[k]) for k in ("condition", "then", "else")]
    if op == "default":
        return [("base", node["base"])] + [(f"exceptions/{i}/{k}", e[k])
            for i, e in enumerate(node["exceptions"]) for k in ("guard", "value")]
    return []


def walk(node, pointer):
    yield node, pointer
    for part, child in children(node):
        yield from walk(child, pointer + "/" + part)


def dependency_closure(bundle, rule_id):
    rules = {r["id"]: r for r in bundle["rules"]}
    seen, facts = set(), set()

    def visit(name):
        if name in seen:
            return
        seen.add(name)
        for field in ("scope", "body"):
            for node, _ in walk(rules[name][field], ""):
                if node["op"] == "fact":
                    facts.add(node["name"])
                elif node["op"] == "rule":
                    visit(node["name"])
    visit(rule_id)
    return seen, facts
