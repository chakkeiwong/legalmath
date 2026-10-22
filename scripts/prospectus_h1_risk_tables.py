"""Admitted complete H1 risk reading and isolated installed comparisons."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile

from scripts import prospectus_h1_risk_source as source
from scripts.prospectus_h1_risk_source import ROOT, HERE, REVIEW, PLAN, STAGES, save, read, file_hash, load, files, require, child, storage
from scripts.prospectus_basf_pension_install import dependencies
from scripts.prospectus_installed_profile_worker import execution_guard
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor import process_ledger

RUNNER = ROOT / "scripts/prospectus_installed_h1_risk_tables.py"
TEST = "tests/prospectus/test_h1_risk_tables.py"
LITERAL = "Reviewed original-image risk literal or correction basis changed"
ANCHOR = "Exact original risk occurrence/character association required"
INVENTORY = "Complete risk source-fragment inventory required"
PIN = "Pinned risk profile, graph or complete previous consumer changed"
COLUMN = "Reviewed risk columns, asset categories, measures and units required"
DATE = "Original risk stock dates and thousand/million units required"
CASES = {
    "wrong-date": DATE, "wrong-sector-unit": DATE, "wrong-rating-unit": DATE,
    "amount-percent-column": COLUMN, "gross-impairment": LITERAL, "wrong-asset-category": COLUMN,
    "cross-row": LITERAL, "cross-date": LITERAL,
    "omitted-cell": "Unexpected or missing fields", "duplicate-cell": ANCHOR,
    "lost-sign": LITERAL, "dash-as-zero": LITERAL,
    "wrong-rating-group": "Original risk row role and rating group required",
    "lost-group-scope": "Original rating model/internal-scale group scope required",
    "wrong-internal-scale": LITERAL, "wrong-shared-span": ANCHOR,
    "invented-box": ANCHOR, "omitted-split-fragment": INVENTORY,
    "omitted-occurrence": INVENTORY, "omitted-qualification": INVENTORY,
    "changed-source": "Original risk PDF required", "changed-image": "Original reviewed risk image changed",
    "uncorrected-ocr": LITERAL, "wrong-correction-basis": LITERAL,
    "independent-review": "Unsupported risk review authority",
    "financial-validation": "Risk reading cannot validate accounts or select legal incorporation",
    "legal-selection": "Risk reading cannot validate accounts or select legal incorporation",
    "stale-prior": PIN, "stale-graph": PIN, "stale-pin": PIN,
    "omitted-row": "Complete ordered risk row inventory required", "duplicated-character": INVENTORY,
}
PARTITIONS = {"controls-" + letter: list(CASES)[8*i:8*i+8] for i, letter in enumerate("abcd")}


def workspace():
    return Path(read(HERE / "workspace.json")["directory"])


def methods():
    paths = [Path(__file__), Path(source.__file__), RUNNER, ROOT / TEST, ROOT / PLAN,
        REVIEW / "REVIEW.md", REVIEW / "history.json", HERE / "IMAGE-REVIEW.md",
        HERE / "IMPLEMENTATION-REVIEW.md", HERE / "draft-selector-audit.json", ROOT / "pyproject.toml",
        ROOT / "scripts/prospectus_installed_profile_worker.py", ROOT / "scripts/prospectus_basf_pension_source.py",
        ROOT / "scripts/prospectus_basf_pension_install.py"]
    paths += [ROOT / "src/legalmath" / name for name in files(ROOT / "src/legalmath")]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def profile():
    from legalmath.prospectus import h1_risk_tables as note
    require((HERE / "IMAGE-REVIEW.md").is_file() and (HERE / "IMPLEMENTATION-REVIEW.md").is_file(), "Complete image/implementation review required")
    package, original = files(ROOT / "src/legalmath"), read(REVIEW / "history.json")["package"]
    require(len(original) == 438 and all(package.get(k) == v for k, v in original.items()), "Existing438 package files changed")
    require(sorted(set(package) - set(original)) == ["prospectus/h1_risk_spec.py", "prospectus/h1_risk_tables.py"], "Unexpected new source files")
    require(read(HERE / "draft-selector-audit.json")["occurrences"] == 933, "Complete static selector review required")
    save("methods.json", methods())
    for name in read(HERE / "methods.json"):
        target = HERE / "methods" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    value = note.make_profile(load(HERE / "products.json.gz")["P1"]["payload"]["graph"],
        load(HERE / "baseline-consumer.json.gz"), read(HERE / "rendered-source.json"))
    save("profile.json", value)
    save("profile-pin.json", {"sha256": digest(value)})
    save("control-partitions.json", PARTITIONS)
    save("intended-refusals.json", CASES)
    return {"tables": len(value["tables"]), "numeric_cells": 720, "source_files": len(package), "fixed_controls": len(CASES)}


def compare():
    from legalmath.prospectus import h1_risk_tables as note
    p, cash = read(HERE / "profile.json"), read(HERE / "cash-flow-profile.json")
    result = note.consume(load(HERE / "products.json.gz"), cash, p, ROOT,
        expected_cash_flow_profile_sha256=digest(cash), expected_profile_sha256=read(HERE / "profile-pin.json")["sha256"])
    require({k: result[k] for k in ("answer", "cash_flow_review", "cash_flow_explanation")} == load(HERE / "baseline-consumer.json.gz"), "Protected complete previous consumer changed")
    review = result["risk_table_review"]
    require(review["source_occurrences"] == 933 and review["numeric_cells"] == 720, "Incomplete risk reading")
    save("risk-consumer.json.gz", result)
    summary = {"status": "PASS", "source_occurrences": 933, "table_rows": [len(t["rows"]) for t in review["tables"]],
        "numeric_cells": 720, "complete_previous_consumer_equal": True,
        "arithmetic": review["arithmetic"], "explanation": result["risk_table_explanation"],
        "automatic_interpretation": False, "independent_legal_acceptance": False}
    save("comparison.json", summary)
    return {k: summary[k] for k in ("status", "source_occurrences", "table_rows", "numeric_cells", "complete_previous_consumer_equal")}


def altered(profile, name):
    value = deepcopy(profile)
    sector, other, ratings = value["tables"]
    cells = sector["rows"][0]["cells"]
    if name == "wrong-date": sector["dates"] = ["2010-06-29"]
    elif name == "wrong-sector-unit": sector["monetary_unit"] = "million EUR"
    elif name == "wrong-rating-unit": ratings["monetary_unit"] = "thousand EUR"
    elif name == "amount-percent-column": ratings["header"]["columns"][0]["unit"] = "percent"
    elif name == "gross-impairment": cells["loans-gross"], cells["loans-impairment"] = cells["loans-impairment"], cells["loans-gross"]
    elif name == "wrong-asset-category": sector["header"]["columns"][2]["asset_category"] = "Financial guarantees issued"
    elif name == "cross-row": sector["rows"][0]["cells"], sector["rows"][1]["cells"] = sector["rows"][1]["cells"], cells
    elif name == "cross-date": sector["rows"][0]["cells"] = deepcopy(other["rows"][0]["cells"])
    elif name == "omitted-cell": del cells["trading-assets"]
    elif name == "duplicate-cell": cells["trading-assets"]["source"] = deepcopy(cells["loans-gross"]["source"])
    elif name == "lost-sign": cells["loans-impairment"]["printed"] = "24 779"
    elif name == "dash-as-zero": cells["fair-value-assets"]["printed"] = "0"
    elif name == "wrong-rating-group": ratings["rows"][0]["group"] = "medium"
    elif name == "lost-group-scope": ratings["groups"][0]["row_ids"].pop()
    elif name == "wrong-internal-scale": ratings["rows"][7]["label"]["printed"] = "42-13"
    elif name == "wrong-shared-span": other["header"]["source"][31]["end"] -= 1
    elif name == "invented-box": sector["rows"][18]["cells"]["available-for-sale-impairment"]["source"][0]["bbox"] = [1,2,3,4]
    elif name == "omitted-split-fragment": sector["rows"][18]["cells"]["available-for-sale-impairment"]["source"].pop()
    elif name == "omitted-occurrence": value["context"]["163-decoration"].pop()
    elif name == "omitted-qualification": value["context"]["163-native-scope"] = []
    elif name == "changed-source": value["source"]["sha256"] = "0" * 64
    elif name == "changed-image": value["source"]["images"][1]["sha256"] = "0" * 64
    elif name == "uncorrected-ocr": ratings["rows"][0]["cells"]["2009:percent"]["printed"] = "2.02%"
    elif name == "wrong-correction-basis": ratings["rows"][16]["cells"]["2010:amount"]["basis"] = "INFERRED_FROM_TOTAL"
    elif name == "independent-review": value["reviewer"]["independent"] = True
    elif name == "financial-validation": value["financial_values_validated"] = True
    elif name == "legal-selection": value["selected_reading"] = "incorporated-original"
    elif name == "stale-prior": value["prior_sha256"] = "0" * 64
    elif name == "stale-graph": value["graph_sha256"] = "0" * 64
    elif name == "stale-pin": value["reviewer"]["identity"] += " changed"
    elif name == "omitted-row": ratings["rows"].pop(38)
    elif name == "duplicated-character": value["context"]["162-native-scope"].append(deepcopy(value["context"]["162-native-scope"][0]))
    else: raise ValueError("Unreviewed risk control")
    return value


def controls(mode):
    from legalmath.prospectus import h1_risk_tables as note
    p = read(HERE / "profile.json")
    graph = load(HERE / "products.json.gz")["P1"]["payload"]["graph"]
    prior, results = load(HERE / "baseline-consumer.json.gz"), []
    for name in read(HERE / "control-partitions.json")[mode]:
        value = altered(p, name)
        pin = digest(p) if name == "stale-pin" else digest(value)
        save("adverse-inputs/" + name + ".json.gz", {"profile": value, "expected_profile_sha256": pin})
        try:
            note.evaluate(graph, prior, value, ROOT, expected_profile_sha256=pin)
        except ValueError as exc:
            row = {"case": name, "refused": True, "repinned": name != "stale-pin", "reason": str(exc)}
            save("adverse-results/" + name + ".json", row)
            require(row["reason"] == CASES[name], "Unintended risk refusal: " + name + ": " + row["reason"])
            results.append(row)
        else:
            raise ValueError("Altered risk reading accepted: " + name)
    save(mode + ".json", results)
    return {"actual_refusals": len(results), "repinned": sum(r["repinned"] for r in results), "all_intended_reasons": True}


def tests():
    with (HERE / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "--junitxml=" + str(HERE / "tests.xml")]))
    require(code == 0, "Risk tests failed")
    return {"tests": checked_tests(HERE / "tests.xml", 1), "exit_code": code}


def install_prepare():
    history = read(REVIEW / "history.json")
    env = Path(history["environment"])
    require(files(env / "lib/python3.11/site-packages/legalmath") == history["package"], "438-file installed comparator changed")
    needed = sum(p.stat().st_size for p in env.rglob("*") if p.is_file())
    needed += sum(p.stat().st_size for p in (ROOT / "src").rglob("*") if p.is_file())
    require(storage() + needed + 64 * 1024**2 < 698 * 1024**2, "Installation capacity with64MiB reserve exhausted")
    temp = Path(tempfile.mkdtemp(prefix="installed-h1-risk-", dir=ROOT / ".localresources/prospectus"))
    save("workspace.json", {"directory": str(temp), "cloned_from": str(env), "measured_copy_bytes": needed})
    shutil.copytree(env, temp / "environment", symlinks=True)
    (temp / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", temp / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", temp / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copyfile(RUNNER, temp / "runner.py")
    package = files(temp / "source/src/legalmath")
    require(package == files(ROOT / "src/legalmath") and len(package) == 440, "Copied package differs")
    save("source-package.json", package)
    save("dependency-files.json", dependencies(temp / "environment"))
    return {"source_files": len(package), "preserved_files": 438, "dependency_entries": len(read(HERE / "dependency-files.json"))}


def build():
    (HERE / "wheel").mkdir()
    child("build", [str(workspace() / "environment/bin/python"), "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
        "--no-index", "--wheel-dir", str(HERE / "wheel"), str(workspace() / "source")])
    wheels = list((HERE / "wheel").glob("*.whl"))
    require(len(wheels) == 1, "Exactly one offline wheel required")
    result = {"path": str(wheels[0].relative_to(HERE)), "sha256": file_hash(wheels[0])}
    save("built-wheel.json", result)
    return result


def install():
    wheel = read(HERE / "built-wheel.json")
    require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Built wheel changed")
    child("install", [str(workspace() / "environment/bin/python"), "-m", "pip", "install", "--no-index", "--no-deps",
        "--force-reinstall", str(HERE / wheel["path"])])
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependencies changed")
    require(files(workspace() / "environment/lib/python3.11/site-packages/legalmath") == read(HERE / "source-package.json"), "Installed package differs")
    return {"installed": True, "dependencies_unchanged": True}


def installed(mode):
    require(file_hash(workspace() / "runner.py") == file_hash(RUNNER), "Installed runner changed")
    child(mode, [str(workspace() / "environment/bin/python"), "-I", str(workspace() / "runner.py"), str(HERE), str(ROOT), mode])
    result = read(HERE / "installed-results" / mode / "result.json")
    require(result["status"] == "PASS", "Installed risk comparison failed")
    return result


def verify():
    package = workspace() / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(HERE / "source-package.json")
    require(files(package) == expected == files(ROOT / "src/legalmath"), "Installed or current package changed")
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependency drift")
    for mode in ("positive", *PARTITIONS):
        folder = HERE / "installed-results" / mode
        result, proof = read(folder / "result.json"), read(folder / "import-proof.json")
        require(result["status"] == "PASS" and result["mode"] == mode and result["process_guard"] == {"starts": 0, "blocked": 0}, "Invalid isolated result")
        require(read(folder / "package-files.json") == expected and proof["isolated"] == 1
            and Path(proof["prefix"]).resolve() == (workspace() / "environment").resolve(), "Wrong installed identity")
        for item in proof["modules"].values():
            p = Path(item["path"]).resolve()
            require(p.is_relative_to(package) and file_hash(p) == item["sha256"] == expected[str(p.relative_to(package))], "Wrong installed module")
    require(load(HERE / "installed-results/positive/risk-consumer.json.gz") == load(HERE / "risk-consumer.json.gz"), "Full installed output differs")
    expected_controls = sum([read(HERE / (mode + ".json")) for mode in PARTITIONS], [])
    actual_controls = sum([read(HERE / "installed-results" / mode / "controls.json") for mode in PARTITIONS], [])
    require(expected_controls == actual_controls and [r["case"] for r in actual_controls] == list(CASES), "Ordered installed refusals differ")
    require(all(r["reason"] == CASES[r["case"]] for r in actual_controls), "Intended refusal mismatch")
    require(len(process_ledger.checked(HERE / "command-ledger.json")["reservations"]) == 8, "Wrong outer process count")
    require(len(process_ledger.checked(HERE / "native-ledger.json")["reservations"]) == 1, "Wrong native render count")
    save("actual-controls.json", expected_controls)
    result = {**read(HERE / "comparison.json"), "installed_complete_output_equal": True, "actual_refusals": 32,
        "repinned": 31, "exact_package_files": 440, "preexisting_package_files_unchanged": 438,
        "unchanged_dependency_entries": len(read(HERE / "dependency-files.json")), "outer_children": 8,
        "native_renders": 1, "new_ocr_extraction_network_gpu": 0, "different_host_portability": False}
    save("verified-result.json", result)
    return {k: result[k] for k in ("status", "installed_complete_output_equal", "actual_refusals", "exact_package_files")}


def seal():
    require((HERE / "RESULT.md").is_file() and read(HERE / "verified-result.json")["status"] == "PASS", "Actual risk result analysis required")
    return {"validated": True, "task_complete": False, "independent_legal_acceptance": False}


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES[3:], "Choose remaining admitted H1 risk stage")
    stage = sys.argv[1]
    def action():
        if stage.startswith("installed-"):
            return installed(stage.removeprefix("installed-"))
        if stage in ("build", "install"):
            return globals()[stage]()
        with execution_guard() as guard:
            result = controls(stage) if stage in PARTITIONS else globals()[stage.replace("-", "_")]()
            require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected risk process action")
        return {**result, "process_guard": guard.result()}
    raise SystemExit(source.run(stage, action))
