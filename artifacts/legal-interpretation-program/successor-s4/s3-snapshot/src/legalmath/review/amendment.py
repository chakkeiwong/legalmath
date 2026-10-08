"""Change impact uses the dependency graph and keeps original decisions intact."""
from ..canonical import digest
from ..ir.graph import dependency_closure


def changes(old, new):
    a, b = ({r["id"]: r for r in bundle["rules"]} for bundle in (old, new))
    meaning_a, meaning_b = ({i["id"]: i for i in bundle["interpretations"]} for bundle in (old, new))
    meaning_changes = {k for k in set(meaning_a) | set(meaning_b) if meaning_a.get(k) != meaning_b.get(k)}
    spans_a, spans_b = ({s["id"]: s for s in bundle["source_spans"]} for bundle in (old, new))
    span_changes = {k for k in set(spans_a) | set(spans_b) if spans_a.get(k) != spans_b.get(k)}
    facts_a, facts_b = ({f["name"]: f for f in bundle["facts"]} for bundle in (old, new))
    fact_changes = {k for k in set(facts_a) | set(facts_b) if facts_a.get(k) != facts_b.get(k)}
    direct = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    from ..ir.graph import walk
    for rules in (a, b):
        for name, r in rules.items():
            references = [r]
            for field in ("scope", "body"):
                for node, _ in walk(r[field], ""):
                    references.extend(node.get("exceptions", []))
            if any(item["interpretation_id"] in meaning_changes or set(item["source_span_ids"]) & span_changes for item in references):
                direct.add(name)
    affected = set(direct)
    for bundle in (old, new):
        for r in bundle["rules"]:
            rules, facts = dependency_closure(bundle, r["id"])
            if rules & direct or facts & fact_changes:
                affected.add(r["id"])
    return {"old_hash": digest(old), "new_hash": digest(new), "direct_rule_changes": sorted(direct),
        "affected_rule_ids": sorted(affected), "changed_definitions": sorted(meaning_changes),
        "changed_source_spans": sorted(span_changes), "changed_facts": sorted(fact_changes),
        "required_actions": ["Re-review affected interpretations", "Rebuild and verify Java", "Approve the new exact hashes"] if affected else [],
        "obligation_migration": "REQUIRES_SEPARATE_REVIEW", "semantic_equivalence": "NOT_CHECKED"}
