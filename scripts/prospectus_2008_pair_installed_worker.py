"""Consume the retained original bilingual pair using only the existing installation."""
from copy import deepcopy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import traceback

sys.dont_write_bytecode = True
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
CASES = ("missing-discrepancy", "changed-discrepancy", "missing-input", "missing-selection", "false-page", "unsupplied-selection")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if str(path).endswith(".gz") else raw
    require(sum(p.stat().st_size for p in FOLDER.rglob("*") if p.is_file()) + len(data) < 126 * 1024**2,
            "Original pair installed evidence cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def load():
    original = helper.read(FOLDER / "original-P1.json.gz")
    request = deepcopy(original["payload"]["request"])
    request["source_report_readings"] = helper.read(FOLDER / "reading-input.json")
    return {"P1": helper.p1_from(request, original["payload"]["graph"]),
            **helper.read(FOLDER / "candidate-P2-P5.json.gz")}


def candidate():
    reference = load()
    p1 = reference["P1"]
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2, reference["P3"]["payload"]["interpretation_input"])
    actual = {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
              "P5": service.financial_product(p1, p2, p3)}
    answer = helper.consume(actual)
    require(actual == reference, "Complete installed original pair products differ")
    require(answer == helper.read(FOLDER / "candidate-answer.json.gz"), "Complete installed original pair answer differs")
    comparison = {"complete_products_equal": True, "complete_answer_equal": True,
        "products": {k: v["sha256"] for k, v in actual.items()}, "complete_answer_sha256": digest(answer),
        "report_sha256": answer["report_sha256"],
        "answer_reference": {"path": str((FOLDER / "candidate-answer.json.gz").relative_to(ROOT)),
                             "file_sha256": helper.sha(FOLDER / "candidate-answer.json.gz")}}
    save(TARGET / "complete-comparison.json", comparison)
    return comparison


def mutation(reference, case):
    """Independently reconstruct the exact recorded saved-chain counterexample."""
    changed = deepcopy(reference)
    p2 = changed["P2"]["payload"]
    p3 = changed["P3"]["payload"]
    request = changed["P1"]["payload"]["request"]
    if case == "missing-discrepancy":
        del p3["source_discrepancies"]
    elif case == "changed-discrepancy":
        p3["source_discrepancies"]["discrepancies"][0]["resolved_amount"] = "1500000000"
    elif case == "missing-input":
        p3["interpretation_input"] = None
    elif case == "missing-selection":
        del p2["source_report_readings"]
    elif case == "unsupplied-selection":
        del request["source_report_readings"]
    elif case == "false-page":
        selected = p2["source_report_readings"]
        reading = selected["reports"][0]
        reading["pages"][0]["page"] += 1
        reading["sha256"] = digest({k: v for k, v in reading.items() if k != "sha256"})
        packet = p3["interpretation_input"]["source_discrepancies"]
        packet["readings_sha256"] = digest(selected)
        packet["discrepancies"][0]["sides"][0]["reading_sha256"] = reading["sha256"]
        p3["source_discrepancies"] = source_discrepancies.admit(changed["P1"]["payload"]["graph"], selected, packet)
    else:
        raise ValueError("Unknown installed pair counterexample")
    changed["P1"] = helper.p1_from(request, changed["P1"]["payload"]["graph"])
    for phase, parents in (("P2", ("P1",)), ("P3", ("P1", "P2")), ("P4", ("P1", "P3")), ("P5", ("P2", "P3"))):
        changed[phase] = service.seal(phase, request["bundle"], {p: changed[p]["sha256"] for p in parents}, changed[phase]["payload"])
    return changed


def controls(cases):
    reference = load()
    rows = {}
    for case in cases:
        changed = mutation(reference, case)
        hashes = {k: v["sha256"] for k, v in changed.items()}
        require(hashes == helper.read(FOLDER / "phases" / (case + "-input.json"))["products"],
                "Installed pair counterexample identities differ: " + case)
        expected = helper.read(FOLDER / "phases" / (case + "-result.json"))
        result = helper.refuse(lambda: helper.consume(changed), expected["reason"])
        require(result == expected, "Installed pair refusal differs")
        rows[case] = {**result, "products": hashes}
    return rows


def main():
    global ROOT, FOLDER, TARGET, helper, service, source_discrepancies, digest
    ROOT, FOLDER, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    TARGET = FOLDER / "commands" / stage
    def block(event, _):
        if event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Installed original pair forbids native/network: " + event)
    sys.addaudithook(block)
    def expired(*_):
        raise TimeoutError("Installed original pair consumer exceeded105 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(105)
    from legalmath.prospectus.successor import service, source_discrepancies
    from legalmath.prospectus.successor.contracts import digest
    helper_path = Path(__file__).with_name("helper.py")
    spec = importlib.util.spec_from_file_location("retained_fy_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.ROOT, helper.FOLDER, helper.TARGET = ROOT, FOLDER, TARGET
    helper.service, helper.digest, helper.save = service, digest, save
    require(helper.sha(helper_path) == helper.read(FOLDER / "installed-harness.json")["helper_sha256"], "Copied helper changed")
    prior = ROOT / "docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-09/attempt-005"
    expected = helper.read(prior / "source-package.json")
    result = {"status": "FAIL", "stage": stage}
    try:
        before = helper.identity(expected)
        actions = {"installed-candidate": candidate,
            "installed-controls-a": lambda: controls(CASES[:2]),
            "installed-controls-b": lambda: controls(CASES[2:4]),
            "installed-controls-c": lambda: controls(CASES[4:])}
        details = actions[stage]()
        after = helper.identity(expected)
        result.update(status="PASS", details=details, before=before, after=after, new_native_calls=0,
                      helper_sha256=helper.sha(helper_path))
    except BaseException as exc:
        result.update(error={"type": type(exc).__name__, "message": str(exc)}, traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
    save(TARGET / "installed-result.json", result)
    print(json.dumps({"status": result["status"], "stage": stage, "error": result.get("error")}))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
