"""Occurrence-aware finite clause interpretation; supplied meanings remain premises."""
from copy import deepcopy
import re
from .contracts import QueryResult, digest
from .predicates import names, decide

EFFECTS = {"principal_loss", "conversion", "repayment", "debt", "coupon",
           "statutory_loss", "creditor_amendment", "none", "unknown"}


def paragraphs(assembly):
    groups = []
    for u in assembly["units"]:
        if u["role"] in {"EXCLUDED", "HEADER", "INSTRUCTION"}:
            continue
        key = (u["context"], u["role"], u["source"]["document"], tuple(u["questions"]))
        if not groups or groups[-1]["key"] != key:
            groups.append({"key": key, "text": "", "parts": [], "unit": u})
        g = groups[-1]
        if g["parts"]:
            g["text"] += " "
        start = len(g["text"])
        g["text"] += u["text"]
        g["parts"].append((u, start, len(g["text"])))
    return groups


def nominate(assembly):
    nodes = []
    for group in paragraphs(assembly):
        text, ctx = group["text"], {}
        # The match owns its occurrence; .find(quote) is deliberately not used.
        matches = list(re.finditer(r"\S(?:.*?\S)?(?:(?<=[.!?])(?=\s|$)|$)", text, re.S))
        if not matches:
            matches = [None]
        for match in matches:
            start, end = (match.start(), match.end()) if match else (0, 0)
            sentence = text[start:end]
            u = group["unit"]
            spans = [{"unit": v["unit"], "start": max(start, a) - a, "end": min(end, b) - a}
                     for v, a, b in group["parts"] if min(end, b) > max(start, a)]
            node = {"id": u["unit"] + ":clause:" + str(len(nodes)), "units": [s["unit"] for s in spans] or [u["unit"]],
                    "spans": spans, "quote": sentence, "effect": "unknown", "actor": "unknown", "affected": "unknown",
                    "modality": "statement", "election": "none", "assets": [], "role": u["role"],
                    "polarity": True, "conditions": [], "exceptions": [], "questions": u["questions"],
                    "origin": "bounded-grammar-proposal"}
            if u["role"] == "EXAMPLE":
                node.update(effect="none", role="EXAMPLE")
            elif re.fullmatch(r"The following sentence is a non-operative example and has no legal effect: the Notes shall be converted into ordinary shares\.", sentence):
                node.update(effect="none", role="EXAMPLE")
            elif re.fullmatch(r"Conversion is solely at the holder's option\.", sentence):
                ctx["election"] = "holder"
                node.update(effect="none", actor="holder", affected="holder", election="holder")
            elif re.fullmatch(r"On exercise of that option, the Notes shall be converted into ordinary shares\.", sentence):
                node.update(effect="conversion", actor="issuer", affected="holder", election=ctx.get("election", "unknown"),
                            assets=["common"], modality="shall")
            elif sentence == "The Notes are unsecured obligations of the Issuer.":
                node.update(effect="debt", actor="issuer", affected="holder")
            elif sentence == "The Notes will be redeemed at 100 per cent of their principal amount at maturity.":
                node.update(effect="repayment", actor="issuer", affected="holder", modality="shall")
            elif re.fullmatch(r"Upon a Trigger Event, the principal amount of the Notes shall be written down to zero\.", sentence):
                node.update(effect="principal_loss", actor="issuer", affected="holder", trigger="Trigger Event", modality="shall")
            elif re.fullmatch(r"Upon a Solvency Event, the Issuer's obligation to repay the principal of the Notes ceases permanently without payment\.", sentence):
                node.update(effect="principal_loss", actor="issuer", affected="holder", trigger="Solvency Event", modality="shall")
            nodes.append(node)
    return nodes


