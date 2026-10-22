"""Isolated installed FY consumer; this file never adds checkout code to sys.path."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith(".gz") else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if str(path).endswith(".gz") else raw
    require(sum(p.stat().st_size for p in FOLDER.rglob("*") if p.is_file()) + len(data) < 63 * 1024**2,
            "Installed evidence cap")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


def files(folder):
    result = {}
    for p in sorted(folder.rglob("*")):
        require(not p.is_symlink(), "Package symlink")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            result[str(p.relative_to(folder))] = sha(p)
    return result


def identity(expected):
    require(sys.flags.isolated == 1 and sys.version_info[:2] == (3, 11), "Isolated Python3.11 required")
    package = Path(service.__file__).resolve().parents[2]
    require(package == Path(sys.prefix) / "lib/python3.11/site-packages/legalmath", "Wrong installed module location")
    require(files(package) == expected, "Installed package bytes differ")
    require(all(not Path(p).resolve().is_relative_to(ROOT / "src") for p in sys.path if p), "Checkout import path")
    loaded = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package), "Import escaped installation: " + name)
            require(expected[str(path.relative_to(package))] == sha(path), "Loaded module changed")
            loaded[name] = {"path": str(path), "sha256": sha(path)}
    return {"python": sys.executable, "prefix": sys.prefix, "sys_path": sys.path,
            "isolated": sys.flags.isolated, "package": str(package), "modules": loaded}


def p1_from(request, graph):
    return service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": graph})


def load_products(folder, prefix):
    ref = read(folder / (prefix + "-P1-reference.json.gz"))
    path = ROOT / ref["original_P1"]
    require(sha(path) == ref["file_sha256"], "Original P1 changed")
    p1 = p1_from(ref["request"], read(path)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "Referenced P1 differs")
    return {"P1": p1, **read(folder / (prefix + "-P2-P5.json.gz"))}


def consume(values):
    return service.consume(values, ROOT, mode="frozen", include_artifacts=True)


def refuse(thunk, expected):
    try: thunk()
    except ValueError as exc:
        require(expected in str(exc), "Wrong refusal: " + str(exc))
        return {"rejected": True, "reason": str(exc)}
    raise ValueError("Adverse input accepted")


def matched():
    results = {}
    for name in ("baseline", "after"):
        reference = load_products(PRODUCT, name)
        p1 = reference["P1"]
        p2 = service.construction_product(p1, ROOT)
        p3 = service.interpretation_product(p1, p2, reference["P3"]["payload"]["interpretation_input"])
        actual = {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
                  "P5": service.financial_product(p1, p2, p3)}
        save(TARGET / (name + "-P2-P5.json.gz"), {k: v for k, v in actual.items() if k != "P1"})
        answer = consume(actual)
        save(TARGET / (name + "-answer.json.gz"), answer)
        require(actual == reference, "Complete installed products changed: " + name)
        require(answer == read(PRODUCT / (name + "-answer.json.gz")), "Complete installed answer changed: " + name)
        results[name] = {"complete_products_equal": True, "complete_answer_equal": True,
                         "report_sha256": answer["report_sha256"], "P1": p1["sha256"]}
    return {"matched": results, "cells_consumed": 200, "native_extraction_established": False}


def controls():
    actual = load_products(PRODUCT, "after")
    graph, request = actual["P1"]["payload"]["graph"], actual["P1"]["payload"]["request"]
    results = {}
    prior = PRODUCT.parent / "attempt-005"
    for path in sorted((prior / "cell-controls").glob("*.json.gz")):
        bad_request = deepcopy(request)
        bad_request["source_statement_cells"]["reading"] = read(path)
        bad = p1_from(bad_request, graph)
        cases = read(PRODUCT / "input-controls" / (path.stem + "-result.json"))
        require(bad["sha256"] == cases["P1_sha256"], "Installed negative P1 differs")
        result = refuse(lambda: service.construction_product(bad, ROOT), "reading differs")
        result.update(input=str(path.relative_to(ROOT)), input_sha256=sha(path), P1=bad["sha256"])
        results[path.name] = result
    require(len(results) == 14, "Incomplete retained controls")
    for change in ("crossed-profile", "crossed-reading", "geometry", "edition"):
        path = PRODUCT / "input-controls" / (change + "-input.json.gz")
        delta = read(path)
        bad_graph, bad_request = deepcopy(graph), deepcopy(request)
        bad_request["source_statement_cells"] = delta["source_statement_cells"]
        if delta["changed_unit"]:
            unit = delta["changed_unit"]
            bad_graph["units"] = [unit if u["id"] == unit["id"] else u for u in bad_graph["units"]]
        bad = p1_from(bad_request, bad_graph)
        require(bad["sha256"] == delta["expected_P1_sha256"], "Installed input reconstruction differs")
        expected = "Unsupported" if change == "crossed-profile" else "reading differs" if change == "crossed-reading" else "original pages"
        result = refuse(lambda: service.construction_product(bad, ROOT), expected)
        result.update(input=str(path.relative_to(ROOT)), input_sha256=sha(path), P1=bad["sha256"])
        results[change] = result
    for change in ("missing-p2", "changed-p2", "missing-p3", "changed-p3", "unsupplied"):
        bad = deepcopy(actual)
        if change == "missing-p2": del bad["P2"]["payload"]["source_statement_cells"]
        elif change == "changed-p2": bad["P2"]["payload"]["source_statement_cells"]["reading"]["rows"][0]["cells"][0]["value"] += 1
        elif change == "missing-p3": del bad["P3"]["payload"]["source_statement_cells_sha256"]
        elif change == "changed-p3": bad["P3"]["payload"]["source_statement_cells_sha256"] = "0" * 64
        else: del bad["P1"]["payload"]["request"]["source_statement_cells"]
        bad["P1"] = p1_from(bad["P1"]["payload"]["request"], graph)
        for phase, parents in {"P2": ("P1",), "P3": ("P1", "P2"), "P4": ("P1", "P3"), "P5": ("P2", "P3")}.items():
            bad[phase] = service.seal(phase, request["bundle"], {p: bad[p]["sha256"] for p in parents}, bad[phase]["payload"])
        ref = PRODUCT / "phase-controls" / (change + "-input.json")
        hashes = {p: v["sha256"] for p, v in bad.items()}
        require(hashes == read(ref)["product_hashes"], "Installed phase reconstruction differs")
        results[change] = {**refuse(lambda: consume(bad), "Consumed statement cells"),
                           "input": str(ref.relative_to(ROOT)), "input_sha256": sha(ref), "product_hashes": hashes}
    require(len(results) == 23, "Incomplete installed controls")
    return {"actual_public_refusals": 23, "cases": results}


def prior_profiles():
    base = ROOT / "docs/implementation/prospectus-execution-authority/attempts"
    nine = base / "source-bes-dep-01/attempt-005"
    answer = consume(read(nine / "after-products.json.gz"))
    require(digest(answer) == read(nine / "answer-reconstruction.json")["expected_complete_answer_sha256"], "Installed9M complete answer differs")
    nine_hash = answer["report_sha256"]
    q1 = base / "source-bes-dep-11/attempt-004"
    ref = read(q1 / "after-P1-reference.json.gz")
    original = ROOT / ref["original_p1"]
    require(sha(original) == ref["original_p1_file_sha256"], "Original Q1 source changed")
    p1 = p1_from(ref["request"], read(original)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_P1_sha256"], "Q1 reconstruction differs")
    values = {"P1": p1, **read(q1 / "after-P2-P5.json.gz")}
    answer = service.consume(values, ROOT, mode="frozen")
    require(answer == read(q1 / "after-answer.json.gz"), "InstalledQ1 answer changed")
    return {"nine_month_complete_answer_equal": True, "nine_month_report": nine_hash,
            "q1_complete_answer_equal": True, "q1_report": answer["report_sha256"]}


def main():
    global ROOT, FOLDER, PRODUCT, TARGET, service, digest
    ROOT, FOLDER, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    PRODUCT = ROOT / "docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-08/attempt-006"
    TARGET = FOLDER / "commands" / stage
    def block(event, _):
        if event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Installed FY consumer forbids subprocess/network: " + event)
    sys.addaudithook(block)
    def expired(*_): raise TimeoutError("Installed FY consumer exceeded105 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(105)
    from legalmath.prospectus.successor import service
    from legalmath.prospectus.successor.contracts import digest
    expected = read(FOLDER / ("old-package.json" if stage == "old-profile" else "source-package.json"))
    identity(expected)
    if stage == "old-profile":
        p1 = load_products(PRODUCT, "after")["P1"]
        result = refuse(lambda: service.construction_product(p1, ROOT), "Unsupported source statement cell profile")
        result["scope"] = "Actual older installed public interface rejects absent FY profile"
    else: result = {"matched": matched, "controls": controls, "prior-profiles": prior_profiles}[stage]()
    save(TARGET / "installed-proof.json", identity(expected))
    save(TARGET / "installed-result.json", {"status": "PASS", "stage": stage, "details": result,
         "new_native_calls": 0, "independent_acceptance": False, "whole_program_complete": False})
    print(json.dumps({"status": "PASS", "stage": stage}))
    return 0


if __name__ == "__main__": raise SystemExit(main())
