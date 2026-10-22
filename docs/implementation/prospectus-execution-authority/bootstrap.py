"""One-time, lossless obligation migration; no historical result is promoted."""
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from legalmath.prospectus.execution_authority import Authority, REL, digest, file_hash, read, write

BASE = ROOT / REL
C = "docs/implementation/prospectus-integration-closure"
G = C + "/ocr-geometry-repair-2026-10-12"
PLAN = "docs/plans/prospectus-execution-authority-2026-10-12.md"


def main():
    if (BASE / "program.json").exists():
        raise ValueError("Migration already retained")
    originals = [C + "/gap-status.json", C + "/attribution-review.json",
                 C + "/bes-onward-sources/attempt-002/source-disposition.json",
                 "docs/implementation/prospectus-basf-reference-repair/NEXT-PROGRAM.md"]
    names = ["gap-status.json", "attribution-review.json", "bes-dependencies.json", "basf-next.md"]
    bindings = {}
    for original, name in zip(originals, names):
        target = BASE / "baseline" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / original, target)
        bindings[str(target.relative_to(ROOT))] = file_hash(target)
    gaps, attribution, onward = (read(ROOT / p) for p in originals[:3])
    tasks = {}

    def task(key, title, *, handler="agent", deps=(), priority=100, stream="engineering", criterion=None, external=None):
        tasks[key] = {"id": key, "title": title, "handler": handler, "depends_on": list(deps),
                      "priority": priority, "stream": stream, "obligations": [],
                      "inputs": [str((BASE / "baseline/gap-status.json").relative_to(ROOT))],
                      "dossier": str((BASE / "dossiers" / (key + ".md")).relative_to(ROOT)),
                      "acceptance": criterion or "Retain source-bound positive/adverse and actual downstream evidence; add or run the reviewed task-specific validator before acceptance. A submitted PASS is not completion.",
                      "budget_key": key, "timeout_seconds": 120,
                      "reason": title + "; close only the specified evidence requirement"}
        if external:
            tasks[key]["external_input"] = external
        return key

    task("native-cohort", "Freeze actual OCR/layout development cases and missing families", handler="native-cohort", priority=10,
         criterion="Recompute frozen P1 identities and complete reviewed report spans; preserve all missing real layout families and development exposure labels")
    task("native-interfaces", "Consume the cohort and preserve direct native callback geometry", handler="native-interfaces", deps=["native-cohort"], priority=20,
         criterion="Lossless callback-event accounting, known colon geometry and exact downstream cohort binding; no production/native-patch promotion")
    task("native-layout-cases", "Add independently reviewed table, rotation, vertical and bidirectional pages", deps=["native-interfaces"], priority=30, stream="automatic")
    task("native-candidates", "Compare isolated native group-axis repair and direct-recognition adapter", deps=["native-interfaces"], priority=40)
    task("page-coverage", "Review remaining image/vector/table source coverage", priority=50, stream="automatic")
    task("portuguese-2008", "Consume retained Portuguese 2008 audit through P1 and report scope", priority=45)
    task("source-authority", "Establish edition, authenticity and publication/knowledge evidence", priority=60, stream="assisted")
    task("relation-discovery", "Evaluate source-bound automatic row and qualification relations", priority=95, stream="automatic")
    for i, (key, title) in enumerate([
        ("basf-references", "Bind complete BASF prose references and targets without cosmetic renumbering"),
        ("basf-margins", "Review full BASF margin scope groups and governed source occurrences"),
        ("basf-office", "Acquire or conditionally analyse BASF calculation-agent office authority"),
        ("basf-incorporation", "Preserve and adjudicate conflicting BASF incorporation readings"),
        ("basf-meanings", "Complete source-specific BASF meanings, bilingual priority and unresolved intervals")]):
        task(key, title, priority=80 + i, stream="assisted")
    task("law-applicability", "Review real dated-law and authority cases with excluded-premise controls", priority=90, stream="assisted")
    task("reasoning-corpus", "Run an independently enumerated larger finite reasoning corpus", priority=100)
    task("authoring-export", "Run actual assigned-reader cross-document exports through the service", handler="external", stream="assisted",
         external="Qualified assigned readers and genuine independently authored browser exports; local fixture exports cannot satisfy this requirement")
    task("finance-conventions", "Review real-source coupon conventions and exact irregular schedule comparators", priority=110, stream="assisted")
    task("entitlement", "Validate conditional entitlement/transfer cases through financial consumers", priority=112, stream="assisted")
    task("instrument-facts", "Obtain case-specific entitlement and dated legal/event facts", handler="external", stream="assisted",
         external="Actual client/instrument/event records for the chosen case; conditional local analysis continues without them")
    task("native-binding", "Bind actual native libraries, negative lookups and environment inputs", priority=120)
    task("native-confinement", "Integrate a supported immutable production runtime/read boundary", deps=["native-binding"], priority=121)
    task("portability", "Repeat installed actual consumers on a second host or equivalent isolated runtime", deps=["native-confinement"], priority=122)
    task("recovery", "Extend real multilingual/correction worker recovery against clean recomputation", priority=125)
    task("independent-packet", "Prepare and freeze a genuinely unexposed independent review cohort", priority=130, stream="assisted")
    task("independent-readings", "Obtain qualified first readings, adjudication and sign-offs", handler="external", deps=["independent-packet"], stream="assisted",
         external="Authorized qualified readers/adjudicator and authentic signed, unexposed first readings; missing people cannot be supplied by agent-generated records")
    task("actus-prerequisites", "Resolve retained ACTUS pinned-core/version/licence prerequisites", priority=140, stream="package_evaluation")
    task("actus-comparison", "Run actual plain-PAM numerical comparison under reviewed identical inputs", deps=["actus-prerequisites"], priority=141, stream="package_evaluation")
    task("cdm-profile", "Specify the CDM receiver/version/profile and required native functions", handler="external", stream="package_evaluation",
         external="Receiving-system/profile decision and supported runtime prerequisites; no integration or package rejection is inferred")
    task("cdm-roundtrip", "Run the official bond fixture through the named CDM exchange", deps=["cdm-profile"], priority=145, stream="package_evaluation")
    task("authority-acceptance", "Verify master coverage, actual transitions and final capability attribution", priority=150)
    dep_tasks = {}
    for i, row in enumerate(onward["rows"]):
        key = "source-" + row["id"].lower()
        dep_tasks[row["id"]] = task(key, "Resolve " + row["title"], priority=65 + i, stream="assisted")

    maps = {
        "G01": ["native-cohort", "native-interfaces", "native-candidates", "page-coverage", "portuguese-2008", "source-authority", "native-confinement", "portability", "independent-readings", *dep_tasks.values()],
        "G02": ["law-applicability", "basf-office", "independent-readings"],
        "G03": ["basf-references", "basf-margins", "basf-incorporation", "basf-meanings"],
        "G04": ["independent-packet", "independent-readings"], "G05": ["authoring-export"],
        "G06": ["reasoning-corpus", "law-applicability"], "G07": ["reasoning-corpus"],
        "G08": ["native-layout-cases", "page-coverage", "native-candidates"],
        "G09": ["relation-discovery", "basf-references", "basf-margins"],
        "G10": ["native-cohort", "native-interfaces", "native-layout-cases", "native-candidates", "portuguese-2008"],
        "G11": ["authoring-export", "independent-readings"],
        "G12": ["basf-references", "basf-margins", "basf-office", "basf-incorporation", "basf-meanings", "instrument-facts", "independent-readings"],
        "G13": ["basf-references", "basf-incorporation", "basf-meanings", *dep_tasks.values()],
        "G14": ["finance-conventions", "entitlement", "instrument-facts", "basf-office"],
        "G15": ["finance-conventions", "entitlement", "instrument-facts"],
        "G16": ["native-binding", "recovery"], "G17": ["portability", "recovery"],
        "G18": ["native-binding", "native-confinement", "portability"],
        "G19": ["independent-packet", "independent-readings"],
        "G20": ["authority-acceptance", "source-authority", "native-confinement", "independent-readings"],
        "E01": ["basf-office", "basf-incorporation", "basf-meanings"],
        "E02": ["independent-packet", "independent-readings"],
        "E03": ["finance-conventions", "entitlement", "instrument-facts"],
        "E04": ["actus-prerequisites", "actus-comparison"], "E05": ["cdm-profile", "cdm-roundtrip"],
    }
    package_tasks = [["native-layout-cases", "relation-discovery"], ["authoring-export"], ["finance-conventions"],
                     ["native-candidates", "page-coverage"], ["reasoning-corpus"], ["recovery"],
                     ["actus-prerequisites", "actus-comparison"], ["cdm-profile", "cdm-roundtrip"],
                     ["native-binding", "native-confinement", "portability"]]
    inventory, obligations = [], []

    def obligation(oid, original, locator, value, selected, scope="engineering"):
        origin = {"path": original, "sha256": file_hash(ROOT / original), "locator": locator,
                  "record_sha256": digest(value)}
        inventory.append({"id": oid, "origin": origin, "scope": scope, "record": value})
        obligations.append({"id": oid, "origin": origin, "scope": scope,
                            "tasks": selected, "budget_keys": sorted({tasks[t]["budget_key"] for t in selected})})
        for key in selected:
            tasks[key]["obligations"].append(oid)

    for group in ("gaps", "external_requirements"):
        for index, row in enumerate(gaps[group]):
            obligation(row["id"], originals[0], f"/{group}/{index}", row, maps[row["id"]])
    for index, row in enumerate(gaps["residual_scope"]):
        obligation(f"RESIDUAL-{index+1:02d}", originals[0], f"/residual_scope/{index}", row, maps[row["finding"]], "retained_scope_limit")
    for index, row in enumerate(onward["rows"]):
        compact = {k: v for k, v in row.items() if k not in {"search_hits", "candidate_paths"}}
        obligation(row["id"], originals[2], f"/rows/{index}", row, [dep_tasks[row["id"]]], "assisted")
        inventory[-1]["record"] = compact
        inventory[-1]["full_record_retained_in_baseline"] = True
    for index, row in enumerate(attribution["packages"]):
        obligation(f"PACKAGE-{index+1:02d}", originals[1], f"/packages/{index}", row, package_tasks[index], "package_evaluation")
    sections = re.split(r"\n(?=[1-5]\. )", (ROOT / originals[3]).read_text())
    for index, keys in enumerate([["basf-references"], ["basf-margins"], ["basf-office"], ["basf-incorporation"], ["independent-packet", "independent-readings", "instrument-facts", "actus-comparison", "cdm-roundtrip"]]):
        obligation(f"BASF-{index+1:02d}", originals[3], f"numbered-package-{index+1}", sections[index+1], keys, "assisted")

    native_paths = [G + "/consumer/attempt-002/evidence/source-product.json.gz",
                    G + "/direct-recognition-001/callback.json", G + "/direct-recognition-001/started.json",
                    G + "/direct-recognition-001/result.json",
                    "docs/plans/prospectus-native-geometry-followup-2026-10-12.md",
                    "scripts/prospectus_report_scope.py", "src/legalmath/prospectus/successor/service.py",
                    "src/legalmath/prospectus/successor/contracts.py"]
    from scripts.prospectus_report_scope import CASES, SOURCES
    freeze = ROOT / C / "source-report-scope-2026-10-12/freeze-002"
    native_paths += [str(p.relative_to(ROOT)) for p in freeze.iterdir() if p.is_file()]
    for case in CASES.values():
        native_paths.append(str((SOURCES / case["source"]).relative_to(ROOT)))
        if "request" in case:
            native_paths.append(str((SOURCES / case["request"]).relative_to(ROOT)))
    for key in ("native-cohort", "native-interfaces"):
        tasks[key]["inputs"] += sorted(set(native_paths))
    for key, row in tasks.items():
        relevant = [entry for entry in inventory if entry["id"] in row["obligations"]]
        text = ("# " + row["title"] + "\n\nTask `" + key + "`; original obligations: "
                + ", ".join(row["obligations"]) + ".\n\nAcceptance: " + row["acceptance"] + "\n\n"
                + "Read the retained original records below before acting. Exact source identities are in the migration inventory. "
                + "Preserve historical failures and unresolved source facts. A planning record or test total cannot close this task.\n\n"
                + "Required evidence: source/method bindings, positive and adverse controls, actual downstream consumer result, limitations and next justified action. "
                + "For independent readings, the existing authenticated-reader admission and genuine unexposed review remain mandatory.\n\n")
        for entry in relevant:
            record = entry["record"]
            summary = {k: record[k] for k in ("finding", "remaining", "requirement", "scope", "title", "reason", "next_action") if k in record} if isinstance(record, dict) else record
            text += "## " + entry["id"] + "\n\n" + (json.dumps(summary, indent=2, ensure_ascii=False) if isinstance(summary, dict) else summary) + "\n\n"
        path = ROOT / row["dossier"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    write(BASE / "baseline/inventory.json", inventory, exclusive=True)
    prior = {f"R{i}": len(list((ROOT / C / "phases" / f"R{i}").glob("attempt-*"))) for i in range(9)}
    write(BASE / "baseline/prior-attempts.json", prior, exclusive=True)
    bindings[str((BASE / "baseline/prior-attempts.json").relative_to(ROOT))] = file_hash(BASE / "baseline/prior-attempts.json")
    program = {"version": "prospectus-authority.v1", "revision": 1, "plan": PLAN,
               "inventory_sha256": digest(inventory), "baseline_files": bindings,
               "obligations": obligations, "tasks": list(tasks.values()),
               "budgets": {key: {"maximum_new_attempts": 2,
                                  "provenance": "One reviewed task admission plus one changed repair; historical phase attempts retained separately and not reset"}
                           for key in tasks},
               "permission_boundary": "No new network, install, external-message or host permission",
               "legacy_validation": "Current R0–R8 are verification evidence, not task-completion predicates"}
    write(BASE / "revisions/0001.json", program, exclusive=True)
    write(BASE / "program.json", program, exclusive=True)
    authority = Authority(ROOT)
    with authority.lock():
        authority.append("REVISION", program_sha256=digest(program), review=PLAN, review_sha256=file_hash(ROOT / PLAN))
        authority.refresh_locked()
    write(BASE / "migration.json", {"status": "PASS", "original_gaps": 20, "external_requirements": 5,
          "residual_scopes": 6, "bes_dependencies": len(onward["rows"]), "packages": len(attribution["packages"]),
          "basf_packages": 5, "register_entries": len(inventory), "tasks": len(tasks),
          "unmapped": [], "scope_removed": [], "historical_results_promoted": [],
          "note": "Overlapping traceability entries; count is not a legal-progress metric"}, exclusive=True)
    print(json.dumps({"status": "PASS", "register_entries": len(inventory), "tasks": len(tasks)}))


if __name__ == "__main__":
    main()
