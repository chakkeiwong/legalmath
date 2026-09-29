"""Strict OFAC simple-XML snapshots. A name hit is an identity candidate only."""
from datetime import datetime
import unicodedata
import xml.etree.ElementTree as ET

from .evidence import sha


def normalize(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Nonempty entity name required")
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def parse(data, *, list_kind):
    if list_kind not in {"SDN", "CONSOLIDATED"}:
        raise ValueError("Explicit OFAC list family required")
    if len(data) > 64_000_000 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Unsupported or oversized XML")
    root = ET.fromstring(data)
    tag = lambda node: node.tag.split("}")[-1]
    if tag(root) != "sdnList":
        raise ValueError("Not an OFAC simple-XML list")
    namespace = root.tag.removesuffix("sdnList")

    def text(node, path):
        found = node.find("/".join(namespace + part for part in path.split("/")))
        return found.text.strip() if found is not None and found.text else ""

    info = root.find(namespace + "publshInformation")
    if info is None:
        raise ValueError("Missing publication metadata")
    publication = datetime.strptime(text(info, "Publish_Date"), "%m/%d/%Y").date().isoformat()
    expected = int(text(info, "Record_Count"))
    entries, ids = [], set()
    for node in root.findall(namespace + "sdnEntry"):
        uid = text(node, "uid")
        if not uid or uid in ids:
            raise ValueError("Missing or duplicate OFAC identifier")
        ids.add(uid)
        names = [" ".join(filter(None, [text(node, "firstName"), text(node, "lastName")]))]
        names.extend(" ".join(filter(None, [text(a, "firstName"), text(a, "lastName")]))
                     for a in node.findall(namespace + "akaList/" + namespace + "aka"))
        programs = [p.text.strip() for p in node.findall(namespace + "programList/" + namespace + "program") if p.text]
        if not programs or not names[0]:
            raise ValueError("Missing OFAC name or program")
        if list_kind == "SDN" and all(p.startswith("NS-") for p in programs):
            raise ValueError("Only non-SDN program tags in a declared SDN snapshot")
        entries.append({"uid": uid, "names": names, "programs": programs,
                        "identifiers": [{"type": text(i, "idType"), "number": text(i, "idNumber"),
                                         "country": text(i, "idCountry")} for i in
                            node.findall(namespace + "idList/" + namespace + "id")]})
    if len(entries) != expected or expected <= 0:
        raise ValueError("Truncated or empty OFAC list")
    return {"list_kind": list_kind, "source_sha256": sha(data), "published_date": publication,
            "entries": entries, "record_count": len(entries),
            "legal_currentness": "NOT_ESTABLISHED"}


def candidates(snapshot, name, *, program=None):
    query = normalize(name)
    matches = [row for row in snapshot["entries"]
               if (program is None or program in row["programs"])
               and query in {normalize(n) for n in row["names"] if n.strip()}]
    return {"status": "IDENTITY_CANDIDATES" if matches else "NO_EXACT_NAME_CANDIDATE",
            "matches": matches, "source_sha256": snapshot["source_sha256"],
            "identity_established": False, "sanctions_clearance": "NOT_ESTABLISHED"}


def changes(old, new):
    if old["list_kind"] != new["list_kind"]:
        raise ValueError("Cannot compare different sanctions lists")
    left, right = ({r["uid"]: r for r in s["entries"]} for s in (old, new))
    return {"added": sorted(right.keys() - left.keys()), "removed": sorted(left.keys() - right.keys()),
            "changed": sorted(k for k in left.keys() & right.keys() if left[k] != right[k]),
            "invalidate_prior_screening": old["source_sha256"] != new["source_sha256"]}
