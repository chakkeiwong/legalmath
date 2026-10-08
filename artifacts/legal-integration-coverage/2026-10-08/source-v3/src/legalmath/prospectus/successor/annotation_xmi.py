"""Strict INCEpTION XMI exchange; Cassis is an optional sidecar dependency.

Decoding recovers provenance and group links from the exported CAS itself.
Expected source/text are checks, never replacements for missing CAS fields.
"""
import io
import re
import zipfile
from copy import deepcopy

from .annotation_bridge import export, reimport, to_utf16, from_utf16
from .contracts import digest

SPAN = "webanno.custom.LegalEvidence"
RELATION = "webanno.custom.LegalRelation"
IDENTITY = "webanno.custom.LegalSource"
GROUP_LINK = "same_evidence_group"
CAS_METADATA = "de.tudarmstadt.ukp.clarin.webanno.api.type.CASMetadata"


def display_offsets(text, begin, end):
    """INCEpTION's display spans trim whitespace; source offsets remain separate."""
    while begin < end and text[begin].isspace():
        begin += 1
    while end > begin and text[end-1].isspace():
        end -= 1
    if begin == end:
        raise ValueError("Whitespace-only evidence needs a non-span representation")
    return begin, end


def normalized(packet):
    checked = reimport(packet, packet["text"], packet["source"])
    return {"source": checked["source"], "text": packet["text"],
            "groups": sorted(checked["groups"], key=lambda g: g["id"]),
            "relations": sorted(checked["relations"], key=lambda r: r["id"])}


def type_system():
    import cassis
    ts = cassis.TypeSystem()
    for name, strings, integers in [
        (IDENTITY, ("document", "sourceSHA", "textSHA", "exchangeVersion"), ()),
        (SPAN, ("groupId", "label", "sourceSHA", "textSHA", "quote"), ("piece", "groupSize", "sourceBegin", "sourceEnd")),
        (RELATION, ("relationId", "kind"), ())]:
        kind = ts.create_type(name=name, supertypeName="uima.tcas.Annotation")
        for feature in strings:
            ts.create_feature(kind, name=feature, rangeType="uima.cas.String")
        for feature in integers:
            ts.create_feature(kind, name=feature, rangeType="uima.cas.Integer")
    for feature in ("Governor", "Dependent"):
        ts.create_feature(RELATION, name=feature, rangeType=SPAN)
    ts.create_type(name=CAS_METADATA, supertypeName="uima.tcas.Annotation")
    for feature in ("projectId", "sourceDocumentId", "lastChangedOnDisk"):
        ts.create_feature(CAS_METADATA, name=feature, rangeType="uima.cas.Long")
    for feature in ("projectName", "sourceDocumentName", "username"):
        ts.create_feature(CAS_METADATA, name=feature, rangeType="uima.cas.String")
    return ts


def encode(packet):
    import cassis
    normalized(packet)
    if any(r["kind"] == GROUP_LINK for r in packet["relations"]):
        raise ValueError("Reserved structural relation kind")
    ts = type_system()
    cas = cassis.Cas(typesystem=ts)
    cas.sofa_string = packet["text"]
    # Per the official internal schema, -1 denotes a CAS not yet stored on disk.
    # The server fills its own project/user metadata when persisting the upload.
    cas.add(ts.get_type(CAS_METADATA)(begin=0, end=0, lastChangedOnDisk=-1))
    source = packet["source"]
    if any(not re.fullmatch(r"[0-9a-f]{64}", source[k]) for k in ("source_sha256", "text_sha256")):
        raise ValueError("Hex source hashes required")
    cas.add(ts.get_type(IDENTITY)(begin=0, end=0, document=source["document"],
        sourceSHA=source["source_sha256"], textSHA=source["text_sha256"], exchangeVersion="legalmath-xmi.v1"))
    heads = {}
    for group in packet["groups"]:
        members = []
        for i, piece in enumerate(group["spans"]):
            begin, end = display_offsets(cas.sofa_string, from_utf16(cas.sofa_string, piece["begin"]),
                                         from_utf16(cas.sofa_string, piece["end"]))
            ann = ts.get_type(SPAN)(begin=begin, end=end, sourceBegin=piece["begin"], sourceEnd=piece["end"],
                groupId=group["id"], label=group["label"],
                piece=i, groupSize=len(group["spans"]), quote=piece["quote"],
                sourceSHA=source["source_sha256"], textSHA=source["text_sha256"])
            cas.add(ann)
            members.append(ann)
        heads[group["id"]] = members[0]
        for i, member in enumerate(members[1:], 1):
            cas.add(ts.get_type(RELATION)(begin=member.begin, end=member.end,
                Governor=members[0], Dependent=member, relationId=group["id"]+":piece:"+str(i), kind=GROUP_LINK))
    for edge in packet["relations"]:
        head = heads[edge["from"]]
        target = heads[edge["to"]]
        cas.add(ts.get_type(RELATION)(begin=target.begin, end=target.end, Governor=head,
            Dependent=heads[edge["to"]], relationId=edge["id"], kind=edge["kind"]))
    return cas.to_xmi().encode(), ts.to_xml().encode()


