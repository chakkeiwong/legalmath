"""Finish the original page59 diagnosis using only sealed saved operands."""
from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-05/attempt-009"
FAILED = HERE.parent / "attempt-008"
SCOPE = HERE.parent / "attempt-007"
RISK = HERE.parent / "attempt-006"
REVIEW = BASE / "reviews/h1-equity-retained-165"
PLAN = "docs/plans/prospectus-h1-equity-retained-diagnosis-2026-10-16.md"
STAGES = ("prepare", "analyze", "seal")
SELECTOR = {"version": "bes-h1-equity-retained-diagnosis.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "combined008_009_seconds": 360,
    "combined006_009_seconds": 1800, "combined006_009_bytes": 700*1024**2,
    "combined008_009_bytes": 32*1024**2, "additional_source_parses": 0,
    "additional_text_extractions": 0, "renders_ocr_network_gpu_children": 0,
    "production_edits": 0, "unchanged_retries": 0}


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        stream.write("\n")


def read_gzip(name):
    return json.loads(gzip.decompress((FAILED / name).read_bytes()))


def used_bytes(folders):
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def bounds():
    environments = [Path(read(p / "workspace.json")["directory"]) for p in (RISK, SCOPE)]
    return {"bytes008_009": used_bytes((FAILED, HERE)),
        "bytes006_009": used_bytes([RISK, SCOPE, FAILED, HERE, *environments]),
        "seconds008": read(FAILED / "result.json")["cumulative_seconds"],
        "seconds006_008": sum(read(p / "result.json")["cumulative_seconds"] for p in (RISK, SCOPE, FAILED))}


def bindings():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-05"]
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and task.get("equity_retained_diagnosis") == SELECTOR
        and admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task
        and admitted["binding"] == authority.binding(task), "Current unchanged retained-diagnosis admission required")
    require(not (HERE / "outputs.json").exists(), "Retained diagnosis already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Historical evidence or method changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Production files changed")
    return admitted


def text_operand(row):
    require(row["operator"] in {"Tj", "TJ"}, "Expected explicit text-showing operator")
    values = row["operands"][0] if row["operator"] == "TJ" else row["operands"]
    strings = [v for v in values if isinstance(v, dict)]
    require(all(set(v) == {"decoded", "original_bytes_hex"} for v in strings), "Original ASCII bytes required")
    require(all(bytes.fromhex(v["original_bytes_hex"]).decode("ascii") == v["decoded"] for v in strings), "ASCII byte/text mismatch")
    return "".join(v["decoded"] for v in strings)


def original_operands(value):
    """Compare the same bytes despite pypdf's two saved string representations."""
    if isinstance(value, list):
        return [original_operands(v) for v in value]
    if isinstance(value, dict):
        if "original_bytes_hex" in value:
            return {"bytes_hex": value["original_bytes_hex"]}
        return {k: original_operands(v) for k, v in value.items()}
    return value


def prepare():
    failure = read(FAILED / "result.json")
    error = read(FAILED / "stages/inspect/error.json")["traceback"]
    require(failure["status"] == "FAIL" and failure["error"] == {
        "type": "TypeError", "message": "Object of type bytes is not JSON serializable"}
        and '"decoded_content_sha256":digest(raw)' in error, "Exact retained wrapper failure required")
    require(not (FAILED / "inspection.json").exists() and not (FAILED / "source-action-result.json").exists(), "Failed result must remain failed")
    raw = FAILED / "page59-decoded-content.bin"
    require(file_hash(raw) == sha256(raw.read_bytes()).hexdigest(), "Binary evidence hashing mismatch")
    ops, visitors = read_gzip("page59-operators.json.gz"), read_gzip("visitor-operands.json.gz")
    require(len(ops) == len(visitors) == 2258 and all(original_operands(o) == original_operands({k: v[k] for k in o}) for o, v in zip(ops, visitors)), "Saved operator/callback coverage mismatch")
    require(read_gzip("forms.json.gz") == [], "Unexpected nested forms; stop this finite analysis")
    require(len(read_gzip("visitor-text.json.gz")) == 212 and len(read(FAILED / "original-page59-units.json")) == 463, "Retained source counts changed")
    counts = dict(Counter(o["operator"] for o in ops))
    require(counts.get("Tj") == 73 and counts.get("TJ") == 123 and not any(k in counts for k in ("'", '"', "BDC", "BMC")), "Unexpected text or marked-content operator")
    save("retained-evidence.json", {"failed_attempt": str(FAILED.relative_to(ROOT)),
        "files": {name: file_hash(FAILED / name) for name in read(FAILED / "outputs.json")},
        "decoded_content_sha256": file_hash(raw), "decoded_bytes": raw.stat().st_size,
        "operator_counts": counts, "callback_count": len(visitors), "text_fragments": 212,
        "original_occurrences": 463, "source_actions_added": 0,
        "missing_original_summary": True, "package_files_preserved": 441})
    return {"saved_operators": len(ops), "saved_text_fragments": 212, "new_source_actions": 0}


