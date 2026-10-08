"""S4 deterministic inputs; legal readings stay qualified and individually retained."""
from pathlib import Path
from legalmath.canonical import canonical, digest
from legalmath.interpretation.semantics import conditional_ir as ir, integration
from scripts import legal_interpretation_s3_data as s3
from scripts.legal_interpretation_successor_data import retained_inputs

ROOT = Path(__file__).resolve().parents[1]


def runner_for(directory):
    runner = s3.runner_for(directory)
    runner.semantic_options = {**runner.semantic_options, "profile": integration.CONDITIONAL_PROFILE}
    integration.configuration(runner.semantic_options)
    return runner


def execute_product(directory):
    document, source, inputs, provenance = s3.product_inputs()
    runner = runner_for(directory)
    return runner, runner.run([document], s3.SLICE, semantic_inputs=inputs), provenance


def reading_inventory():
    packet, overlay, candidates, questions, comparisons = retained_inputs(ROOT)
    reasons = {
        "allocation": "A responsibility allocation needs a justified source-to-duty relation.",
        "allocation-and-adequacy": "Responsibility and adequacy need distinct sufficient premises.",
        "allocation-and-conduct": "Allocation does not establish supervision or required conduct.",
        "unresolved-discharge": "The discharge standard and its relation to conduct remain unresolved.",
    }
    rows = []
    for cid, reading in sorted(candidates.items()):
        comparison = comparisons[cid]
        roles = [r for r in overlay["records"] if r["reading_id"] == cid]
        rows.append({"reading_id": cid, "reading_hash": digest(reading),
            "original_reading": reading, "packet_hash": digest(packet),
            "role_records": [{"role": r["role"], "hash": digest(r)} for r in roles],
            "category": comparison["category"], "comparison": comparison,
            "formalization": "EXISTING_CONDITIONAL_FORMULA" if reading.get("formalization") else "UNFORMALIZED",
            "source_to_rule": "NOT_ESTABLISHED", "remaining_gap": reasons[comparison["category"]],
            "s4_disposition": "RETAINED; no English-to-rule repair established"})
    if len(rows) != 35 or sum(r["formalization"] == "UNFORMALIZED" for r in rows) != 32:
        raise ValueError("Retained reading inventory changed")
    if sum(len(r["role_records"]) for r in rows) != 70:
        raise ValueError("Retained role inventory changed")
    return {"readings": rows, "unsupported_constructs": [
        "Automatic formalization of 32 retained English readings",
        "Negative recursive heads or dynamically generated contrary evidence",
        "Recursive defeasible argument trees and automatic legal priorities",
        "Source-to-rule equivalence and full legal discharge standards",
        "Universal correctness of source lowering, codecs, Java and the JVM"],
        "preferred_argument_bound": 8, "new_profile": ir.PROFILE,
        "legal_correctness": "NOT_ESTABLISHED", "release_eligible": False}


def recursive_programs():
    def make(name, codes, count, rules):
        value = {"profile": ir.PROFILE, "context_hash": digest({"synthetic_scenario": name}),
            "fact_ids": ["fixed." + str(i) for i in range(len(codes))], "codes": codes,
            "heads": ["positive." + str(i) for i in range(count)],
            "rules": [{"id": name + "." + str(i), "head": h, "facts": fs, "parents": ps}
                      for i, (h, fs, ps) in enumerate(rules)]}
        return ir.decode(canonical(value))
    cases = {f"evidence-{c}": make(f"evidence-{c}", [c], 2,
        [(0, [0], []), (1, [], [0]), (0, [], [1])]) for c in range(4)}
    cases["unseeded-cycle"] = make("unseeded-cycle", [], 2, [(0, [], [1]), (1, [], [0])])
    cases["alternative-seed"] = make("alternative-seed", [3], 2,
        [(0, [0], []), (0, [], []), (1, [], [0])])
    cases["joint-parents"] = make("joint-parents", [], 3,
        [(0, [], []), (1, [], []), (2, [], [0, 1])])
    cases["maximum-chain"] = make("maximum-chain", [], 64,
        [(i, [], [] if i == 0 else [i - 1]) for i in range(64)])
    return cases
