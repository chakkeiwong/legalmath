"""Preserve closure receipts and refresh the executable next step."""
import shutil
from scripts import run_prospectus_closure_next as m

NEXT = {
    "tools": ("inventory", "Bind the retained BES source identities."),
    "inventory": ("language", "Qualify the installed CPU OCR engine and language data."),
    "language": ("smoke", "Check one page before processing the retained scans."),
    "smoke": ("ocr", "Process the remaining pages with the qualified runtime."),
    "ocr": ("review", "Review rendered material terms before admitting any derivative."),
    "review": ("validate", "Replay provenance and compare the seven reader inputs."),
    "validate": ("dossiers", "Trace incorporation, scope and precedence in the retained sources."),
    "checks": ("validate", "Use the passing intake checks to admit reviewed derivatives and verify the reader comparison."),
    "dossiers": ("repairs", "Run source-supported conditional repairs and adverse tests."),
    "repairs": ("packet", "Prepare independent review records and an unseen-validation protocol."),
    "packet": ("document", "Build the source-based addendum and inspect every rendered page."),
    "document": ("verify", "Record rendered-page inspection, then verify current results and preserved historical evidence."),
    "verify": (None, "See REPORT.md and the independent-review packet for remaining source and human dependencies."),
}
def verify_history():
    checked = 0
    for path in sorted((m.OUT/"phases").glob("*/receipt.json")):
        receipt = m.read(path)
        for name, digest in receipt.get("outputs", {}).items():
            if m.sha(path.parent/name) != digest:
                raise ValueError("Prior phase output changed: " + str(path.parent/name))
        for name, digest in receipt.get("data", {}).items():
            if m.sha(m.ROOT/name) != digest:
                raise ValueError("Prior source/derivative changed: " + name)
        checked += 1
    return checked

def snapshot(folder, name):
    target = folder/name
    target.mkdir()
    for source in sorted(m.OUT.iterdir()):
        if source.name in {"phases", ".lock", "NEXT-PHASE.md", "__pycache__"}:
            continue
        if source.is_file():
            shutil.copyfile(source, target/source.name)
        elif source.is_dir():
            shutil.copytree(source, target/source.name)
    return target

def method_snapshot(folder):
    paths = sorted((m.ROOT/"scripts").glob("prospectus_closure_*.py"))
    paths += [m.ROOT/"scripts/run_prospectus_closure_next.py", m.ROOT/"scripts/prospectus_reviewed_extraction.py"]
    paths += sorted((m.ROOT/"tests/closure_next").glob("*.py"))
    paths += [m.ROOT/"docs/plans/prospectus-closure-execution-2026-10-05.md"]
    result = {}
    for path in paths:
        relative = path.relative_to(m.ROOT)
        destination = folder/"method"/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        result[str(relative)] = m.sha(path)
    return result

def refresh(folder, receipt):
    phase, status = receipt["phase"], receipt["status"]
    following, action = NEXT.get(phase, (None, "Review the recorded result before selecting the next phase."))
    if status != "PASS":
        following = phase
        action = "Repair the recorded execution error, review the repair, then rerun this phase. The failed receipt remains preserved."
    command = (".venv/bin/python scripts/run_prospectus_closure_next.py " + following) if following else None
    text = "# Next phase\n\nLast: " + phase + " — " + status + "\n\n"
    text += "Receipt: " + str((folder/"receipt.json").relative_to(m.ROOT)) + "\n\n" + action + "\n"
    if command:
        text += "\nCommand: `" + command + "`\n"
    text += "\nIndependent source adjudication, complete operative documents, actual investigation facts and intended-use acceptance remain separate promotion requirements. Failures trigger repair unless an integrity or budget veto fires.\n"
    (m.OUT/"NEXT-PHASE.md").write_text(text)
