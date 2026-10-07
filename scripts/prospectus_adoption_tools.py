"""Fixed, isolated, CPU-only tool setup for the reviewed adoption trial."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ENV = Path("/tmp/prospectus-adoption-tools")
OUT = ROOT / "docs/implementation/prospectus-adoption/tool-setup"


def setup():
    OUT.mkdir(parents=True, exist_ok=True)
    attempts = sorted(OUT.glob("attempt-*"))
    if len(attempts) >= 3:
        raise ValueError("Tool setup attempt cap reached; revise the recorded plan")
    folder = OUT / f"attempt-{len(attempts)+1:03d}"
    folder.mkdir()
    start = time.monotonic()
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    commands = [
        [str(ROOT / ".venv/bin/python"), "-m", "venv", str(ENV)],
        [str(ENV / "bin/python"), "-m", "pip", "install", "--no-cache-dir", "--retries", "1", "--timeout", "30",
         "--index-url", "https://download.pytorch.org/whl/cpu", "torch==2.9.0", "torchvision==0.24.0"],
        [str(ENV / "bin/python"), "-m", "pip", "install", "--no-cache-dir", "--retries", "1", "--timeout", "30",
         "--report", str(folder / "pip-report.json"), "docling==2.60.1", "QuantLib==1.38", "dkpro-cassis==0.10.1"],
        [str(ENV / "bin/python"), "-m", "pip", "freeze"],
    ]
    records = []
    try:
        for i, command in enumerate(commands):
            remaining = 900 - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError("Tool setup time budget exhausted")
            run = subprocess.run(command, env=env, cwd=ROOT, capture_output=True, timeout=remaining)
            (folder / f"command-{i}.log").write_bytes(run.stdout + run.stderr)
            records.append({"argv": command, "returncode": run.returncode})
            if run.returncode:
                raise RuntimeError("Tool setup failed; inspect preserved command log")
        size = sum(p.stat().st_size for p in ENV.rglob("*") if p.is_file() and not p.is_symlink())
        if size > 3_000_000_000:
            raise ValueError("3 GB sidecar/model storage cap exceeded; model execution vetoed")
        # Bind matched release source/docs. These are feasibility sources, not
        # a claim of having run the INCEpTION server or read independent labels.
        resources = {
            "inception-38-pom.xml": "https://raw.githubusercontent.com/inception-project/inception/inception-38.0/pom.xml",
            "inception-38-offsets.ts": "https://raw.githubusercontent.com/inception-project/inception/inception-38.0/inception/inception-js-api/src/main/ts/src/util/OffsetUtils.ts",
            "docling-model.json": "https://huggingface.co/api/models/docling-project/docling-models",
        }
        sources = []
        for name, url in resources.items():
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    raw = response.read(8_000_000)
                (folder / name).write_bytes(raw)
                sources.append({"name": name, "url": url, "sha256": hashlib.sha256(raw).hexdigest()})
            except Exception as exc:
                sources.append({"name": name, "url": url, "error": str(exc)})
        result = {"status": "INSTALLED", "environment": str(ENV), "bytes": size, "resources": sources}
    except Exception as exc:
        result = {"status": "FAILED", "error": str(exc)}
    result.update(commands=records, wall_seconds=time.monotonic()-start, cpu_gpu="CPU; CUDA_VISIBLE_DEVICES=-1",
                  plan="docs/plans/prospectus-adoption-execution-2026-10-07.md")
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({**result, "directory": str(folder)}, indent=2))
    if result["status"] != "INSTALLED":
        raise SystemExit(1)


def models():
    """Only the layout model; OCR/table/VLM downloads are disabled in the trial."""
    model_dir = Path("/tmp/prospectus-adoption-models/ds4sd--docling-layout-old")
    folder = OUT / "layout-model"
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "receipt.json").exists():
        raise ValueError("Model receipt exists; verify/reuse instead of overwriting")
    start = time.monotonic()
    with urllib.request.urlopen("https://huggingface.co/api/models/ds4sd/docling-layout-old", timeout=30) as response:
        metadata_raw = response.read()
    metadata = json.loads(metadata_raw)
    revision = metadata["sha"]
    (folder / "metadata.json").write_bytes(metadata_raw)
    model_dir.mkdir(parents=True, exist_ok=True)
    records = []
    try:
        for name in ("README.md", "config.json", "preprocessor_config.json", "model.safetensors"):
            url = "https://huggingface.co/ds4sd/docling-layout-old/resolve/" + revision + "/" + name
            target = model_dir / name
            sha = hashlib.sha256()
            count = 0
            with urllib.request.urlopen(url, timeout=90) as response, target.open("xb") as stream:
                while chunk := response.read(1024*1024):
                    count += len(chunk)
                    if count > 800_000_000 or time.monotonic()-start > 900:
                        raise ValueError("Model download resource bound exceeded")
                    stream.write(chunk)
                    sha.update(chunk)
            records.append({"file": str(target), "sha256": sha.hexdigest(), "bytes": count, "url": url})
        size = sum(p.stat().st_size for base in (ENV, model_dir) for p in base.rglob("*") if p.is_file() and not p.is_symlink())
        if size > 3_000_000_000:
            raise ValueError("Sidecar plus models exceed 3 GB")
        result = {"status": "DOWNLOADED_NOT_YET_EVALUATED", "repository": metadata["id"], "revision": revision,
                  "files": records, "total_sidecar_model_bytes": size}
    except Exception as exc:
        result = {"status": "FAILED", "error": str(exc), "files": records}
    result["wall_seconds"] = time.monotonic()-start
    (folder / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] == "FAILED":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "models"])
    args = parser.parse_args()
    (setup if args.command == "setup" else models)()
