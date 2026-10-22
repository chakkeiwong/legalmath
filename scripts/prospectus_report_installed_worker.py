"""Isolated installed report tests; legalmath never imports from the checkout."""
from copy import deepcopy
import importlib.util
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import traceback

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def save(path, value):
    """The copied helper uses this attempt's reviewed storage scope."""
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if str(path).endswith(".gz") else raw
    require(sum(p.stat().st_size for p in FOLDER.rglob("*") if p.is_file()) + len(data) < 94 * 1024**2,
            "Installed report evidence cap exceeded")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def products(p1, p2, supplied):
    p3 = service.interpretation_product(p1, p2, supplied)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
            "P5": service.financial_product(p1, p2, p3)}


def reports():
    rows = {}
    for label in ("unknown", "candidate"):
        reference = helper.load_products(SOURCE, label)
        p1 = reference["P1"]
        actual = products(p1, service.construction_product(p1, ROOT), reference["P3"]["payload"]["interpretation_input"])
        answer = helper.consume(actual)
        require(actual == reference and answer == helper.read(SOURCE / (label + "-answer.json.gz")),
                "Complete installed original report products/answer differ: " + label)
        helper.save(TARGET / (label + "-P2-P5.json.gz"), {k: v for k, v in actual.items() if k != "P1"})
        helper.save(TARGET / (label + "-answer.json.gz"), answer)
        rows[label] = {"all_products_equal": True, "whole_answer_equal": True, "report_sha256": answer["report_sha256"]}
    return rows


def synthetic_controls(old):
    cases = helper.read(SOURCE / "reproduced-counterexamples.json")
    rows = {}
    for case, expected in cases.items():
        is_interpretation = case.startswith("interpretation-")
        name = case.removeprefix("interpretation-")
        bad = helper.read(SOURCE / "before" / (name + "-products.json.gz"))
        def call():
            if is_interpretation:
                return service.interpretation_product(bad["P1"], bad["P2"], bad["P3"]["payload"]["interpretation_input"])
            return service.consume(bad, SOURCE / "synthetic", mode="frozen")
        if old:
            result = call()
            if is_interpretation:
                require(result == helper.read(SOURCE / "before" / (case + ".json.gz")), "Old interpretation differs")
            else:
                require(result == helper.read(SOURCE / "before" / (case + "-answer.json.gz")), "Old accepted answer differs")
            rows[case] = {"incorrectly_accepted": True, "result_sha256": digest(result)}
        else:
            rows[case] = helper.refuse(call, "report" if is_interpretation is False and name not in ("missing-p2", "changed-p2", "unsupplied-readings") else "Report")
    require(len(rows) == 11, "Incomplete exact synthetic counterexamples")
    return rows