def build(assembly, supplied=None):
    nodes = nominate(assembly) if supplied is None else deepcopy(supplied)
    units = {u["unit"]: u for u in assembly["units"]}
    ids = set()
    for n in nodes:
        if n["id"] in ids or n["effect"] not in EFFECTS:
            raise ValueError("Duplicate clause or unsupported typed effect")
        ids.add(n["id"])
        if not n["units"] or any(u not in units for u in n["units"]):
            raise ValueError("Unbound clause")
        if not n.get("quote") and n["effect"] != "unknown":
            raise ValueError("Nonempty semantic evidence required")
        if any(units[u]["role"] not in {"OPERATIVE", "EXAMPLE", "UNKNOWN"} for u in n["units"]):
            raise ValueError("Semantic assertion from excluded source")
        # Legacy unique quotations can migrate without guessing an occurrence.
        if "spans" not in n:
            if len(n["units"]) != 1 or units[n["units"][0]]["text"].count(n["quote"]) != 1:
                raise ValueError("Explicit occurrence spans required for duplicate or multiline quotations")
            pos = units[n["units"][0]]["text"].index(n["quote"])
            n["spans"] = [{"unit": n["units"][0], "start": pos, "end": pos + len(n["quote"])}]
        fragments = []
        previous = {}
        for s in n["spans"]:
            if set(s) != {"unit", "start", "end"} or s["unit"] not in n["units"]:
                raise ValueError("Invalid clause occurrence")
            a, b, text = s["start"], s["end"], units[s["unit"]]["text"]
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(text) or a < previous.get(s["unit"], 0):
                raise ValueError("Invalid or overlapping occurrence interval")
            previous[s["unit"]] = b
            fragments.append(text[a:b])
        if " ".join(fragments) != n["quote"] or (n["quote"] and list(dict.fromkeys(s["unit"] for s in n["spans"])) != n["units"]):
            raise ValueError("Clause quote differs from occurrence spans")
        for key in ("actor", "affected", "modality", "election", "role", "polarity", "questions", "assets", "conditions", "exceptions"):
            if key not in n:
                raise ValueError("Missing typed clause argument: " + key)
        if type(n["polarity"]) is not bool or not isinstance(n["assets"], list):
            raise ValueError("Explicit polarity and asset list required")
        if not isinstance(n["questions"], list) or set(n["questions"]) != set().union(
                *(set(units[u]["questions"]) for u in n["units"])):
            raise ValueError("Clause question scope must preserve its source-unit scope")
        if n["role"] == "OPERATIVE" and any(units[u]["role"] != "OPERATIVE" for u in n["units"]):
            raise ValueError("Unreviewed or example source cannot become an operative assertion")
        for key in ("conditions", "exceptions"):
            if isinstance(n[key], list):
                if any(not isinstance(x, str) for x in n[key]):
                    raise ValueError("Condition references must name clause nodes")
            else:
                names(n[key])
        if "predicate" in n:
            names(n["predicate"])
    edges = [{"from": n["id"], "to": target, "kind": key, "resolved": target in ids}
             for n in nodes for key in ("exceptions", "conditions") if isinstance(n[key], list) for target in n[key]]
    coverage = {u: set() for u in units}
    for n in nodes:
        for s in n["spans"]:
            coverage[s["unit"]].update(range(s["start"], s["end"]))
    uncovered = [u["unit"] for u in assembly["units"] if u["role"] in {"OPERATIVE", "UNKNOWN"}
                 and (not u["text"].strip() or any(i not in coverage[u["unit"]] and not ch.isspace()
                                                   for i, ch in enumerate(u["text"])))]
    return {"nodes": nodes, "edges": edges, "uncovered_units": uncovered,
            "assembly_sha256": digest(assembly),
            "origin": "assisted-proposal" if supplied is not None else "automatic-bounded-grammar"}


def active(node, by_id, observations):
    def expression(value, kind):
        if not isinstance(value, list):
            return value
        if not value:
            return kind == "conditions"
        return {"all" if kind == "conditions" else "any":
                [by_id.get(k, {}).get("predicate", "unresolved:" + k) for k in value]}
    return decide({"all": [expression(node["conditions"], "conditions"),
                           {"not": expression(node["exceptions"], "exceptions")}]}, observations)


