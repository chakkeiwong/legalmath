"""Isolated pinned-package operations; no model calls or downloads."""
import json
import os
from pathlib import Path
import re
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RES = ROOT / ".localresources/legal-tool-comparison"


def passages(units):
    rows = []
    for unit in units:
        # The retained corpus normalizes newlines. Use explicit overlapping
        # character windows, retaining exact offsets; these are not paragraphs.
        start, text = 0, unit["text"]
        while start < len(text):
            end = min(start + 1000, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + 750, end)
                if boundary > start:
                    end = boundary
            if text[start:end].strip():
                rows.append({"unit_id": unit["id"], "start": start, "end": end,
                             "text": text[start:end], "source": unit.get("source"), "role": unit.get("role")})
            if end == len(text):
                break
            boundary = text.find(" ", end - 250, end)
            start = boundary + 1 if boundary >= 0 else end - 250
    return rows


def retrieval(data):
    from rank_bm25 import BM25Okapi
    units = data["corpus"]["units"]
    corpus = passages(units)
    whole = [{"unit_id": u["id"], "start": 0, "end": len(u["text"]), "text": u["text"],
              "source": u.get("source"), "role": u.get("role")} for u in units]
    token = lambda s: re.findall(r"[a-z0-9]+", s.lower())
    rows = []
    for mode, candidates in (("lexical_overlap", whole), ("whole_bm25", whole), ("passage_bm25", corpus)):
        docs = [token(c["text"]) for c in candidates]
        model = BM25Okapi(docs, k1=1.5, b=0.75, epsilon=0.25) if mode != "lexical_overlap" else None
        for q in data["questions"]:
            tokens = token(q["question"])
            scores = model.get_scores(tokens) if model else [len(set(tokens) & set(d)) for d in docs]
            order = sorted(range(len(candidates)), key=lambda i: (-float(scores[i]), candidates[i]["unit_id"], candidates[i]["start"]))[:8]
            selected = [{**candidates[i], "score": float(scores[i])} for i in order]
            expected = data.get("targets", {}).get(q["id"], [])
            matched = [e for e in expected if any(e["unit_id"] == p["unit_id"] and e["quote"] in p["text"] for p in selected)]
            rows.append({"mode": mode, "question_id": q["id"], "passages": selected,
                         "annotated_targets": len(expected), "targets_found": len(matched),
                         "missing": [e for e in expected if e not in matched]})
    return {"status": "EXECUTED", "rows": rows, "whole_units": len(whole),
            "passages": len(corpus), "parameters": {"k1": 1.5, "b": .75, "epsilon": .25, "k": 8,
                 "maximum_characters": 1000, "overlap_characters": 250},
            "scope": "Development passage annotations; ranking does not establish entailment"}


def xml_schema():
    from lxml import etree
    class Resolver(etree.Resolver):
        def resolve(self, url, pubid, context):
            if url in ("http://www.w3.org/2009/01/xml.xsd", "https://www.w3.org/2009/01/xml.xsd"):
                return self.resolve_filename(str(RES / "xml.xsd"), context)
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    parser.resolvers.add(Resolver())
    xsd = etree.XMLSchema(etree.parse(str(RES / "legalruleml-source/xsd-schema/compact/lrml-compact.xsd"), parser))
    return etree, parser, xsd


