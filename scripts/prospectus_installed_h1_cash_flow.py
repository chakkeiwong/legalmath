"""One isolated original-source H1 cash-flow replay from the installed wheel."""
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.dont_write_bytecode = True
from legalmath.prospectus import h1_cash_flow, h1_cash_flow_spec
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE, ROOT = [Path(p).resolve() for p in sys.argv[1:3]]
MODE = sys.argv[3]
assert MODE in {"positive", "controls-a", "controls-b"}
TARGET = HERE / "installed-results" / MODE
TARGET.mkdir(parents=True, exist_ok=False)
ENV = Path(sys.executable).parent.parent.resolve()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = TARGET / name
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw)


modules = [h1_cash_flow, h1_cash_flow_spec, service]
proof = {"python": sys.executable, "prefix": sys.prefix, "isolated": sys.flags.isolated, "sys_path": sys.path,
    "modules": {m.__name__: {"path": m.__file__, "sha256": sha(Path(m.__file__))} for m in modules},
    "dependencies": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve() == ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT / "src") for p in sys.path if p)
package = ENV / "lib/python3.11/site-packages/legalmath"
files = {str(p.relative_to(package)): sha(p) for p in package.rglob("*")
    if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
assert files == read(HERE / "source-package.json") and len(files) == 438
save("package-files.json", files)
save("import-proof.json", proof)
guard = {"starts": 0, "blocked": 0}


def audit(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.forkpty", "os.exec", "os.spawn", "pty.spawn"}:
        guard["blocked"] += 1
        raise RuntimeError("Installed H1 replay forbids process/network actions")


sys.addaudithook(audit)
products = read(HERE / "products.json.gz")
prior = read(HERE / "baseline-answer.json.gz")
if MODE == "positive":
    profile = read(HERE / "profile.json")
    value = h1_cash_flow.consume(products, profile, ROOT, expected_profile_sha256=digest(profile))
    assert value == read(HERE / "cash-flow-consumer.json.gz") and value["answer"] == prior
    save("cash-flow-consumer.json.gz", value)
    details = {"complete_output_equal": True, "previous_answer_equal": True}
else:
    expected = read(HERE / (MODE + ".json"))
    assert [r["case"] for r in expected] == read(HERE / "control-partitions.json")[MODE] and len(expected) == 12
    observed = []
    for row in expected:
        altered = read(HERE / "adverse-inputs" / (row["case"] + ".json.gz"))
        try:
            h1_cash_flow.evaluate(products["P1"]["payload"]["graph"], prior, altered["profile"], ROOT,
                expected_profile_sha256=altered["expected_profile_sha256"])
        except ValueError as exc:
            observed.append({"case": row["case"], "refused": True, "repinned": row["repinned"], "reason": str(exc)})
        else:
            raise ValueError("Installed altered cash-flow profile accepted: " + row["case"])
    assert observed == expected
    save("controls.json", observed)
    details = {"controls": len(observed), "cases": [r["case"] for r in observed], "all_exact_refusals": True}
assert guard == {"starts": 0, "blocked": 0}
save("result.json", {"status": "PASS", "mode": MODE, **details, "exact_package_files": len(files),
    "process_guard": guard, "cpu_gpu": "CPU only; GPU devices intentionally hidden", "same_host_only": True,
    "independent_legal_acceptance": False})
print(json.dumps({"status": "PASS", "mode": MODE, **details}))
