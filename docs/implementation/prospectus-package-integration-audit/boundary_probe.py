"""Follow-up checks of fresh intake versus persisted-product consumption."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audit_probe", HERE / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.contracts import digest, write


def main():
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="prospectus-boundary-audit-") as temp:
        folder = Path(temp)
        req = probe.request(folder, [probe.PREFIX])
        raw = {"source_sha256": req["bundle"]["documents"][0]["sha256"], "page_count": 1,
               "runtime": {"dpi": 300, "language": "eng"},
               "pages": [{"page": 1, "text": probe.PREFIX, "words": []}]}
        path = folder / "ocr.json"
        write(path, raw)
        req["bundle"]["documents"][0]["ocr"] = {"path": "ocr.json", "sha256": digest(path.read_bytes())}
        req.pop("assembly")
        p1 = service.source_product(req, folder)
        p2 = service.construction_product(p1, folder)
        p3 = service.interpretation_product(p1, p2)
        products = {"P1": p1, "P2": p2, "P3": p3,
                    "P4": service.law_product(p1, p3), "P5": service.financial_product(p1, p2, p3)}
        original = service.consume(products, folder)
        raw["pages"][0]["text"] = "Corrected raw extraction that invalidates the old declared OCR hash."
        write(path, raw)
        replay = service.consume(products, folder)
        fresh = probe.outcome(lambda: service.source_product(req, folder))
        with patch.object(source_graph.subprocess, "run", side_effect=FileNotFoundError("pdftotext")):
            missing = probe.outcome(lambda: source_graph.pdf_units(folder / "source.txt", req["bundle"]["documents"][0]))
        result = {"original_status": original["questions"]["Q1"]["status"],
                  "changed_ocr_stored_product_replay_identical": replay == original,
                  "fresh_intake_after_ocr_change": fresh, "missing_poppler_error_path": missing}
    output = HERE / "boundary-results.json"
    if output.exists():
        raise ValueError("Preserve prior boundary evidence")
    record = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=probe.ROOT, text=True).strip(),
              "command": [sys.executable, *sys.argv], "environment": sys.executable,
              "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1 inherited from probe before imports",
              "data_version": "Synthetic OCR derivative; mocked missing-binary error", "random_seeds": "N/A deterministic",
              "wall_seconds": time.monotonic() - started,
              "plan": "docs/plans/prospectus-package-integration-audit-2026-10-08.md",
              "result_file": str(output.relative_to(probe.ROOT)),
              "method": {p.name: digest(p.read_bytes()) for p in (HERE / "probe.py", Path(__file__))},
              "results": result}
    write(output, record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
