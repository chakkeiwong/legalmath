"""Question-local reachability with explicit unresolved and cyclic support."""

KINDS = {"reference", "definition", "conditions", "exceptions", "negation", "priority"}


def close(nodes, edges, roots):
    available = set(nodes)
    adjacency = {key: [] for key in available}
    for edge in edges:
        if edge["kind"] not in KINDS or edge["from"] not in available:
            raise ValueError("Invalid typed reference edge")
        adjacency[edge["from"]].append(edge)
    reached, unresolved, active = set(), set(), set()
    def visit(key):
        if key in active:
            unresolved.add("Unsupported reference cycle: " + key)
            return
        if key in reached:
            return
        if key not in available:
            unresolved.add("Missing reference target: " + key)
            return
        reached.add(key)
        active.add(key)
        for edge in adjacency[key]:
            if not edge.get("resolved"):
                unresolved.add("Unresolved reference: " + edge.get("id", key + ":" + str(edge["to"])))
            if edge["kind"] == "priority" and not edge.get("authority"):
                unresolved.add("Unsupported priority: " + key)
            if edge["to"] is not None:
                visit(edge["to"])
        active.remove(key)
    for root in roots:
        visit(root)
    return {"roots": sorted(roots), "reachable": sorted(reached), "unresolved": sorted(unresolved)}
