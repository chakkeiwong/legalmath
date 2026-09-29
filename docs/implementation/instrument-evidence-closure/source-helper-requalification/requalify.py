"""Requalify the reviewed one-expression source-reference change, offline."""
from pathlib import Path
import difflib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
import run_instrument_evidence_closure as master
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.prospectus.common import read, write, sha, now
from legalmath.interpretation.assurance import source_references as refs
from run_instrument_transport_study import prepare

out = Path(__file__).parent / "attempt-001"
out.mkdir(exist_ok=False)
old = read(master.OUT / "E3/attempt-002/inputs.json")
current = master.identity("E3")
changed = {p: {"tested": h, "current": current["files"].get(p)}
           for p, h in old["files"].items() if h != current["files"].get(p)}
helper = "src/legalmath/interpretation/assurance/source_references.py"
assert set(changed) == {helper}
assert set(current["files"]) == set(old["files"])
assert old["tools"] == current["tools"]
with zipfile.ZipFile(master.OUT / "baseline.zip") as archive:
    previous = archive.read(helper)
assert sha(previous) == old["files"][helper]
present = (ROOT / helper).read_bytes()
(out / "source_references.tested.py").write_bytes(previous)
(out / "source_references.current.py").write_bytes(present)
(out / "source-change.diff").write_text("".join(difflib.unified_diff(
    previous.decode().splitlines(True), present.decode().splitlines(True),
    fromfile="tested/source_references.py", tofile="current/source_references.py")))
write(out / "inputs.json", current)
command = [sys.executable, "-m", "pytest", "-q",
           "tests/assurance/test_continuation_references.py",
           "tests/assurance/test_capacity_tables.py",
           "tests/prospectus/test_instrument_transport_study.py",
           "--junitxml=" + str(out / "tests.xml")]
started = now()
clock = time.monotonic()
manifest = {"status": "RESERVED", "started_at": started,
    "git_commit": "79a6313c79138aa81c48fd50229d9226acdcfbc5",
    "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
    "test_command": command, "environment": sys.executable,
    "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1", "seeds": "N/A: deterministic",
    "input_hash": digest(current), "script_sha256": sha(Path(__file__).read_bytes()),
    "review": "docs/implementation/instrument-evidence-closure/continuation-review.md",
    "live_calls": 0, "changed": changed}
write(out / "manifest.json", manifest)
try:
    new = prepare(out / "transport-study")
    retained = read(master.OUT / "E3/attempt-002/transport-study/prepared.json")
    assert new == retained
    for row in retained["requests"]:
        name = row["id"] + ".json"
        assert ((out / "transport-study/requests" / name).read_bytes() ==
                (master.OUT / "E3/attempt-002/transport-study/requests" / name).read_bytes())
    record = read(out / "transport-study/requests" / (retained["requests"][0]["id"] + ".json"))
    packet = record["original_request"]["source_packet"]
    table = record["references"]
    refs.verify_table(table, packet, table["request_hash"])
    bad = deepcopy(table)
    assert bad["spans"][0]["start_codepoint"] == 0
    bad["spans"][0]["start_codepoint"] = False
    try:
        refs.verify_table(bad, packet, table["request_hash"])
    except LegalMathError:
        pass
    else:
        raise AssertionError("Boolean masquerading as codepoint was accepted")
    with (out / "pytest.log").open("w") as log:
        completed = subprocess.run(command, cwd=ROOT, stdout=log,
            stderr=subprocess.STDOUT, timeout=180,
            env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"})
    assert completed.returncode == 0, (out / "pytest.log").read_text()
    assert master.identity("E3") == current, "Bound method mutated during check"
    tree = ET.parse(out / "tests.xml")
    counts = {key: sum(int(s.get(key, "0")) for s in tree.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    result = {"status": "PASS", "prepared_requests": len(retained["requests"]),
        "requests_byte_identical": True, "lossless_decode": True,
        "boolean_codepoint_mutation": "REJECTED", "regression": counts,
        "legal_accuracy": "NOT_ESTABLISHED", "live_calls": 0,
        "tested_method_preserved": True, "current_helper_sha256": sha(present)}
    write(out / "result.json", result)
    manifest["status"] = "PASS"
    print(json.dumps(result, indent=2))
except Exception as exc:
    manifest.update(status="FAILED", error=str(exc))
    raise
finally:
    manifest.update(finished_at=now(), wall_seconds=round(time.monotonic()-clock, 3),
        output_hashes={str(p.relative_to(out)): sha(p.read_bytes())
                      for p in sorted(out.rglob("*"))
                      if p.is_file() and p.name != "manifest.json"})
    write(out / "manifest.json", manifest)
