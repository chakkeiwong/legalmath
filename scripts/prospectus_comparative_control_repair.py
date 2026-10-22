"""Complete immutable comparative controls with exactly reconstructible deltas."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import signal
import sys
import time
import traceback

from scripts import prospectus_comparative_basis as previous

w = previous.w
ROOT, BASE = w.ROOT, w.BASE
OLD = previous.HERE
HERE = OLD.parent / "attempt-009"
REVIEW = BASE / "reviews/comparative-controls-203"
PLAN = "docs/plans/prospectus-comparative-control-repair-2026-10-17.md"
ROUTE = BASE / "closure-routes-2026-10-17-comparative-controls-203.json"
PROPOSAL = BASE / "proposals/comparative-controls-203.json"
REVIEW_JSON = BASE / "proposals/comparative-controls-203-review.json"
PRIOR_BYTES = 165135276
PRIOR_SECONDS = 581.1294155055657
STAGES = ("verify", "controls", "seal")
SELECTOR = {"version": "comparative-compact-controls.v1", "stages": list(STAGES),
            "prior_bytes": PRIOR_BYTES, "prior_seconds": PRIOR_SECONDS,
            "new_seconds": 180, "combined_seconds": 1080,
            "new_bytes": 20 * 1024**2, "combined_bytes": 180 * 1024**2,
            "previous_combined_bytes": 160 * 1024**2,
            "work_seconds": 45, "stage_seconds": 50, "all_cases": 56,
            "retained_cases": 28, "remaining_cases": 28, "new_native_network_model_calls": 0,
            "additional_repairs": 0}
SUPPORT = (REVIEW, ROOT / PLAN, Path(__file__), ROUTE, PROPOSAL, REVIEW_JSON,
           BASE / "revisions/0203.json", BASE / "program.json")


def storage():
    new = w.path_bytes((HERE, *SUPPORT))
    return {"previous_bytes": PRIOR_BYTES, "new_inclusive_bytes": new, "combined_bytes": PRIOR_BYTES + new}


def save(name, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if name.endswith(".gz"):
        raw = gzip.compress(raw, mtime=0)
    bound = storage()
    w.require(bound["new_inclusive_bytes"] + len(raw) < SELECTOR["new_bytes"] - 256 * 1024
              and bound["combined_bytes"] + len(raw) < SELECTOR["combined_bytes"] - 1024**2,
              "Compact repair inclusive storage exhausted")
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def delta(before, after, path=()):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [change for key in before for change in delta(before[key], after[key], (*path, key))]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [change for i in range(len(before)) for change in delta(before[i], after[i], (*path, i))]
    return [{"path": list(path), "before_sha256": w.digest(before), "replacement": after}]


def reconstruct(original, changes):
    value = deepcopy(original)
    seen = []
    for change in changes:
        path = change["path"]
        w.require(path and not any(path[:len(p)] == p or p[:len(path)] == path for p in seen), "Overlapping or root delta")
        seen.append(path)
        parent = value
        for key in path[:-1]:
            parent = parent[key]
        w.require(w.digest(parent[path[-1]]) == change["before_sha256"], "Delta applies to different baseline content")
        parent[path[-1]] = deepcopy(change["replacement"])
    return value


def bindings():
    authority = w.Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-06"]
    admitted = w.read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    w.require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
              and task["comparative_control_repair"] == SELECTOR and admitted["task_spec"] == task
              and admitted["program_sha256"] == w.digest(program) and admitted["binding"] == authority.binding(task),
              "Unchanged current compact repair admission required")
    w.require(not (HERE / "outputs.json").exists(), "Compact repair already sealed")
    history = w.read(REVIEW / "history.json")
    w.require(all(w.file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Historical comparative evidence changed")
    w.require(w.files(ROOT / "src/legalmath") == history["package"], "Production changed")
    w.require(w.HERE == OLD, "Frozen evaluator must reference original008 context")
    return admitted


def verify():
    profile = w.read(OLD / "profile.json")
    analysis = w.validate(profile, w.read(OLD / "profile-pin.json")["sha256"])
    method = w.evaluator()
    intended = w.read(OLD / "intended-refusals.json")
    w.require(intended == method.CASES and len(intended) == 56, "Frozen full case set required")
    historical = []
    for path in sorted((OLD / "adverse-results").glob("*.json")):
        result = w.read(path)
        name = result["case"]
        bad = method.altered(profile, name)
        retained = w.load(OLD / "adverse-inputs" / (name + ".json.gz"))
        w.require(retained == {"profile": bad, "expected_pin": w.digest(bad)} and result ==
                  {"case": name, "refused": True, "repinned": True, "reason": intended[name]},
                  "Historical refusal does not match exact frozen mutation")
        historical.append({"case": name, "path": str(path.relative_to(ROOT)), "sha256": w.file_hash(path),
                           "input_path": str((OLD / "adverse-inputs" / (name + ".json.gz")).relative_to(ROOT)),
                           "input_sha256": w.file_hash(OLD / "adverse-inputs" / (name + ".json.gz")),
                           "reason": result["reason"], "new_execution": False})
    w.require(len(historical) == 28 and len({r["case"] for r in historical}) == 28, "Exactly28 retained refusals required")
    combined = w.compose(OLD / "answer-composition.json")
    baseline = w.compose(w.PRIOR)
    eps = w.compose(w.EPS)
    w.require(all(combined[k] == baseline[k] for k in baseline) and set(combined) == set(baseline) | {w.KEY},
              "Full answer008 must extend unchanged007 by only its recorded reading")
    w.require(combined[w.KEY]["profile"] == profile and combined[w.KEY]["analysis"] == analysis, "Answer differs from frozen profile")
    metadata = w.read(OLD / "answer-composition.json")
    w.require(w.digest(eps) == metadata["EPS_full_composed_sha256"], "Full EPS answer changed")
    w.require(combined["questions"]["Q3"]["status"] == "PARTIAL"
              and sum(d["id"].startswith("BES-DEP-") and d["status"] == "UNRESOLVED" for d in combined["dependencies"]) == 14,
              "Original substantive limitations required")
    save("verification.json", {"analysis": analysis, "historical_refusals": historical,
         "remaining": [name for name in intended if name not in {r["case"] for r in historical}],
         "source008_answer_sha256": w.digest(combined), "source007_answer_sha256": w.digest(baseline),
         "EPS_answer_sha256": w.digest(eps), "complete_answers_decoded": True})
    return {"historical_refusals_verified": 28, "remaining": 28, "full_answers_preserved": True}


def controls():
    profile = w.read(OLD / "profile.json")
    method = w.evaluator()
    verified = w.read(HERE / "verification.json")
    results = []
    for name in verified["remaining"]:
        bad = method.altered(profile, name)
        patch = delta(profile, bad)
        w.require(patch and reconstruct(profile, patch) == bad, "Lossless mutation reconstruction required")
        receipt = {"case": name, "baseline_path": str((OLD / "profile.json").relative_to(ROOT)),
                   "baseline_file_sha256": w.file_hash(OLD / "profile.json"), "baseline_content_sha256": w.digest(profile),
                   "frozen_mutation_method_sha256": w.file_hash(OLD / "reading.py"), "changes": patch,
                   "reconstructed_profile_sha256": w.digest(bad)}
        path = "adverse-deltas/" + name + ".json.gz"
        save(path, receipt)
        actual_receipt = w.load(HERE / path)
        restored = reconstruct(w.read(ROOT / actual_receipt["baseline_path"]), actual_receipt["changes"])
        w.require(restored == bad and w.digest(restored) == actual_receipt["reconstructed_profile_sha256"],
                  "Persisted delta does not reconstruct the exact intended adverse input")
        expected = method.CASES[name]
        try:
            w.validate(restored, w.digest(restored))
        except ValueError as exc:
            w.require(str(exc) == expected, "Wrong compact semantic refusal: " + name + ": " + str(exc))
            result = {"case": name, "refused": True, "repinned": True, "reason": str(exc),
                      "lossless_reconstruction": True, "new_execution": True, "delta_file": path,
                      "delta_sha256": w.file_hash(HERE / path)}
            save("adverse-results/" + name + ".json", result)
            results.append(result)
        else:
            raise ValueError("Changed comparative reading accepted: " + name)
    all_names = [r["case"] for r in verified["historical_refusals"]] + [r["case"] for r in results]
    w.require(len(results) == 28 and len(all_names) == len(set(all_names)) == 56 and set(all_names) == set(method.CASES),
              "Every frozen intended case must have actual refusal evidence")
    save("actual-controls.json", {"historical_verified": verified["historical_refusals"],
         "newly_executed": results, "total": 56, "historical_failed_attempt_preserved": True})
    return {"actual_new_refusals": 28, "retained_refusals_verified": 28, "all_cases": 56}


def seal():
    w.require((HERE / "RESULT.md").is_file(), "Actual repair interpretation and manifest required")
    result = w.read(HERE / "actual-controls.json")
    w.require(result["total"] == 56 and len(result["newly_executed"]) == 28
              and all(r["refused"] and r["repinned"] and r["lossless_reconstruction"] for r in result["newly_executed"]),
              "Complete compact refusal evidence required")
    save("verified-result.json", {"answer_reference": str((OLD / "answer-composition.json").relative_to(ROOT)),
         "answer_reference_sha256": w.file_hash(OLD / "answer-composition.json"),
         "source_reading": str((OLD / "SOURCE-REVIEW.md").relative_to(ROOT)),
         "verification": w.read(HERE / "verification.json"), "controls": {"total": 56, "old": 28, "new": 28},
         "result_sha256": w.file_hash(HERE / "RESULT.md"), "task_complete": False})
    return {"compact_storage_repair_complete": True, "source06_complete": False, "independent_acceptance": False}


def run(stage):
    with w.Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        w.require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                  {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                  "Repeated, skipped or interrupted compact repair stage")
        rows = [w.read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        w.require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows), "Failed repair predecessor")
        spent = w.read(REVIEW / "preflight.json")["preparation_seconds"] + sum(r["wall_seconds"] for r in rows)
        def within(elapsed=0):
            bound = storage()
            return spent + elapsed < 180 and PRIOR_SECONDS + spent + elapsed < 1080 and \
                bound["new_inclusive_bytes"] < 20 * 1024**2 - 256 * 1024 and bound["combined_bytes"] < 180 * 1024**2 - 1024**2
        w.require(within(), "Compact repair cumulative bounds exhausted")
        save("stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
             "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_comparative_control_repair", stage],
             "git_commit": admitted["git_commit"], "python": sys.executable, "plan": PLAN,
             "CPU_GPU": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic",
             "data_version": str(OLD.relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Compact repair deadline; no retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 180 - spent, 1080 - PRIOR_SECONDS - spent))
        try:
            with w.execution_guard() as guard:
                details = globals()[stage]()
            w.require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected repair process/network action")
            details["process_guard"] = guard.result()
            bindings()
            w.require(time.monotonic() - tick < 50 and within(time.monotonic() - tick), "Repair bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
                  "details": details, "wall_seconds": time.monotonic() - tick, "bounds": storage()}
        result["new_cumulative_seconds"] = spent + result["wall_seconds"]
        result["original_cumulative_seconds"] = PRIOR_SECONDS + result["new_cumulative_seconds"]
        save("stages/" + stage + "/result.json", result)
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-06", "task_complete": False,
                 "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", w.files(HERE))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "original_cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
