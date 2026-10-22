"""Optional source-complete supplied BASF Note22 interpretation and diagnostics."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
import math
from pathlib import Path
import re

from . import basf_pension_spec as spec
from . import basf_statement, basf_hedge_note
from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = "basf-pension-note-review.v1"
DOCUMENT = basf_statement.DOCUMENT


def quantity(literal, kind):
    """Retain exact types and source dashes without numerical imputation."""
    if kind == "text":
        if not isinstance(literal, str) or not literal:
            raise ValueError("Printed reference text required")
        return {"literal": literal, "kind": kind, "status": "PRINTED_TEXT", "value": None, "unit": None}
    units = {"million_eur": "million EUR", "percent": "%", "supplied_rate_percent": "%"}
    if kind not in units:
        raise ValueError("Unsupported pension quantity type")
    if kind == "supplied_rate_percent":
        if literal != "–" and (not isinstance(literal,str) or re.fullmatch(r"[0-9]+\.[0-9]{2}",literal) is None):
            raise ValueError("Original two-decimal rate or dash required")
        value = None if literal == "–" else str(Decimal(literal))
        status = "PRINTED_DASH_UNKNOWN" if value is None else "PRINTED_DECIMAL"
    else:
        parsed = basf_statement.integer_millions(literal)
        value, status = parsed["integer_millions"], parsed["status"]
        if kind == "percent" and value is not None and not 0 <= value <= 100:
            raise ValueError("Allocation percentage outside its source meaning")
    return {"literal": literal, "kind": kind, "status": status, "value": value, "unit": units[kind],
            "unit_basis": "SUPPLIED_CONVENTIONAL_RATE_UNIT_NOT_PRINTED" if kind == "supplied_rate_percent" else "PRINTED_TABLE_UNIT"}


def original_span(unit, selector):
    if isinstance(selector, int):
        return 0, len(unit["raw"])
    number, part = selector.split(":")
    marker = spec.SHARED[int(number)]
    raw = unit["raw"]
    if raw.count(marker) != 1:
        raise ValueError("Unique original cross-column split required")
    split = raw.index(marker)
    if split < 1 or raw[split-1] != " ":
        raise ValueError("Original cross-column separator changed")
    return {"left": (0,split-1), "separator": (split-1,split), "right": (split,len(raw))}[part]


def box(anchors):
    return [min(a["bbox"][0] for a in anchors), min(a["bbox"][1] for a in anchors),
            max(a["bbox"][2] for a in anchors), max(a["bbox"][3] for a in anchors)]


def overlap(left, right, axis):
    return max(left[axis], right[axis]) < min(left[axis+2], right[axis+2])


def evaluate(graph, prior, profile, root, *, expected_profile_sha256):
    keys = {"version","graph_sha256","prior_sha256","reviewer","source","metadata","prose","tables",
            "typographic","shared_separators","excluded_note23","selected_reading","financial_values_validated"}
    fields(profile, keys, keys)
    if (profile["version"] != VERSION or digest(profile) != expected_profile_sha256
            or profile["graph_sha256"] != digest(graph) or profile["prior_sha256"] != digest(prior)):
        raise ValueError("Pinned pension profile, graph or complete previous consumer changed")
    if profile["selected_reading"] is not None or profile["financial_values_validated"] is not False:
        raise ValueError("Pension reading cannot select incorporation or validate accounts")
    reviewer = profile["reviewer"]
    fields(reviewer, {"identity","basis","independent"}, {"identity","basis","independent"})
    if (not isinstance(reviewer["identity"],str) or not reviewer["identity"].strip()
            or reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or reviewer["independent"] is not False):
        raise ValueError("Unsupported pension review authority")
    source = profile["source"]
    fields(source, {"document","path","sha256","images"}, {"document","path","sha256","images"})
    if source["document"] != DOCUMENT or [p["page"] for p in source["images"]] != list(spec.COUNTS):
        raise ValueError("All six original pension pages required")
    root = Path(root).resolve()
    for item in [source, *source["images"]]:
        name = item["path"]; path = (root/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != item["sha256"]:
            raise ValueError("Original pension PDF or reviewed image changed")
    units = {u["id"]:u for u in graph["units"]}
    pages = [u for u in graph["units"] if u["document"] == DOCUMENT and u["page"] in spec.COUNTS and u["visible"]]
    if (len(units) != len(graph["units"]) or {p:sum(u["page"]==p for u in pages) for p in spec.COUNTS} != spec.COUNTS
            or any(u["source_sha256"] != source["sha256"] or u["text_sha256"] != digest(u["raw"].encode()) for u in pages)):
        raise ValueError("Complete original pension occurrence inventory changed")
    used = defaultdict(list)

    def original(anchors, page, selectors):
        if not isinstance(anchors,list) or len(anchors) != len(selectors):
            raise ValueError("Complete pension source-fragment inventory required")
        result = []
        for a, selector in zip(anchors, selectors):
            number = int(str(selector).split(":")[0])
            unit = units[DOCUMENT+":p"+str(page)+":l"+str(number)]
            start,end = original_span(unit,selector)
            b = bind(graph,a)
            if (b["unit"] != unit["id"] or b["start"] != start or b["end"] != end
                    or b["document"] != DOCUMENT or b["page"] != page or b["source_sha256"] != source["sha256"]):
                raise ValueError("Exact original pension occurrence/character association required")
            bounds = b["bbox"]
            if (not isinstance(bounds,list) or len(bounds)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in bounds)
                    or bounds[0]>=bounds[2] or bounds[1]>=bounds[3]):
                raise ValueError("Finite original pension geometry required")
            used[unit["id"]].append((start,end)); result.append(b)
        return result

    fields(profile["metadata"], {str(p) for p in spec.COUNTS}, {str(p) for p in spec.COUNTS})
    metadata = {str(p):original(profile["metadata"][str(p)],p,[0,1,2]) for p in spec.COUNTS}
    if list(profile["prose"]) != list(spec.PROSE):
        raise ValueError("Every pension paragraph and qualification required")
    prose = {}
    for key,(page,selectors,column,meaning) in spec.PROSE.items():
        p = profile["prose"][key]
        fields(p,{"column","meaning","anchors"},{"column","meaning","anchors"})
        if p["column"] != column or p["meaning"] != meaning:
            raise ValueError("Pension qualification, country or reading column changed")
        prose[key] = {**deepcopy(p), "anchors":original(p["anchors"],page,selectors)}
    fields(profile["typographic"],{str(p) for p in spec.TYPOGRAPHIC},{str(p) for p in spec.TYPOGRAPHIC})
    typography = {str(p):original(profile["typographic"][str(p)],p,ids) for p,ids in spec.TYPOGRAPHIC.items()}
    if any(a["quote"] != "\xad" for aa in typography.values() for a in aa):
        raise ValueError("Original isolated soft hyphens required")
    separators = original(profile["shared_separators"],261,[str(n)+":separator" for n in spec.SHARED])
    if any(a["quote"] != " " for a in separators):
        raise ValueError("Shared occurrence separator changed")
    excluded = original(profile["excluded_note23"],266,spec.EXCLUDED)
    if [a["quote"] for a in excluded[:2]] != ["23","Other provisions"] or any(a["bbox"][0]<298 for a in excluded):
        raise ValueError("Actual mixed-column Note23 boundary required")

    if list(profile["tables"]) != list(spec.TABLES):
        raise ValueError("All eleven pension tables required")
    tables = {}
    for key, t in spec.TABLES.items():
        p = profile["tables"][key]; page=t["page"]
        fields(p,{"page","kind","scope","title","unit","columns","groups","rows"},
                 {"page","kind","scope","title","unit","columns","groups","rows"})
        if any(p[k] != t[k] for k in ("page","kind","scope")):
            raise ValueError("Pension table type, page or financial scope changed")
        title = original(p["title"],page,t["title"])
        unit = original(p["unit"],page,t["unit"])
        if t["kind"] in ("million_eur","percent") and [a["quote"] for a in unit] != ["Million €" if t["kind"]=="million_eur" else "%"]:
            raise ValueError("Printed pension table unit changed")
        if [c["id"] for c in p["columns"]] != [c[0] for c in t["columns"]] or len(p["groups"]) != len(t["groups"]):
            raise ValueError("Complete ordered pension columns and grouped headers required")
        columns=[]; headers={}
        for c,(name,ids) in zip(p["columns"],t["columns"]):
            fields(c,{"id","anchors"},{"id","anchors"})
            anchors=original(c["anchors"],page,ids)
            headers[name]=anchors; columns.append({"id":name,"anchors":anchors})
        groups=[]
        for g,(ids,members) in zip(p["groups"],t["groups"]):
            fields(g,{"members","anchors"},{"members","anchors"})
            if g["members"] != members:
                raise ValueError("Country,year or sensitivity grouped-header association changed")
            groups.append({"members":members,"anchors":original(g["anchors"],page,ids)})
        if [r["id"] for r in p["rows"]] != [r["id"] for r in t["rows"]]:
            raise ValueError("Complete ordered pension rows required")
        rows=[]; last_bottom=box(title)[3]
        for r, expected in zip(p["rows"],t["rows"]):
            fields(r,{"id","parent","label","cells"},{"id","parent","label","cells"})
            if r["parent"] != expected["parent"]:
                raise ValueError("Included of-which row scope changed")
            label=original(r["label"],page,expected["label"]); lb=box(label)
            if lb[1] <= last_bottom:
                raise ValueError("Pension row geometry/order changed")
            last_bottom=lb[3]
            fields(r["cells"],headers,headers)
            cells={}
            for (name,_),ids,literal in zip(t["columns"],expected["cells"],expected["values"]):
                anchors=original(r["cells"][name],page,ids); cb=box(anchors)
                if " ".join(a["quote"] for a in anchors) != literal:
                    raise ValueError("Original pension cell literal changed")
                if not overlap(lb,cb,1) or lb[2]>=cb[0]:
                    raise ValueError("Pension cell row/label geometry changed")
                if headers[name]:
                    hb=box(headers[name])
                    if hb[3]>=cb[1] or not overlap(hb,cb,0):
                        raise ValueError("Pension cell column/header geometry changed")
                cells[name]={**quantity(literal,t["kind"]),"source":anchors}
            rows.append({"id":r["id"],"parent":r["parent"],"label":label,"cells":cells})
        tables[key]={"page":page,"kind":t["kind"],"scope":t["scope"],"title":title,"unit":unit,
                     "columns":columns,"groups":groups,"rows":rows}
    if set(used) != {u["id"] for u in pages}:
        raise ValueError("Missing or extra original pension occurrence")
    for u in pages:
        spans=sorted(used[u["id"]]); end=0
        for start,stop in spans:
            if start!=end or stop<=start:
                raise ValueError("Every original pension character must occur exactly once")
            end=stop
        if end != len(u["raw"]):
            raise ValueError("Incomplete original pension character coverage")
    incorporation=prior["answer"]["incorporation"]
    if incorporation["status"] != "UNRESOLVED" or incorporation["selected_reading"] is not None:
        raise ValueError("Both original unresolved incorporation alternatives required")
    alternatives=[{"id":r["id"],"condition":r["condition"],
        "all_note_pages_in_candidate":set(spec.COUNTS)<=set(r["candidate_pages"]),
        "legal_incorporation_established":False} for r in incorporation["readings"]]
    if len(alternatives)!=2 or not all(r["all_note_pages_in_candidate"] for r in alternatives):
        raise ValueError("Original pension note scope under both alternatives changed")
    result={"version":VERSION,"profile_sha256":digest(profile),"metadata":metadata,"prose":prose,
        "tables":tables,"typographic":typography,"shared_separators":separators,"excluded_note23":excluded,
        "page_occurrences_accounted":len(used),"note_occurrences":len(used)-len(excluded),
        "excluded_occurrences":len(excluded),"all_original_characters_once":True,
        "printed_cells":sum(len(r["cells"]) for t in tables.values() for r in t["rows"]),
        "incorporation_alternatives":alternatives,"selected_reading":None,"financial_values_validated":False,
        "independent_legal_acceptance":False,"field_associations":"SUPPLIED_EXPOSED_REVIEW",
        "profile":deepcopy(profile)}
    result["comparisons"]=diagnostics(tables,prior)
    result["answer"]=explain(result,prior)
    return result


def comparison(name, left, right, *, scope):
    """Signed exact sums of one quantity type; an unknown vetoes arithmetic."""
    quantities=[q for sign,q in left+right]
    if any(type(s) is not int or s not in (-1,1) for s,q in left+right):
        raise ValueError("Explicit signed accounting association required")
    if not quantities or len({(q["kind"],q["unit"]) for q in quantities}) != 1:
        raise ValueError("Cannot compare different pension quantity types")
    if quantities[0]["kind"] not in {"million_eur","percent"}:
        raise ValueError("Rate sensitivity and reference text are not additive")
    known=all(q["value"] is not None for q in quantities)
    residual=sum(s*q["value"] for s,q in left)-sum(s*q["value"] for s,q in right) if known else None
    return {"name":name,"left":[{"sign":s,"quantity":deepcopy(q)} for s,q in left],
        "right":[{"sign":s,"quantity":deepcopy(q)} for s,q in right],"left_minus_right":residual,
        "status":"UNKNOWN_COMPONENT" if not known else "EQUAL_PRINTED_VALUES" if residual==0 else "PRINTED_DIFFERENCE",
        "scope":scope,"role":"EXPLANATORY_ONLY"}


def diagnostics(tables,prior):
    rows={k:{r["id"]:r for r in t["rows"]} for k,t in tables.items()}
    def q(table,row,col):return rows[table][row]["cells"][col]
    out=[]
    def check(name,left,right,scope):out.append(comparison(name,left,right,scope=scope))
    for y in ("2022","2021"):
        for t in ("dbo","assets","net"):
            parts=[(1,r["cells"][y]) for r in tables[t]["rows"] if r["parent"] is None and r["id"]!="closing"]
            check(t+":"+y+":movement",[(1,q(t,"closing",y))],parts,"Opening balance plus primary movements; of-which rows excluded")
        check("dbo:"+y+":actuarial",[(1,q("dbo","actuarial",y))],
            [(1,q("dbo",r,y)) for r in ("financial_assumptions","demographic_assumptions","experience")],
            "Three printed actuarial components of the parent movement")
        check("net:"+y+":assets-minus-provisions",[(1,q("net","closing",y))],
            [(1,q("net","benefit_assets",y)),(-1,q("net","provisions",y))],"Printed negative net-liability convention")
        for target,parts in (("operating",("defined_benefit","defined_contribution")),("financial",("underfunded_interest","overfunded_interest"))):
            check("expenses:"+y+":"+target,[(1,q("expenses",target,y))],[(1,q("expenses",r,y)) for r in parts],"Same printed expense subtotal")
        for target,parts in (("total",("equity","debt","real_estate","alternative","cash")),("debt",("government","other_debt"))):
            check("allocation:"+y+":"+target,[(1,q("asset_structure",target,y))],[(1,q("asset_structure",r,y)) for r in parts],"Percent allocations; subordinate debt rows are included once")
        for t in ("dbo","assets","ceiling","net"):
            col=t+":"+y
            check("regional:"+col,[(1,q("regional","total",col))],
                [(1,r["cells"][col]) for r in tables["regional"]["rows"] if r["id"]!="total"],"Sum of printed country balances; no dash imputation")
            other=q(t,"closing",y) if t in ("dbo","assets","net") else q("net","ceiling",y)
            check("regional-vs-movement:"+col,[(1,q("regional","total",col))],[(1,other)],"Same dated aggregate, gross assets distinguished from funding total")
        for country in rows["regional"]:
            check("regional-net:"+country+":"+y,[(1,q("regional",country,"net:"+y))],
                [(1,q("regional",country,"assets:"+y)),(-1,q("regional",country,"dbo:"+y)),(1,q("regional",country,"ceiling:"+y))],
                "Assets minus obligations plus printed signed ceiling; a dash leaves the comparison unknown")
        for kind in ("dbo","assets"):
            col=y+":"+kind
            check("funding-total:"+col,[(1,q("funding","total",col))],
                [(1,q("funding",r,col)) for r in ("unfunded","funded","ceiling")],"Full printed column sum with dashes retained")
        check("funding-dbo:"+y,[(1,q("funding","total",y+":dbo"))],[(1,q("dbo","closing",y))],"Same obligation balance")
        check("funding-gross-assets:"+y,[(1,q("funding","funded",y+":assets"))],[(1,q("assets","closing",y))],"Funded gross assets before ceiling")
        check("funding-after-ceiling:"+y,[(1,q("funding","total",y+":assets"))],
            [(1,q("assets","closing",y)),(1,q("net","ceiling",y))],"Gross assets plus signed ceiling; no zero substitution for prior-year dash")
        check("funding-net:"+y,[(1,q("net","closing",y))],
            [(1,q("funding","total",y+":assets")),(-1,q("funding","total",y+":dbo"))],"Funding total after ceiling minus obligation")
        source_row=next(r for r in prior["statement_review"]["rows"] if r["id"]=="pensions")["cells"][y]
        statement_q={"kind":"million_eur","unit":"million EUR","value":source_row["integer_millions"],"source":deepcopy(source_row)}
        check("candidate-remeasurement-bridge:"+y,[(1,statement_q)],
            [(1,q("net",r,y)) for r in ("actuarial","return_deviation","ceiling")],
            "Candidate comparison only: common complete scope with statement remeasurement is not established; residual cannot be attributed to rounding or similar obligations")
        out[-1]["scope_equivalence_established"]=False
        out.append({"name":"note20-net-vs-note22-gross:"+y,"role":"EXPLANATORY_ONLY",
            "status":"SCOPE_EQUIVALENCE_NOT_ESTABLISHED","left_minus_right":None,
            "note20":deepcopy(prior["oci_note_review"]["amounts"]["pension_net_"+y]),
            "reason":"Note20 includes deferred taxes and equity-method components; Note22 movements cannot be equated to that after-tax amount."})
    return out


def explain(review,prior):
    prose=review["prose"]; tables=review["tables"]
    bridge=[c for c in review["comparisons"] if c["name"].startswith("candidate-remeasurement-bridge:")]
    return {"status":"SUPPLIED_CONDITIONAL_SOURCE_INTERPRETATION",
        "summary":"BASF's pension disclosure depends on local funding and employer-support rules as well as accounting measurement. Gross plan assets, asset ceilings, signed net liabilities, pension expenses and after-tax OCI have distinct scopes.",
        "country_qualifications":{c:{"source":deepcopy(prose[c]),"basis":"REPORT_DESCRIPTION_NOT_INDEPENDENT_CURRENT_LAW"}
                                  for c in ("germany","us","switzerland","uk")},
        "subsidiary_liability":deepcopy(prose["subsidiary_liability"]),
        "funding": {"source":deepcopy(prose["asset_ceiling"]),"table":deepcopy(tables["funding"]),
            "interpretation":"The2022 funded plan assets20,083million become19,652million after the431million ceiling. These are different printed quantities; a positive Swiss asset surplus does not imply that every surplus is an available economic benefit."},
        "sensitivity":{"source":deepcopy(prose["sensitivity_limit"]),"table":deepcopy(tables["sensitivity"]),
            "linear_extrapolation_permitted":False,"combined_change_addition_permitted":False},
        "measurement":{"timing":deepcopy(prose["assumption_timing"]),"model_change":deepcopy(prose["discount_change"]),
            "interest_timing":deepcopy(prose["interest_timing"]),"rate_unit_basis":"SUPPLIED_CONVENTION_NOT_PRINTED"},
        "oci":{"recognition_rule":deepcopy(prose["oci_rule"]),"candidate_comparisons":bridge,
            "unique_complete_bridge_established":False,"rounding_cause_established":False,
            "interpretation":"The note explains direct-equity recognition and supplies component movements. It does not establish a unique complete reconciliation to the earlier statement and after-tax Note20 amount."},
        "incorporation":deepcopy(review["incorporation_alternatives"]),
        "previous_onward_requirement":deepcopy(prior["oci_note_review"]["onward_requirements"][0]),
        "full_note_transcription_supplied":True,"independent_financial_acceptance":False,
        "independent_legal_acceptance":False,"financial_values_validated":False,"selected_reading":None}


def consume(products, prior_profiles, hedge_profile, profile, root, *,
            expected_prior_profiles_sha256, expected_hedge_profile_sha256, expected_profile_sha256,
            reconciliation_profile=None, expected_reconciliation_profile_sha256=None):
    prior=basf_hedge_note.consume(products,prior_profiles,hedge_profile,root,
        expected_prior_profiles_sha256=expected_prior_profiles_sha256,expected_profile_sha256=expected_hedge_profile_sha256)
    review=evaluate(products["P1"]["payload"]["graph"],prior,profile,root,expected_profile_sha256=expected_profile_sha256)
    result={**prior,"pension_note_review":review,"pension_explanation":deepcopy(review["answer"])}
    if reconciliation_profile is None:
        if expected_reconciliation_profile_sha256 is not None:
            raise ValueError("Reconciliation profile required with its expected identity")
        return result
    from .basf_pension_reconciliation import evaluate as reconcile
    reconciled=reconcile(products["P1"]["payload"]["graph"],result,reconciliation_profile,root,
        expected_profile_sha256=expected_reconciliation_profile_sha256)
    return {**result,"pension_reconciliation_review":reconciled,
            "pension_reconciliation_explanation":deepcopy(reconciled["answer"])}
