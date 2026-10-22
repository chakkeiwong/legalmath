"""Reviewed structure and meaning adapters consumed by the prospectus service.

These mechanical checks bind supplied interpretations. They do not authenticate
reviewers or establish that their legal reading is correct.
"""
from copy import deepcopy
from .anchors import bind, fields
from .contracts import digest
from .occurrences import uses


def review(row):
    fields(row, {"reviewer", "reason", "kind"}, {"reviewer", "reason", "kind"})
    if not row["reviewer"] or not row["reason"] or row["kind"] not in {"DEVELOPMENT", "SUPPLIED_REVIEW"}:
        raise ValueError("Explicit supplied review record required")


def structure(graph, admission):
    """Recompute projections from retained package bytes, then bind reviewed edges."""
    fields(admission, {"version", "graph_sha256", "documents", "governing", "review"},
           {"version", "graph_sha256", "documents", "governing", "review"})
    if admission["version"] not in {"prospectus-layout.v1", "prospectus-layout.v2"} or admission["graph_sha256"] != digest(graph):
        raise ValueError("Layout source graph changed")
    review(admission["review"])
    from .layout_adapter import project_layout
    projections = []
    for row in admission["documents"]:
        fields(row, {"document", "source_sha256", "docling"}, {"document", "source_sha256", "docling"})
        units = [u for u in graph["units"] if u["document"] == row["document"]]
        if not units:
            raise ValueError("Layout document missing")
        projection = project_layout(units, row["docling"], source_sha256=row["source_sha256"])
        projections.append({"document": row["document"], **projection})
    # Layout margins repeatedly cite the same body. Keep all candidates for
    # each identity so duplicate-source refusals remain exactly those of bind.
    # This index exists only during this immutable graph admission.
    source_units = {}
    for unit in graph['units']:
        source_units.setdefault(unit['id'], []).append(unit)

    def bind_source(source):
        if isinstance(source, dict) and isinstance(source.get('unit'), str):
            return bind({'units': source_units.get(source['unit'], [])}, source)
        return bind(graph, source)

    ids = set()
    for edge in admission["governing"]:
        fields(edge, {"id", "kind", "from", "to", "questions", "reason"},
               {"id", "kind", "from", "to", "questions", "reason"})
        if (edge["id"] in ids or not edge["id"] or edge["kind"] != "governs" or not edge["reason"] or
                not edge["to"] or not edge["questions"] or set(edge["questions"]) - {"Q1", "Q2"}):
            raise ValueError("Invalid reviewed governing relationship")
        ids.add(edge["id"])
        bind_source(edge["from"])
        for target in edge["to"]:
            source = target
            if admission['version'] == 'prospectus-layout.v2':
                fields(target, {'source', 'use'}, {'source', 'use'})
                bind_source(target['source'])
                fields(target['use'], {'unit', 'start', 'end'}, {'unit', 'start', 'end'})
                use = target['use']
                if (not isinstance(use['unit'], str) or not use['unit'] or
                        type(use['start']) is not int or type(use['end']) is not int or
                        not 0 <= use['start'] < use['end'] or
                        use['end'] - use['start'] != target['source']['end'] - target['source']['start']):
                    raise ValueError('Invalid selected governing occurrence')
                source = target['source']
            bind_source(source)
    version = 'admitted-layout.v2' if admission['version'] == 'prospectus-layout.v2' else 'admitted-layout.v1'
    return {"version": version, "input_sha256": digest(admission),
            "projections": projections, "governing": admission["governing"],
            "review": admission["review"], "automatic_legal_scope": False}


def governing_dependencies(graph, assembly, *, _lookup=None):
    if _lookup is not None:
        _lookup._check(graph, assembly)
    locate = uses if _lookup is None else _lookup.uses
    result = []
    # Complete multi-line conditions repeat the same governed occurrences.
    # Reuse a lookup only within this fixed graph/assembly call; question and
    # the complete anchor remain part of its identity, including empty uses.
    mappings_by_source = {}
    for edge in graph.get("layout", {}).get("governing", []):
        for question in edge["questions"]:
            mappings = []
            for target in edge["to"]:
                explicit = graph.get('layout', {}).get('version') == 'admitted-layout.v2'
                source = target['source'] if explicit else target
                key = (question, digest(source))
                if key not in mappings_by_source:
                    mappings_by_source[key] = locate(graph, assembly, source, question=question)
                found = mappings_by_source[key]
                if explicit:
                    found = [m for m in found if all(m[k] == target['use'][k] for k in ('unit', 'start', 'end'))]
                mappings.append(deepcopy(found))
            result.append({"id": "governing:" + edge["id"] + ":" + question,
                "questions": [question], "status": "RESOLVED" if all(len(m) == 1 for m in mappings) else "UNRESOLVED",
                "authority": edge["from"], "target_uses": mappings,
                "reason": "Every source-reviewed governed occurrence must survive in the selected question"})
    return result