def evaluate(graph, assembly, scope, dependencies, observations=None):
    observations = observations or {}
    results, by_id = {}, {n["id"]: n for n in graph["nodes"]}
    def answer(question, effects, conversion=None):
        relevant_units = {u["unit"] for u in assembly["units"] if question in u["questions"]}
        relevant = [n for n in graph["nodes"] if question in n["questions"]]
        unresolved = [n["id"] for n in relevant if n["effect"] == "unknown"]
        unresolved += [u["unit"] for u in assembly["units"] if question in u["questions"] and u["role"] == "UNKNOWN"]
        unresolved += sorted(relevant_units.intersection(graph["uncovered_units"]))
        unresolved += [d["id"] for d in dependencies if question in d["questions"] and d["status"] != "RESOLVED"]
        if not scope.get(question, {}).get("complete", False):
            unresolved.append("Question scope not complete: " + question)
        positives, negatives, conflicts, mixed, repayments = [], [], [], [], []
        for n in relevant:
            if n["role"] != "OPERATIVE" or n["effect"] not in effects | {"repayment"}:
                continue
            if n["actor"] == "unknown" or n["affected"] == "unknown":
                unresolved.append("Missing actor/affected interest: " + n["id"])
                continue
            activation = active(n, by_id, observations)
            if activation["status"] == "NO":
                continue
            if activation["status"] == "CONFLICT":
                conflicts.append(n["id"])
                continue
            if activation["status"] == "UNKNOWN":
                unresolved.append("Unresolved condition/exception: " + n["id"])
                continue
            if n["effect"] == "repayment":
                if n["polarity"]:
                    repayments.append(n["id"])
                continue
            if conversion:
                if not n["assets"] or n["election"] not in {"none", "issuer", "holder"}:
                    unresolved.append("Missing conversion arguments: " + n["id"])
                    continue
                if conversion == "common_only" and n["polarity"] and set(n["assets"]) != {"common"}:
                    mixed.append(n["id"])
                if "common" not in n["assets"]:
                    continue
                if conversion == "common_only" and set(n["assets"]) != {"common"}:
                    continue
                if conversion == "compulsory_common" and (n["election"] != "none" or n["modality"] not in {"shall", "automatic"}):
                    continue
            (positives if n["polarity"] else negatives).append(n["id"])
        if conflicts or (positives and negatives):
            status = "CONFLICT"
        elif unresolved:
            status = "UNKNOWN"
        elif mixed:
            status = "NO"
        elif positives:
            status = "YES"
        elif negatives or repayments:
            status = "NO"
        else:
            status = "UNKNOWN"
            unresolved.append("No affirmative absence/repayment interpretation")
        return QueryResult(question, status, status == "YES" if status in {"YES", "NO"} else None,
                           positives + negatives + conflicts + mixed, sorted(set(unresolved))).json()
    results["Q1"] = answer("Q1", {"principal_loss"})
    subs = {name: answer("Q2", {"conversion"}, name) for name in ("compulsory_common", "possible_common", "common_only")}
    results["Q2"] = {**subs["compulsory_common"], "subquestions": subs, "question_version": "Q2.v2",
                    "conversion_alternatives": [{k: n[k] for k in ("id", "actor", "election", "assets", "conditions", "exceptions")}
                                               for n in graph["nodes"] if n["effect"] == "conversion" and n["role"] == "OPERATIVE"]}
    results["Q1"]["statutory_disclosures"] = [n["id"] for n in graph["nodes"] if n["effect"] == "statutory_loss"]
    results["Q1"]["creditor_amendments"] = [n["id"] for n in graph["nodes"] if n["effect"] == "creditor_amendment"]
    complete = {q: {"complete": not results[q]["unresolved"], "unresolved": results[q]["unresolved"]} for q in ("Q1", "Q2")}
    results["Q3"] = QueryResult("Q3", "COMPLETE" if all(v["complete"] for v in complete.values()) else "PARTIAL",
                                complete, quantifier="Q1 and Q2 only; other declared questions added by service").json()
    return results
