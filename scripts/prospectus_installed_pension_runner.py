"""Isolated installed Note22 consumer with complete replay and actual refusals."""
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ["CUDA_VISIBLE_DEVICES"]="-1"
sys.dont_write_bytecode=True
from legalmath.prospectus import basf_pension_note,basf_pension_spec,basf_hedge_note,basf_oci_notes,basf_equity,basf_statement
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE,ROOT=[Path(p).resolve() for p in sys.argv[1:3]]
TARGET=HERE/"installed-results";TARGET.mkdir(exist_ok=False)
ENV=Path(sys.executable).parent.parent.resolve()


def read(path):
    raw=path.read_bytes();return json.loads(gzip.decompress(raw) if path.suffix==".gz" else raw)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name,value):
    path=TARGET/name;raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with path.open("xb") as stream:stream.write(gzip.compress(raw,mtime=0) if path.suffix==".gz" else raw)


modules=[basf_pension_note,basf_pension_spec,basf_hedge_note,basf_oci_notes,basf_equity,basf_statement,service]
proof={"python":sys.executable,"prefix":sys.prefix,"isolated":sys.flags.isolated,"sys_path":sys.path,
    "modules":{m.__name__:{"path":m.__file__,"sha256":sha(Path(m.__file__))} for m in modules},
    "dependencies":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve()==ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT/"src") for p in sys.path if p)
package=ENV/"lib/python3.11/site-packages/legalmath"
files={str(p.relative_to(package)):sha(p) for p in package.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix!=".pyc"}
assert files==read(HERE/"source-package.json")
save("package-files.json",files);save("import-proof.json",proof)
guard={"starts":0,"blocked":0}


def audit(event,args):
    if event in {"subprocess.Popen","os.system","os.posix_spawn","os.fork","os.exec","os.spawn","socket.connect","socket.bind","socket.getaddrinfo"}:
        guard["blocked"]+=1
        raise RuntimeError("Installed pension replay forbids process/network actions")


sys.addaudithook(audit)
products=read(HERE/"products.json.gz");old=read(HERE/"prior-profiles.json");hp=read(HERE/"hedge-profile.json");p=read(HERE/"profile.json")
value=basf_pension_note.consume(products,old,hp,p,ROOT,
    expected_prior_profiles_sha256=digest(old),expected_hedge_profile_sha256=digest(hp),expected_profile_sha256=digest(p))
assert value==read(HERE/"pension-consumer.json.gz")
prior=read(HERE/"baseline-consumer.json.gz")
assert {k:value[k] for k in prior}==prior
save("pension-consumer.json.gz",value)
observed=[]
for row in read(HERE/"actual-controls.json"):
    altered=read(HERE/"adverse-inputs"/(row["case"]+".json.gz"))
    try:basf_pension_note.evaluate(products["P1"]["payload"]["graph"],prior,altered["profile"],ROOT,
        expected_profile_sha256=altered["expected_profile_sha256"])
    except ValueError as error:observed.append({"case":row["case"],"refused":True,"repinned":row["repinned"],"reason":str(error)})
    else:raise ValueError("Installed altered pension profile accepted: "+row["case"])
assert observed==read(HERE/"actual-controls.json") and guard=={"starts":0,"blocked":0}
save("controls.json",observed)
save("result.json",{"status":"PASS","complete_output_equal":True,"earlier_outputs_unchanged":True,
    "controls":len(observed),"exact_package_files":len(files),"process_guard":guard,
    "cpu_gpu":"CPU only;GPU devices intentionally hidden","same_host_only":True,"independent_legal_acceptance":False})
print(json.dumps({"status":"PASS","controls":len(observed),"complete_output_equal":True}))
