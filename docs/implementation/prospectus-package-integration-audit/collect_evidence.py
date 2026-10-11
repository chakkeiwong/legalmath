"""Record audit source identities and package call sites without running packages."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PACKAGES = {"docling", "QuantLib", "cassis", "fitz", "pypdf", "research_assistant",
            "z3", "hypothesis", "pydantic", "jsonschema", "playwright"}


def main():
    paths = list((ROOT / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += list((ROOT / "tests/prospectus_successor").glob("*.py"))
    paths += list((ROOT / "tests/prospectus_integration").glob("*.py"))
    paths += list((ROOT / "tests/prospectus_inception").glob("*.py"))
    scripts = ("prospectus_adoption_sidecar.py", "prospectus_adoption_tools.py",
               "prospectus_adoption_survey.py", "prospectus_integration_repair.py",
               "prospectus_integration_jobs.py", "prospectus_integration_authoring.py",
               "prospectus_integration_codec.py", "prospectus_tool_feasibility.py",
               "prospectus_inception.py", "prospectus_closure_pdf_worker.py",
               "prospectus_reviewed_extraction.py", "run_prospectus_closure_next.py",
               "verify_prospectus_adoption.py", "prospectus_delivery.py")
    paths += [ROOT / "scripts" / n for n in scripts]
    names = ["pyproject.toml", "requirements-dev.lock", "scripts/fresh_install.sh",
             "src/legalmath/cli.py", "src/legalmath/transaction/engine.py",
             "src/legalmath/prospectus/eligibility.py", "src/legalmath/prospectus/models.py",
             "src/legalmath/prospectus/checks.py", "src/legalmath/prospectus/InstrumentArithmetic.lean",
             "src/legalmath/prospectus/Prospectus.lean",
             "src/legalmath/prospectus/successor/basf_scope_review.json",
             "docs/research/prospectus-adoption-2026-10-07/SURVEY.md",
             "docs/plans/prospectus-adoption-program-2026-10-07.md",
             "docs/implementation/prospectus-adoption/state.json",
             "docs/implementation/prospectus-adoption/verification/attempt-007/manifest.json",
             "docs/implementation/prospectus-adoption/phases/A3/attempt-008/critical-span-results.json",
             "docs/implementation/prospectus-adoption/phases/A4/attempt-008/comparison.json",
             "docs/implementation/prospectus-adoption/phases/A6/attempt-008/product.json",
             "docs/implementation/prospectus-integration-repair/authoring-011/result.json",
             "docs/implementation/prospectus-integration-repair/feasibility-006/deferred-tool-decisions.json",
             "docs/implementation/prospectus-integration-repair/official-sources/cdm-python-readme.txt",
             "docs/implementation/prospectus-integration-repair/official-sources/actus-python-architecture.txt"]
    paths += [ROOT / n for n in names]
    imports, hashes = {}, {}
    for path in sorted(set(paths)):
        relative = str(path.relative_to(ROOT))
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([node.module or ""] if isinstance(node, ast.ImportFrom) else
                       [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                package = module.split(".")[0]
                if package in PACKAGES:
                    imports.setdefault(package, []).append({"path": relative, "line": node.lineno, "module": module})
    result = {"baseline": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "command": [sys.executable, *sys.argv],
              "scope": "Static call-site inventory and selected source hashes; not a package or runtime execution",
              "files": hashes, "package_imports": imports,
              "executables_found_without_running": {n: shutil.which(n) for n in ("pdftotext", "pdfinfo", "tesseract")},
              "paths_present_without_running": {p: Path(p).exists() for p in (
                  "/tmp/prospectus-adoption-tools/bin/python", "/tmp/prospectus-adoption-models",
                  "/home/chakwong/python/ResearchAssistant",
                  "/home/chakwong/miniconda3/envs/tfgpu/bin/python",
                  "/home/chakwong/python/legalmath/.localresources/browser/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell")}}
    target = HERE / "evidence-index.json"
    if target.exists():
        raise ValueError("Preserve prior evidence index")
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files_bound": len(hashes), "packages_with_imports": sorted(imports), "output": str(target)}, indent=2))


if __name__ == "__main__":
    main()
