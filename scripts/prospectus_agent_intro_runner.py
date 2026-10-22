"""Run the installed optional agent-introduction consumer."""
import gzip, hashlib, importlib.metadata, json
from pathlib import Path
import subprocess, sys
from legalmath.prospectus import basf_agent_introduction
from legalmath.prospectus.successor.contracts import digest

HERE, ROOT = [Path(p).resolve() for p in sys.argv[1:3]]
MODE = sys.argv[3]; assert MODE in ("answer", "controls")
TARGET = HERE / ("installed-" + MODE); TARGET.mkdir(exist_ok=False)
ENV = Path(sys.executable).parent.parent.resolve()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def save(name, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with (TARGET / name).open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


proof = {"python": sys.executable, "prefix": sys.prefix, "isolated": sys.flags.isolated,
         "sys_path": sys.path,
         "modules": {basf_agent_introduction.__name__: {"path": basf_agent_introduction.__file__,
                     "sha256": sha(basf_agent_introduction.__file__)}},
         "dependencies": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve() == ENV
assert Path(basf_agent_introduction.__file__).resolve().is_relative_to(ENV)
assert all(not Path(p).resolve().is_relative_to(ROOT / "src") for p in sys.path if p)
package = ENV / "lib/python3.11/site-packages/legalmath"
expected = read(HERE / "source-package.json")
files = {str(p.relative_to(package)): sha(p) for p in package.rglob("*")
         if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
assert files == expected
save("package-files.json", files); save("import-proof.json", proof)


def no_native(*args, **kwargs): raise AssertionError("Native children forbidden")
subprocess.Popen = no_native
products = read(HERE / "products.json.gz"); prior = read(HERE / "prior-consumer.json.gz")
profile = read(HERE / "profile.json")
if MODE == "answer":
    result = basf_agent_introduction.consume(products, prior, profile, ROOT,
        expected_prior_sha256=digest(prior), expected_profile_sha256=digest(profile))
    assert result == read(HERE / "agent-introduction-consumer.json.gz")
    save("agent-introduction-consumer.json.gz", result)
    outcome = {"status": "PASS", "full_output_equal": True, "native_calls": 0, "same_host_only": True}
else:
    observed = []
    for row in read(HERE / "actual-controls.json"):
        value = read(HERE / "adverse-inputs" / (row["case"] + ".json.gz"))
        try:
            basf_agent_introduction.evaluate(products, prior, value["profile"], ROOT,
                expected_profile_sha256=value["expected_profile_sha256"])
        except ValueError as error:
            observed.append({"case": row["case"], "refused": True, "repinned": row["repinned"], "reason": str(error)})
        else: raise AssertionError("Altered profile accepted: " + row["case"])
    assert observed == read(HERE / "actual-controls.json")
    save("controls.json", observed)
    outcome = {"status": "PASS", "controls": len(observed), "native_calls": 0, "same_host_only": True}
save("result.json", outcome); print(outcome)
