"""Explicit optional scan runtime; no package installation on assessment."""
import json
import os
from pathlib import Path
import re
import subprocess
from .anchors import fields
from .contracts import bound_path, digest


class ExtractionUnavailable(ValueError):
    """An optional extraction capability cannot execute under its profile."""


def scan(document, root):
    profile = document["scan_profile"]
    fields(profile, {"version", "dpi", "language", "max_pages", "tessdata", "models"},
           {"version", "dpi", "language", "max_pages", "tessdata", "models"})
    if (profile["version"] != "pymupdf-scan.v1" or profile["dpi"] != 300 or
            type(profile["max_pages"]) is not int or not 1 <= profile["max_pages"] <= 20 or
            not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3})*", profile["language"])):
        raise ValueError("Unsupported bounded scan profile")
    models = profile["language"].split("+")
    if set(profile["models"]) != set(models):
        raise ValueError("Every requested OCR language requires a pinned model")
    tessdata = bound_path(root, profile["tessdata"])
    for language in models:
        path = tessdata / (language + ".traineddata")
        if not path.is_file() or digest(path.read_bytes()) != profile["models"][language]:
            raise ExtractionUnavailable("OCR language model missing or changed: " + language)
    interpreter = Path(os.environ.get("LEGALMATH_OCR_PYTHON", str(Path(root) / ".localresources/prospectus/ocr/bin/python")))
    if not interpreter.is_file():
        raise ExtractionUnavailable("Configure LEGALMATH_OCR_PYTHON with the reviewed CPU OCR environment")
    worker = Path(__file__).with_name("ocr_worker.py")
    spec = {**{k: profile[k] for k in ("dpi", "language", "max_pages")},
            "source": str(bound_path(root, document["path"])), "tessdata": str(tessdata)}
    try:
        run = subprocess.run([str(interpreter), str(worker)], input=json.dumps(spec), text=True,
            capture_output=True, timeout=300, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "OMP_THREAD_LIMIT": "1"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionUnavailable("OCR runtime unavailable or exceeded the 300-second bound") from exc
    if run.returncode:
        raise ExtractionUnavailable("OCR worker failed: " + run.stderr[-1500:])
    data = json.loads(run.stdout)
    data["runtime"].update(interpreter_sha256=digest(interpreter.read_bytes()),
        worker_sha256=digest(worker.read_bytes()), language_models=profile["models"],
        dependency_assurance="DECLARED_INPUTS; native read coverage not confined")
    return data
