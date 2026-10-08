"""Encode reviewed occurrences; retain the previous decisions without alteration."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor.contracts import digest

BASE = "basf-base-september-2022-exchange"
FINAL = "basf-2032-final"
BASELINE = "docs/implementation/prospectus-adoption/phases/A1/attempt-007/product.json"
GRAPH = "docs/implementation/prospectus-repair-2026-10-06/phases/P1/attempt-009/source-graph.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def historical(name):
    path = ROOT / name
    receipt = json.loads((path.parent / "receipt.json").read_text())
    assert sha(path) == receipt["outputs"][path.name]
    return json.loads(path.read_text())


graph = historical(GRAPH)
baseline = historical(BASELINE)
assert sha(ROOT / BASELINE) == "6c4172b8507803dbe898a8a0c7458c6882343c2604f36424e8e65b4c9384161f"
assert sha(OUT / "prior-review.json") == "cb793b799409816e0512dfc831a11ac48f0e04298a44e46684f7a978988e19eb"
data = json.loads((OUT / "prior-review.json").read_text())
units = {u["id"]: u for u in graph["units"]}
raw = baseline["raw_body"]


def source(key, start=0, end=None):
    unit = units[key]
    end = len(unit["raw"]) if end is None else end
    return {"unit": key, "document": unit["document"], "source_sha256": unit["source_sha256"],
            "start": start, "end": end, "quote": unit["raw"][start:end]}


def lines(document, page, first, last):
    return [source(f"{document}:p{page}:l{line}") for line in range(first, last + 1)]


def target(a, b):
    spans = []
    for span in baseline["source_map"]:
        left, right = max(a, span["start"]), min(b, span["end"])
        if left < right:
            spans.append(source(span["unit"], left - span["start"], right - span["start"]))
    return {"start": a, "end": b, "text": raw[a:b], "spans": spans}


review = "IMPLEMENTER_SOURCE_IMAGE_REVIEW; NOT INDEPENDENT LEGAL ADJUDICATION"
mapping = {s["unit"]: s for s in baseline["source_map"]}
parent = next(e for e in baseline["operations"] if e["reason"] == "different_rates")
a, b = mapping[f"{BASE}:p111:l54"]["start"], mapping[f"{BASE}:p111:l55"]["end"]
assert raw[a:b] == '(jeweils ein\n"Zinszahlungstag")'
data["rules"].append({"id": "different-rate-table-caption", "operation": "exclude_attached",
    "target": target(a, b), "attachment": {"decision": "different_rates",
        "branch": target(parent["start"], parent["end"])},
    "premises": lines(FINAL, 4, 1, 10), "governing": lines(BASE, 111, 38, 45),
    "reason": "Caption belongs to the excluded different-rate table; retain the single-rate definition",
    "review": review})
old_inventory = json.loads((ROOT / "docs/implementation/prospectus-basf-scope-repair/source-review-001/baseline-brackets.json").read_text())
by_id = {row["id"]: row for row in old_inventory}
dated = next(r for r in baseline["rules"] if r["rule"] == "dated_call:selected")
for name in ("B24", "B25", "B26", "B27"):
    row = by_id[name]
    assert raw[row["start"]:row["end"]] == "[\n]"
    assert dated["start"] < row["start"] < row["end"] < dated["end"]
    data["rules"].append({"id": name, "operation": "exclude",
        "target": target(row["start"], row["end"]),
        "premises": lines(FINAL, 6, 9, 21), "governing": lines(FINAL, 3, 10, 15),
        "reason": "Unused spare call-table cell; final terms supply one date range and amount",
        "review": review})

data["version"] = "basf-reviewed-scope.v2"
data["source_review"] = str((OUT / "REVIEW.md").relative_to(ROOT))
assert len(data["rules"]) == 67
assert data["rules"][:62] == baseline["scope_review"]["decisions"]
for rule in data["rules"]:
    bound = rule["target"]["spans"] + rule["premises"] + rule["governing"]
    bound += rule.get("attachment", {}).get("branch", {}).get("spans", [])
    assert all(s["unit"] in data["units"] for s in bound)
save(ROOT / "src/legalmath/prospectus/successor/basf_scope_review.json", data)

remaining = []
roles = {"B12": "heading §4(4)", "B13": "heading §4(5)", "B16": "heading §4(6)",
    "B21": "heading §5(4)", "B31": "heading §5(5)", "B35": "heading §5(8)",
    "B36": "heading §5(10)", "B37": "subheading §5(10)(a)", "B40": "§5(10)(b) refers to §5(5)",
    "B62": "list marker §6(2)(i)", "B66": "list marker §6(2)(iv)",
    "B79": "heading §13(3)", "B80": "§13(3) refers to §14(4)", "B82": "heading §14(4)"}
old_remaining = {(r["start"], r["end"]) for r in baseline["remaining_brackets"]}
for row in old_inventory:
    if (row["start"], row["end"]) not in old_remaining:
        continue
    status = "EXCLUDED_SPARE_CELL" if row["id"] in {"B24", "B25", "B26", "B27"} else "UNRESOLVED"
    remaining.append({**row, "status": status, "role": roles.get(row["id"], "calculation-agent name/office"),
        "reason": "No approved numbering transformation" if row["id"] in roles else
                  "No applicable designated-office evidence" if row["id"] == "B54" else "One populated final-terms row"})
save(OUT / "dispositions.json", remaining)

# An occurrence inventory, not automatic semantic resolution of references.
text = baseline["candidate_text"]
section, offset, headings, references = "", 0, [], []


def projection(start, end):
    result = []
    for entry in baseline["character_map"]:
        left, right = max(start, entry["start"]), min(end, entry["end"])
        if left >= right:
            continue
        if entry["operation"] == "COPY":
            x = entry["raw_start"] + left - entry["start"]
            result += target(x, x + right - left)["spans"]
        else:
            result.append({"substitution_basis": entry["basis"]})
    return result


for line in text.splitlines(keepends=True):
    if re.fullmatch(r"§ \d+", line.strip()):
        section = line.strip()
    record = {"section": section, "start": offset, "end": offset + len(line), "text": line,
              "context": text[max(0, offset - 130):offset + len(line) + 180],
              "sources": projection(offset, offset + len(line))}
    if re.match(r"^\[?\(\d+\)\]?", line):
        headings.append(record)
    if re.search(r"§|Absatz|Absätze|Absätzen|Absatzes", line) and not re.fullmatch(r"§ \d+", line.strip()):
        references.append(record)
    offset += len(line)
save(OUT / "reference-inventory.json", {"comparator": BASELINE, "headings": headings,
    "reference_candidates": references, "bracket_roles": roles,
    "raw_and_rendered_labels": "Identical; no renumbering performed",
    "status": "DIAGNOSTIC_INVENTORY; linguistic reference graph and numbering decision pending"})

margin_rows = []
for row in baseline["unit_accounting"]:
    if row["role"] not in {"MARGIN_INSTRUCTION", "PAGE_HEADER"}:
        continue
    margin_rows.append({"source": source(row["unit"]), "bbox": units[row["unit"]]["bbox"],
        "role": row["role"], "governing_rules": [r["id"] for r in data["rules"]
            if any(s["unit"] == row["unit"] for s in r["governing"])], "status": "UNRESOLVED"})
assert len(margin_rows) == 522
save(OUT / "margin-inventory.json", margin_rows)

evidence = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "review.json"}
old_review = ROOT / "docs/implementation/prospectus-basf-scope-repair/source-review-001"
for name in ("base-111.png", "base-120.png", "final-3.png", "final-4.png", "final-6.png"):
    evidence[str((old_review / name).relative_to(ROOT))] = sha(old_review / name)
save(OUT / "review.json", {"data_sha256": sha(ROOT / "src/legalmath/prospectus/successor/basf_scope_review.json"),
    "evidence": evidence, "comparator_sha256": sha(ROOT / BASELINE), "total_rules": 67,
    "new_rules": 5, "remaining_brackets": 15, "margin_header_obligations": 522,
    "independent_legal_review": False})
print(json.dumps({"rules": 67, "remaining_brackets": 15, "headings": len(headings),
                  "reference_candidate_lines": len(references), "margin_header_occurrences": len(margin_rows)}))
