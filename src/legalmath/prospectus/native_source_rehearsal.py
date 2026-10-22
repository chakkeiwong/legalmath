"""Recorded native bytes through current source code; never fresh execution."""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import subprocess

from . import native_current_preparation as preparation
from .execution_authority import digest, file_hash, read
from .successor import sealed_runtime, sealed_source, service

VERSION = "native-source-rehearsal.v1"
SCRIPT = "scripts/prospectus_native_source_rehearsal.py"
TEST = "tests/prospectus/test_native_source_rehearsal.py"
TESTS = (*preparation.TESTS, TEST)
require = preparation.require


def methods(root):
    names = set(preparation.method_names(root)) | {SCRIPT, TEST}
    return {name: file_hash(preparation.local(root, name)) for name in sorted(names)}


def check_methods(root, folder):
    expected = read(folder / "methods.json")
    require(expected == methods(root), "Source rehearsal methods changed after freeze")
    from hashlib import sha256
    with gzip.open(folder / "method-snapshots.json.gz", "rt") as stream:
        snapshots = json.load(stream)
    require(set(snapshots) == set(expected) and all(sha256(snapshots[n].encode()).hexdigest() == h
        for n, h in expected.items()), "Source rehearsal method snapshots differ")
    return expected


class RecordedBoundary:
    """Match exact supported operations; deliver immutable historical bytes."""
    def __init__(self, root, route):
        self.root, self.route = root, deepcopy(route)
        self.deliveries, self.attempts, self.refusals = [], 0, 0
        self.manifest = read(preparation.local(root, route["manifest"]))

    def load(self, argv, stdin):
        self.attempts += 1
        try:
            require(len(self.deliveries) < len(self.route["calls"]), "Unexpected additional recorded native call")
            call = self.route["calls"][len(self.deliveries)]
            require(argv == call["record"]["argv"], "Recorded native argv differs")
            folder = preparation.local(self.root, call["folder"])
            streams = {name: (folder / name).read_bytes() for name in ("stdin", "stdout", "stderr")}
            require(stdin == streams["stdin"], "Recorded native stdin differs")
            for name, data in streams.items():
                require(len(data) == call["streams"][name]["bytes"] and
                    file_hash(folder / name) == call["streams"][name]["sha256"], "Recorded native stream changed")
            record_name = "command.json" if self.route["route"] == "2009-default" else "receipt.json"
            require(read(folder / record_name) == call["record"], "Recorded native receipt/command changed")
            return call, streams
        except BaseException:
            self.refusals += 1
            raise

    def delivered(self, call, kind, **details):
        self.deliveries.append({"kind": "RECORDED_BYTES_ONLY", "boundary": kind,
            "historical_folder": call["folder"], "argv": call["record"]["argv"],
            "streams": call["streams"], "native_process_launched": False, **details})

    def selected(self, folder, manifest, argv, stdin=b"", timeout=60, *, max_stream=None, **kwargs):
        call, streams = self.load(argv, stdin)
        try:
            require(not kwargs and Path(folder).resolve() == preparation.local(self.root, self.route["manifest"]).parent
                and manifest == self.manifest and timeout == 60, "Recorded runtime context differs")
            cap = sealed_runtime.stream_bound(max_stream)
            require(cap == call["record"]["limits"]["max_stream_bytes"], "Recorded stream bound differs")
            # Keep the real execute() verifier and its current-runtime check active.
            sealed_runtime.verify_receipt(call["record"], manifest, argv, stdin,
                streams["stdout"], streams["stderr"])
            self.delivered(call, "sealed_runtime.run", effective_stream_cap=cap)
            return {"returncode": call["record"]["returncode"], "stdout": streams["stdout"],
                    "stderr": streams["stderr"], "receipt": deepcopy(call["record"])}
        except BaseException:
            self.refusals += 1
            raise

    def default(self, argv, *args, **kwargs):
        data = kwargs.get("input", b"")
        stdin = data.encode() if isinstance(data, str) else data
        call, streams = self.load(argv, stdin)
        try:
            require(self.route["route"] == "2009-default" and not args and kwargs.get("capture_output") is True
                and kwargs.get("timeout") == 90, "Default source call context differs")
            require(min(kwargs["timeout"], 60) == call["record"]["timeout"], "Historical default timeout clamp differs")
            environment = kwargs.get("env", os.environ)
            require({k: environment.get(k) for k in ("CUDA_VISIBLE_DEVICES", "OMP_THREAD_LIMIT", "LANG")}
                == call["record"]["environment"], "Default recorded environment differs")
            result = read(preparation.local(self.root, call["folder"]) / "result.json")
            require(result["returncode"] == 0, "Historical default native call failed")
            self.delivered(call, "subprocess.run", requested_timeout=90, recorded_timeout=60)
            convert = lambda value: value.decode() if kwargs.get("text") else value
            return subprocess.CompletedProcess(argv, result["returncode"],
                convert(streams["stdout"]), convert(streams["stderr"]))
        except BaseException:
            self.refusals += 1
            raise

    @contextmanager
    def installed(self):
        previous_run, previous_native = subprocess.run, sealed_runtime.run
        subprocess.run, sealed_runtime.run = self.default, self.selected
        try:
            yield self
        finally:
            subprocess.run, sealed_runtime.run = previous_run, previous_native

    def complete(self):
        require(self.attempts == len(self.deliveries) == len(self.route["calls"]) == 2
            and self.refusals == 0, "Missing, extra or refused recorded native call")
        return {"version": VERSION, "route": self.route["route"], "deliveries": self.deliveries,
                "native_processes": 0, "fresh_native_execution_established": False}


