from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "docs/prospectus"
PROGRAM = ROOT / "docs/implementation/prospectus-master"
RUNS = ROOT / "artifacts/prospectus-master"
PLAN = ROOT / "docs/plans/prospectus-master-program.md"
PYTHON = ROOT / ".venv/bin/python"
JDK = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"
LEAN = Path("/home/chakwong/.elan/toolchains/leanprover--lean4---v4.20.0/bin/lean")
TOOLCHAIN = {
    "compiler": ROOT / ".localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala",
    "upstream": ROOT / ".localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa",
    "lock": ROOT / "docs/implementation/catala/toolchain-lock.json",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))
