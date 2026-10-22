"""Prepare source identities for the optional BASF agent-introduction review."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import signal
import sys
import time
from scripts import prospectus_basf_default_source as old
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger

ROOT, BASE = old.ROOT, old.BASE
HERE = BASE / "basf-meanings/attempt-014"
PRIOR = BASE / "basf-meanings/attempt-013"
PLAN = "docs/plans/prospectus-basf-agent-introduction-2026-10-15.md"
old.HERE, old.PRIOR, old.PLAN = HERE, PRIOR, PLAN
old.old.HERE, old.old.PRIOR, old.old.PLAN = HERE, PRIOR, PLAN
old.old.base.HERE, old.old.base.PRIOR, old.old.base.PLAN = HERE, PRIOR, PLAN
save, load, bindings = old.save, old.load, old.bindings


def prepare():
    protected = {str((PRIOR / p).relative_to(ROOT)): h for p, h in read(PRIOR / "outputs.json").items()}
    protected[str((PRIOR / "outputs.json").relative_to(ROOT))] = file_hash(PRIOR / "outputs.json")
    assert all(file_hash(ROOT / p) == h for p, h in protected.items())
    save("protected-inputs.json", protected)
    names = [Path(__file__), ROOT / "src/legalmath/prospectus/basf_agent_introduction.py",
             ROOT / PLAN, HERE / "EXECUTION-AUDIT.md", Path(process_ledger.__file__)]
    save("source-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in names})
    for p in names:
        target = HERE / "source-methods" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    shutil.copyfile(PRIOR / "products.json.gz", HERE / "products.json.gz")
    shutil.copyfile(PRIOR / "default-consumer.json.gz", HERE / "prior-consumer.json.gz")
    sources = read(PRIOR / "original-sources.json")
    image_root = ROOT / "docs/implementation/prospectus-basf-scope-repair/source-review-001"
    by_doc = {s["document"]: s for s in sources}
    base = by_doc["basf-base-september-2022-exchange"]
    base["images"] += [
        {"page": page, "path": str((image_root / f"base-{page}.png").relative_to(ROOT)),
         "sha256": file_hash(image_root / f"base-{page}.png")} for page in (123, 124)]
    save("original-sources.json", list(by_doc.values()))
    products = load(HERE / "products.json.gz")
    save("source-page-units.json", [u for u in products["P1"]["payload"]["graph"]["units"]
                                    if (u["document"] == "basf-base-september-2022-exchange" and u["page"] in (123, 124))
                                    or (u["document"] == "basf-2032-final" and u["page"] == 7)])
    process_ledger.create(HERE / "command-ledger.json", 5, 0,
                          "Offline build,install,answer replay,control replay;one repair spare")
    return {"source_documents": 2, "retained_original_pages": [7, 82, 123, 124, 126, 127, 133],
            "native_calls": 0, "http_calls": 0}


def main():
    assert sys.argv[1:] == ["prepare"]
    ad = bindings(); folder = HERE / "invocations/prepare"; folder.mkdir(parents=True, exist_ok=False)
    save("invocations/prepare/started.json", {
        "command": [".venv/bin/python", "-m", "scripts.prospectus_agent_intro_source", "prepare"],
        "git_commit": ad["git_commit"], "plan": PLAN, "environment": sys.executable,
        "started_at": datetime.now(timezone.utc).isoformat(), "random_seeds": "N/A deterministic",
        "cpu_gpu": "CPU only;no framework imports"})
    tick = time.monotonic()
    def expire(signum, frame): raise TimeoutError("120-second source-stage bound")
    signal.signal(signal.SIGALRM, expire); signal.alarm(120)
    try:
        details = prepare(); bindings(); result = {"status": "PASS", "details": details, "wall_seconds": time.monotonic() - tick}
    except BaseException as error:
        save("invocations/prepare/result.json", {"status": "FAIL", "error": repr(error), "wall_seconds": time.monotonic() - tick}); raise
    finally: signal.alarm(0)
    save("invocations/prepare/result.json", result); print(result)


if __name__ == "__main__": main()
