"""Narrow workers and independent acceptance checks for prospectus tasks."""
from collections import Counter
import json
from pathlib import Path
import struct

from .execution_authority import REL, file_hash, read, write

CLOSURE = "docs/implementation/prospectus-integration-closure"
GEOMETRY = CLOSURE + "/ocr-geometry-repair-2026-10-12"
FROZEN = CLOSURE + "/source-report-scope-2026-10-12/freeze-002"
MISSING_FAMILIES = ["real_table", "rotation", "true_vertical_writing", "bidirectional_text", "unexposed_readings"]


def cohort_evidence(root):
    from scripts import prospectus_report_scope as existing
    from .successor.contracts import digest
    from .successor import service
    for name, expected in read(root / FROZEN / "result.json")["inputs"].items():
        if file_hash(root / name) != expected:
            raise ValueError("Frozen original source bytes changed: " + name)
    rows = []
    for name, case in existing.CASES.items():
        frozen = read(root / FROZEN / (name + ".json"))
        p1 = existing.source(case)
        graph = p1["payload"]["graph"]
        text = existing.oracle_reading(graph, case)
        if p1["sha256"] != frozen["p1_sha256"] or digest(graph) != frozen["graph_sha256"]:
            raise ValueError("Frozen source product differs: " + name)
        if digest(text.encode()) != frozen["reading"]["text_sha256"]:
            raise ValueError("Frozen source reading differs: " + name)
        spans = [s for fact in frozen["facts"].values() for s in fact.get("spans", [])]
        if not spans or any(text[s["start"]:s["end"]] != s["quote"] for s in spans):
            raise ValueError("Source-bound report facts differ: " + name)
        selected = [u for u in graph["units"] if u["document"] == case["document"] and u["page"] in case["pages"]]
        rows.append({"id": name, "source_sha256": frozen["reading"]["source_sha256"],
                     "p1_sha256": p1["sha256"], "pages": case["pages"],
                     "unit_count": len(selected), "critical_spans": spans,
                     "text_sha256": digest(text.encode()), "language": "pt" if name.endswith("-pt") else "en",
                     "layout": "body_and_margin" if "sustainability" in name else "report_body",
                     "exposure": "EXPOSED_SUPPLIED_DEVELOPMENT_READING"})
    import gzip
    path = root / GEOMETRY / "consumer/attempt-002/evidence/source-product.json.gz"
    with gzip.open(path, "rt") as stream:
        p1 = json.load(stream)
    service.verify(p1, "P1")
    units = p1["payload"]["graph"]["units"]
    affected = [u for u in units if u.get("geometry_issues")]
    if len(affected) != 1 or affected[0]["page"] != 177:
        raise ValueError("Known geometry case changed")
    words = [w for u in units if u["method"] == "retained-pymupdf-tesseract" for w in u["words"]]
    if len(words) != 1311:
        raise ValueError("Known-case OCR inventory changed")
    rows.append({"id": "portuguese-2009-geometry", "p1_sha256": p1["sha256"],
                 "pages": [174, 175, 176, 177, 178], "ocr_words": len(words),
                 "unknown_geometry_words": sum(w["bbox"] is None for w in words),
                 "language": "pt", "layout": "mixed_axis_native_failure",
                 "exposure": "EXPOSED_SUPPLIED_DEVELOPMENT_READING"})
    return {"version": "native-geometry-development-cohort.v1", "cases": rows,
            "missing_families": MISSING_FAMILIES, "source_authenticity": "NOT_ESTABLISHED",
            "independent_acceptance": "NOT_ESTABLISHED", "native_candidate_promotion_allowed": False,
            "purpose": "Frozen, source-bound development comparator; missing families remain required"}


