"""Bounded work for the reviewed closure refresh; no network operations."""
from scripts import prospectus_refresh as m
import json, shutil, subprocess
S1 = "docs/implementation/prospectus-evidence-closure/phases/S1/attempt-007/inventory.json"
S2 = "docs/implementation/prospectus-evidence-closure/phases/S2/attempt-017/recovery-inspection.json"
S4 = "docs/implementation/prospectus-evidence-closure/phases/S4/attempt-004/clause-groups.json"
OLD = "docs/implementation/prospectus-corner-repair-2026-10-04"
BASF = "basf-base-september-2022-exchange"
SUPPLEMENT = "basf-supplement-february-2023-exchange"
ANNUAL = "basf-annual-2022-exchange"
def sources():
    original = m.read(m.ROOT / S1)["documents"]
    recovered = {r["key"]: r["document"] for r in m.read(m.ROOT / S2) if "document" in r}
    return {k: original[k] for k in ("basf-2032-final", "deutsche-at1-2025")} | {
        k: recovered[k] for k in (BASF, SUPPLEMENT, ANNUAL)}
def inputs(phase):
    paths = [S1, S2, S4]
    for doc in sources().values():
        paths.extend([doc["original"], doc["text"]])
        if doc.get("acquisition_receipt"):
            paths.append(doc["acquisition_receipt"])
    if phase in {"checks", "admit", "document", "verify"}:
        if (m.OUT / "source-review.json").exists():
            paths.append(m.relative(m.OUT / "source-review.json"))
    if phase == "verify":
        paths.append(m.relative(m.OUT / "rendered-review.json"))
    return {p: m.sha(m.ROOT / p) for p in paths}
def baseline(folder):
    prior = m.read(m.PRIOR / "run-manifest.json")
    files = {m.relative(m.PRIOR / "run-manifest.json"): m.sha(m.PRIOR / "run-manifest.json"),
             prior["plan"]: prior["plan_sha256"]}
    for kind in ("method", "data", "artifacts"):
        files.update(prior[kind])
    for path in (m.PRIOR / "phases").rglob("*"):
        if path.is_file():
            files[m.relative(path)] = m.sha(path)
    old = m.read(m.ROOT / OLD / "run-manifest.json")
    files[m.relative(m.ROOT / OLD / "run-manifest.json")] = m.sha(m.ROOT / OLD / "run-manifest.json")
    for kind in ("orchestration", "inputs", "artifacts"):
        files.update(old[kind])
    files.update({OLD + "/candidate/" + k: v for k, v in old["candidate_method"].items()})
    earlier = m.read(m.ROOT / "docs/implementation/prospectus-evidence-closure/baseline.json")
    files.update(earlier["files"])
    m.verify_bindings(files)
    for doc in sources().values():
        m.require(m.sha(m.ROOT / doc["original"]) == doc["sha256"], "Source identity failed")
        m.require(m.sha(m.ROOT / doc["text"]) == doc["text_sha256"], "Extraction identity failed")
    tools = {}
    for name in ("pdftotext", "pdftoppm", "pdfinfo", "latexmk"):
        tools[name] = shutil.which(name)
        m.require(tools[name] is not None, "Required tool missing: " + name)
    for name in ("pdftotext", "pdftoppm", "pdfinfo"):
        run = subprocess.run([tools[name], "-v"], capture_output=True, text=True, timeout=15)
        tools[name + "_version"] = (run.stdout + run.stderr).strip()
    m.write(folder / "baseline.json", {"files": files, "verified_count": len(files),
        "prior_manifest": m.relative(m.PRIOR / "run-manifest.json"), "sources": sources(),
        "tools": tools, "requests": {"used": 188, "limit": 212, "remaining": 24},
        "independent_legal_reviews": 0, "production_promotion": False})
def prepare(folder):
    docs = sources()
    render = {"basf-2032-final": [2, 3, 5, 6, 7],
              BASF: [110, 111, 112, 113, 114, 132, 133],
              SUPPLEMENT: [1, 2], "deutsche-at1-2025": [36, 37, 38]}
    manifest = []
    for key, pages in render.items():
        doc = docs[key]
        for page in pages:
            stem = key + "-" + str(page)
            image = folder / (stem + ".png")
            m.run_command(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile",
                           "-scale-to", "1500", "-png", str(m.ROOT / doc["original"]),
                           str(folder / stem)], folder, stem + "-render", timeout=45)
            row = {"document": key, "page": page, "source_sha256": doc["sha256"],
                   "image": m.relative(image), "image_sha256": m.sha(image)}
            if key == "deutsche-at1-2025":
                path = folder / (stem + ".xhtml")
                m.run_command(["pdftotext", "-f", str(page), "-l", str(page), "-bbox-layout",
                               str(m.ROOT / doc["original"]), str(path)], folder, stem + "-bbox", timeout=45)
                row.update(bbox=m.relative(path), bbox_sha256=m.sha(path))
            manifest.append(row)
    m.write(folder / "prepared.json", manifest)
def checks(folder):
    from scripts.prospectus_refresh_admission import review
    review()
    m.run_command([str(m.ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
                   "tests/closure_refresh", "tests/closure_next",
                   "--junitxml=" + str(folder / "tests.xml")], folder, "tests", timeout=240)
def admit(folder):
    m.latest("checks", current=True)
    from scripts.prospectus_refresh_admission import run
    run(folder)
def document(folder):
    m.latest("admit", current=True)
    from scripts.prospectus_refresh_document import run
    run(folder)
def verify(folder):
    from scripts.prospectus_refresh_document import verify_result
    verify_result(folder)
