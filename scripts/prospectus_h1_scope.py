"""Admitted original H1 conditional incorporation comparison and installation."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
from scripts import prospectus_h1_scope_source as source
from scripts.prospectus_h1_scope_source import ROOT, HERE, REVIEW, PLAN, STAGES, save, read, file_hash, load, files, require, child, storage
from scripts.prospectus_basf_pension_install import dependencies
from scripts.prospectus_installed_profile_worker import execution_guard
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor import process_ledger

RUNNER = ROOT / "scripts/prospectus_installed_h1_scope.py"
TEST = "tests/prospectus/test_h1_incorporation_scope.py"
INVENTORY = "Complete H1 introduction source-fragment inventory required"
ANCHOR = "Exact original H1 introduction occurrence/character association required"
SOURCE = "Original H1 scope source editions required"
PAGE = "Exact conditional H1 page membership and construction basis required"
TARGET = "Complete ordered conditional H1 target occurrences required"
DIFFERENCE = "Exact divider/equity roles, periods and incomplete financial-reading limits required"
LIMIT = "Conditional scope cannot establish legal selection, financial validation or source authority"
PIN = "Pinned H1 scope profile, graph or complete prior consumer changed"
CASES = {
 "omitted-restriction": INVENTORY, "omitted-including": INVENTORY, "partial-quote": ANCHOR,
 "wrong-item": ANCHOR, "wrong-edition": SOURCE, "omitted-target-page": PAGE,
 "extra-target-page": PAGE, "duplicated-target-unit": TARGET,
 "lost-target-unit": TARGET, "lost-difference-page": DIFFERENCE, "wrong-statement-role": DIFFERENCE,
 "wrong-period": "Original Bank six-month H1 period required", "unsupported-selection": LIMIT,
 "independent-review": "Unsupported H1 scope review authority", "financial-validation": LIMIT,
 "changed-image": "Original reviewed H1 scope image changed",
 "changed-source": SOURCE, "stale-graph": PIN, "stale-prior": PIN, "stale-pin": PIN,
 "complete-equity-reading": DIFFERENCE, "omitted-construction": "Both original conditional scope constructions required",
 "lost-notes-scope": "Exact original H1 enumerated subitem page sets required", "individual-audit-opinion": LIMIT,
}
PARTITIONS = {"controls-" + letter: list(CASES)[8*i:8*i+8] for i,letter in enumerate("abc")}


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


def tests():
    with (HERE / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "--junitxml=" + str(HERE / "tests.xml")]))
    require(code == 0, "Scope tests failed")
    return {"tests": checked_tests(HERE / "tests.xml", 1), "exit_code": code}


def install_prepare():
    history = read(REVIEW / "history.json")
    env = Path(history["environment"])
    require(files(env / "lib/python3.11/site-packages/legalmath") == history["package"], "440-file installed comparator changed")
    needed = sum(p.stat().st_size for p in env.rglob("*") if p.is_file())
    needed += sum(p.stat().st_size for p in (ROOT / "src").rglob("*") if p.is_file())
    require(storage() + needed + 64 * 1024**2 < 698 * 1024**2, "Installation capacity with64MiB reserve exhausted")
    temp = Path(tempfile.mkdtemp(prefix="installed-h1-scope-", dir=ROOT / ".localresources/prospectus"))
    save("workspace.json", {"directory": str(temp), "cloned_from": str(env), "measured_copy_bytes": needed})
    shutil.copytree(env, temp / "environment", symlinks=True)
    (temp / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", temp / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", temp / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copyfile(RUNNER, temp / "runner.py")
    package = files(temp / "source/src/legalmath")
    require(package == files(ROOT / "src/legalmath") and len(package) == 441, "Copied package differs")
    save("source-package.json", package)
    save("dependency-files.json", dependencies(temp / "environment"))
    return {"source_files": len(package), "preserved_files": 440, "dependency_entries": len(read(HERE / "dependency-files.json"))}


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
    require(result["status"] == "PASS", "Installed scope comparison failed")
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
    require(load(HERE / "installed-results/positive/scope-consumer.json.gz") == load(HERE / "scope-consumer.json.gz"), "Full installed output differs")
    expected_controls = sum([read(HERE / (mode + ".json")) for mode in PARTITIONS], [])
    actual_controls = sum([read(HERE / "installed-results" / mode / "controls.json") for mode in PARTITIONS], [])
    require(expected_controls == actual_controls and [r["case"] for r in actual_controls] == list(CASES), "Ordered installed refusals differ")
    require(all(r["reason"] == CASES[r["case"]] for r in actual_controls), "Intended refusal mismatch")
    require(len(process_ledger.checked(HERE / "command-ledger.json")["reservations"]) == 7, "Wrong outer process count")
    require(len(process_ledger.checked(HERE / "native-ledger.json")["reservations"]) == 1, "Wrong native render count")
    save("actual-controls.json", expected_controls)
    result = {**read(HERE / "comparison.json"), "installed_complete_output_equal": True, "actual_refusals": 24,
        "repinned": 23, "exact_package_files": 441, "preexisting_package_files_unchanged": 440,
        "unchanged_dependency_entries": len(read(HERE / "dependency-files.json")), "outer_children": 7,
        "native_renders": 1, "new_ocr_extraction_network_gpu": 0, "different_host_portability": False}
    save("verified-result.json", result)
    return {k: result[k] for k in ("status", "installed_complete_output_equal", "actual_refusals", "exact_package_files")}


def seal():
    require((HERE / "RESULT.md").is_file() and read(HERE / "verified-result.json")["status"] == "PASS", "Actual scope result analysis required")
    return {"validated": True, "task_complete": False, "independent_legal_acceptance": False}


def profile():
    from legalmath.prospectus import h1_incorporation_scope as note
    require((HERE / "IMAGE-REVIEW.md").is_file() and (HERE / "IMPLEMENTATION-REVIEW.md").is_file(), "Complete source/implementation review required")
    package, original = files(ROOT / "src/legalmath"), read(REVIEW / "history.json")["package"]
    require(len(original) == 440 and all(package.get(k) == v for k, v in original.items()), "Existing440 package files changed")
    require(sorted(set(package) - set(original)) == ["prospectus/h1_incorporation_scope.py"], "Unexpected new source files")
    require(read(HERE / "draft-selector-audit.json")["intro_occurrences"] == 73, "Complete static scope source review required")
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
    return {"candidates": len(value["candidates"]), "source_files": len(package), "fixed_controls": len(CASES)}


def compare():
    from legalmath.prospectus import h1_incorporation_scope as note
    p, cash, risk = read(HERE / "profile.json"), read(HERE / "cash-flow-profile.json"), read(HERE / "risk-profile.json")
    result = note.consume(load(HERE / "products.json.gz"), cash, risk, p, ROOT,
        expected_cash_profile_sha256=digest(cash), expected_risk_profile_sha256=digest(risk),
        expected_profile_sha256=read(HERE / "profile-pin.json")["sha256"])
    require({k: result[k] for k in note.PRIOR_KEYS} == load(HERE / "baseline-consumer.json.gz"), "Protected complete previous consumer changed")
    review = result["h1_scope_review"]
    require([c["page_count"] for c in review["candidates"]] == [123,121]
        and [c["source_occurrences"] for c in review["candidates"]] == [12777,12309]
        and review["page_difference"]["first_only"] == [55,59]
        and len(review["difference"]["first_only"]) == 468, "Wrong original conditional scope effect")
    effects = result["h1_scope_explanation"]["downstream_effects"]
    require(effects["cash_flow_page60_common"] and effects["risk_pages162_163_common"], "Lost common original source pages")
    save("scope-consumer.json.gz", result)
    summary = {"status": "PASS", "introduction_occurrences": 73, "target_occurrences": 12777,
        "candidate_pages": [123,121], "candidate_occurrences": [12777,12309], "difference_pages": [55,59],
        "difference_occurrences": 468, "complete_previous_consumer_equal": True,
        "explanation": result["h1_scope_explanation"], "automatic_interpretation": False, "independent_legal_acceptance": False}
    save("comparison.json", summary)
    return {k: summary[k] for k in ("status", "candidate_pages", "candidate_occurrences", "difference_pages", "complete_previous_consumer_equal")}


def altered(profile, name):
    value = deepcopy(profile)
    broad, listed = value["candidates"]
    if name == "omitted-restriction": value["intro"]["restriction"] = []
    elif name == "omitted-including": value["intro"]["identity-and-range"].pop()
    elif name == "partial-quote": value["intro"]["identity-and-range"][0]["end"] -= 1
    elif name == "wrong-item": value["intro"]["identity-and-range"][0] = deepcopy(value["intro"]["other-items"][0])
    elif name == "wrong-edition": value["source"]["introducer"]["document"] = "another-prospectus"
    elif name == "omitted-target-page": broad["pages"].remove(59)
    elif name == "extra-target-page": listed["pages"].insert(4,55)
    elif name == "duplicated-target-unit": broad["source_units"].append(broad["source_units"][0])
    elif name == "lost-target-unit": listed["source_units"].pop()
    elif name == "lost-difference-page": value["difference_pages"].pop()
    elif name == "wrong-statement-role": value["difference_pages"][1]["role"] = "SECTION_DIVIDER"
    elif name == "wrong-period": value["period"]["end"] = "2010-09-30"
    elif name == "unsupported-selection": value["limits"]["selected_reading"] = "overall-range"
    elif name == "independent-review": value["reviewer"]["independent"] = True
    elif name == "financial-validation": value["limits"]["financial_values_validated"] = True
    elif name == "changed-image": value["source"]["report"]["images"][1]["sha256"] = "0" * 64
    elif name == "changed-source": value["source"]["report"]["sha256"] = "0" * 64
    elif name == "stale-graph": value["graph_sha256"] = "0" * 64
    elif name == "stale-prior": value["prior_sha256"] = "0" * 64
    elif name == "stale-pin": value["reviewer"]["identity"] += " changed"
    elif name == "complete-equity-reading": value["difference_pages"][1]["complete_financial_reading"] = True
    elif name == "omitted-construction": value["candidates"].pop()
    elif name == "lost-notes-scope": value["enumerated_subitems"]["notes"].remove(171)
    elif name == "individual-audit-opinion": value["limits"]["individual_statement_audit_opinion"] = True
    else: raise ValueError("Unreviewed scope control")
    return value


def controls(mode):
    from legalmath.prospectus import h1_incorporation_scope as note
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
            require(row["reason"] == CASES[name], "Unintended scope refusal: " + name + ": " + row["reason"])
            results.append(row)
        else:
            raise ValueError("Altered scope reading accepted: " + name)
    save(mode + ".json", results)
    return {"actual_refusals": len(results), "repinned": sum(r["repinned"] for r in results), "all_intended_reasons": True}


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES[3:], "Choose remaining admitted H1 scope stage")
    stage = sys.argv[1]
    def action():
        if stage.startswith("installed-"):
            return installed(stage.removeprefix("installed-"))
        if stage in ("build", "install"):
            return globals()[stage]()
        with execution_guard() as guard:
            result = controls(stage) if stage in PARTITIONS else globals()[stage.replace("-", "_")]()
            require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected scope process action")
        return {**result, "process_guard": guard.result()}
    raise SystemExit(source.run(stage, action))
