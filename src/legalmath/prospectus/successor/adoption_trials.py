"""Recorded, offline optional-tool comparisons on frozen development inputs."""
from fractions import Fraction
import os
from pathlib import Path
import sys
from .contracts import digest, read, write
from .adoption_jobs import REL, parent


def run_sidecar(root, folder, context, kind, data, timeout=180):
    path = folder / (kind + "-input.json")
    write(path, data)
    destination = folder / kind
    argv = [str(root / ".venv/bin/python"), "-m", "scripts.prospectus_adoption_sidecar", kind,
            "--input", str(path), "--output", str(destination)]
    # Bind the interpreter actually used, resolved distributions and worker.
    context.tool(["/tmp/prospectus-adoption-tools/bin/python", "--version"], timeout=15)
    site = Path("/tmp/prospectus-adoption-tools/lib/python3.11/site-packages")
    # Version/RECORD alone misses changed source or extension bytes under an old
    # version. Bind the whole sidecar distribution, without duplicating its files.
    context.external_tree(site)
    context.read_bytes("scripts/prospectus_adoption_sidecar.py")
    run = context.tool(argv, timeout=timeout, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"})
    (folder / (kind + "-worker.log")).write_bytes(run.stdout + run.stderr)
    if not (destination / "result.json").exists():
        return {"execution": "FAILED", "error": "Worker omitted result", "returncode": run.returncode}
    return read(destination / "result.json")


def layout_trial(root, folder, state, context):
    from .annotation_bridge import export, reimport
    from .layout_adapter import map_layout, project_layout, evaluate_relationships
    setup = context.read_json(REL + "/tool-setup/attempt-001/result.json")
    context.read_bytes(REL + "/tool-setup/attempt-001/pip-report.json")
    context.read_bytes(REL + "/tool-setup/attempt-001/inception-38-pom.xml")
    context.read_bytes(REL + "/tool-setup/attempt-001/inception-38-offsets.ts")
    context.read_bytes("docs/research/prospectus-adoption-2026-10-07/sources/inception-curation/source.html")
    text = "😀 Recht e\u0301gal. Same. Same.\nNo loss except\nunder the amend-\nment."
    groups = [{"id": "definition", "label": "definition", "spans": [{"start": 0, "end": 2, "quote": text[:2]},
              {"start": text.index("amend-"), "end": len(text), "quote": text[text.index("amend-"):]}]},
              {"id": "exception", "label": "exception", "spans": [{"start": text.index("No loss"),
               "end": text.index("under"), "quote": text[text.index("No loss"):text.index("under")]}]}]
    source = {"document": "explicit-adapter-test", "source_sha256": digest(b"synthetic adapter fixture"), "text_sha256": digest(text.encode())}
    packet = export(text, source, groups, [{"id": "edge", "from": "definition", "to": "exception", "kind": "exception"}])
    annotation = run_sidecar(root, folder, context, "annotation", packet)
    if annotation["execution"] == "EXECUTED":
        imported = reimport(read(folder / "annotation/reimport.json"), text, source)
        if sorted(imported["groups"], key=lambda g:g["id"]) != sorted(groups, key=lambda g:g["id"]):
            raise ValueError("UIMA group round trip changed source occurrences")
        if sorted(imported["relations"], key=lambda r:r["id"]) != sorted(packet["relations"], key=lambda r:r["id"]):
            raise ValueError("UIMA round trip changed semantic relations")
        write(folder / "annotation-roundtrip.json", imported)
    model_receipt = context.read_json(REL + "/tool-setup/layout-model/receipt.json", optional=True)
    if not model_receipt or model_receipt["status"] == "FAILED":
        return {"engineering": "ANNOTATION_BRIDGE_CHECKED; LAYOUT_NOT_EXECUTED", "annotation": annotation,
                "primary": "LAYOUT_PREREQUISITE_MISSING", "remaining": ["Complete bounded layout-model installation", "Actual INCEpTION server and independent-reader trial pending"]}
    for row in model_receipt["files"]:
        context.external_bytes(row["file"], expected=row["sha256"])
    inputs = context.read_json(str(parent(root, state, "A0").relative_to(root)))
    units = context.read_json(str(parent(root, state, "A0", "raw-units.json").relative_to(root)))
    pages = []
    for doc_id, page in (("basf-base-september-2022-exchange", 112), ("deutsche-at1-2025", 52)):
        doc = next(d for d in inputs["documents"] if d["id"] == doc_id)
        context.read_bytes(doc["path"], expected=doc["sha256"])
        pages.append({"document": doc_id, "path": doc["path"], "sha256": doc["sha256"], "page": page})
    # Freeze target critical lines before predictions. These implementer targets
    # test retention, not independent legal truth.
    critical = [u for u in units if any(u["document"] == p["document"] and u["page"] == p["page"] for p in pages)
                and (any(s in u["raw"].lower() for s in ("folgendes", "actual/actual", "bezugsperiode", "nicht", "not ", "unless", "except"))
                     or any(ch.isdigit() for ch in u["raw"]))]
    write(folder / "critical-spans-before-prediction.json", critical)
    trial = run_sidecar(root, folder, context, "layout", {"pages": pages}, timeout=240)
    mapped, strict, primary = [], [], "NOT_EVALUATED_RUNTIME_FAILURE"
    if trial["execution"] == "EXECUTED":
        for row in trial["pages"]:
            raw = [u for u in units if u["document"] == row["document"] and u["page"] == row["page"]]
            document = read(folder / "layout" / row["output"])
            strict.append(map_layout(raw, document, source_sha256=row["sha256"]))
            mapping = project_layout(raw, document, source_sha256=row["sha256"])
            mapped.append({"document": row["document"], "page": row["page"], **mapping})
        write(folder / "layout-source-maps.json", mapped)
        write(folder / "layout-strict-baseline.json", strict)
        recovered = {(c["unit"], c["source_offset"]) for m in mapped for r in m["mappings"] for c in r["characters"]}
        missing = [{"unit": u["id"], "quote": u["raw"]} for u in critical
                   if any((u["id"], i) not in recovered for i,ch in enumerate(u["raw"]) if not ch.isspace())]
        primary = "REJECTED_CRITICAL_SPAN_LOSS" if missing else "SPANS_PRESERVED; GOVERNING_ATTACHMENT_UNRESOLVED"
        review = context.read_json("docs/implementation/prospectus-integration-repair/margin-review.json")
        context.read_bytes(review["image"], expected=review["image_sha256"])
        mappings = [item for page in mapped for item in page["mappings"]]
        # The layout worker supplies no scope edges. Measure that empty proposal
        # against the reviewed occurrence-bound target; never credit review to it.
        relationships = evaluate_relationships(units, mappings, [], [review["edge"]])
        write(folder / "governing-relationship-results.json", relationships)
        write(folder / "critical-span-results.json", {"designated": len(critical), "missing": missing,
              "baseline": "All designated raw words retained, semantic margin attachment unresolved",
              "exact_mapping_repaired": not missing, "baseline_failure_resolved": not missing and relationships["status"] == "PASS",
              "governing_margin_attachment": relationships,
              "default_promotion": False, "projection": "Raw characters preserved; normalized candidate text kept separately"})
    return {"engineering": "OPTIONAL_LAYOUT_TRIAL_EXECUTED; BASELINE_RETAINED", "primary": primary,
            "layout": trial, "annotation": annotation, "model_revision": model_receipt.get("revision"),
            "remaining": ["Review governing attachments before expanding layout cohort; optional raw projection is development evidence",
                          "Obtain authenticated independent first readings using the separately tested authoring workflow",
                          "Adjudicate multilingual evidence; optional adapters do not supply legal labels"]}


def coupon_cases():
    def row(key, start, end, refs, expected, convention="ACT_ACT_ICMA", frequency=2, eom=True):
        return {"id": key, "start": start, "end": end, "references": [{"start": a, "end": b} for a,b in refs],
                "frequency": frequency, "eom": eom, "convention": convention, "expected_exact": str(expected)}
    regular = [("2024-02-29", "2024-08-31")]
    return [
        row("regular-leap-eom", "2024-02-29", "2024-08-31", regular, "1/2"),
        row("short-first", "2024-03-31", "2024-08-31", regular, "153/368"),
        row("long-first", "2024-01-31", "2024-08-31", [("2023-08-31", "2024-02-29"), *regular], "211/364"),
        row("short-final", "2024-08-31", "2024-11-30", [("2024-08-31", "2025-02-28")], "91/362"),
        row("long-final", "2024-02-29", "2024-11-30", [*regular, ("2024-08-31", "2025-02-28")], "136/181"),
        row("annual-regular", "2023-03-08", "2024-03-08", [("2023-03-08", "2024-03-08")], "1", frequency=1, eom=False),
        row("isda-year-boundary", "2023-12-31", "2024-03-01", [], Fraction(1,365)+Fraction(60,366), "ACT_ACT_ISDA"),
        row("act365-leap", "2024-02-28", "2024-03-01", [], "2/365", "ACT_365_FIXED"),
        row("act360-leap", "2024-02-28", "2024-03-01", [], "1/180", "ACT_360")]


def coupon_trial(root, folder, state, context):
    from .fixed_coupon import year_fraction, adjusted
    for name in ("quantlib-daycount", "quantlib-calendar", "quantlib-daycount-tests"):
        source = "docs/research/prospectus-adoption-2026-10-07/sources/" + name + "/source.cpp"
        context.read_bytes(source)
    cases = coupon_cases()
    local = []
    for row in cases:
        value = year_fraction(row["start"], row["end"], row["convention"], references=row["references"],
                              frequency=row["frequency"], eom=row["eom"])
        if value != Fraction(row["expected_exact"]):
            raise ValueError("Coupon differs from predeclared independent fraction: " + row["id"])
        local.append({"id": row["id"], "exact": str(value)})
    trial = run_sidecar(root, folder, context, "coupon", {"cases": cases, "calendar_dates": ["2024-03-29", "2024-05-01", "2024-12-25"]})
    if trial["execution"] != "EXECUTED":
        raise ValueError("QuantLib comparator failed; see coupon/result.json")
    discrepancies = [r for r in trial["fractions"] if abs(r["year_fraction"] - float(Fraction(next(c["exact"] for c in local if c["id"] == r["id"])))) > 1e-12]
    calendar = {"edition": "TARGET rules in QuantLib 1.38; explicit 2024 development list", "valid_from": "2024-01-01",
                "valid_until": "2025-01-01", "holidays": ["2024-01-01", "2024-03-29", "2024-04-01", "2024-05-01", "2024-12-25", "2024-12-26"],
                "weekend": [5,6], "coverage": "COMPLETE_DECLARED_INTERVAL"}
    for row in trial["calendar"]:
        for kind, key in (("FOLLOWING", "following"), ("MODIFIED_FOLLOWING", "modified_following")):
            if adjusted(row["input"], kind, calendar) != row[key]:
                discrepancies.append(row)
    write(folder / "comparison.json", {"local": local, "comparator": trial, "discrepancies": discrepancies,
        "criterion": "Exact predeclared fractions; QuantLib within 1e-12 years; exact holiday-adjusted dates"})
    if discrepancies:
        raise ValueError("Financial comparator discrepancy requires convention/arithmetic repair")
    return {"engineering": "EXACT_COUPON_AND_QUANTLIB_COMPARISON_PASS", "primary": "NINE_EXACT_FRACTIONS_AND_SIX_ADJUSTED_DATES_PASS",
            "comparator": trial, "local": local,
            "remaining": ["Admit actual instrument calendar edition, entitlement and event premises before instrument-specific coupon support",
                          "Full settlement, tax, FX and actual transfers remain outside this conditional coupon slice"]}