def dispositions(graph, assembly, admission):
    from .occurrences import _raw_index, segments
    fields(admission, {"version", "assembly_sha256", "review", "units"},
           {"version", "assembly_sha256", "review", "units"})
    if admission["version"] != "reviewed-dispositions.v1" or admission["assembly_sha256"] != digest(assembly):
        raise ValueError("Reviewed disposition assembly changed")
    review(admission["review"])
    result = deepcopy(assembly)
    by_id = {u["unit"]: u for u in result["units"]}
    original_occurrences = {}
    for original in assembly["units"]:
        original_occurrences.setdefault(original["unit"], []).append(original)
    validated_roles, raw_index = set(), None
    seen = set()
    reading_roles = {"OPERATIVE", "UNKNOWN"}
    reading_changed = False
    for row in admission["units"]:
        fields(row, {"unit", "text_sha256", "role", "reason", "sources"},
               {"unit", "text_sha256", "role", "reason", "sources"})
        if row["unit"] not in by_id or row["unit"] in seen:
            raise ValueError("Unknown or duplicate reviewed disposition")
        seen.add(row["unit"])
        unit = by_id[row["unit"]]
        if unit["role"] == "EXCLUDED" or row["role"] not in {"OPERATIVE", "EXAMPLE", "HEADER", "INSTRUCTION", "UNKNOWN"}:
            raise ValueError("Reviewed meaning cannot override an excluded construction branch")
        if digest(unit["text"].encode()) != row["text_sha256"] or not row["reason"] or not row["sources"]:
            raise ValueError("Reviewed disposition text/evidence changed")
        coverage = set()
        for source in row["sources"]:
            # The old full search validated all maps of this original role,
            # even maps unrelated to the named occurrence. Keep that check,
            # but do it once in this immutable graph/assembly call.
            bind(graph, source)
            if unit["role"] not in validated_roles:
                if raw_index is None:
                    raw_index = _raw_index(graph)
                for original in assembly["units"]:
                    if original["role"] == unit["role"]:
                        segments(graph, original, _raw=raw_index)
                validated_roles.add(unit["role"])
            # Keep every original occurrence of the identity: duplicate named
            # uses must remain ambiguous, and prior role edits cannot affect it.
            matches = uses(graph, {"units": original_occurrences[unit["unit"]]},
                           source, roles=(unit["role"],))
            if len(matches) != 1:
                raise ValueError("Reviewed source does not map to selected text")
            coverage.update(range(matches[0]["start"], matches[0]["end"]))
        if any(i not in coverage for i, char in enumerate(unit["text"]) if not char.isspace()):
            raise ValueError("Reviewed disposition must cover the complete selected unit")
        reading_changed |= (unit["role"] in reading_roles) != (row["role"] in reading_roles)
        unit.update(role=row["role"], reason=row["reason"])
    result["unresolved"] = [u["unit"] for u in result["units"] if u["role"] == "UNKNOWN"]
    result["reviewed_dispositions"] = admission
    result["status"] = "PARTIAL" if result["unresolved"] else "COMPLETE_UNDER_SUPPLIED_DISPOSITIONS"
    # BASF v1 defines this field as its constructed candidate, separately from
    # the ledger of selected and unreviewed source units. A role-only review
    # must preserve that candidate even when the two readings happen to agree.
    if reading_changed and assembly.get("version") != "assembled-contract.v1":
        prior_reading = "\n".join(u["text"] for u in assembly["units"]
                                  if u["role"] in reading_roles)
        if assembly.get("continuous_text") != prior_reading:
            raise ValueError("Reviewed role change requires a source-bound constructed reading map")
        result["continuous_text"] = "\n".join(
            u["text"] for u in result["units"] if u["role"] in reading_roles)
    return result


