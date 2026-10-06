"""Typed, source-bound legal-premise evaluation with explicit scope and uncertainty.

The engine evaluates declared interpretations. It does not derive or adjudicate
those interpretations from unrestricted legal prose.
"""
from datetime import date
from fractions import Fraction
from pathlib import Path
import re
from .common import digest, read, sha


def truth_all(values):
    return False if False in values else None if None in values else True


def expression(node, facts):
    if type(node) is bool or node is None:
        return node
    if not isinstance(node, dict) or len(node) != 1:
        raise ValueError("One typed operator required")
    op, value = next(iter(node.items()))
    if op == "fact":
        values = facts.get(value, [])
        if not isinstance(values, list):
            raise ValueError("Fact must retain a list of observations")
        present = [v for v in values if v is not None]
        if any(type(v) is not bool for v in present):
            raise ValueError("Boolean premise expected")
        return present[0] if present and len(set(present)) == 1 else None
    if op in ("all", "any"):
        if not isinstance(value,list) or not value:
            raise ValueError("Nonempty expression list required")
        values = [expression(n, facts) for n in value]
        return truth_all(values) if op == "all" else True if True in values else None if None in values else False
    if op == "not":
        result = expression(value, facts)
        return None if result is None else not result
    if op == "elapsed_days_at_least":
        if not isinstance(value,list) or len(value)!=3 or type(value[2]) is not int or value[2]<0:
            raise ValueError("Two date premise names and a nonnegative day count required")
        dates=[]
        for name in value[:2]:
            values=facts.get(name,[])
            if not values or any(v is None for v in values) or len(set(values))!=1:
                return None
            dates.append(date.fromisoformat(values[0]))
        return (dates[1]-dates[0]).days >= value[2]
    if op in ("before", "on_or_after"):
        if not isinstance(value,list) or len(value)!=2:
            raise ValueError("Two date premises required")
        dates=[]
        for name in value:
            values=facts.get(name,[])
            if not isinstance(values,list):
                raise ValueError("Date premise must retain observations")
            if not values or any(v is None for v in values) or len(set(values)) != 1:
                return None
            dates.append(date.fromisoformat(values[0]))
        return dates[0]<dates[1] if op=="before" else dates[0]>=dates[1]
    raise ValueError("Unknown rule operator: " + str(op))


def check_anchors(anchors, sources, root):
    if not anchors:
        raise ValueError("A source-bound rule needs anchors")
    checked=[]
    for anchor in anchors:
        source=sources[anchor["source_key"]]
        original=Path(root)/source["original"]
        text_path=Path(root)/source["text"]
        if sha(original.read_bytes()) != anchor["source_sha256"] or source["sha256"] != anchor["source_sha256"]:
            raise ValueError("Changed legal source")
        if sha(text_path.read_bytes()) != source["text_sha256"]:
            raise ValueError("Changed legal extraction")
        text=text_path.read_text()
        if "paragraph" in anchor:
            parts=re.split(r"\n(?=\d+\n)",text)
            paragraphs={p.split("\n",1)[0]:p.split("\n",1)[1] for p in parts if re.match(r"^\d+\n",p)}
            text=paragraphs.get(str(anchor["paragraph"]),"")
        elif "page" in anchor:
            pages=text.split("\f")
            if pages and not pages[-1].strip():pages.pop()
            if type(anchor["page"]) is not int or not 1 <= anchor["page"] <= len(pages):
                raise ValueError("Invalid bound source page")
            text=pages[anchor["page"]-1]
        norm=lambda value:" ".join(value.split())
        if norm(anchor["quote"]) not in norm(text):
            raise ValueError("Source anchor does not replay")
        checked.append(dict(anchor))
    return checked


def evaluate_rule(rule, context, sources, root):
    anchors=check_anchors(rule["anchors"],sources,root)
    problems=[]
    for field, allowed in rule["scope"].items():
        actual=context.get(field)
        if actual is None:
            problems.append("MISSING_SCOPE:"+field)
        elif actual not in allowed:
            problems.append("OUT_OF_SCOPE:"+field)
    known=context.get("known_at")
    if not known:
        problems.append("MISSING_KNOWLEDGE_DATE")
    elif date.fromisoformat(known)<date.fromisoformat(rule["source_date"]):
        problems.append("SOURCE_POSTDATES_KNOWLEDGE")
    facts=context.get("facts",{})
    # Sources may contain assumptions, allegations and dissents. Keep their role;
    # they cannot become findings by changing only the requested result name.
    if context.get("requested_stage") != rule["stage"]:
        problems.append("STAGE_MISMATCH")
    value=expression(rule["condition"],facts) if not problems else None
    if value is None and not problems:
        problems.append("MISSING_OR_CONFLICTING_PREMISE")
    result={"rule_id":rule["id"],"conclusion":rule["conclusion"],
            "stage":rule["stage"],"value_under_declared_premises":value,
            "status":"UNRESOLVED" if problems else "CONDITIONAL",
            "issues":problems,"anchors":anchors,"rule_hash":digest(rule),
            "context_hash":digest(context),"independent_legal_adjudication":False,
            "source_interpretation":"DECLARED_AND_ANCHORED_NOT_INDEPENDENTLY_PROVED",
            "certified_legal_answer":None,"may_execute_transaction":False}
    if rule.get("arithmetic") and value is True:
        # Exact complement of an expressly supplied remaining percentage.
        name=rule["arithmetic"]["remaining_percent"]
        values=facts.get(name,[])
        if not isinstance(values,list) or len(values)!=1 or not isinstance(values[0],str):
            result["status"]="UNRESOLVED";result["issues"].append("MISSING_REMAINING_PERCENT")
        else:
            remaining=Fraction(values[0])
            if not 0<=remaining<=100:
                raise ValueError("Percentage outside 0..100")
            result["reported_remaining_percent"]=str(remaining)
            result["implied_reduction_percent"]=str(100-remaining)
            result["ultimate_recovery"]="NOT_ESTABLISHED"
    result["receipt_hash"]=digest(result)
    return result


def investigate(issue, documents, context_packet, root):
    """Join contractual reading, dependency checks and scoped external-law outputs."""
    from .loss_absorption_reader import analyze_issue
    contractual=analyze_issue(issue,documents,root)
    legal=[evaluate_rule(r,context_packet["context"],context_packet["sources"],root)
           for r in context_packet["rules"]]
    return {"contractual":contractual,"external_law":legal,
            "status":"UNRESOLVED" if contractual["answer"] is None or any(
                r["status"]=="UNRESOLVED" for r in legal) else "CONDITIONAL",
            "certified_legal_answer":None,"may_execute_transaction":False,
            "qualification":"Contractual features and external legal conclusions retain their distinct source, date and premise conditions."}
