"""Versioned engineering contracts; evidence integrity is not legal adjudication."""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import os

VERSION = "prospectus-successor.v2"
QUESTIONS = {
    "Q1": "Contractual principal loss; statutory disclosure reported separately",
    "Q2": "Compulsory common conversion, possible common and common-only alternatives",
    "Q3": "Completeness of the declared source scope for each question",
    "Q4": "Dated authority and observed event, conditional on supplied premises",
    "Q5": "Named conditional financial calculation, with units and conventions",
    "Q6": "Existing bank obligations; no automatic transaction permission",
}
STATUSES = {"YES", "NO", "UNKNOWN", "CONFLICT"}
PURPOSES = {"issue_formation", "amendment", "event", "review"}


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with tmp.open("w") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def bound_path(root, relative):
    root = Path(root).resolve()
    result = (root / relative).resolve()
    if not result.is_relative_to(root):
        raise ValueError("Source escapes declared root")
    return result


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Explicit timezone required")
    return result


@dataclass(frozen=True)
class TextUnit:
    id: str
    document: str
    source_sha256: str
    page: int
    order: int
    raw: str
    bbox: list | None
    parent: str
    language: str
    method: str
    review: str = "UNEVALUATED"

    def json(self):
        return {**asdict(self), "normalized": " ".join(self.raw.split()),
                "text_sha256": digest(self.raw.encode())}


@dataclass
class QueryResult:
    question: str
    status: str
    value: object = None
    witnesses: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    quantifier: str = "declared instrument and source scope"
    qualification: str = "CONDITIONAL_ON_SUPPLIED_SCOPE_AND_INTERPRETATION"

    def json(self):
        if self.status not in STATUSES | {"COMPLETE", "PARTIAL", "UNSUPPORTED", "CONDITIONAL"}:
            raise ValueError("Invalid result status")
        return {"version": VERSION, **asdict(self)}


def validate_request(request):
    from .anchors import fields
    fields(request, {"version", "bundle", "assembly", "construction", "clauses", "scope",
                     "reference_dispositions", "law_bases", "law_relation", "facts",
                     "financial_scenario", "bank", "observations"}, {"version", "bundle"})
    if request.get("version") != VERSION:
        raise ValueError("Unsupported request version")
    bundle = request["bundle"]
    if not bundle.get("instrument_id") or bundle.get("purpose") not in PURPOSES:
        raise ValueError("Instrument and declared purpose required")
    for key in ("issue_date", "effective_at", "known_at"):
        timestamp(bundle[key])
    documents = bundle["documents"]
    if not documents or len({d["id"] for d in documents}) != len(documents):
        raise ValueError("Nonempty distinct document inventory required")
    for d in documents:
        if not d.get("language") or not d.get("authority"):
            raise ValueError("Source language and authority description required")
        if len(d["sha256"]) != 64:
            raise ValueError("Expected source byte hash required")
    return bundle
