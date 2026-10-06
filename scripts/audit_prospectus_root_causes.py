"""Small deterministic diagnosis of the preserved readers; never a legal benchmark.

Run from the worktree with python3 -m scripts.audit_prospectus_root_causes.
Only the new investigation directory is written. Each reader runs in its own
process so a candidate import cannot silently replace the production baseline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-root-cause-2026-10-06"
CANDIDATE = ROOT / "docs/implementation/prospectus-corner-repair-2026-10-04/candidate"
PREFIX = "The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity. "
CASES = [
    ("repayment_control", [PREFIX], [False], "Within this explicitly complete synthetic text there is no loss feature."),
    ("write_down_control", [PREFIX + "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."], [True], "Explicit principal write-down control; event occurrence is not being asserted."),
    ("empty_operative_page", [PREFIX, ""], [None], "An unread operative page must prevent a negative coverage conclusion."),
    ("unfamiliar_loss_wording", [PREFIX + "Upon a Solvency Event, the Issuer's obligation to repay the principal of the Notes ceases permanently without payment."], [True, None], "The expressly unpaid cessation must be recognized or remain unresolved, not silently excluded."),
    ("unprovided_referenced_condition", [PREFIX + "The payment obligations under the Notes are subject to Condition 14 of the Agency Agreement."], [None], "An unprovided condition governing payment needs a dependency disposition before a negative."),
    ("nonoperative_example", [PREFIX + "The following sentence is a non-operative example and has no legal effect: the Notes shall be converted into ordinary shares."], [False, None], "A sentence explicitly described as non-operative must not establish an operative conversion power."),
    ("inherited_holder_option", [PREFIX + "Conversion is solely at the holder's option. On exercise of that option, the Notes shall be converted into ordinary shares."], [False, None], "An inherited holder election must not become compulsory conversion."),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def worker(name):
    source = ROOT / "src" if name == "production" else CANDIDATE / "src"
    sys.path.insert(0, str(source))
    from legalmath.prospectus import loss_absorption_reader as reader
    if Path(reader.__file__).resolve() != source / "legalmath/prospectus/loss_absorption_reader.py":
        raise RuntimeError("Wrong imported reader baseline")
    rows = []
    for key, pages, acceptable, obligation in CASES:
        folder = OUT / "probes/inputs" / key
        original = folder / "synthetic-source.txt"
        data = "\f".join(pages).encode()
        document = {"source_sha256": sha(data), "pages": [{"page": i, "text": p} for i, p in enumerate(pages, 1)]}
        extraction = folder / "pages.json"
        meta = {"id": key, "original": str(original.relative_to(ROOT)), "sha256": sha(data),
                "text": str(extraction.relative_to(ROOT)), "text_sha256": sha(extraction.read_bytes()), "pages": len(pages)}
        issue = {"id": key, "title": "Synthetic Notes due 2032", "identifiers": [], "documents": [{"id": key}]}
        result = reader.analyze_issue(issue, {key: meta}, ROOT)
        rows.append({"id": key, "diagnostic_obligation": obligation, "acceptable_answers": acceptable,
                     "obligation_satisfied": any(result["answer"] is x for x in acceptable), "result": result})
    print(json.dumps({"reader": name, "imported_path": str(Path(reader.__file__).relative_to(ROOT)),
                      "reader_sha256": sha(Path(reader.__file__).read_bytes()), "cases": rows}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("production", "candidate"))
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if args.worker:
        worker(args.worker)
        return
    started = time.monotonic()
    for key, pages, _, _ in CASES:
        folder = OUT / "probes/inputs" / key
        folder.mkdir(parents=True, exist_ok=True)
        data = "\f".join(pages).encode()
        (folder / "synthetic-source.txt").write_bytes(data)
        write(folder / "pages.json", {"source_sha256": sha(data), "pages": [{"page": i, "text": p} for i, p in enumerate(pages, 1)]})
    results = []
    for name in ("production", "candidate"):
        command = [sys.executable, "-m", "scripts.audit_prospectus_root_causes", "--worker", name]
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                             capture_output=True, text=True, timeout=45)
        if run.returncode:
            write(OUT / ("probes/" + name + "-failure.json"), {"command": command, "returncode": run.returncode,
                                                               "stdout": run.stdout, "stderr": run.stderr})
            raise RuntimeError(name + " diagnostic harness failed")
        result = json.loads(run.stdout)
        write(OUT / ("probes/" + name + ".json"), result)
        results.append(result)
    summary = [{"id": c[0], **{r["reader"]: next(x["result"]["answer"] for x in r["cases"] if x["id"] == c[0]) for r in results}} for c in CASES]
    bindings = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for base in (ROOT / "src/legalmath/prospectus", CANDIDATE / "src/legalmath/prospectus") for p in sorted(base.glob("*.py"))}
    write(OUT / "probes/manifest.json", {"purpose": "Debugging-only constructed counterexamples; no accuracy estimate or independent legal labels",
          "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "command": [sys.executable, "-m", "scripts.audit_prospectus_root_causes"], "interpreter": sys.version,
          "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1; no ML framework or device initialized", "random_seeds": "N/A deterministic",
          "data_version": "Synthetic inputs and reader hashes retained below", "wall_seconds": time.monotonic() - started,
          "plan": "docs/plans/prospectus-root-cause-investigation-2026-10-06.md", "method_sha256": sha(Path(__file__).read_bytes()),
          "reader_bindings": bindings, "summary": summary,
          "artifacts": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((OUT / "probes").rglob("*")) if p.is_file() and p.name != "manifest.json"}})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