def encode_rules(rules):
    etree, _, _ = xml_schema()
    ns = {"lrml": "http://docs.oasis-open.org/legalruleml/ns/v1.0/", "ruleml": "http://ruleml.org/spec"}
    def el(parent, kind, text=None, **attrs):
        prefix, name = kind.split(":")
        child = etree.SubElement(parent, "{" + ns[prefix] + "}" + name, **attrs)
        child.text = text
        return child
    root = etree.Element("{" + ns["lrml"] + "}LegalRuleML", nsmap=ns)
    sources = el(root, "lrml:LegalSources")
    identities = sorted({s for row in rules for s in row["sources"]})
    source_keys = {s: "source" + str(i) for i, s in enumerate(identities)}
    for source, key in source_keys.items():
        el(sources, "lrml:LegalSource", key=key, sameAs=source)
    links = el(root, "lrml:Associations")
    for row in rules:
        for s in row["sources"]:
            a = el(links, "lrml:Association")
            el(a, "lrml:appliesSource", keyref="#" + source_keys[s])
            el(a, "lrml:toTarget", keyref="#" + row["id"])
    statements = el(root, "lrml:Statements")
    for row in rules:
        st = el(statements, "lrml:ConstitutiveStatement", key=row["id"])
        rule = el(st, "ruleml:Rule")
        condition = el(rule, "ruleml:if")
        conjunction = el(condition, "ruleml:And")
        for req in row["requirements"]:
            atom = el(conjunction, "ruleml:Atom")
            el(atom, "ruleml:Rel", req["kind"])
            el(atom, "ruleml:Ind", req["id"])
            el(atom, "ruleml:Ind", req["statement"])
        atom = el(el(rule, "ruleml:then"), "ruleml:Atom")
        el(atom, "ruleml:Rel", "conditional_" + row["modality"])
        el(atom, "ruleml:Ind", row["consequence"])
    return root, ns


def decode_rules(root, ns):
    sources = {n.get("key"): n.get("sameAs") for n in root.findall("lrml:LegalSources/lrml:LegalSource", ns)}
    links = {}
    for node in root.findall("lrml:Associations/lrml:Association", ns):
        target = node.find("lrml:toTarget", ns).get("keyref")[1:]
        source = node.find("lrml:appliesSource", ns).get("keyref")[1:]
        links.setdefault(target, []).append(sources[source])
    rows = []
    for node in root.findall("lrml:Statements/lrml:ConstitutiveStatement", ns):
        identity = node.get("key")
        requirements = []
        for atom in node.findall("ruleml:Rule/ruleml:if/ruleml:And/ruleml:Atom", ns):
            inds = atom.findall("ruleml:Ind", ns)
            requirements.append({"kind": atom.findtext("ruleml:Rel", namespaces=ns),
                                 "id": inds[0].text, "statement": inds[1].text})
        conclusion = node.find("ruleml:Rule/ruleml:then/ruleml:Atom", ns)
        rows.append({"id": identity, "requirements": requirements,
            "modality": conclusion.findtext("ruleml:Rel", namespaces=ns).removeprefix("conditional_"),
            "consequence": conclusion.findtext("ruleml:Ind", namespaces=ns), "sources": links.get(identity, [])})
    return rows


def interchange(data):
    from copy import deepcopy
    etree, _, xsd = xml_schema()
    root, ns = encode_rules(data["rules"])
    schema_ok = xsd.validate(root)
    errors = [str(e) for e in xsd.error_log]
    roundtrip = decode_rules(root, ns)
    mutations = []
    for name in ("drop-condition", "change-condition", "drop-source"):
        bad = deepcopy(root)
        if name == "drop-source":
            victim = bad.find("lrml:Associations/lrml:Association", ns)
            victim.getparent().remove(victim)
        else:
            victim = bad.find("lrml:Statements/lrml:ConstitutiveStatement/ruleml:Rule/ruleml:if/ruleml:And/ruleml:Atom", ns)
            if name == "drop-condition":
                victim.getparent().remove(victim)
            else:
                victim.find("ruleml:Ind", ns).text = "invented-requirement"
        mutations.append({"id": name, "schema_accepts": xsd.validate(bad),
                          "identity_check_rejects": decode_rules(bad, ns) != data["rules"]})
    return {"status": "PASS" if schema_ok and roundtrip == data["rules"] and all(m["identity_check_rejects"] for m in mutations) else "FAILED",
            "schema_valid": schema_ok, "schema_errors": errors, "roundtrip": roundtrip,
            "roundtrip_equal": roundtrip == data["rules"], "mutation_controls": mutations,
            "xml": etree.tostring(root, pretty_print=True, encoding="unicode"),
            "profile": "Conditional requirements/consequence/modality/source references; human warrant and applicability remain outside logical semantics"}


