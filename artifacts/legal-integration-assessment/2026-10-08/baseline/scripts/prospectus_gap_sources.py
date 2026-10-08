"""Seal source-based issue selection before executing the frozen reader."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/"docs/prospectus/gap-closure"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")

def register(proposal):
    spec = json.loads(Path(proposal).read_text())
    freeze = ROOT/spec["freeze"]
    frozen = json.loads(freeze.read_text())
    for path, value in frozen["files"].items():
        if sha(ROOT/path) != value: raise ValueError("Method changed since source challenge freeze: "+path)
    folder = DATA/spec["name"]; folder.mkdir(exist_ok=False)
    docs = {}
    for selected in spec["sources"]:
        receipt_path = ROOT/selected["receipt"]
        receipt = json.loads(receipt_path.read_text())
        original = ROOT/receipt["path"]
        if not receipt["retained"] or sha(original) != receipt["sha256"]:
            raise ValueError("Missing or changed acquired document")
        if receipt.get("content_kind") != "pdf": raise ValueError("Fresh source is not a retained PDF")
        reader = PdfReader(original)
        key = selected["id"]
        text_path = folder/(key+".json")
        text = {"id": key, "source_sha256": receipt["sha256"], "pages": [
            {"page": i+1, "text": page.extract_text() or ""} for i, page in enumerate(reader.pages)],
            "preliminary_indicator": False, "extraction": "pypdf; no OCR or legal equivalence claim"}
        write(text_path, text)
        docs[key] = {"id": key, "original": receipt["path"], "text": str(text_path.relative_to(ROOT)),
            "sha256": receipt["sha256"], "text_sha256": sha(text_path), "pages": len(reader.pages),
            "url": receipt["url"], "identity_markers": selected.get("identity_markers", [])}
    for issue in spec["issues"]:
        if set(issue) & {"expected_answer", "expected_answers", "answer", "quality"}:
            raise ValueError("No answer or quality labels allowed")
        issue["data_role"] = "fresh-family-frozen-challenge"
    inventory = {"documents": docs, "issues": spec["issues"],
        "scope": "Dated selected public offering terms. Other contracts, amendments and current legal eligibility remain qualified.",
        "freeze": spec["freeze"], "acquisition_selection": spec["selection_basis"]}
    write(folder/"issue-inventory.json", inventory)
    write(folder/"registration.json", {"at": datetime.now(timezone.utc).isoformat(),
        "proposal_sha256": sha(Path(proposal)), "freeze_sha256": sha(freeze),
        "inventory_sha256": sha(folder/"issue-inventory.json"), "selection_basis": spec["selection_basis"],
        "classified": False, "method_changed_after_document_inspection": False})
    print(folder/"issue-inventory.json")
