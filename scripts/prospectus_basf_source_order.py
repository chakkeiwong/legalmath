"""Check the bounded BASF ordering repair without changing historical attempts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/implementation/prospectus-basf-source-order")
PLAN = "docs/plans/prospectus-basf-source-order-2026-10-08.md"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor import basf, jobs

    base = ROOT / REL
    base.mkdir(parents=True, exist_ok=True)
    index = 1
    while (base / f"run-{index:03d}").exists():
        index += 1
    out = base / f"run-{index:03d}"
    out.mkdir()
    started = time.monotonic()
    methods = [ROOT / PLAN, Path(__file__), ROOT / "tests/prospectus_successor/test_basf_sources.py"]
    methods += [ROOT / "src/legalmath/prospectus/successor" / (name + ".py")
                for name in ("basf", "basf_order", "intervals", "contracts", "anchors")]
    bindings = {str(p.relative_to(ROOT)): sha(p) for p in methods}
    inputs, commands = {}, []
    failure, comparison, counts = None, None, None

    def bound(relative, expected=None):
        path = ROOT / relative
        observed = sha(path)
        if expected and observed != expected:
            raise ValueError("Changed source/comparator: " + str(relative))
        inputs[str(relative)] = observed
        return path

    def historical(relative):
        path = Path(relative)
        receipt = json.loads(bound(path.parent / "receipt.json").read_text())
        return json.loads(bound(path, receipt["outputs"][path.name]).read_text())

    try:
        graph = historical("docs/implementation/prospectus-repair-2026-10-06/phases/P1/attempt-009/source-graph.json")
        baseline = historical("docs/implementation/prospectus-adoption/phases/A1/attempt-004/product.json")
        admission = json.loads(bound(jobs.BASF).read_text())
        for source in admission["sources"].values():
            bound(source["original"], source["sha256"])
        review = json.loads(bound(REL / "source-review-001/review.json").read_text())
        for name, expected in review["image_hashes"].items():
            bound(REL / "source-review-001" / name, expected)

        argv = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
                "tests/prospectus_successor/test_basf_sources.py", "--junitxml=" + str(out / "tests.xml")]
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "CUDA_VISIBLE_DEVICES": "-1"}
        tick = time.monotonic()
        run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
        (out / "tests.txt").write_text(run.stdout + run.stderr)
        commands.append({"argv": argv, "returncode": run.returncode, "wall_seconds": time.monotonic() - tick})
        suites = ET.parse(out / "tests.xml").getroot()
        counts = {key: sum(int(s.get(key, "0")) for s in suites.iter("testsuite"))
                  for key in ("tests", "failures", "errors", "skipped")}
        if run.returncode:
            raise ValueError("Focused tests failed; see tests.txt")

        current = basf.construct(graph, admission)
        reviewed = [{k: r[k] for k in ("id", "page", "before", "after", "source_units_sha256", "review")}
                    for r in review["reviewed_orders"]]
        if current["reading_order"]["decisions"] != reviewed:
            raise ValueError("Construction differs from the source-image review")
        old_ids = [s["unit"] for s in baseline["source_map"]]
        new_ids = [s["unit"] for s in current["source_map"]]
        if sorted(old_ids) != sorted(new_ids) or len(set(new_ids)) != len(new_ids):
            raise ValueError("Source occurrence set changed")
        by_id = {u["id"]: u for u in graph["units"]}
        for product in (baseline, current):
            for span in product["source_map"]:
                if product["raw_body"][span["start"]:span["end"]] != by_id[span["unit"]]["raw"]:
                    raise ValueError("Source occurrence text changed")
        if current["interval_accounting"]["gaps"]:
            raise ValueError("Source intervals lack dispositions")
        comparison = {
            "status": "SOURCE_ORDER_REPAIR_PASS", "source_occurrences_preserved": len(new_ids),
            "reviewed_permutations": len(reviewed), "source_characters_preserved": True,
            "before": {"unresolved_intervals": len(baseline["interval_accounting"]["unresolved"]),
                       "remaining_brackets": len(baseline["remaining_brackets"])},
            "after": {"unresolved_intervals": len(current["interval_accounting"]["unresolved"]),
                      "remaining_brackets": len(current["remaining_brackets"])},
            "remaining": current["remaining"], "independent_legal_review": False,
            "full_german_contract_constructed": False,
            "scope": "Five source-reviewed permutations; all other ordering retains its prior review status"}
        save(out / "comparison.json", comparison)
        save(out / "product.json", current)
        for name, expected in {**bindings, **inputs}.items():
            if sha(ROOT / name) != expected:
                raise ValueError("Evidence or method changed during verification: " + name)
    except Exception as exc:
        failure = str(exc)
        save(out / "failure.json", {"error": failure})

    save(out / "manifest.json", {
        "status": "FAILED" if failure else "SOURCE_ORDER_REPAIR_PASS; LEGAL_ACCEPTANCE_PENDING",
        "failure": failure, "command": [sys.executable, "-m", "scripts.prospectus_basf_source_order"],
        "commands": commands, "wall_seconds": time.monotonic() - started,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "environment": {"driver": sys.version, "application_python": str(ROOT / ".venv/bin/python"),
                        "PYTHONPATH": str(ROOT / "src"), "CUDA_VISIBLE_DEVICES": "-1"},
        "cpu_gpu": "CPU; test subprocess intentionally hides GPU; driver imports no GPU library",
        "random_seeds": "N/A; deterministic source regression", "data_version": basf.SHA,
        "plan": PLAN, "result_file": str(REL / "RESULT.md"), "method": bindings, "inputs": inputs,
        "tests": counts, "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({"directory": str(out.relative_to(ROOT)), "failure": failure,
                      "tests": counts, "comparison": comparison}, indent=2))
    if failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
