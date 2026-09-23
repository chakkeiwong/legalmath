"""Verify a second source-linked candidate without altering the accepted program."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

from legalmath.canonical import canonical, digest, raw_digest, loads
from legalmath.conformance import evaluate_case
from legalmath.errors import LegalMathError
from legalmath.ir.trace import verify_result
from legalmath.java.manifest import build_candidate, run_java
from legalmath.review.coverage import coverage_report
from legalmath.review.lifecycle import Lifecycle
from legalmath.review.releases import Releases
from legalmath.sources.intake import import_source, resolve_span
from legalmath.sources.dependencies import record_dependency, closure
from legalmath.storage import Database
from prepare import HERE, ROOT, FIELDS, RULE, START, END, AT
from truth_oracle import expected_status


def snapshot(values):
    facts = {}
    for name, state in values.items():
        if state == "U": entry = {"type": "bool", "status": "unknown", "reason": "MISSING"}
        elif state == "C": entry = {"type": "bool", "status": "conflict", "evidence_ids": ["synthetic.a", "synthetic.b"]}
        else:
            entry = {"type": "bool", "status": "known", "value": state != "F", "evidence_ids": ["synthetic." + name],
                "valid_from": START, "valid_until": END, "recorded_at": START}
            if state == "STALE": entry["valid_until"] = AT
            if state == "FUTURE_RECORDED": entry["recorded_at"] = "2026-09-22T00:00:01.000000Z"
        facts[name] = entry
    return {"subject_id": "synthetic.incentive_component", "facts": facts}


def request(bundle, ident, values, expected):
    return {"id": ident, "bundle": bundle, "rule_id": RULE, "snapshot": snapshot(values), "valid_at": AT, "known_at": AT, "mode": "draft",
        "expected": {"status": expected, **({"value": expected == "TRUE"} if expected in ("TRUE", "FALSE") else {})}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--jdk", default=str(ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"))
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()): raise RuntimeError("Use a fresh evidence directory")
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_utc = datetime.now(timezone.utc).isoformat()
    oracle = loads((HERE / "oracle.json").read_bytes())
    freeze = loads((HERE / "oracle-freeze.json").read_bytes())
    assert raw_digest((HERE / "oracle.json").read_bytes()) == freeze["oracle_sha256"]
    assert freeze["candidate_exists_at_oracle_freeze"] is False
    bundle = loads((HERE / "gift-control.bundle.json").read_bytes())
    inventory = loads((HERE / "circular-disposition.json").read_bytes())["provisions"]
    source_raw = (ROOT / ".localresources/sfc/23EC46.json").read_bytes()
    assert raw_digest(source_raw) == freeze["retained_raw_sha256"] == freeze["fresh_raw_sha256"]
    named = [request(bundle, c["id"], {**oracle["defaults"], **c["overrides"]}, c["expected"]) for c in oracle["cases"]]
    # First execute the source-written scenarios; do not generate expected values
    # from the candidate or from the program under test.
    for c in named:
        result = evaluate_case(c)
        assert all(result[k] == v for k, v in c["expected"].items()), (c["id"], c["expected"], result)
        assert verify_result(bundle, c["snapshot"], RULE, result)
    print(f"Source-written scenarios passed in Python: {len(named)}", flush=True)
    truth_cases = []
    for states in product("TFU", repeat=len(FIELDS)):
        values = dict(zip(FIELDS, states))
        truth_cases.append(request(bundle, "table." + "".join(states).lower(), values, expected_status(values)))
    cases = named + truth_cases
    (out / "cases.json").write_bytes(canonical(cases))
    db = Database(out / "database")
    lc, releases = Lifecycle(db), Releases(db)
    lc.register({"test.author": {"roles": ["author"], "token": "public-unreleased-author"},
                 "test.engineer": {"roles": ["engineering"], "token": "public-unreleased-engineer"}})
    with db.transaction() as con:
        source = import_source(db, con, "23EC46", source_raw, "application/json", freeze["official_url"],
            freeze["recorded_at_utc"].replace("+00:00", "Z"), authority="RETAINED_PUBLIC_SOURCE")
        for locator in ("Code of Conduct paragraph 3.11, applicable version", "Code of Conduct FAQ question 1, 30 September 2010 reference and applicable version"):
            record_dependency(db, con, {"from_revision_id": source["revision_id"], "locator": locator,
                "target_revision_id": None, "relation": "references", "resolution_status": "unresolved",
                "resolution_note": "Circular summary inspected; underlying source and legal version not independently adjudicated in this bounded test."})
    state = lc.create("test.author", "create", bundle)
    with db.connect() as con:
        coverage = coverage_report(db, con, bundle, inventory)
        dependencies = closure(db, con, [source["revision_id"]])
        for span in bundle["source_spans"]: resolve_span(db, con, span)
        bad_span = deepcopy(bundle["source_spans"][0]); bad_span["start"] += 1
        try: resolve_span(db, con, bad_span)
        except LegalMathError as exc: assert exc.code == "E_HASH_MISMATCH"
        else: raise AssertionError("Altered source offsets were accepted")
    (out / "coverage.json").write_bytes(canonical(coverage))
    (out / "dependencies.json").write_bytes(canonical(dependencies))
    built = releases.build("test.engineer", "candidate", state["bundle_hash"], out / "candidate", args.jdk, cases)
    verification = loads((out / "candidate/verification-report.json").read_bytes())
    results = loads((out / "candidate/verification-results.json").read_bytes())
    # Persist the named-case comparison with human-readable source reasoning.
    named_report = [{**c, "python_status": r["python"]["status"], "java_status": r["java"]["status"],
        "python_result_hash": r["python"]["result_hash"], "java_result_hash": r["java"]["result_hash"]}
        for c, r in zip(oracle["cases"], results[:len(named)])]
    (out / "named-case-results.json").write_bytes(canonical(named_report))
    print(f"Generated Java and Python match the fixed outcomes: {len(cases)} cases", flush=True)
    mutations = {}
    for name in ("remove_discount_exception", "omit_product_type_route", "assume_gift_without_evidence", "ignore_actor_scope"):
        mutant = deepcopy(bundle)
        rule = mutant["rules"][0]
        if name == "remove_discount_exception": rule["body"]["args"].pop()
        elif name == "omit_product_type_route": rule["body"]["args"][1] = rule["body"]["args"][1]["args"][0]
        elif name == "assume_gift_without_evidence": rule["body"]["args"][0] = {"node_id": "mutant.gift", "op": "literal", "type": "bool", "value": True}
        else: rule["scope"] = {"node_id": "mutant.scope", "op": "literal", "type": "bool", "value": True}
        build = build_candidate(mutant, out / "mutants" / name, args.jdk)
        actual = run_java(build["jar"], named, args.jdk, build["class_name"])
        detected = [c["id"] for c, r in zip(named, actual) if r["status"] != c["expected"]["status"]]
        assert detected, "The fixed source-written cases did not detect " + name
        mutations[name] = {"detected_by_cases": detected, "jar_sha256": build["manifest"]["jar_sha256"], "bundle_hash": digest(mutant)}
        (out / "mutants" / name / "actual-results.json").write_bytes(canonical(actual))
    # No synthetic meaning approval is manufactured. This candidate must remain
    # blocked because source dependencies, legal issues and reviewed coverage are open.
    try: lc.transition("test.author", "submit", state["bundle_hash"], "submit", state["revision"])
    except LegalMathError as exc: assert exc.code == "E_DEPENDENCY"
    else: raise AssertionError("Unresolved references were allowed into review")
    with db.connect() as con:
        pending = con.execute("SELECT count(*) FROM issues WHERE bundle_hash=? AND resolved=0", (state["bundle_hash"],)).fetchone()[0]
        assert pending == 5
        assert lc.state(con, state["bundle_hash"])["state"] == "DRAFT"
        assert con.execute("SELECT count(*) FROM releases").fetchone()[0] == 0
    assert db.verify()
    with (out / "prior-acceptance-check.json").open("w") as log:
        subprocess.run([sys.executable, str(ROOT / "scripts/check_execution.py")], cwd=ROOT, check=True, stdout=log)
    result = {"status": "SCOPED_SECOND_CIRCULAR_ENGINEERING_CHECK_PASSED", "source": "23EC46", "selected_paragraph": 10,
        "authority": "UNREVIEWED_CANDIDATE", "source_raw_sha256": raw_digest(source_raw), "oracle_sha256": freeze["oracle_sha256"],
        "bundle_hash": state["bundle_hash"], "java": built, "verification_passed": verification["passed"],
        "named_scenarios_passed": len(named), "three_valued_combinations_passed": len(truth_cases), "total_cases": len(cases),
        "compiled_mutants_detected": mutations, "inventory_paragraphs": 18, "inventory_footnotes": 4,
        "open_legal_issues": pending, "unresolved_external_sources": len(dependencies["unresolved"]),
        "review_submission_blocked": True, "released": False, "automatic_translation_tested": False,
        "independent_legal_adjudication": "PENDING", "blind_held_out_circular": False,
        "outcome": "Correct execution relative to the explicitly stated interpretation and supplied fact classifications; complete source-to-rule correctness is not established."}
    (out / "result.json").write_bytes(canonical(result))
    paths = sorted(p for p in HERE.iterdir() if p.is_file())
    manifest = {"started_utc": started_utc, "finished_utc": datetime.now(timezone.utc).isoformat(), "command": [sys.executable, *sys.argv],
        "git_commit": "N/A: workspace is not a Git repository", "environment": {"python": sys.version, "platform": platform.platform(), "jdk": str(Path(args.jdk).resolve())},
        "device": "CPU only; no GPU/ML framework invoked", "random_seed": "N/A: exhaustive deterministic inputs", "wall_seconds": round(time.monotonic() - started, 3),
        "plan": "docs/plans/second-circular-verification.md", "result": str(out / "result.json"),
        "input_sha256": {str(p.relative_to(ROOT)): raw_digest(p.read_bytes()) for p in paths},
        "artifact_sha256": {str(p.relative_to(out)): raw_digest(p.read_bytes()) for p in sorted(out.rglob("*"))
            if p.is_file() and "database" not in p.relative_to(out).parts},
        "program_unchanged_from_prior_acceptance": True, "status": result["status"]}
    (out / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
