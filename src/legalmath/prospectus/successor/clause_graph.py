"""Bounded English nomination plus explicitly supplied typed interpretations.

The grammar accounts for all sentences and returns unknown for unrecognized
language. Typed inputs are assisted premises, never independent legal labels.
"""
import re
from .contracts import QueryResult, digest
from .source_graph import REFERENCE

EFFECTS = {"principal_loss", "conversion", "repayment", "debt", "coupon",
           "statutory_loss", "creditor_amendment", "none", "unknown"}


def nominate(assembly):
    nodes, contexts = [], {}
    for unit in assembly["units"]:
        if unit["role"] in {"EXCLUDED", "HEADER", "INSTRUCTION"}:
            continue
        text = unit["text"]
        if unit["role"] == "EXAMPLE":
            nodes.append(_node(unit, text, "none", role="EXAMPLE"))
            continue
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        ctx = contexts.setdefault(unit["context"], {})
        for sentence in sentences:
            if not sentence.strip():
                nodes.append(_node(unit, sentence, "unknown"))
                continue
            low = sentence.lower()
            if re.fullmatch(r"The following sentence is a non-operative example and has no legal effect: the Notes shall be converted into ordinary shares\.", sentence):
                nodes.append(_node(unit, sentence, "none", role="EXAMPLE"))
            elif "solely at the holder's option" in low:
                ctx["election"] = "holder"
                nodes.append(_node(unit, sentence, "none", election="holder"))
            elif "on exercise of that option" in low and "converted into ordinary shares" in low:
                nodes.append(_node(unit, sentence, "conversion", election=ctx.get("election", "unknown"),
                                   assets=["common"], modality="shall"))
            elif re.fullmatch(r"The Notes are unsecured obligations of the Issuer\.", sentence):
                nodes.append(_node(unit, sentence, "debt"))
            elif re.fullmatch(r"The Notes will be redeemed at 100 per cent of their principal amount at maturity\.", sentence):
                nodes.append(_node(unit, sentence, "repayment"))
            elif re.fullmatch(r"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero\.", sentence):
                nodes.append(_node(unit, sentence, "principal_loss", trigger="Trigger Event", modality="shall"))
            elif re.fullmatch(r"Upon a Solvency Event, the Issuer's obligation to repay the principal of the Notes ceases permanently without payment\.", sentence):
                nodes.append(_node(unit, sentence, "principal_loss", trigger="Solvency Event", modality="shall"))
            else:
                nodes.append(_node(unit, sentence, "unknown"))
    for index, node in enumerate(nodes):
        node["id"] += ":" + str(index)
    return nodes


def _node(unit, quote, effect, **values):
    return {"id": unit["unit"] + ":" + str(digest(quote)[:16]), "units": [unit["unit"]],
        "quote": quote, "effect": effect, "actor": "issuer", "affected": "holder",
        "modality": "statement", "election": "none", "assets": [],
        "role": "OPERATIVE", "polarity": True, "conditions": [], "exceptions": [],
        "questions": unit["questions"], "origin": "bounded-grammar-proposal", **values}


