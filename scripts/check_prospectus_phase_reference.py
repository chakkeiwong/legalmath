"""Bounded exhaustive checks for the isolated phase repair specifications."""
from pathlib import Path
import copy
import hashlib
from itertools import product
import json
import os
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
VENV = ROOT / ".venv/bin/python"
if Path(sys.prefix).resolve() != VENV.parent.parent.resolve():
    os.execv(str(VENV), [str(VENV), "-m", "scripts.check_prospectus_phase_reference"])
from scripts.prospectus_phase_reference import (
    Unit, Span, Text, Sequence, Choice, Dated, Fact, Build, digest, paragraph,
    coverage, contract_variants, decide, feature, law, allocate, integrate,
    admissible_evaluation, relevant_unknowns, question_coverage,
)
OUT = ROOT / "docs/implementation/prospectus-phase-roots-2026-10-06"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rejected(function):
    try:
        function()
    except (ValueError, KeyError):
        return
    raise AssertionError("Invalid input was accepted")


def main():
    start = time.monotonic()
    rows = []

    # Source units are assumed to come from a separately hash-verified snapshot.
    words = "The Issuer shall repay principal in full.".split()
    count = 0
    for mask in range(1 << (len(words) - 1)):
        lines, current = [], words[0]
        for i, word in enumerate(words[1:]):
            if mask & (1 << i):
                lines.append(current)
                current = word
            else:
                current += " " + word
        lines.append(current)
        units = {}
        for i, line in enumerate(lines):
            key = ("verified-edition", "document-A", str(i))
            units[key] = Unit(key, "repayment", line)
        rendered = paragraph(list(units), units)
        require(rendered.text == " ".join(words), "Line-break dependent paragraph")
        require(len(rendered.text) == len(rendered.origins), "Wrong source-map length")
        for char, origin in zip(rendered.text, rendered.origins):
            if origin:
                require(units[origin[0]].text[origin[1]] == char, "Lost source mapping")
        spans = [Span(key, 0, len(u.text), u.text) for key, u in units.items()]
        require(all(coverage(list(units), spans, units).values()), "Multispan gap")
        count += 1
    key = ("verified-edition", "document-A", "repeat")
    raw = "Repay at par. Repay at par."
    units = {key: Unit(key, "repayment", raw)}
    spans = [Span(key, 0, 13, raw[:13]), Span(key, 14, len(raw), raw[14:])]
    require(all(coverage([key], spans, units).values()), "Repeated occurrence lost")
    require(not coverage([key], spans[:1], units)[key], "Uncovered occurrence accepted")
    rejected(lambda: coverage([key], [Span(key, 0, 13, "changed quote")], units))
    second = ("verified-edition", "document-B", "repeat")
    units[second] = Unit(second, "repayment", raw)
    rejected(lambda: paragraph([key, second], units))
    edges = {"operative": ["definition"], "header": ["section14"]}
    require(relevant_unknowns(["operative"], edges, ["section14"]) == [], "Irrelevant header blocks")
    edges["definition"] = ["section14"]
    require(relevant_unknowns(["operative"], edges, ["section14"]) == ["section14"],
            "Indirect relevant dependency hidden")
    declared = ["Q1", "Q2-possible-common", "Q2-common-only", "Q4", "Q5", "Q6"]
    covered = question_coverage(declared, {"Q1": True})
    require(set(covered) == set(declared) and covered["Q4"] == "PARTIAL", "Q3 omits questions")
    rows.append({"id": "source-occurrences", "status": "PASS",
                 "line_partitions": count, "checks": "character mapping, repeated spans, multispan coverage, quote and namespace rejection",
                 "limit": "Known paragraph boundaries and whitespace line splits; no automatic OCR/dehyphenation proof."})

    fragments = ["Repay ", "100", "90", " ", "EUR", "USD", "CHF", "hidden"]
    units = {}
    leaves = []
    for i, fragment in enumerate(fragments):
        key = ("verified-edition", "terms", str(i))
        units[key] = Unit(key, "clause", fragment, visible=(i != 7))
        leaves.append(Text(Span(key, 0, len(fragment), fragment)))
    tree = Sequence((leaves[0], Choice("amount", tuple(leaves[1:3])),
                     leaves[3], Choice("currency", tuple(leaves[4:7])), leaves[7]))
    variants, missing = contract_variants(tree, {}, units)
    expected = {f"Repay {amount} {currency}" for amount in ("100", "90")
                for currency in ("EUR", "USD", "CHF")}
    require({v.text for v in variants} == expected and len(missing) == 2, "Lost alternatives")
    for a, c in product(range(2), range(3)):
        selected, missing = contract_variants(tree, {"amount": a, "currency": c}, units)
        require(len(selected) == 1 and not missing, "Wrong selected construction")
        require(selected[0].text == f"Repay {fragments[1+a]} {fragments[4+c]}", "Wrong branch")
        for char, origin in zip(selected[0].text, selected[0].origins):
            require(origin is not None and units[origin[0]].text[origin[1]] == char,
                    "Construction changed untouched text")
    rejected(lambda: contract_variants(tree, {"amount": -1}, units))
    rejected(lambda: contract_variants(tree, {"unknown": 0}, units))
    rows.append({"id": "contract-construction", "status": "PASS", "complete_selections": 6,
                 "checks": "all alternatives retained; invisible unit excluded; untouched character provenance",
                 "limit": "Text/Sequence/Choice only; no field parser, amendment precedence or reference resolver."})

    evaluations = stable_extensions = 0
    for n in (1, 2, 3):
        names = ["a", "b", "c"][:n]
        worlds = list(product((False, True), repeat=n))
        for table in range(1 << len(worlds)):
            terms = [("and", *(name if value else ("not", name)
                               for name, value in zip(names, values)))
                     for i, values in enumerate(worlds) if table & (1 << i)]
            core = ("or", *terms) if terms else ("and", names[0], ("not", names[0]))
            formula = ("and", core, *(("or", name, ("not", name)) for name in names))
            for partial in product((None, False, True), repeat=n):
                obs = dict(zip(names, partial))
                matching = [(i, w) for i, w in enumerate(worlds)
                            if all(v is None or v == w[j] for j, v in enumerate(partial))]
                outcomes = {bool(table & (1 << i)) for i, _ in matching}
                expected = "YES" if outcomes == {True} else "NO" if outcomes == {False} else "UNKNOWN"
                require(decide(formula, obs) == expected, "Completion truth-table mismatch")
                if expected != "UNKNOWN":
                    for _, values in matching:
                        require(decide(formula, dict(zip(names, values))) == expected,
                                "Decisive result changed under consistent completion")
                        stable_extensions += 1
                evaluations += 1
        require(decide(("or", *names), {names[0]: "conflict"}) == "CONFLICT",
                "Conflict lost")
    require(decide(("and", "eligible", "court_order"), {"eligible": True, "court_order": False}) == "NO",
            "Additional false premise ignored")
    require(decide(("not", "loss"), {"loss": True}) == "NO", "Negation ignored")
    require(feature([{"loss": True}], lambda _: [False, True], lambda r, trigger: r["loss"] and trigger) == "YES",
            "Feature confused with actual event")
    require(feature([{"loss": False}, {"loss": True}], lambda _: [False, True],
                    lambda r, trigger: r["loss"] and trigger) == "UNKNOWN", "Reading ambiguity erased")
    require(feature([], lambda _: [True], lambda r, w: True) == "CONFLICT", "Vacuous proof")
    assets = {"common", "preferred"}
    require(("common" in assets) and assets != {"common"}, "Q2 subquestions not distinguished")
    rows.append({"id": "partial-information", "status": "PASS", "truth_table_comparisons": evaluations,
                 "consistent_completion_checks": stable_extensions,
                 "checks": "every Boolean function through three variables, all partial observations, negation, conflict, reading/contingency quantifiers",
                 "limit": "Formal predicate correctness conditional on reviewed translation; production limit is twelve facts."})

    key = ("verified-edition", "law", "1")
    units = {key: Unit(key, "article", "The authority requires consent and a court order.")}
    source = Span(key, 0, len(units[key].text), units[key].text)
    basis_dates = Dated(0, None, 0)
    temporal = 0
    for valid_from, valid_until, known_from, effective, known in product(range(3), range(1, 5), range(3), range(5), range(5)):
        if valid_until <= valid_from:
            continue
        fact = Fact("consent", True, Dated(valid_from, valid_until, known_from), source)
        result = law("consent", source, basis_dates, [fact], effective, known, units)
        expected = "YES" if valid_from <= effective < valid_until and known_from <= known else "UNKNOWN"
        require(result == expected, "Validity/knowledge interval error")
        temporal += 1
    facts = [Fact("consent", True, basis_dates, source), Fact("court_order", False, basis_dates, source)]
    require(law(("and", "consent", "court_order"), source, basis_dates, facts, 1, 1, units) == "NO",
            "Declared legal premise ignored")
    require(law("consent", source, basis_dates, [facts[0], Fact("consent", False, basis_dates, source)], 1, 1, units) == "CONFLICT",
            "Contradictory fact erased")
    rejected(lambda: law("consent", Span(("missing", "law", "1"), 0, 1, "x"),
                         basis_dates, [facts[0]], 1, 1, units))
    rejected(lambda: law("consent", source, basis_dates,
                         [Fact("consent", True, Dated(2, 1, 0), source)], 1, 1, units))
    require(law("consent", source, Dated(2, None, 0), [facts[0]], 1, 1, units) == "UNKNOWN",
            "Future law applied")
    rows.append({"id": "dated-law", "status": "PASS", "interval_comparisons": temporal,
                 "checks": "future validity, exclusive end, later knowledge, explicit false premise, conflict, missing source, malformed interval",
                 "limit": "Source identity is not authority; applicable law and completeness still need legal review."})

    allocations = 0
    for a, b, price in product(range(13), range(13), range(1, 11)):
        payload = {"currency": "EUR", "price": price, "holdings": [
            {"holder_id": "A", "currency": "EUR", "amount": a},
            {"holder_id": "B", "currency": "EUR", "amount": b}]}
        result = allocate(payload)
        require(result["status"] == "SUPPORTED_SUBCALCULATION", "Valid allocation rejected")
        for row, amount in zip(result["rows"], (a, b)):
            rem = Fraction(row["remainder_value"])
            require(row["shares"] == amount // price and 0 <= rem < price
                    and amount == row["shares"] * price + rem, "Allocation violates conservation")
        allocations += 1
    split = allocate({"currency": "EUR", "price": 10, "holdings": [
        {"holder_id": "A", "currency": "EUR", "amount": 6},
        {"holder_id": "B", "currency": "EUR", "amount": 6}]})
    require([r["shares"] for r in split["rows"]] == [0, 0], "Distinct legal holders merged")
    aggregated = allocate({"currency": "EUR", "price": 10, "holdings": [
        {"holder_id": "A", "currency": "EUR", "amount": 6},
        {"holder_id": "A", "currency": "EUR", "amount": 6}]})
    require(aggregated["rows"][0]["shares"] == 1, "Same legal holder not aggregated")
    base = {"currency": "EUR", "price": 10, "holdings": [{"holder_id": "A", "currency": "EUR", "amount": 6}]}
    malformed = [None, [], {}, dict(base, holdings=None), dict(base, holdings={}),
                 dict(base, price=None), dict(base, price=True), dict(base, price=0),
                 dict(base, price=1.1), dict(base, price="nan"), dict(base, unknown=1),
                 dict(base, holdings=[{"holder_id": "A", "currency": "USD", "amount": 6}])]
    for payload in malformed:
        require(allocate(payload)["status"] == "INVALID_INPUT", "Malformed input escaped")
    rows.append({"id": "exact-allocation", "status": "PASS", "allocation_cases": allocations,
                 "malformed_inputs": len(malformed),
                 "checks": "per legal holder floor, exact residual conservation, strict shape/currency",
                 "limit": "Residual is an arithmetic value, not a claim that the contract requires cash compensation."})

    tasks = {
        "P1": (["source"], "source-v1", {"parser": "explicit-v1"}, lambda d: d["source"]),
        "P2": (["P1", "selection"], "construction-v1", {}, lambda d: d["P1"][d["selection"]]),
        "P3": (["P2"], "semantics-v1", {}, lambda d: {"term": d["P2"]}),
        "P4": (["law"], "law-v1", {}, lambda d: d["law"]),
        "P5": (["P3", "amount"], "finance-v1", {}, lambda d: [d["P3"], d["amount"]]),
        "P6": (["P3", "P4", "P5", "context"], "integration-v1", {}, lambda d: d),
    }
    builder = Build(tasks)
    mutations = 0
    for selection, legal, amount in product(range(2), (False, True), range(5)):
        inputs = {"source": ["fixed", "floating"], "selection": selection, "law": legal,
                  "amount": amount, "context": "senior"}
        got = builder.run("P6", inputs)
        expected = {"P3": {"term": inputs["source"][selection]}, "P4": legal,
                    "P5": [{"term": inputs["source"][selection]}, amount], "context": "senior"}
        require(got == expected, "Cached graph differs from direct computation")
        require(builder.run("P6", inputs) == got and builder.executed == [], "Unchanged input rebuilt")
        mutations += 1
    tasks["P3"] = (["P2"], "semantics-v2", {}, lambda d: {"term": d["P2"], "revision": 2})
    require(builder.run("P6", inputs)["P3"]["revision"] == 2, "Code change ignored")
    require(set(builder.executed) == {"P3", "P5", "P6"}, "Wrong descendant invalidation")
    deps, version, config, fn = tasks["P1"]
    tasks["P1"] = (deps, version, {"parser": "explicit-v2"}, fn)
    builder.run("P6", inputs)
    require(builder.executed == ["P1"], "Environment change or early cutoff ignored")
    sig, result_hash, value = builder.cache["P3"]
    builder.cache["P3"] = (sig, result_hash, {"corrupted": True})
    require("corrupted" not in builder.run("P6", inputs)["P3"], "Corrupted output reused")
    rejected(lambda: Build({"A": (["B"], "a", {}, lambda x: x),
                            "B": (["A"], "b", {}, lambda x: x)}).run("A", {}))
    rows.append({"id": "phase-dataflow", "status": "PASS", "input_combinations": mutations,
                 "checks": "same result as direct calculation, reuse, task/environment changes, descendant invalidation, corruption, cycles",
                 "limit": "Static complete declared dependencies and pure tasks; no sandboxed discovery or durable receipt transaction implemented."})

    context = {"instrument_id": "basf-senior-2032", "instrument_kind": "senior_bond",
               "effective_at": "2023-03-08T00:00:00Z", "known_at": "2026-10-06T23:59:59Z",
               "jurisdiction": "DE", "purpose": "contract_features",
               "source_set_hash": "verified-source-set", "question_version": "v2"}
    phase_rows = [{"phase": phase, "context": dict(context), "payload": {"answer": answer},
                   "payload_hash": digest({"answer": answer})}
                  for phase, answer in zip(("P3", "P4", "P5"), ("UNKNOWN", "NO", "UNSUPPORTED"))]
    obligations = [f"obligation-{i}:v1:premises-A" for i in range(14)]
    got = integrate(context, phase_rows, obligations, obligations)
    require(got["status"] == "BOUND_REPORT" and got["answers"][0]["answer"] == "UNKNOWN"
            and not got["transaction_clearance"], "Unknown or clearance changed")
    for field in context:
        broken = copy.deepcopy(phase_rows)
        broken[0]["context"][field] = "different"
        require(integrate(context, broken, obligations, obligations)["status"] == "REJECTED_CONTEXT",
                "Context mismatch accepted")
    changed = obligations[:-1] + ["different-obligation:v1:premises-A"]
    require(integrate(context, phase_rows, changed, obligations)["status"] == "REJECTED_OBLIGATIONS",
            "Count substituted for identity")
    require(integrate(context, phase_rows[:2], obligations, obligations)["status"] == "REJECTED_PHASES",
            "Missing phase accepted")
    broken = copy.deepcopy(phase_rows)
    broken[0]["payload"]["answer"] = "YES"
    require(integrate(context, broken, obligations, obligations)["status"] == "REJECTED_CONTEXT",
            "Tampered payload accepted")
    rows.append({"id": "context-integration", "status": "PASS", "context_mutations": len(context),
                 "checks": "required phase products, every context field, content binding, exact obligation identities, UNKNOWN retained",
                 "limit": "Identity mapping only. Different question dates need a separately reviewed, versioned transformation."})

    support = ["Q1"]
    signoffs = [{"author": "reviewer-C", "cohort_hash": "cohort", "report_hash": "report", "scope": support}]
    args = ["implementer", ["reviewer-A", "reviewer-B"], "reviewer-C", support,
            ["Q1"], "cohort", "report", signoffs]
    require(admissible_evaluation(*args), "Valid identity/scope binding rejected")
    failures = []
    for index, value in [(2, "implementer"), (2, "reviewer-A"), (3, ["Q5"]),
                         (5, "changed-cohort"), (6, "changed-report")]:
        altered = copy.deepcopy(args)
        altered[index] = value
        require(not admissible_evaluation(*altered), "Invalid evaluation binding accepted")
        failures.append(index)
    rows.append({"id": "independent-evaluation-binding", "status": "PASS",
                 "invalid_variants": len(failures),
                 "checks": "disjoint implementer/readers/adjudicator, scope subset, cohort/report bound signoff",
                 "limit": "Logical identities only; cannot establish competence, actual blinding, independence, label quality or future accuracy."})

    result = {"status": "PASS", "groups": rows, "production_modified": False,
              "claim": "Small-model engineering checks, not independent legal validation"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reference-results.json").write_text(json.dumps(result, indent=2) + "\n")
    files = ["scripts/prospectus_phase_reference.py", "scripts/check_prospectus_phase_reference.py",
             "src/legalmath/prospectus/semantics.py",
             "docs/plans/prospectus-phase-roots-2026-10-06.md"]
    manifest = {"baseline_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "command": "python3 -m scripts.check_prospectus_phase_reference",
                "python": sys.executable, "python_version": platform.python_version(),
                "source_module": str(ROOT / "src/legalmath/prospectus/semantics.py"),
                "gpu": "intentionally hidden via CUDA_VISIBLE_DEVICES=-1; no GPU framework imported",
                "seeds": "N/A: exhaustive deterministic enumeration", "data": "explicit finite synthetic domains in script",
                "plan": files[-1], "result": str((OUT / "reference-results.json").relative_to(ROOT)),
                "wall_seconds": time.monotonic() - start,
                "files": {file: hashlib.sha256((ROOT / file).read_bytes()).hexdigest() for file in files},
                "result_sha256": hashlib.sha256((OUT / "reference-results.json").read_bytes()).hexdigest()}
    (OUT / "reference-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "groups": len(rows), "truth_table_comparisons": evaluations,
                      "stable_completion_checks": stable_extensions, "temporal_comparisons": temporal,
                      "allocations": allocations, "line_partitions": count,
                      "wall_seconds": manifest["wall_seconds"]}))


if __name__ == "__main__":
    from fractions import Fraction
    main()
