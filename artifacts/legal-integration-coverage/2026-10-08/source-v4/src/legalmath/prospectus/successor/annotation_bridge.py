"""Exact edition-bound grouped spans for the INCEpTION 38 UIMA exchange trial."""
from copy import deepcopy
from .anchors import fields
from .contracts import digest


def to_utf16(text, offset):
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise ValueError("Invalid code-point offset")
    return len(text[:offset].encode("utf-16-le")) // 2


def from_utf16(text, offset):
    if type(offset) is not int or offset < 0:
        raise ValueError("Invalid UTF-16 offset")
    cursor = 0
    for i, char in enumerate(text):
        if cursor == offset:
            return i
        cursor += 2 if ord(char) > 0xffff else 1
        if cursor > offset:
            raise ValueError("UTF-16 offset splits a surrogate pair")
    if cursor == offset:
        return len(text)
    raise ValueError("UTF-16 offset exceeds source")


def export(text, source, groups, relations):
    fields(source, {"document", "source_sha256", "text_sha256"}, {"document", "source_sha256", "text_sha256"})
    if digest(text.encode()) != source["text_sha256"] or len(source["source_sha256"]) != 64:
        raise ValueError("Annotation source edition mismatch")
    ids, converted = set(), []
    for group in groups:
        fields(group, {"id", "label", "spans"}, {"id", "label", "spans"})
        if not group["id"] or group["id"] in ids or not group["spans"] or not isinstance(group["label"], str):
            raise ValueError("Distinct evidence group and nonempty spans required")
        ids.add(group["id"])
        spans, previous = [], -1
        for span in group["spans"]:
            fields(span, {"start", "end", "quote"}, {"start", "end", "quote"})
            a, b = span["start"], span["end"]
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(text) or a < previous or text[a:b] != span["quote"]:
                raise ValueError("Stale, overlapping or invalid evidence span")
            previous = b
            spans.append({"begin": to_utf16(text, a), "end": to_utf16(text, b), "quote": span["quote"]})
        converted.append({"id": group["id"], "label": group["label"], "spans": spans})
    relation_ids = set()
    for relation in relations:
        fields(relation, {"id", "from", "to", "kind"}, {"id", "from", "to", "kind"})
        if not relation["id"] or relation["id"] in relation_ids or relation["from"] not in ids or relation["to"] not in ids or not relation["kind"]:
            raise ValueError("Unbound relation")
        relation_ids.add(relation["id"])
    return {"version": "legal-evidence-uima.v1", "target_release": "INCEpTION 38.0", "source": deepcopy(source),
            "text": text, "offset_unit": "UTF16_CODE_UNITS", "groups": converted, "relations": deepcopy(relations),
            "blind_protocol": {"recommendations": False, "premerge": False},
            "independence": "NOT_ESTABLISHED_BY_EXCHANGE"}


def reimport(packet, text, source):
    if packet["version"] != "legal-evidence-uima.v1" or packet["source"] != source or packet["text"] != text or packet["offset_unit"] != "UTF16_CODE_UNITS":
        raise ValueError("Annotation edition or text changed")
    groups = [{"id": g["id"], "label": g["label"], "spans": [
        {"start": from_utf16(text, s["begin"]), "end": from_utf16(text, s["end"]), "quote": s["quote"]}
        for s in g["spans"]]} for g in packet["groups"]]
    # Validate the complete edit, including repeated occurrences and relation IDs.
    checked = export(text, source, groups, packet["relations"])
    return {"source": source, "groups": groups, "relations": checked["relations"],
            "original_export_sha256": digest(packet), "status": "IMPORTED_REQUIRES_READER_IDENTITY_AND_ADJUDICATION"}
