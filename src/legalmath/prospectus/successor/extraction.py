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


def scan_profile(document, root, *, hybrid=False):
    profile = document["hybrid_profile" if hybrid else "scan_profile"]
    keys = {"version", "dpi", "language", "max_pages", "tessdata", "models"}
    optional_geometry = hybrid and profile.get("version") == "pymupdf-hybrid.v2"
    if hybrid:
        keys |= {"page_count", "pages"}
    if optional_geometry:
        keys.add("geometry_policy")
    fields(profile, keys, keys)
    version = ("pymupdf-hybrid.v2" if optional_geometry else
               "pymupdf-hybrid.v1" if hybrid else "pymupdf-scan.v1")
    if optional_geometry and profile["geometry_policy"] != "preserve-text-without-invalid-box.v1":
        raise ValueError("Unsupported optional OCR geometry policy")
    if (profile["version"] != version or profile["dpi"] != 300 or
            type(profile["max_pages"]) is not int or not 1 <= profile["max_pages"] <= 20 or
            not isinstance(profile["language"], str) or
            not re.fullmatch(r"[a-z]{3}(?:\+[a-z]{3})*", profile["language"])):
        raise ValueError("Unsupported bounded scan profile")
    if hybrid:
        count, pages = profile["page_count"], profile["pages"]
        if (type(count) is not int or count <= 0 or
                document.get("page_count", count) != count or not isinstance(pages, list) or
                not 1 <= len(pages) <= profile["max_pages"] or
                any(type(p) is not int or not 1 <= p <= count for p in pages) or
                pages != sorted(set(pages))):
            raise ValueError("Hybrid pages must be an ordered unique bounded original-page selection")
    models = profile["language"].split("+")
    if (not isinstance(profile["models"], dict) or set(profile["models"]) != set(models) or
            any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
                for value in profile["models"].values())):
        raise ValueError("Every requested OCR language requires a pinned model")
    tessdata = bound_path(root, profile["tessdata"])
    for language in models:
        try:
            path = bound_path(root, tessdata / (language + ".traineddata"))
        except ValueError as exc:
            raise ExtractionUnavailable("OCR language model outside declared root: " + language) from exc
        if not path.is_file() or digest(path.read_bytes()) != profile["models"][language]:
            raise ExtractionUnavailable("OCR language model missing or changed: " + language)
    return profile, tessdata


def scan(document, root, *, hybrid=False):
    from .sealed_source import current, worker_inputs
    profile, tessdata = scan_profile(document, root, hybrid=hybrid)
    interpreter = Path(os.environ.get("LEGALMATH_OCR_PYTHON", str(Path(root) / ".localresources/prospectus/ocr/bin/python")))
    if not interpreter.is_file():
        raise ExtractionUnavailable("Configure LEGALMATH_OCR_PYTHON with the reviewed CPU OCR environment")
    worker = Path(__file__).with_name("ocr_worker.py")
    spec = {**{k: profile[k] for k in ("dpi", "language", "max_pages")},
            "source": str(bound_path(root, document["path"])), "tessdata": str(tessdata)}
    if hybrid:
        spec.update(selected_pages=profile["pages"], page_count=profile["page_count"],
                    source_sha256=document["sha256"])
    receipt = None
    try:
        runtime = current()
        if runtime is None:
            run = subprocess.run([str(interpreter), str(worker)], input=json.dumps(spec), text=True,
                capture_output=True, timeout=300, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "OMP_THREAD_LIMIT": "1"})
        else:
            argv = [str(interpreter), str(worker)]
            result = runtime.execute(argv, json.dumps(spec).encode(), worker_inputs(interpreter, worker, spec, profile))
            run = subprocess.CompletedProcess(argv, result['returncode'], result['stdout'].decode(), result['stderr'].decode())
            receipt = result['receipt']
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionUnavailable("OCR runtime unavailable or exceeded the 300-second bound") from exc
    if run.returncode:
        raise ExtractionUnavailable("OCR worker failed: " + run.stderr[-1500:])
    data = json.loads(run.stdout)
    data["runtime"].update(interpreter_sha256=digest(interpreter.read_bytes()),
        worker_sha256=digest(worker.read_bytes()), language_models=profile["models"],
        dependency_assurance="DECLARED_INPUTS; native read coverage not confined")
    if receipt:
        data['runtime'].update(sealed_execution=receipt,
            dependency_assurance='SEALED_EXPLICIT_NATIVE_FILES; kernel/proc/dev trusted; reuse disabled')
    return data


def verify_hybrid_images(document, root, data):
    """Rerender retained page images from the bound original without OCR."""
    from .sealed_source import current, worker_inputs
    profile, tessdata = scan_profile(document, root, hybrid=True)
    interpreter = Path(os.environ.get("LEGALMATH_OCR_PYTHON", str(Path(root) / ".localresources/prospectus/ocr/bin/python")))
    if not interpreter.is_file():
        raise ExtractionUnavailable("Configure LEGALMATH_OCR_PYTHON with the reviewed CPU OCR environment")
    worker = Path(__file__).with_name("ocr_worker.py")
    spec = {"source":str(bound_path(root, document["path"])),
            "source_sha256":document["sha256"], "page_count":profile["page_count"],
            "selected_pages":profile["pages"], "max_pages":profile["max_pages"],
            "dpi":profile["dpi"], "language":profile["language"],
            "tessdata":str(tessdata), "verify_images_only":True}
    receipt = None
    try:
        runtime = current()
        if runtime is None:
            run = subprocess.run([str(interpreter),str(worker)], input=json.dumps(spec),text=True,
                capture_output=True,timeout=90,
                env={**os.environ,"CUDA_VISIBLE_DEVICES":"-1","OMP_THREAD_LIMIT":"1"})
        else:
            argv = [str(interpreter), str(worker)]
            result = runtime.execute(argv, json.dumps(spec).encode(), worker_inputs(interpreter, worker, spec, profile))
            run = subprocess.CompletedProcess(argv, result['returncode'], result['stdout'].decode(), result['stderr'].decode())
            receipt = result['receipt']
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ExtractionUnavailable("Hybrid image verification unavailable or timed out") from exc
    if run.returncode:
        raise ExtractionUnavailable("Hybrid image verification failed: "+run.stderr[-1500:])
    verified=json.loads(run.stdout)
    if (verified.get('source_sha256')!=document['sha256'] or
            verified.get('page_count')!=profile['page_count'] or
            verified.get('selected_pages')!=profile['pages'] or
            not verified.get('verification_only') or
            [{k:p.get(k) for k in ('page','image_sha256','image_width','image_height','width_points','height_points')}
             for p in verified['pages']] !=
            [{k:p.get(k) for k in ('page','image_sha256','image_width','image_height','width_points','height_points')}
             for p in data['pages']]):
        raise ValueError("Retained hybrid page images differ from the bound original")
    if receipt:
        verified['runtime']['sealed_execution'] = receipt
    return {"verified_image_pages":profile['pages'],
            "verification_worker_sha256":digest(worker.read_bytes()),
            "verification_interpreter_sha256":digest(interpreter.read_bytes()),
            "verification_runtime":verified['runtime']}