def annotation_clauses(graph, assembly, admission):
    from .annotation_bridge import reimport
    from .clause_graph import build
    allowed = {"version", "assembly_sha256", "review", "packets", "meanings"}
    if admission.get('version') == 'reviewed-annotation-meaning.v2':
        allowed.add('cross_document_relations')
    fields(admission, allowed,
           {"version", "assembly_sha256", "review", "packets", "meanings"})
    if admission["version"] not in {"reviewed-annotation-meaning.v1", "reviewed-annotation-meaning.v2"} or admission["assembly_sha256"] != digest(assembly):
        raise ValueError("Annotation meaning assembly changed")
    review(admission["review"])
    selected = {u["unit"]: u for u in assembly["units"]}
    groups, relations, packet_ids, packets = {}, [], set(), {}
    for item in admission["packets"]:
        fields(item, {"id", "packet", "map"}, {"id", "packet", "map"})
        if not item["id"] or item["id"] in packet_ids:
            raise ValueError("Distinct annotation packet identity required")
        packet_ids.add(item["id"])
        packet = item["packet"]
        packets[item['id']] = packet
        decoded = reimport(packet, packet["text"], packet["source"])
        for edge in decoded["relations"]:
            if edge["kind"] not in {"conditions", "exceptions"}:
                raise ValueError("Unconsumed authored relation kind: " + edge["kind"])
            relations.append((item["id"] + ":" + edge["from"], item["id"] + ":" + edge["to"], edge["kind"]))
        mappings = []
        for row in item["map"]:
            fields(row, {"start", "end", "source", "use", "correction"}, {"start", "end", "source", "use"})
            source = bind(graph, row["source"])
            mapped_text = source['quote']
            if row.get('correction'):
                entries = [r for r in graph.get('corrections',{}).get('entries',[]) if r['id'] == row['correction']]
                if len(entries) != 1 or entries[0]['source'] != row['source']:
                    raise ValueError('Correction does not bind this annotation source')
                mapped_text = entries[0]['text']
            if (source["document"] != packet["source"]["document"] or source["source_sha256"] != packet["source"]["source_sha256"] or
                    type(row["start"]) is not int or type(row["end"]) is not int or
                    not 0 <= row["start"] < row["end"] <= len(packet["text"]) or
                    packet["text"][row["start"]:row["end"]] != mapped_text):
                raise ValueError("Annotation raw source map changed")
            match = [m for m in uses(graph, assembly, row["source"]) if m["unit"] == row["use"]]
            if len(match) != 1:
                raise ValueError("Annotation must refer to an operative selected occurrence")
            mappings.append((row, match[0]))
        for group in decoded["groups"]:
            key = item["id"] + ":" + group["id"]
            if key in groups:
                raise ValueError("Duplicate annotation group identity")
            spans = []
            for span in group["spans"]:
                covering = [(r, m) for r, m in mappings if r["start"] <= span["start"] < span["end"] <= r["end"]]
                if len(covering) != 1:
                    raise ValueError("Annotation span requires one exact mapped interval; split cross-unit spans explicitly")
                row, match = covering[0]
                if row.get('correction'):
                    from .corrections import sources
                    for raw_source in sources(graph, row['correction'], span['start']-row['start'], span['end']-row['start']):
                        raw_uses = [m for m in uses(graph, assembly, raw_source) if m['unit'] == row['use']]
                        if len(raw_uses) != 1:
                            raise ValueError('Corrected annotation raw evidence is not selected')
                        spans.append({k:raw_uses[0][k] for k in ('unit','start','end')})
                    continue
                start = match["start"] + span["start"] - row["start"]
                spans.append({"unit": match["unit"], "start": start, "end": start + span["end"] - span["start"]})
            groups[key] = spans
    link_ids = set()
    for edge in admission.get('cross_document_relations', []):
        fields(edge, {'id','from','to','kind','review'}, {'id','from','to','kind','review'})
        review(edge['review'])
        if not edge['id'] or edge['id'] in link_ids or edge['kind'] not in {'conditions','exceptions'}:
            raise ValueError('Invalid reviewed cross-document relation')
        link_ids.add(edge['id'])
        endpoints = []
        documents = []
        for endpoint in (edge['from'], edge['to']):
            fields(endpoint, {'packet','packet_sha256','group'}, {'packet','packet_sha256','group'})
            packet = packets.get(endpoint['packet'])
            key = endpoint['packet'] + ':' + endpoint['group']
            if packet is None or digest(packet) != endpoint['packet_sha256'] or key not in groups:
                raise ValueError('Cross-document endpoint or packet changed')
            endpoints.append(key)
            documents.append(packet['source']['document'])
        if documents[0] == documents[1]:
            raise ValueError('Use authored local relations within a single document')
        relations.append((*endpoints, edge['kind']))
    clauses, used, owners = [], set(), {}
    for meaning in admission["meanings"]:
        fields(meaning, {"groups", "clause"}, {"groups", "clause"})
        if not meaning["groups"] or any(g not in groups for g in meaning["groups"]):
            raise ValueError("Meaning lacks actual authored evidence groups")
        used.update(meaning["groups"])
        spans = [s for g in meaning["groups"] for s in groups[g]]
        clause = deepcopy(meaning["clause"])
        for group in meaning["groups"]:
            owners.setdefault(group, []).append(clause["id"])
        if set(clause) & {"spans", "units", "quote", "role", "questions", "origin"}:
            raise ValueError("Meaning cannot override evidence-derived fields")
        clause.update(spans=spans, units=list(dict.fromkeys(s["unit"] for s in spans)),
            quote=" ".join(selected[s["unit"]]["text"][s["start"]:s["end"]] for s in spans),
            role="OPERATIVE", questions=sorted(set().union(*(set(selected[s["unit"]]["questions"]) for s in spans))),
            origin="reviewed-authored-evidence")
        clauses.append(clause)
    if set(groups) != used:
        raise ValueError("Authored evidence groups require explicit meaning dispositions")
    authored_links = set()
    for source, target, kind in relations:
        if len(owners[source]) != 1 or len(owners[target]) != 1:
            raise ValueError("Authored relation endpoints require one unambiguous clause meaning")
        authored_links.add((owners[source][0], owners[target][0], kind))
    meaning_links = {(n["id"], target, kind) for n in clauses for kind in ("conditions", "exceptions")
                     if isinstance(n.get(kind), list) for target in n[kind]}
    if authored_links != meaning_links:
        raise ValueError("Authored relations differ from supplied clause links")
    build(assembly, clauses)
    return clauses