def build(assembly, supplied=None):
    nodes = nominate(assembly) if supplied is None else supplied
    units = {u["unit"]: u for u in assembly["units"]}
    ids = set()
    for node in nodes:
        if node["id"] in ids or node["effect"] not in EFFECTS:
            raise ValueError("Duplicate clause or unsupported typed effect")
        ids.add(node["id"])
        if not node["units"] or any(u not in units for u in node["units"]):
            raise ValueError("Unbound clause")
        if not node.get("quote") and node["effect"] != "unknown":
            raise ValueError("Nonempty semantic evidence required")
        joined = " ".join(units[u]["text"] for u in node["units"])
        if node["quote"] not in joined:
            raise ValueError("Clause quotation not in assembled source")
        if any(units[u]["role"] not in {"OPERATIVE", "EXAMPLE", "UNKNOWN"} for u in node["units"]):
            raise ValueError("Semantic assertion from excluded source")
        for key in ("actor", "affected", "modality", "election", "role", "polarity", "questions", "assets", "conditions", "exceptions"):
            if key not in node:
                raise ValueError("Missing typed clause argument: " + key)
        if type(node["polarity"]) is not bool:
            raise ValueError("Explicit polarity required")
    edges = []
    for node in nodes:
        for key in ("exceptions", "conditions"):
            for target in node[key]:
                edges.append({"from": node["id"], "to": target, "kind": key, "resolved": target in ids})
    # Account for non-whitespace characters, not just presence of one quoted line.
    uncovered = []
    nodes_by_unit = {}
    for node in nodes:
        for key in node["units"]:
            nodes_by_unit.setdefault(key, []).append(node)
    for unit in assembly["units"]:
        if unit["role"] not in {"OPERATIVE", "UNKNOWN"}:
            continue
        coverage = [False] * len(unit["text"])
        for n in nodes_by_unit.get(unit["unit"], []):
            if len(n["units"]) == 1 and n["quote"]:
                pos = unit["text"].find(n["quote"])
                for i in range(pos, pos + len(n["quote"])):
                    coverage[i] = True
        if not unit["text"].strip() or any(not c and not ch.isspace() for c, ch in zip(coverage, unit["text"])):
            uncovered.append(unit["unit"])
    return {"nodes": nodes, "edges": edges, "uncovered_units": uncovered,
            "origin": "assisted-proposal" if supplied is not None else "automatic-bounded-grammar"}


def evaluate(graph, assembly, scope, dependencies):
    results = {}
    for question, effects in (("Q1", {"principal_loss"}), ("Q2", {"conversion"})):
        relevant_units = {u["unit"] for u in assembly["units"] if question in u["questions"]}
        relevant = [n for n in graph["nodes"] if question in n["questions"]]
        unresolved = [n["id"] for n in relevant if n["effect"] == "unknown"]
        unresolved += [u["unit"] for u in assembly["units"] if question in u["questions"] and u["role"] == "UNKNOWN"]
        unresolved += sorted(relevant_units.intersection(graph["uncovered_units"]))
        unresolved += [d["id"] for d in dependencies if question in d["questions"] and d["status"] != "RESOLVED"]
        unresolved += [e["to"] for e in graph["edges"] if not e["resolved"] and
                       any(n["id"] == e["from"] for n in relevant)]
        if not scope.get(question, {}).get("complete", False):
            unresolved.append("Question scope not complete: " + question)
        positives, negatives = [], []
        for n in relevant:
            if n["role"] != "OPERATIVE" or n["effect"] not in effects:
                continue
            if n["conditions"] or n["exceptions"]:
                # Relations are retained but truth/priority is never guessed.
                unresolved.append("Unresolved condition/exception: " + n["id"])
                continue
            if question == "Q2":
                if n["election"] == "holder":
                    continue
                if n["election"] not in {"none", "issuer"} or not n["assets"]:
                    unresolved.append("Missing conversion arguments: " + n["id"])
                    continue
                if n["assets"] != ["common"]:
                    continue
            (positives if n["polarity"] else negatives).append(n["id"])
        if positives and negatives:
            status = "CONFLICT"
        elif unresolved:
            status = "UNKNOWN"
        elif positives:
            status = "YES"
        elif any(n["effect"] == "repayment" and n["polarity"] and n["role"] == "OPERATIVE" for n in relevant):
            status = "NO"
        else:
            status = "UNKNOWN"
            unresolved.append("No affirmative absence/repayment interpretation")
        results[question] = QueryResult(question, status, status == "YES" if status in {"YES", "NO"} else None,
            positives + negatives, sorted(set(unresolved))).json()
    results["Q2"]["conversion_alternatives"] = [{k: n[k] for k in
        ("id", "actor", "election", "assets", "conditions", "exceptions")} for n in graph["nodes"]
        if n["effect"] == "conversion" and n["role"] == "OPERATIVE"]
    results["Q1"]["statutory_disclosures"] = [n["id"] for n in graph["nodes"] if n["effect"] == "statutory_loss"]
    results["Q1"]["creditor_amendments"] = [n["id"] for n in graph["nodes"] if n["effect"] == "creditor_amendment"]
    results["Q3"] = QueryResult("Q3", "COMPLETE" if all(not results[q]["unresolved"] for q in ("Q1", "Q2")) else "PARTIAL",
        {q: {"complete": not results[q]["unresolved"], "unresolved": results[q]["unresolved"]} for q in ("Q1", "Q2")}).json()
    return results