def callback_words(root):
    direct = root / GEOMETRY / "direct-recognition-001"
    events = read(direct / "callback.json")
    start = read(direct / "started.json")
    image_name = next(p for p in start["bindings"] if p.endswith("p177-300dpi.png"))
    image_path = Path(image_name)
    if file_hash(image_path) != start["bindings"][image_name]:
        raise ValueError("Native callback source raster changed")
    with image_path.open("rb") as stream:
        header = stream.read(24)
    width, height = struct.unpack(">II", header[16:24])
    words = []
    for index, event in enumerate(events):
        key = [event["line_bbox"], event["word_bbox"]]
        if not words or words[-1]["group"] != key:
            words.append({"group": key, "text": "", "callback_indices": []})
        words[-1]["text"] += event["character"]
        words[-1]["callback_indices"].append(index)
    for word in words:
        x0, y0, x1, y1 = word["group"][1]
        word["within_raster"] = 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height
    colon = [w for w in words if w["text"] == ":" and w["group"][1] == [2211, 3002, 2217, 3022]]
    if len(colon) != 1 or not colon[0]["within_raster"]:
        raise ValueError("Known recognition box changed")
    sequence = "".join(e["character"] for e in events)
    if "".join(w["text"] for w in words) != sequence or sum(not c.isspace() for c in sequence) != 1409:
        raise ValueError("Callback character accounting changed")
    return {"version": "native-callback-word-diagnostic.v1", "image_sha256": file_hash(image_path),
            "raster_size": [width, height], "events_sha256": file_hash(direct / "callback.json"),
            "words": words, "nonspace_characters": 1409,
            "invalid_word_boxes": sum(not w["within_raster"] for w in words),
            "coordinate_system": "retained native callback raster pixels; no PDF coordinates assigned",
            "production_adapter": False}


def interface_evidence(root, cohort, words):
    return {"version": "native-geometry-interface-decision.v1", "cohort_cases": [r["id"] for r in cohort["cases"]],
            "missing_families": cohort["missing_families"], "callback_words": len(words["words"]),
            "callback_characters": words["nonspace_characters"],
            "candidates": {
                "native_axis": {"baseline": "MuPDF 1.27.2 pinned native build",
                                "required": "Reproduce existing PDF before patch; preserve established group axis separately from writing direction; compare actual emitted PDF and downstream consumers"},
                "direct_callback": {"baseline": "Retained native events and original raster",
                                    "required": "Isolated ABI; retain each event, Unicode and word boundaries, image/model/library hashes; explicitly validate raster-to-page transform and downstream layout/correction consumers"}},
            "promotion_vetoes": ["lost_character_or_qualifier", "invalid_or_fabricated_position", "unsupported_writing_direction", "changed_matched_answer", "missing_required_source_family"],
            "next_action": "Implement bounded candidates under the frozen interfaces; keep missing real layout families as promotion vetoes",
            "native_patch_validated": False, "production_adapter_validated": False,
            "legal_acceptance": "NOT_ESTABLISHED"}


def predecessor_attempt(root, task_id):
    from .execution_authority import Authority
    state = Authority(root).status()
    row = next(r for r in state["tasks"] if r["id"] == task_id)
    if row["state"] != "COMPLETE":
        raise ValueError("Substantive predecessor is not current")
    return root / row["attempt"]


def execute(root, attempt, task):
    if task["handler"] == "native-cohort":
        write(attempt / "cohort.json", cohort_evidence(root), exclusive=True)
    elif task["handler"] == "native-interfaces":
        previous = predecessor_attempt(root, "native-cohort")
        cohort = read(previous / "cohort.json")
        words = callback_words(root)
        write(attempt / "callback-words.json", words, exclusive=True)
        write(attempt / "interfaces.json", interface_evidence(root, cohort, words), exclusive=True)
        write(attempt / "predecessor.json", {"attempt": str(previous.relative_to(root)),
              "cohort_sha256": file_hash(previous / "cohort.json")}, exclusive=True)
    else:
        raise ValueError("No automatic handler for this agent/human task")


def validate(root, attempt, task):
    result = read(attempt / "result.json")
    if result.get("status") != "PASS" or result.get("task") != task["id"]:
        raise ValueError("Worker result failed or belongs to another task")
    if task["handler"] == "native-cohort":
        if read(attempt / "cohort.json") != cohort_evidence(root):
            raise ValueError("Cohort differs from actual source products and reviewed spans")
        return True
    if task["handler"] == "native-interfaces":
        previous = predecessor_attempt(root, "native-cohort")
        cohort = read(previous / "cohort.json")
        words = read(attempt / "callback-words.json")
        if words != callback_words(root):
            raise ValueError("Callback evidence is not a lossless view of retained native events")
        if read(attempt / "interfaces.json") != interface_evidence(root, cohort, words):
            raise ValueError("Interface decision omits required case/qualifier controls")
        if read(attempt / "predecessor.json")["cohort_sha256"] != file_hash(previous / "cohort.json"):
            raise ValueError("Downstream cohort binding changed")
        return True
    if task.get("validator") is not None:
        from .execution_acceptance import validate as validate_registered
        return validate_registered(root, attempt, task)
    # Agent and human dossiers require a reviewed task-specific validator before
    # acceptance. Keeping a submitted result never closes a capability by fiat.
    return False
