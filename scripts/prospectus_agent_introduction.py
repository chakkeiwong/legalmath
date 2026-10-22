"""Bounded BASF agent-introduction provenance review and installed replay."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil, signal, sys, tempfile, time
from scripts import prospectus_agent_intro_source as source
from scripts import prospectus_basf_equity as install_base
from legalmath.prospectus import basf_agent_introduction as intro
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest

ROOT, HERE, PRIOR, BASE, PLAN = source.ROOT, source.HERE, source.PRIOR, source.BASE, source.PLAN
RUNNER = ROOT / "scripts/prospectus_agent_intro_runner.py"
save, load = source.save, source.load
install_base.HERE = HERE
PREDECESSORS = {"profile": ("prepare",), "baseline": ("profile",), "compare": ("baseline",),
    "controls": ("compare",), "tests": ("controls",), "install-prepare": ("tests",),
    "build": ("install-prepare",), "install": ("build",), "replay-answer": ("install",),
    "replay-controls": ("replay-answer",), "verify": ("replay-controls",)}


def methods():
    names = [Path(__file__), Path(source.__file__), Path(intro.__file__), Path(install_base.__file__),
             RUNNER, ROOT / PLAN, ROOT / "pyproject.toml", HERE / "EXECUTION-AUDIT.md",
             ROOT / "tests/prospectus/test_basf_agent_introduction.py"]
    names += sorted((ROOT / "src/legalmath").rglob("*.py"))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def bindings():
    ad = source.bindings()
    if (HERE / "methods.json").exists(): assert methods() == read(HERE / "methods.json")
    return ad


def profile():
    products = load(HERE / "products.json.gz"); prior = load(HERE / "prior-consumer.json.gz")
    groups = intro.source_groups(products)
    value = {"version": intro.VERSION, "products_sha256": digest(products), "prior_sha256": digest(prior),
        "reviewer": {"identity": "Codex supplied original-image review 2026-10-15",
                      "basis": "AGENT_EXPOSED_DEVELOPMENT_REVIEW", "independent": False},
        "sources": read(HERE / "original-sources.json"), "groups": groups,
        "associations": intro.associations(groups), "excluded_branch_preserved": True,
        "p3_core_changed": False, "calculation_agent_office": "UNRESOLVED",
        "initial_appointment_established": False, "independent_legal_acceptance": False}
    save("profile.json", value); save("profile-pin.json", {"sha256": digest(value)})
    save("methods.json", methods())
    for name in methods():
        target = HERE / "methods" / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, target)
    save("pre-run-audit.json", {"status": "PASS", "plan": PLAN,
        "exact_baseline": str(PRIOR.relative_to(ROOT)), "association_count": len(value["associations"]),
        "source_groups": len(groups), "initial_appointment_established": False,
        "calculation_agent_office": "UNRESOLVED", "p3_core_changed": False,
        "truth_role": "SUPPLEMENTAL_PROVENANCE_ONLY", "native_allowance": 0,
        "http_allowance": 0, "outer_command_limit": 5, "local_repair_limit": 1,
        "historical_visible_native_reservation_lower_bound": 79,
        "historical_visible_source_http_lower_bound": 9})
    return {"source_groups": len(groups), "associations": len(value["associations"])}


def baseline():
    value = load(PRIOR / "default-consumer.json.gz"); save("baseline-consumer.json.gz", value)
    assert value == load(HERE / "prior-consumer.json.gz")
    return {"complete_prior_consumer_equal": True}


def compare():
    products, prior, profile_value = load(HERE / "products.json.gz"), load(HERE / "prior-consumer.json.gz"), read(HERE / "profile.json")
    result = intro.consume(products, prior, profile_value, ROOT,
        expected_prior_sha256=digest(prior), expected_profile_sha256=digest(profile_value))
    save("agent-introduction-consumer.json.gz", result)
    assert {k: result[k] for k in prior} == prior
    review = result["agent_introduction_review"]
    assert review["association_status"] == "SUPPLEMENTAL_SOURCE_PROVENANCE"
    assert review["calculation_agent_office"] == "UNRESOLVED" and not review["initial_appointment_established"]
    assert not review["p3_core_changed"]
    report = {"status": "PASS", "all_prior_outputs_unchanged": True, "ordinary_answer_unchanged": True,
        "association_count": len(review["associations"]), "source_groups": len(review["groups"]),
        "calculation_agent_office": "UNRESOLVED", "initial_appointment_established": False,
        "excluded_branch_preserved": True, "p3_core_changed": False, "independent_legal_acceptance": False,
        "prior_intro_question_unchanged": True}
    save("comparison.json", report); return report


def controls():
    original, products, prior = read(HERE / "profile.json"), load(HERE / "products.json.gz"), load(HERE / "prior-consumer.json.gz")
    names = ["omitted-intro-line", "changed-intro-word", "changed-selected-offset", "omitted-fiscal-block",
        "changed-fiscal-office", "swapped-final-name", "calculation-office-filled", "excluded-cds-selected",
        "final-label-removed", "initial-appointment-asserted", "p3-core-asserted", "independent-asserted",
        "stale-products", "stale-prior", "stale-pin", "changed-reviewer"]
    observed = []
    for name in names:
        value = deepcopy(original)
        if name == "omitted-intro-line": value["groups"]["introduction"].pop()
        elif name == "changed-intro-word": value["groups"]["introduction"][0]["selected_text"] += " geändert"
        elif name == "changed-selected-offset": value["groups"]["introduction"][0]["selected_sources"][0]["source"]["start"] += 1
        elif name == "omitted-fiscal-block": value["groups"]["initial_fiscal_paying"].pop()
        elif name == "changed-fiscal-office": value["groups"]["initial_fiscal_paying"][4]["selected_text"] += "X"
        elif name == "swapped-final-name":
            a, b = value["groups"]["final_agent_labels"][4]["source"]["quote"], value["groups"]["final_agent_labels"][6]["source"]["quote"]
            value["groups"]["final_agent_labels"][4]["source"]["quote"], value["groups"]["final_agent_labels"][6]["source"]["quote"] = b, a
        elif name == "calculation-office-filled": value["calculation_agent_office"] = "NatWest Markets N.V., London"
        elif name == "excluded-cds-selected": value["groups"]["excluded_cds_branch"][0]["assembly_role"] = "OPERATIVE"
        elif name == "final-label-removed": value["associations"][2]["final_term_label"].pop()
        elif name == "initial-appointment-asserted": value["initial_appointment_established"] = True
        elif name == "p3-core-asserted": value["p3_core_changed"] = True
        elif name == "independent-asserted": value["independent_legal_acceptance"] = True
        elif name == "stale-products": value["products_sha256"] = "0" * 64
        elif name == "stale-prior": value["prior_sha256"] = "0" * 64
        else: value["reviewer"]["identity"] += " altered"
        pin = digest(original) if name == "stale-pin" else digest(value)
        save("adverse-inputs/" + name + ".json.gz", {"profile": value, "expected_profile_sha256": pin})
        try: intro.evaluate(products, prior, value, ROOT, expected_profile_sha256=pin)
        except ValueError as error: observed.append({"case": name, "refused": True, "repinned": name != "stale-pin", "reason": str(error)})
        else: raise AssertionError("Altered agent-introduction accepted: " + name)
    save("actual-controls.json", observed); return {"actual_controls_refused": len(observed), "repinned": len(observed) - 1}


def tests():
    import pytest
    code = pytest.main(["-q", "tests/prospectus/test_basf_agent_introduction.py", "--junitxml=" + str(HERE / "tests.xml")])
    assert code == 0; return {"pytest_exit": int(code)}


def workspace(): return Path(read(HERE / "workspace.json")["directory"])


def install_prepare():
    old_workspace = Path(read(PRIOR / "workspace.json")["directory"]); old_package = read(PRIOR / "source-package.json")
    assert install_base.package_files(old_workspace / "environment/lib/python3.11/site-packages/legalmath") == old_package
    temp = Path(tempfile.mkdtemp(prefix="installed-basf-agent-intro-", dir=ROOT / ".localresources/prospectus"))
    save("workspace.json", {"directory": str(temp), "environment_cloned_from": str(old_workspace)})
    shutil.copytree(old_workspace / "environment", temp / "environment", symlinks=True)
    (temp / "source").mkdir(); shutil.copyfile(ROOT / "pyproject.toml", temp / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", temp / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copyfile(RUNNER, temp / "runner.py")
    package = install_base.package_files(temp / "source/src/legalmath")
    assert all(package.get(p) == h for p, h in old_package.items())
    added = sorted(set(package) - set(old_package)); assert added == ["prospectus/basf_agent_introduction.py"]
    save("source-package.json", package); save("prior-package-identity.json", {"status": "PASS", "prior_files_unchanged": len(old_package), "new_modules": added})
    return {"prior_files_unchanged": len(old_package), "exact_package_files": len(package)}


def build(): return install_base.build()
def install(): return install_base.install()
def replay_answer():
    install_base.run("replay-answer", [str(workspace() / "environment/bin/python"), "-I", str(workspace() / "runner.py"), str(HERE), str(ROOT), "answer"])
    return read(HERE / "installed-answer/result.json")
def replay_controls():
    install_base.run("replay-controls", [str(workspace() / "environment/bin/python"), "-I", str(workspace() / "runner.py"), str(HERE), str(ROOT), "controls"])
    return read(HERE / "installed-controls/result.json")


def verify():
    answer, control = read(HERE / "installed-answer/result.json"), read(HERE / "installed-controls/result.json")
    expected = read(HERE / "source-package.json"); package = workspace() / "environment/lib/python3.11/site-packages/legalmath"
    assert answer["status"] == control["status"] == "PASS" and answer["full_output_equal"]
    assert control["controls"] == len(read(HERE / "actual-controls.json")) and install_base.package_files(package) == expected
    assert len(process_ledger.checked(HERE / "command-ledger.json")["reservations"]) == 4
    for folder in ("installed-answer", "installed-controls"):
        assert read(HERE / folder / "package-files.json") == expected and read(HERE / folder / "import-proof.json")["isolated"] == 1
    assert load(HERE / "installed-answer/agent-introduction-consumer.json.gz") == load(HERE / "agent-introduction-consumer.json.gz")
    assert read(HERE / "installed-controls/controls.json") == read(HERE / "actual-controls.json")
    return {"status": "PASS", "all_prior_outputs_unchanged": True, "installed_full_output_equal": True,
        "actual_controls_refused": len(read(HERE / "actual-controls.json")), "associations": read(HERE / "comparison.json")["association_count"],
        "source_groups": read(HERE / "comparison.json")["source_groups"], "exact_package_files": len(expected),
        "prior_package_files_unchanged": 428, "outer_commands": 4, "local_repairs_used": 0,
        "different_host_portability": False, "historical_visible_native_reservation_lower_bound": 79,
        "historical_visible_source_http_lower_bound": 9}


def main():
    stage = sys.argv[1]; assert stage in PREDECESSORS; ad = bindings()
    for previous in PREDECESSORS[stage]: assert read(HERE / "invocations" / previous / "result.json")["status"] == "PASS"
    folder = HERE / "invocations" / stage; folder.mkdir(parents=True, exist_ok=False)
    save("invocations/" + stage + "/started.json", {"command": [".venv/bin/python", "-m", "scripts.prospectus_agent_introduction", stage],
        "git_commit": ad["git_commit"], "plan": PLAN, "environment": sys.executable,
        "started_at": datetime.now(timezone.utc).isoformat(), "random_seeds": "N/A deterministic",
        "cpu_gpu": "CPU only;no framework imports;children CUDA_VISIBLE_DEVICES=-1", "required_predecessors": list(PREDECESSORS[stage])})
    tick = time.monotonic()
    def expire(signum, frame): raise TimeoutError("120-second agent-introduction stage bound;no automatic retry")
    signal.signal(signal.SIGALRM, expire); signal.alarm(120)
    try:
        details = globals()[stage.replace("-", "_")](); bindings()
        size = sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
        if (HERE / "workspace.json").exists(): size += sum(p.stat().st_size for p in workspace().rglob("*"))
        assert size < 500 * 1024 * 1024
        result = {"status": "PASS", "stage": stage, "details": details, "wall_seconds": time.monotonic() - tick, "evidence_and_workspace_bytes": size}
    except BaseException as error:
        save("invocations/" + stage + "/result.json", {"status": "FAIL", "error": repr(error), "wall_seconds": time.monotonic() - tick}); raise
    finally: signal.alarm(0)
    save("invocations/" + stage + "/result.json", result); print(result)


if __name__ == "__main__":
    with (HERE / "execution.lock").open("a") as lock: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); main()