def load_export(raw, types=None):
    import cassis
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            xmis = [n for n in archive.namelist() if n.lower().endswith(".xmi")]
            systems = [n for n in archive.namelist() if n.lower().endswith("typesystem.xml")]
            if len(xmis) != 1 or len(systems) != 1:
                raise ValueError("One XMI and exported type system required")
            if sum(i.file_size for i in archive.infolist()) > 20_000_000:
                raise ValueError("Annotation export exceeds bound")
            raw, types = archive.read(xmis[0]), archive.read(systems[0])
    if types is None:
        raise ValueError("Exported type system required")
    ts = cassis.load_typesystem(io.BytesIO(types))
    return cassis.load_cas_from_xmi(io.BytesIO(raw), typesystem=ts)


def decode(raw, expected_source, expected_text, *, types=None):
    cas = load_export(raw, types)
    identities = list(cas.select(IDENTITY))
    if len(identities) != 1:
        raise ValueError("Export lost or duplicated source identity")
    identity = identities[0]
    source = {"document": identity.document, "source_sha256": identity.sourceSHA, "text_sha256": identity.textSHA}
    if identity.exchangeVersion != "legalmath-xmi.v1" or source != expected_source:
        raise ValueError("Source edition changed")
    if cas.sofa_string != expected_text or digest(cas.sofa_string.encode()) != source["text_sha256"]:
        raise ValueError("Source text changed")
    grouped, by_id = {}, {}
    for ann in cas.select(SPAN):
        if ann.sourceSHA != source["source_sha256"] or ann.textSHA != source["text_sha256"]:
            raise ValueError("Evidence source edition changed")
        if not ann.groupId or type(ann.piece) is not int or type(ann.groupSize) is not int:
            raise ValueError("Missing group identity or member count")
        source_start, source_end = from_utf16(cas.sofa_string, ann.sourceBegin), from_utf16(cas.sofa_string, ann.sourceEnd)
        if (ann.begin, ann.end) != display_offsets(cas.sofa_string, source_start, source_end):
            raise ValueError("Display span no longer matches source offsets")
        grouped.setdefault(ann.groupId, []).append(ann)
        by_id[ann.xmiID] = ann
    groups, expected_links = [], set()
    for group_id, members in sorted(grouped.items()):
        members.sort(key=lambda a: a.piece)
        if [a.piece for a in members] != list(range(len(members))) or any(a.groupSize != len(members) for a in members):
            raise ValueError("Missing or duplicated evidence group member")
        if len({a.label for a in members}) != 1:
            raise ValueError("Discontinuous group has conflicting labels")
        groups.append({"id": group_id, "label": members[0].label,
            "spans": [{"start": from_utf16(cas.sofa_string, a.sourceBegin),
                       "end": from_utf16(cas.sofa_string, a.sourceEnd), "quote": a.quote} for a in members]})
        expected_links.update((group_id+":piece:"+str(a.piece), members[0].xmiID, a.xmiID) for a in members[1:])
    actual_links, relations, relation_ids = set(), [], set()
    for edge in cas.select(RELATION):
        if not edge.relationId or edge.relationId in relation_ids:
            raise ValueError("Missing or duplicate relation identity")
        relation_ids.add(edge.relationId)
        if edge.Governor is None or edge.Dependent is None or any(a.xmiID not in by_id for a in (edge.Governor, edge.Dependent)):
            raise ValueError("Relation endpoint is not a retained evidence member")
        if (edge.begin, edge.end) != (edge.Dependent.begin, edge.Dependent.end):
            raise ValueError("Relation offsets do not match target")
        if edge.kind == GROUP_LINK:
            actual_links.add((edge.relationId, edge.Governor.xmiID, edge.Dependent.xmiID))
        else:
            if edge.Governor.piece != 0 or edge.Dependent.piece != 0:
                raise ValueError("Semantic relation must reference group heads")
            relations.append({"id": edge.relationId, "from": edge.Governor.groupId,
                              "to": edge.Dependent.groupId, "kind": edge.kind})
    if actual_links != expected_links:
        raise ValueError("Missing, extra or redirected discontinuous group links")
    return export(cas.sofa_string, source, groups, sorted(relations, key=lambda e: e["id"]))


def project_layers():
    """Schema for the inspected 38.0 project importer; no implicit token snapping."""
    def feature(name, kind="uima.cas.String", visible=False):
        return {"name": name, "uiName": name, "type": kind, "enabled": True,
                "visible": visible, "required": True, "remember": False,
                "multi_value_mode": "NONE", "link_mode": "NONE", "curatable": True}
    def layer(name, title, kind, features):
        return {"name": name, "uiName": title, "type": kind, "description": "Source-bound legal evidence; provisional implementer trial",
                "enabled": True, "built_in": False, "readonly": name == IDENTITY,
                "cross_sentence": True, "allow_stacking": True, "anchoring_mode": "CHARACTERS",
                "overlap_mode": "ANY_OVERLAP", "validation_mode": "ALWAYS", "features": features}
    identity = layer(IDENTITY, "Source edition", "span", [feature(n) for n in ("document", "sourceSHA", "textSHA", "exchangeVersion")])
    spans = layer(SPAN, "Legal evidence", "span", [feature(n, visible=n in {"groupId", "label", "quote"})
        for n in ("groupId", "label", "sourceSHA", "textSHA", "quote")] + [feature(n, "uima.cas.Integer")
        for n in ("piece", "groupSize", "sourceBegin", "sourceEnd")])
    relations = layer(RELATION, "Legal relations", "relation", [feature(n, visible=True) for n in ("relationId", "kind")])
    relations["attach_type"] = {"name": SPAN}
    return [identity, spans, relations]
