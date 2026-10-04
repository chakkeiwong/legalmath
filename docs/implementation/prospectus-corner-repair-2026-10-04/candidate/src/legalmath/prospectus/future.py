"""Prospective source observations bound to the complete interpretation method.

An observation records checked preservation/quotation properties and qualified
candidate conclusions. It never converts those properties into legal accuracy.
"""
from pathlib import Path
import re
import shutil

from ..qualification import assurance, prospective
from . import archive, evidence
from .common import PLAN, PROGRAM, ROOT, RUNS, digest, now, read, relative, sha, write

QUESTION = "SFC product classification/selling rules and SPI streamlining eligibility under explicit premises"


def method_identity():
    from .legal_review import dossier_files
    files = sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(__file__).parent.glob("*.lean"))
    files += [ROOT / "scripts/prospectus_master.py", ROOT / "pyproject.toml", PLAN, PROGRAM / "allowlist.json"]
    files += dossier_files(ROOT)
    preflight = read(PROGRAM / "preflight.json")
    return {"files": {relative(p): sha(p.read_bytes()) for p in files},
            "backends": assurance.method_manifest(),
            "tool_versions": {k: v for k, v in preflight.items() if k not in ("sources", "policy")}}


def observe(directory, expected_hash, row, metadata, *, method_hash=None, root=archive.ARCHIVE):
    """Use only fixed catalogue documents; metadata carries chronology, no grades."""
    required = {"task_id", "family", "published_at", "first_seen_at"}
    if set(metadata) != required or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,100}", metadata["task_id"]):
        raise ValueError("Only source chronology and task identity are accepted; quality labels are forbidden")
    method_hash = method_hash or digest(method_identity())
    root = Path(root)
    manifest = read(root / "manifest.json")
    entry = manifest["documents"][row["id"]]
    source = root / entry["file"]
    if sha(source.read_bytes()) != entry["sha256"]:
        raise ValueError("Prospective original changed")
    item = {**metadata, "source_hash": entry["sha256"], "question_hash": digest(QUESTION)}
    directory = Path(directory)
    # Selection occurs before extraction; all rejections are preserved by the ledger.
    spec, events = prospective.load(directory, expected_hash)
    selected = next((e for e in events if e["kind"] == "SELECT" and e["item"]["task_id"] == item["task_id"]), None)
    if selected:
        if selected["item"] != item or selected["method_hash"] != method_hash:
            raise ValueError("Previously registered observation changed")
    else:
        selected = prospective.admit(directory, expected_hash, item, method_hash=method_hash)
    if selected["status"] != "PENDING":
        return {"task_id": item["task_id"], "status": "INELIGIBLE", "reasons": selected["reasons"]}
    if method_hash != spec["method_hash"] or any(e["kind"] == "REPAIR" for e in events):
        raise ValueError("Frozen method or untouched-window premise changed")
    output = directory / "observations" / (item["task_id"] + ".json")
    prior = next((e for e in events if e["kind"] == "OBSERVE" and e["task_id"] == item["task_id"]), None)
    if prior:
        if not output.exists() or digest(read(output)) != prior["qualification_hash"]:
            raise ValueError("Prospective qualification missing or altered")
        return read(output)
    doc = archive.extract(source, entry["kind"])
    claims = evidence.observations(row, doc)
    result = evidence.describe(row, doc, claims)
    qualification = {"task_id": item["task_id"], "source_sha256": entry["sha256"], "method_hash": method_hash,
        "question_hash": item["question_hash"], "created_at": now(), "status": "OBSERVED_QUALIFIED",
        "quotations_checked": len(claims), "candidate_report": result, "claims": claims,
        "legal_correctness": "NOT_ESTABLISHED", "human_quality_evidence": False,
        "property_checked": "Unchanged original bytes, mechanically reproduced quotations and conservative candidate possible worlds; no backend execution or source-language entailment theorem is inferred"}
    write(output, qualification)
    with prospective.locked(directory):
        spec, events = prospective.load(directory, expected_hash)
        if any(e["kind"] == "REPAIR" or (e["kind"] == "OBSERVE" and e["task_id"] == item["task_id"]) for e in events):
            raise ValueError("Prospective window changed during observation")
        prospective.append(directory, spec, events, {"kind": "OBSERVE", "task_id": item["task_id"],
            "qualification_hash": digest(qualification), "summary": {"legal_correctness": "NOT_ESTABLISHED"},
            "unknown_future_legal_generalization": "NOT_ESTABLISHED"})
    return qualification


def intake(current):
    """Explicit future submissions only; no scheduled or unbounded network work."""
    path = PROGRAM / "future-intake.json"
    if not path.exists():
        return {"status": "READY", "submissions": 0, "instructions": "Provide document ID already preserved in catalog, task_id, family, published_at and first_seen_at; never an expected answer."}
    p6 = ROOT / current["phases"]["P6"]["directory"] / "prospective"
    frozen = read(p6 / "freeze.json")
    ledger = RUNS / "prospective" / frozen["window_hash"]
    if not ledger.exists():
        ledger.mkdir(parents=True)
        shutil.copyfile(p6 / "freeze.json", ledger / "freeze.json")
        (ledger / "events").mkdir()
    rows = {r["id"]: r for r in archive.catalog()}
    items = read(path)
    if not isinstance(items, list) or len(items) > 32:
        raise ValueError("Future intake requires a bounded list")
    outcomes = []
    for item in items:
        if set(item) != {"document", "task_id", "family", "published_at", "first_seen_at"}:
            raise ValueError("Future input schema forbids labels and expected answers")
        metadata = {k: v for k, v in item.items() if k != "document"}
        outcome = observe(ledger, frozen["window_hash"], rows[item["document"]], metadata)
        outcomes.append({"task_id": outcome["task_id"], "status": outcome["status"]})
    return {"outcomes": outcomes, "ledger": prospective.report(ledger, frozen["window_hash"])}