def original_mutation(good, name):
    bad = deepcopy(good)
    request, selected, semantic = bad["P1"]["payload"]["request"], bad["P2"]["payload"], bad["P3"]["payload"]
    if name == "missing-p2":
        del selected["source_report_readings"]
    elif name == "changed-p2":
        readings = selected["source_report_readings"]
        reading = readings["reports"][0]
        reading["pages"][0]["page"] += 9
        reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
        scope = semantic["interpretation_input"]["source_report_scope"]
        scope["readings_sha256"] = digest(readings)
        scope["reports"][0]["reading_sha256"] = reading["sha256"]
        semantic["source_report_scope"] = report_scope.admit(readings, scope)
    elif name == "unsupplied-readings":
        del request["source_report_readings"]
    elif name == "missing-p3":
        del semantic["source_report_scope"]
    elif name == "changed-p3":
        semantic["source_report_scope"]["reports"][0]["facts"]["report_date"]["spans"][0]["quote"] = "Lisbon, 1 January 2099."
    elif name == "unsupplied-scope":
        semantic["interpretation_input"] = None
    else:
        raise ValueError("Unknown original mutation")
    bad["P1"] = helper.p1_from(request, bad["P1"]["payload"]["graph"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")), ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        bad[phase] = service.seal(phase, request["bundle"], {p: bad[p]["sha256"] for p in parents}, bad[phase]["payload"])
    return bad


def report_controls():
    results = {"synthetic": synthetic_controls(False), "original": {}}
    good = helper.load_products(SOURCE, "candidate")
    for name in ("missing-p2", "changed-p2", "unsupplied-readings", "missing-p3", "changed-p3", "unsupplied-scope"):
        bad = original_mutation(good, name)
        hashes = {k: v["sha256"] for k, v in bad.items()}
        require(hashes == helper.read(SOURCE / "original-integrity" / (name + "-input.json"))["products"],
                "Installed original counterexample reconstruction differs")
        expected = helper.read(SOURCE / "original-integrity" / (name + "-result.json"))
        result = helper.refuse(lambda: helper.consume(bad), expected["reason"])
        results["original"][name] = {**result, "products": hashes}
    return results


def qualifications(labels):
    good = helper.load_products(SOURCE, "candidate")
    positive = helper.read(SOURCE / "candidate-answer.json.gz")
    rows = {}
    for name in labels:
        scope = helper.read(SOURCE / "controls" / (name + "-scope.json"))
        if name.startswith("false-"):
            expected = helper.read(SOURCE / "controls" / (name + "-result.json"))
            rows[name] = helper.refuse(lambda: service.interpretation_product(good["P1"], good["P2"], {"source_report_scope": scope}), expected["reason"])
        else:
            values = products(good["P1"], good["P2"], {"source_report_scope": scope})
            answer = helper.consume(values)
            delta = helper.read(SOURCE / "controls" / (name + "-answer-delta.json.gz"))
            hashes = {k: v["sha256"] for k, v in values.items()}
            require(hashes == delta["products"] and digest(answer) == delta["complete_answer_sha256"] and
                    answer == {**positive, **delta["replace"]}, "Installed adverse complete answer differs: " + name)
            helper.save(TARGET / (name + "-answer-delta.json.gz"), {"baseline": str((SOURCE / "candidate-answer.json.gz").relative_to(ROOT)),
                "replace": {k: v for k, v in answer.items() if positive.get(k) != v}, "complete_answer_sha256": digest(answer)})
            rows[name] = {"complete_answer_equal": True, "products": hashes, "report_sha256": answer["report_sha256"]}
    return rows


def main():
    global ROOT, FOLDER, SOURCE, TARGET, helper, service, report_scope, digest
    ROOT, FOLDER, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    SOURCE = ROOT / "docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-09/attempt-003"
    TARGET = FOLDER / "commands" / stage
    def block(event, _):
        if event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Installed report consumer forbids native/network: " + event)
    sys.addaudithook(block)
    def expired(*_):
        raise TimeoutError("Installed report consumer exceeded105 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(105)
    from legalmath.prospectus.successor import service, report_scope
    from legalmath.prospectus.successor.contracts import digest
    helper_path = Path(__file__).with_name("fy_worker.py")
    spec = importlib.util.spec_from_file_location("retained_fy_worker", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.ROOT, helper.FOLDER, helper.TARGET = ROOT, FOLDER, TARGET
    helper.PRODUCT = ROOT / "docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-08/attempt-006"
    helper.service, helper.digest = service, digest
    helper.save = save
    require(helper.sha(helper_path) == helper.read(FOLDER / "harness.json")["fy_helper_sha256"], "Copied helper changed")
    expected = helper.read(FOLDER / ("old-package.json" if stage == "old-boundary" else "source-package.json"))
    result = {"status": "FAIL", "stage": stage}
    try:
        before = helper.identity(expected)
        actions = {"old-boundary": lambda: synthetic_controls(True), "reports": reports, "report-controls": report_controls,
            "audit-qualifications": lambda: qualifications(("paragraph8", "audit_translation", "false-COMMITTEE_REPORT")),
            "committee-context": lambda: qualifications(("knowledge", "recommendation", "committee_purpose", "false-STATUTORY_FINANCIAL_AUDIT")),
            "committee-dates": lambda: qualifications(("borrowed_date", "both_dates")),
            "fy-matched": helper.matched, "fy-controls": helper.controls, "prior-profiles": helper.prior_profiles}
        details = actions[stage]()
        after = helper.identity(expected)
        result.update(status="PASS", details=details, before=before, after=after,
                      helper_sha256=helper.sha(helper_path), new_native_calls=0)
    except BaseException as exc:
        result.update(error={"type": type(exc).__name__, "message": str(exc)}, traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
    helper.save(TARGET / "installed-result.json", result)
    print(json.dumps({"status": result["status"], "stage": stage, "error": result.get("error")}))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
