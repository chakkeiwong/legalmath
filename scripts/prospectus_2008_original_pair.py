"""Reviewed full original2008 bilingual discrepancy; bounded native intake."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PATH="/usr/bin:/bin")
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor import report_scope, service, source_discrepancies
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_report_integrity import read, size, require, p1_from
from scripts.prospectus_installed_consumer import package_files
from scripts.prospectus_installed_current import tree

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-07/attempt-002"
PRIOR = SOURCE.parent / "attempt-001"
INSTALLED = BASE / "attempts/source-bes-dep-09/attempt-005"
REVIEW = BASE / "reviews/original-pair-148"
WORKER = ROOT / "scripts/prospectus_2008_pair_installed_worker.py"
STAGES = ("intake", "readings", "baseline", "candidate", "input-controls-a", "input-controls-b", "input-controls-c",
          "input-controls-d", "input-controls-e", "phase-controls-a", "phase-controls-b", "phase-controls-c",
          "installed-candidate", "installed-controls-a", "installed-controls-b", "installed-controls-c", "seal")
PHASE_CASES = ("missing-discrepancy", "changed-discrepancy", "missing-input", "missing-selection", "false-page", "unsupplied-selection")
REFUSALS = {
    "missing-side": "Both distinct English and Portuguese contexts required",
    "swapped-language": "Complete inspected Note46 first-bullet context required",
    "changed-quote": "Discrepancy context quote or interval changed",
    "truncated-bullet": "Complete inspected Note46 first-bullet context required",
    "resolved_amount": "Unexpected or missing fields",
    "controlling_edition": "Unexpected or missing fields",
    "reading-hash": "Discrepancy side identity, language or content changed",
    "graph-hash": "Discrepancy graph or report readings changed",
    "missing-heading-character": "Report readings differ from supplied source evidence",
    "missing-discrepancy": "Source discrepancy differs from its bound evidence",
    "changed-discrepancy": "Source discrepancy differs from its bound evidence",
    "missing-input": "Source discrepancy lacks supplied evidence",
    "missing-selection": "Report readings differ from supplied source evidence",
    "false-page": "Report readings differ from supplied source evidence",
    "unsupplied-selection": "Report readings lack supplied source evidence",
}


def save(folder, name, value, final=False):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw
    require(size(folder) + len(data) < (128 if final else 126) * 1024**2, "Original pair evidence cap")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def consume(values):
    return service.consume(values, ROOT, mode="frozen", include_artifacts=True)


def products(p1, p2, supplied=None):
    p3 = service.interpretation_product(p1, p2, supplied)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
            "P5": service.financial_product(p1, p2, p3)}


def selected_source(folder):
    original = read(folder / "original-P1.json.gz")
    req = deepcopy(original["payload"]["request"])
    req["source_report_readings"] = read(folder / "reading-input.json")
    return p1_from(req, original["payload"]["graph"])


def load(folder, label):
    return {"P1": selected_source(folder), **read(folder / (label + "-P2-P5.json.gz"))}


def protected(answer):
    return {k: v for k, v in answer.items() if k not in {"source_discrepancies", "consumed_products", "report_sha256"}}


def intake(folder):
    req = deepcopy(read(SOURCE / "request.json"))
    req.pop("source_report_readings")
    req["bundle"]["instrument_id"] = "PTBEQBOM0010-BES-DEP-07-original-annual-pair"
    req["bundle"]["documents"] = read(REVIEW / "documents.json")
    p1 = service.source_product(req, ROOT)
    graph = p1["payload"]["graph"]
    require(len(graph["documents"]) == 2 and [d["page_count"] for d in graph["documents"]] == [286, 284], "Original page count differs")
    require(all(d["extractor"] == "pdftotext-bbox-layout" for d in graph["documents"]), "Unexpected extraction route")
    require(len(list((folder / "native").glob("*.json"))) == 2, "Expected exactly two native launches")
    coverage = {}
    for document in graph["documents"]:
        units = [u for u in graph["units"] if u["document"] == document["id"]]
        require({u["page"] for u in units} == set(range(1, document["page_count"] + 1)), "Original page inventory incomplete")
        coverage[document["id"]] = {"pages": document["page_count"], "units": len(units),
            "blank_or_unread_pages": sorted({u["page"] for u in units if u["method"] == "blank-or-unread"}),
            "text_coverage": "UNREVIEWED outside the selected Note46 context"}
    save(folder, "page-inventory.json", coverage)
    save(folder, "original-P1.json.gz", p1)
    return {"source_units": len(graph["units"]), "source_pages": [286, 284], "native_launches": 2,
            "source_graph_sha256": digest(graph), "runtime_scope": "Declared executable; no new confinement acceptance"}


def readings(folder):
    p1 = read(folder / "original-P1.json.gz")
    graph = p1["payload"]["graph"]
    packet = deepcopy(read(SOURCE / "discrepancy-input.json"))
    admission = {"version": "source-report-readings.v1", "graph_sha256": digest(graph), "review": packet["review"], "reports": []}
    for lang, page in (("en", 241), ("pt", 242)):
        doc = next(d for d in p1["payload"]["request"]["bundle"]["documents"] if d["language"] == lang)
        text = "\n".join(u["raw"] for u in graph["units"] if u["document"] == doc["id"] and u["page"] == page and u["visible"])
        admission["reports"].append({"id": lang + "-note", "document": doc["id"], "source_sha256": doc["sha256"],
            "pages": [{"page": page, "mode": "raw"}], "text_sha256": digest(text.encode())})
    selected = report_scope.readings(graph, admission)
    packet["graph_sha256"], packet["readings_sha256"] = digest(graph), digest(selected)
    for side in packet["discrepancies"][0]["sides"]:
        reading = next(r for r in selected["reports"] if r["id"] == side["reading"])
        heading, context, _ = source_discrepancies._PASSAGES[side["language"]]
        pattern = re.compile(r"(?P<heading>" + source_discrepancies._pattern(heading) + r")\s*•\s*(?P<context>" +
            source_discrepancies._pattern(context) + r")(?=\s*•|\s*$)")
        matches = list(pattern.finditer(reading["text"]))
        require(len(matches) == 1, "Original page lacks unique complete inspected first bullet: " + side["language"])
        start, end = matches[0].span("context")
        side.update(reading_sha256=reading["sha256"], context={"start": start, "end": end, "quote": reading["text"][start:end]})
    admitted = source_discrepancies.admit(graph, selected, packet)
    save(folder, "reading-input.json", admission)
    save(folder, "selected-readings.json.gz", selected)
    save(folder, "discrepancy-input.json", packet)
    save(folder, "admitted-discrepancy.json.gz", admitted)
    return {"full_original_pages_selected": [241, 242], "unique_complete_bullets": 2, "source_text_normalized": False}


def baseline(folder):
    p1 = selected_source(folder)
    p2 = service.construction_product(p1, ROOT)
    require(p2["payload"]["source_report_readings"] == read(folder / "selected-readings.json.gz"), "Original selection changed")
    values = products(p1, p2)
    answer = consume(values)
    require("source_discrepancies" not in answer, "Unrequested baseline discrepancy")
    save(folder, "baseline-P2-P5.json.gz", {k: v for k, v in values.items() if k != "P1"})
    save(folder, "baseline-answer.json.gz", answer)
    return {"original_baseline_consumed": True, "report_sha256": answer["report_sha256"]}


def candidate(folder):
    before = load(folder, "baseline")
    values = products(before["P1"], before["P2"], {"source_discrepancies": read(folder / "discrepancy-input.json")})
    answer = consume(values)
    expected = read(SOURCE / "final-actual-answer.json.gz")["source_discrepancies"][0]
    actual = answer["source_discrepancies"][0]
    require({k: v for k, v in actual.items() if k != "sides"} == {k: v for k, v in expected.items() if k != "sides"}, "Conflict semantics changed")
    for side, old in zip(actual["sides"], expected["sides"], strict=True):
        require(side["language"] == old["language"], "Conflict side language changed")
        for field in ("heading", "context", "monetary_wording"):
            require(" ".join(side[field]["quote"].split()) == " ".join(old[field]["quote"].split()), "Complete conflict wording differs: " + field)
        lang = side["language"]
        document = next(d for d in before["P1"]["payload"]["request"]["bundle"]["documents"] if d["language"] == lang)
        require(side["document"] == document["id"] and side["source_sha256"] == document["sha256"] and
                side["pages"] == [{"page": 241 if lang == "en" else 242, "mode": "raw"}], "Wrong original edition/page")
    require(values["P3"]["payload"]["source_discrepancies"] == read(folder / "admitted-discrepancy.json.gz"), "Actual admitted pair changed")
    require(protected(answer) == protected(read(folder / "baseline-answer.json.gz")), "Complete surrounding answer changed")
    for phase in ("P4", "P5"):
        require(values[phase]["payload"] == before[phase]["payload"], "Law/financial payload changed")
    ids = {d["id"] for d in before["P1"]["payload"]["request"]["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependency changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["independent_legal_acceptance"] and
            not answer["may_execute_transaction"] and actual["resolved_amount"] is None and actual["controlling_edition"] is None and
            not actual["financial_calculation_authorized"], "Unsupported legal/financial promotion")
    save(folder, "candidate-P2-P5.json.gz", {k: v for k, v in values.items() if k != "P1"})
    save(folder, "candidate-answer.json.gz", answer)
    return {"complete_original_pair_consumed": True, "complete_semantic_wording_equal": True,
            "protected_answer_equal": True, "original_dependencies_unresolved": 14, "report_sha256": answer["report_sha256"]}


def reseal(values):
    req = values["P1"]["payload"]["request"]
    values["P1"] = p1_from(req, values["P1"]["payload"]["graph"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")), ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        values[phase] = service.seal(phase, req["bundle"], {p: values[p]["sha256"] for p in parents}, values[phase]["payload"])
    return values


def phase_mutation(good, case):
    bad = deepcopy(good)
    selected, semantic = bad["P2"]["payload"], bad["P3"]["payload"]
    if case == "missing-discrepancy":
        del semantic["source_discrepancies"]
    elif case == "changed-discrepancy":
        semantic["source_discrepancies"]["discrepancies"][0]["resolved_amount"] = "1500000000"
    elif case == "missing-input":
        semantic["interpretation_input"] = None
    elif case == "missing-selection":
        del selected["source_report_readings"]
    elif case == "unsupplied-selection":
        del bad["P1"]["payload"]["request"]["source_report_readings"]
    elif case == "false-page":
        readings = selected["source_report_readings"]
        reading = readings["reports"][0]
        reading["pages"][0]["page"] += 1
        reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
        packet = semantic["interpretation_input"]["source_discrepancies"]
        packet["readings_sha256"] = digest(readings)
        packet["discrepancies"][0]["sides"][0]["reading_sha256"] = reading["sha256"]
        semantic["source_discrepancies"] = source_discrepancies.admit(bad["P1"]["payload"]["graph"], readings, packet)
    else:
        raise ValueError("Unknown saved-chain mutation")
    return reseal(bad)


def refusal(thunk, expected):
    try:
        thunk()
    except ValueError as exc:
        require(str(exc) == expected, "Unexpected refusal: " + str(exc))
        return {"rejected": True, "reason": str(exc)}
    raise ValueError("Original pair adverse evidence accepted")


def input_controls(folder, labels):
    good = load(folder, "candidate")
    results = {}
    for label in labels:
        packet = deepcopy(read(folder / "discrepancy-input.json"))
        p2 = deepcopy(good["P2"])
        row = packet["discrepancies"][0]
        if label == "missing-side":
            row["sides"].pop()
        elif label == "swapped-language":
            row["sides"][0]["language"] = "pt"
        elif label == "changed-quote":
            row["sides"][0]["context"]["quote"] += " altered"
        elif label == "truncated-bullet":
            span = row["sides"][0]["context"]
            span["end"] -= 1
            span["quote"] = span["quote"][:-1]
        elif label in ("resolved_amount", "controlling_edition"):
            row[label] = "1500000000" if label == "resolved_amount" else "pt"
        elif label == "reading-hash":
            row["sides"][0]["reading_sha256"] = "0" * 64
        elif label == "graph-hash":
            packet["graph_sha256"] = "0" * 64
        elif label == "missing-heading-character":
            selected = p2["payload"]["source_report_readings"]
            reading = selected["reports"][0]
            heading = read(folder / "admitted-discrepancy.json.gz")["discrepancies"][0]["sides"][0]["heading"]["start"]
            reading["characters"] = [c for c in reading["characters"] if c["output"] != heading]
            reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
            packet["readings_sha256"] = digest(selected)
            row["sides"][0]["reading_sha256"] = reading["sha256"]
            p2 = service.seal("P2", good["P1"]["payload"]["request"]["bundle"], {"P1": good["P1"]["sha256"]}, p2["payload"])
        else:
            raise ValueError("Unknown input mutation")
        save(folder, "inputs/" + label + ".json.gz", {"packet": packet,
            "modified_P2": p2 if label == "missing-heading-character" else None,
            "P1_sha256": good["P1"]["sha256"], "P2_sha256": p2["sha256"]})
        results[label] = refusal(lambda: service.interpretation_product(good["P1"], p2, {"source_discrepancies": packet}), REFUSALS[label])
        save(folder, "inputs/" + label + "-result.json", results[label])
    return results


def phase_controls(folder, cases):
    good = load(folder, "candidate")
    results = {}
    for case in cases:
        bad = phase_mutation(good, case)
        save(folder, "phases/" + case + "-input.json", {"mutation": case,
            "reconstruction": "Bound phase_mutation(candidate products, case)", "products": {k: v["sha256"] for k, v in bad.items()}})
        results[case] = refusal(lambda: consume(bad), REFUSALS[case])
        save(folder, "phases/" + case + "-result.json", results[case])
    return results


def installed(folder, stage):
    environment = Path(read(INSTALLED / "workspace.json")["directory"]) / "environment"
    require(package_files(environment / "lib/python3.11/site-packages/legalmath") == read(INSTALLED / "source-package.json") == package_files(ROOT / "src/legalmath"), "Installed package changed")
    require(tree(environment, dependencies=True) == read(INSTALLED / "dependencies.json"), "Installed dependencies changed")
    scripts = folder / "installed-harness"
    if stage == "installed-candidate":
        scripts.mkdir()
        shutil.copyfile(WORKER, scripts / "worker.py")
        shutil.copyfile(ROOT / "scripts/prospectus_fy2010_installed_worker.py", scripts / "helper.py")
        save(folder, "installed-harness.json", {"worker_sha256": file_hash(WORKER),
            "helper_sha256": file_hash(scripts / "helper.py"), "prior_installed_outer_commands": 54,
            "prior_installed_native_reservations": 8, "maximum_new_outer_commands": 4, "new_native_allowance": 0})
    require(file_hash(scripts / "worker.py") == file_hash(WORKER) and
        file_hash(scripts / "helper.py") == file_hash(ROOT / "scripts/prospectus_fy2010_installed_worker.py"), "Copied installed harness changed")
    argv = [str(environment / "bin/python"), "-I", "-B", str(scripts / "worker.py"), str(ROOT), str(folder), stage]
    target = folder / "commands" / stage
    target.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "-1"}
    save(folder, "commands/" + stage + "/command.json", {"argv": argv, "cwd": str(scripts), "timeout": 110,
        "env": {k: env[k] for k in ("PYTHONPATH", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "CUDA_VISIBLE_DEVICES")}})
    with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
        run = subprocess.run(argv, cwd=scripts, env=env, stdout=out, stderr=err, timeout=110)
    save(folder, "commands/" + stage + "/result.json", {"returncode": run.returncode})
    require(run.returncode == 0 and read(target / "installed-result.json")["status"] == "PASS", "Installed pair command failed; see retained output")
    require(package_files(environment / "lib/python3.11/site-packages/legalmath") == read(INSTALLED / "source-package.json") and
            tree(environment, dependencies=True) == read(INSTALLED / "dependencies.json"), "Installed environment changed")
    return {"installed_command": stage, "returncode": run.returncode}


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-07"]
    admission = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and admission["program_sha256"] == authority_digest(program)
            and admission["binding"] == a.binding(task), "Current unchanged admission required")
    require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    history = read(REVIEW / "history.json")
    require(all(a.retained_evidence_valid(e) for e in history["events"]), "Retained original evidence changed")
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    starts = list((folder / "stages").glob("*/started.json"))
    require(len(starts) == len(results) == STAGES.index(stage) and all(r["status"] == "PASS" for r in results), "Repeated/skipped/interrupted/failed stage")
    spent = sum(r["wall_seconds"] for r in results)
    require(spent < 1080, "Pair execution budget exhausted")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_2008_original_pair.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admission["git_commit"], "interpreter": sys.executable, "module": service.__file__,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic comparison", "inputs": admission["binding"],
        "history": history, "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT))})
    tick, error, details = time.monotonic(), None, None
    try:
        if stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual result review required")
            details = {"original_bilingual_pair_evaluated": True, "installed_evaluated": True,
                "new_native_calls": 2, "new_installed_outer_commands": 4, "cumulative_installed_outer_commands": 58,
                "cumulative_installed_native_reservations": 8, "source_authority_established": False}
        elif stage.startswith("installed-"):
            details = installed(folder, stage)
        else:
            actions = {"intake": intake, "readings": readings, "baseline": baseline, "candidate": candidate,
                "input-controls-a": lambda p: input_controls(p, ("missing-side", "swapped-language")),
                "input-controls-b": lambda p: input_controls(p, ("changed-quote", "truncated-bullet")),
                "input-controls-c": lambda p: input_controls(p, ("resolved_amount", "controlling_edition")),
                "input-controls-d": lambda p: input_controls(p, ("reading-hash", "graph-hash")),
                "input-controls-e": lambda p: input_controls(p, ("missing-heading-character",)),
                "phase-controls-a": lambda p: phase_controls(p, PHASE_CASES[:2]),
                "phase-controls-b": lambda p: phase_controls(p, PHASE_CASES[2:4]),
                "phase-controls-c": lambda p: phase_controls(p, PHASE_CASES[4:])}
            details = actions[stage](folder)
        require(admission["binding"] == a.binding(task), "Admitted methods or source inputs changed")
        require(spent + time.monotonic() - tick < 1080 and size(folder) < 128 * 1024**2, "Pair cumulative execution/evidence cap")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error, "details": details, "wall_seconds": time.monotonic() - tick}
    save(folder, "stages/" + stage + "/result.json", result, True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "task_complete": False, "independent_acceptance": False,
            "native_acceptance_refreshed": False}, True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True)
    p.add_argument("--stage", choices=STAGES, required=True)
    args = p.parse_args()
    folder = ROOT / args.attempt
    allowed = []
    if args.stage == "intake":
        runtime = read(REVIEW / "runtime.json")
        require(str(Path(shutil.which("pdftotext")).resolve()) == runtime["executable"] and
                file_hash(Path(runtime["executable"])) == runtime["sha256"], "Declared native executable changed")
        documents = read(REVIEW / "documents.json")
        for document in documents:
            require(file_hash(ROOT / document["path"]) == document["sha256"] and
                    file_hash(ROOT / document["acquisition"]["path"]) == document["acquisition"]["sha256"], "Original source/receipt changed")
        allowed = [["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(ROOT / d["path"]), "-"] for d in documents]
    elif args.stage.startswith("installed-"):
        environment = Path(read(INSTALLED / "workspace.json")["directory"]) / "environment"
        allowed = [[str(environment / "bin/python"), "-I", "-B", str(folder / "installed-harness/worker.py"), str(ROOT), str(folder), args.stage]]
    count = 0
    def block(event, values):
        nonlocal count
        if event == "subprocess.Popen":
            require(count < len(allowed) and list(values[1]) == allowed[count], "Unreviewed extra subprocess")
            save(folder, ("native/" if args.stage == "intake" else "outer-launches/" + args.stage + "-") + str(count + 1) + ".json",
                 {"argv": list(values[1]), "at": datetime.now(timezone.utc).isoformat(), "stage": args.stage,
                  "executable_sha256": file_hash(Path(shutil.which(values[0])).resolve())})
            count += 1
        elif event in ("os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Original pair forbids additional process/network route: " + event)
    sys.addaudithook(block)
    def expired(*_):
        raise TimeoutError("Original pair stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try:
        return run(args.attempt, args.stage)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