def analyze():
    ops, visitors = read_gzip("page59-operators.json.gz"), read_gzip("visitor-operands.json.gz")
    # Source-specific exact blocks, not a general PDF text/clip interpreter.
    selections = [("unit_label", 86, 97, "(in thousands of e", "u"),
        ("fair_value_2009_second_half", 686, 697, " 332 0", "3"),
        ("total_gains_2009_second_half", 801, 812, " 639 6", "6"),
        ("balance_2009_12_31", 981, 992, "6 938 8", "8"),
        ("balance_2010_06_30", 1348, 1359, "6 914 9", "7")]
    traces = []
    for name, prefix, last, expected_prefix, expected_last in selections:
        require(text_operand(ops[prefix]) == expected_prefix and text_operand(ops[last]) == expected_last, "Selected raw string differs")
        block = ops[prefix+1:last+3]
        require([r["operator"] for r in block] == ["ET", "q", "i", "re", "W", "n", "BT", "Tm", "Tc", "Tw", "Tj", "ET", "Q"], "Local clip block changed")
        require(visitors[prefix]["cm"] == visitors[last]["cm"] == [1, 0, 0, 1, 0, 0], "Nonidentity source transform")
        rectangle, matrix = block[3]["operands"], block[7]["operands"]
        require(matrix[:4] in ([0, 4.2982, -4.2771, 0], [0, 4.9596, -4.9352, 0]), "Unexpected text orientation")
        require(block[8]["operands"] == block[9]["operands"] == [0], "Unexpected final text spacing")
        traces.append({"case": name, "prefix_operator": prefix, "last_operator": last,
            "encoded_prefix": expected_prefix, "encoded_final_character": expected_last,
            "encoded_join_without_inferred_digits": expected_prefix+expected_last,
            "local_clip_rectangle": rectangle, "text_matrix": matrix,
            "clip_edge_y": rectangle[1]+rectangle[3],
            "origin_to_clip_edge_y": round(rectangle[1]+rectangle[3]-matrix[5], 6),
            "raw_operators": [ops[prefix], *block], "glyph_extent_checked": False})
    save("trace.json", {"cases": traces, "classification_scope": "five representative saved ASCII strings",
        "raw_operator_coverage": 2258, "all_196_text_showing_operands_retained": True,
        "new_source_actions": 0, "page_boxes_unavailable": True})
    return {"representative_traces": len(traces), "new_source_actions": 0}


def seal():
    analysis = read(HERE / "analysis.json")
    require((HERE / "SOURCE-ANALYSIS.md").is_file() and (HERE / "RESULT.md").is_file(), "Actual source analysis/result required")
    require(analysis["classification"] in {"ENCODED_CONTENT_BEYOND_CLIP", "ENCODED_STRINGS_TRUNCATED", "INCONCLUSIVE"}, "Explicit classification required")
    require(analysis["financial_values_validated"] is False and analysis["automatic_recovery_complete"] is False, "No financial or automatic promotion")
    require(analysis["evidence"] and all(file_hash(ROOT / p) == h for p, h in analysis["evidence"].items()), "Actual analysis evidence hashes required")
    save("verified-analysis.json", {**analysis, "source_analysis_sha256": file_hash(HERE / "SOURCE-ANALYSIS.md"),
        "result_sha256": file_hash(HERE / "RESULT.md"), "source_actions_added": 0})
    return {"diagnosis_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        started = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        ended = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(started == ended == set(STAGES[:index]), "Repeated/skipped/interrupted retained stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed predecessor")
        spent, limits = sum(r["wall_seconds"] for r in rows), bounds()
        require(limits["seconds008"]+spent < 360 and limits["seconds006_008"]+spent < 1800
            and limits["bytes008_009"] < 31*1024**2 and limits["bytes006_009"] < 698*1024**2, "Cumulative diagnosis bounds exhausted")
        save("stages/"+stage+"/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m", "scripts.prospectus_h1_equity_retained", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"],
            "python": sys.executable, "cpu_gpu": "CPU only; GPU devices intentionally hidden",
            "random_seeds": "N/A deterministic retained-source analysis", "plan": PLAN,
            "data_version": str((FAILED / "outputs.json").relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Retained diagnosis time bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 360-limits["seconds008"]-spent, 1800-limits["seconds006_008"]-spent))
        try:
            with execution_guard() as guard:
                details = globals()[stage]()
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected process/network action")
            bindings()
            elapsed, current = time.monotonic()-tick, bounds()
            require(elapsed < 115 and limits["seconds008"]+spent+elapsed < 360
                and limits["seconds006_008"]+spent+elapsed < 1800
                and current["bytes008_009"] < 31*1024**2 and current["bytes006_009"] < 698*1024**2, "Retained diagnosis bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/"+stage+"/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
            "details": details, "wall_seconds": time.monotonic()-tick, "bounds": bounds()}
        value["cumulative_seconds"] = spent+value["wall_seconds"]
        save("stages/"+stage+"/result.json", value)
        if error or stage == "seal":
            save("result.json", {**value, "task": "source-bes-dep-05", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "Choose retained prepare/analyze/seal")
    raise SystemExit(run(sys.argv[1]))