def boolean_interchange(data):
    """Native RuleML Boolean expressions; unsupported expressions stay explicit."""
    from copy import deepcopy
    etree, _, xsd = xml_schema()
    ns = {"lrml": "http://docs.oasis-open.org/legalruleml/ns/v1.0/", "ruleml": "http://ruleml.org/spec"}
    rn = "{" + ns["ruleml"] + "}"
    ln = "{" + ns["lrml"] + "}"
    def encode(node):
        op = node["op"]
        if op in ("all", "any", "not"):
            out = etree.Element(rn + {"all": "And", "any": "Or", "not": "Neg"}[op])
            for child in ([node["arg"]] if op == "not" else node["args"]):
                out.append(encode(child))
        elif op == "fact" or (op == "literal" and node["type"] == "bool"):
            out = etree.Element(rn + "Atom")
            etree.SubElement(out, rn + "Rel").text = "input_fact" if op == "fact" else "boolean_constant"
            etree.SubElement(out, rn + "Ind").text = node["name"] if op == "fact" else str(node["value"]).lower()
        else:
            raise ValueError("Unsupported XML expression: " + op)
        out.set("key", node["node_id"])
        return out
    def decode(node):
        label = etree.QName(node).localname
        row = {"node_id": node.get("key")}
        if label in ("And", "Or"):
            return {**row, "op": "all" if label == "And" else "any", "args": [decode(c) for c in node]}
        if label == "Neg":
            return {**row, "op": "not", "arg": decode(node[0])}
        rel, value = node.findtext(rn + "Rel"), node.findtext(rn + "Ind")
        if rel == "input_fact":
            return {**row, "op": "fact", "name": value}
        if rel != "boolean_constant" or value not in ("true", "false"):
            raise ValueError("Unknown XML atom")
        return {**row, "op": "literal", "type": "bool", "value": value == "true"}
    rows = []
    for reading in data["readings"]:
        try:
            root = etree.Element(ln + "LegalRuleML", nsmap=ns)
            statement = etree.SubElement(etree.SubElement(root, ln + "Statements"), ln + "ConstitutiveStatement", key=reading["id"])
            rule = etree.SubElement(statement, rn + "Rule")
            for field, tag in (("scope", "if"), ("result", "then")):
                etree.SubElement(rule, rn + tag).append(encode(reading[field]))
            decoded = {f: decode(rule.find(rn + t)[0]) for f, t in (("scope", "if"), ("result", "then"))}
            equal = all(decoded[f] == reading[f] for f in decoded)
            valid = xsd.validate(root)
            errors = [str(e) for e in xsd.error_log]
            mutation = deepcopy(root)
            atom = mutation.find(".//ruleml:Ind", ns)
            atom.text = "invented_fact" if atom.text not in ("true", "false") else ("false" if atom.text == "true" else "true")
            mutated_rule = mutation.find(".//ruleml:Rule", ns)
            changed = any(decode(mutated_rule.find(rn + t)[0]) != reading[f] for f, t in (("scope", "if"), ("result", "then")))
            rows.append({"id": reading["id"], "status": "PASS" if valid and equal and changed else "FAILED",
                         "schema_errors": errors, "decoded": decoded, "mutation_detected": changed,
                         "xml": etree.tostring(root, encoding="unicode"),
                         "limit": "AST preservation only; unknown/conflict evaluation remains the product's explicit semantics"})
        except ValueError as exc:
            rows.append({"id": reading["id"], "status": "UNSUPPORTED", "reason": str(exc)})
    return {"status": "CHECKED", "readings": rows}


def main():
    operations = {"retrieval": retrieval, "interchange": interchange, "boolean": boolean_interchange}
    from scripts.legal_tool_worker import pyarg, citations
    operations.update(pyarg=pyarg, citations=citations)
    if len(sys.argv) != 4 or sys.argv[1] not in operations:
        raise SystemExit("Fixed worker operation required")
    source, target = [Path(p).resolve() for p in sys.argv[2:]]
    if not source.is_relative_to(ROOT) or not target.is_relative_to(ROOT):
        raise ValueError("Worker path outside worktree")
    value = operations[sys.argv[1]](json.loads(source.read_text()))
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
