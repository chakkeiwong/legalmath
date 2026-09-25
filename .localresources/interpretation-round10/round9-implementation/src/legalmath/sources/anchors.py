from ..canonical import raw_digest
from ..errors import LegalMathError


def make_span(ident, source_id, raw, text, start, end):
    if not 0 <= start < end <= len(text):
        raise LegalMathError("E_SCHEMA")
    return {"id": ident, "source_id": source_id, "raw_sha256": raw_digest(raw),
        "text_sha256": raw_digest(text.encode()), "page": text[:start].count("\f") + 1,
        "start": start, "end": end, "quote_sha256": raw_digest(text[start:end].encode())}


def verify_span(span, raw, text):
    actual = make_span(span["id"], span["source_id"], raw, text, span["start"], span["end"])
    if actual != span:
        raise LegalMathError("E_HASH_MISMATCH")
    return text[span["start"]:span["end"]]
