"""Check the documented reader admission command on XMI and ZIP exports."""
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor import annotation_authoring as draft
from legalmath.prospectus.successor.contracts import digest, write


def main():
    started = time.monotonic()
    rows = {}
    with tempfile.TemporaryDirectory(prefix="prospectus-codec-audit-") as temp:
        folder = Path(temp)
        text = "Synthetic unlabelled source."
        source = {"document": "audit", "source_sha256": digest(b"synthetic PDF identity"),
                  "text_sha256": digest(text.encode())}
        raw, types = draft.empty(text, source)
        envelope = folder / "source.json"
        write(envelope, {"source": source, "text": text})
        (folder / "raw.xmi").write_bytes(raw)
        with zipfile.ZipFile(folder / "export.zip", "w") as archive:
            archive.writestr("source.xmi", raw)
            archive.writestr("TypeSystem.xml", types)
        for name in ("raw.xmi", "export.zip"):
            command = [sys.executable, "-m", "scripts.prospectus_integration_codec", "admit",
                       str(envelope), str(folder / name), str(folder / (name + ".json"))]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            rows[name] = {"command": command, "returncode": run.returncode,
                          "last_error": run.stderr.splitlines()[-1] if run.stderr else None,
                          "output_written": (folder / (name + ".json")).exists()}
    output = Path(__file__).with_name("codec-results.json")
    if output.exists():
        raise ValueError("Preserve prior codec probe")
    record = {"command": [sys.executable, *sys.argv], "git_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "environment": sys.executable,
        "cassis": importlib.metadata.version("dkpro-cassis"), "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
        "random_seeds": "N/A deterministic", "data_version": "Synthetic empty CAS from current draft schema",
        "plan": "docs/plans/prospectus-package-integration-audit-2026-10-08.md",
        "result_file": str(output.relative_to(ROOT)), "wall_seconds": time.monotonic() - started,
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "results": rows}
    write(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