def source_request(root, route):
    folder = preparation.local(root, preparation.ROUTES[route])
    old = preparation.historical.unpack(folder / "P1.json.gz")
    if route.startswith("2009-"):
        raw = preparation.historical.unpack(folder / "raw-P1.json.gz")
        request = deepcopy(raw["payload"]["request"])
    else:
        raw = None
        request = deepcopy(old["payload"]["request"])
    return request, old, raw


def source_product(root, route):
    inventory = read(root / preparation.INVENTORY)
    row = next(r for r in inventory["routes"] if r["route"] == route)
    request, old, old_raw = source_request(root, route)
    boundary = RecordedBoundary(root, row)
    with boundary.installed():
        if route == "2009-default":
            raw = service.source_product(request, root)
        else:
            snapshot = preparation.local(root, row["manifest"]).parent
            runtime = sealed_source.SourceRuntime(snapshot, sealed_runtime.digest(boundary.manifest),
                                                  native_text_max_stream=64 * 1024 * 1024)
            raw = sealed_source.source_product(request, root, runtime)
            require(len(runtime.receipts) == 2, "Actual SourceRuntime receipt count differs")
    proof = boundary.complete()
    p1 = preparation.historical.rebind(raw, old["payload"]["request"]) if old_raw is not None else raw
    proof.update(raw_comparator_available=old_raw is not None,
        raw_complete_equality=raw == old_raw if old_raw is not None else None,
        consumed_P1_complete_equality=p1 == old)
    return p1, raw, proof


def downstream(root, p1, old):
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2, old["P3"]["payload"].get("interpretation_input"))
    p4 = service.law_product(p1, p3, old["P4"]["payload"].get("cases"), old["P4"]["payload"].get("law_input"))
    p5 = service.financial_product(p1, p2, p3, old["P5"]["payload"].get("cases"), old["P5"]["payload"].get("scenario_input"))
    values = dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5)
    return values, service.consume(values, root, mode="frozen", include_artifacts=True)


def check_delivery(root, route, proof):
    require(proof["version"] == VERSION and proof["route"] == route and proof["native_processes"] == 0
        and proof["fresh_native_execution_established"] is False and proof["consumed_P1_complete_equality"] is True,
        "Rehearsal scope or source comparison differs")
    require(proof["raw_comparator_available"] == route.startswith("2009-")
        and proof["raw_complete_equality"] is (True if route.startswith("2009-") else None),
        "Incorrect raw source comparator")
    inventory = read(root / preparation.INVENTORY)
    row = next(r for r in inventory["routes"] if r["route"] == route)
    require(len(proof["deliveries"]) == len(row["calls"]) == 2, "Missing/extra delivered boundary")
    for delivery, call in zip(proof["deliveries"], row["calls"]):
        require(delivery["kind"] == "RECORDED_BYTES_ONLY" and delivery["native_process_launched"] is False
            and delivery["historical_folder"] == call["folder"] and delivery["argv"] == call["record"]["argv"]
            and delivery["streams"] == call["streams"], "Changed recorded source dispatch")


def evidence(root, folder):
    check_methods(root, folder)
    preparation.check_zero_ledger(folder)
    require(preparation.history(root) == read(folder / "historical-evidence.json"), "Historical inputs changed")
    routes = []
    for route in preparation.ROUTES:
        path = folder / "routes" / route
        require((path / "comparison.json").exists(), "Missing source-rehearsal matrix arm")
        result = read(folder / "stages" / ("rehearse-" + route) / "result.json")
        require(result["status"] == "PASS" and result["subprocess_attempts"] == 0
            and 0 <= result["wall_seconds"] <= 120, "Source rehearsal stage failed")
        check_delivery(root, route, read(path / "dispatch.json"))
        comparison = read(path / "comparison.json")
        require(set(comparison["objects"]) == {"P1", "P2", "P3", "P4", "P5", "answer"}, "Missing product")
        baseline = preparation.local(root, preparation.ROUTES[route])
        for key, ref in comparison["objects"].items():
            require(preparation.load_object(root, ref) == preparation.historical.unpack(baseline / (key + ".json.gz")),
                "Complete source/downstream equality failed: " + key)
        routes.append({"route": route, "source_and_downstream_complete_equality": True,
                       "recorded_byte_deliveries": 2, "native_processes": 0})
    return {"version": VERSION, "status": "PASS", "scope": "RECORDED_NATIVE_BYTES_REHEARSAL_ONLY",
        "routes": routes, "native_processes": 0, "fresh_native_execution_established": False,
        "task_acceptance_established": False, "whole_program_complete": False}
