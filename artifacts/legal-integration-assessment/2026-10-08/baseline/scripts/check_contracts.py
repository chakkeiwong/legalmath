"""Regenerate the contract pack and require byte-for-byte stability."""
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def state():
    paths = list((ROOT / "docs/specs/v0.1").rglob("*.json")) + list((ROOT / "src/legalmath/schemas").glob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


before = state()
for script in ("build_spec_examples.py", "build_service_contracts.py", "export_openapi.py"):
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True, cwd=ROOT)
after = state()
if before != after:
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    raise SystemExit("Contract regeneration changed: " + ", ".join(changed))
print(f"Contract regeneration stable across {len(after)} JSON files.")
