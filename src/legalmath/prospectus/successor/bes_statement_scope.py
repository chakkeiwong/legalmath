"""Reviewed exact-source completeness for BES prospectus p37(a).

The rule protects one inspected source/edition, not arbitrary incorporation.
Original profile evidence: source-bes-dep-01 attempts001/002 under the execution
authority. Page text hashes bind retained native readings, not financial truth.
"""
from .contracts import digest
from .occurrences import anchor, segments

PROFILE = "bes-9m10-statement-scope.v1"
INTRO = "f6391acb72db7f88fb5b51df8bd0668a747580ddf6357bc00c0b7e5347b80d60"
RELEASE = "44938fcd6622d7c9ea5466636052a286da42c42cb440cf9f71590fbde71fb841"
PAGES = {
    (INTRO, 37): (73, "5db77de341d25c3a539f6cff9abec87a44186faef985b2be94f33036fea7460e"),
    (RELEASE, 1): (57, "fbdd37c062f2aa490f7e8a5e50f59e161b296e2543cfc549bd116aac06fed500"),
    (RELEASE, 37): (210, "1afe8b0fb8f58243b3f30a74c4e8e0ab829592e44e6ec11f744f2c2214a51d1e"),
    (RELEASE, 38): (94, "8e01a7a5be957edcbc5c79f927e0f33bd2f8f9427bce0d5819b236bda43744c5"),
}


def _page(raw, document, source, number):
    rows = [u for u in raw.values() if u["document"] == document and u["page"] == number]
    count, expected = PAGES[(source, number)]
    if (len(rows) != count or any(not u.get("visible") or u["source_sha256"] != source
            or u["language"] != "en" or u["text_sha256"] != digest(u["raw"].encode()) for u in rows)
            or len({u["order"] for u in rows}) != count):
        raise ValueError("BES statement scope requires complete visible original page units")
    rows.sort(key=lambda u:u["order"])
    if digest("\n".join(u["raw"] for u in rows).encode()) != expected:
        raise ValueError("BES statement scope page reading changed")
    return rows


def check(graph, assembly, row):
    from .bes_q1_scope import check as check_q1
    q1 = check_q1(graph, assembly, row)
    if q1 is not None:
        return q1
    from .bes_fy2010_scope import check as check_fy2010
    fy2010 = check_fy2010(graph, assembly, row)
    if fy2010 is not None:
        return fy2010
    raw = {u["id"]:u for u in graph["units"]}
    if len(raw) != len(graph["units"]):
        raise ValueError("Duplicate source occurrence identity")
    referring = raw.get(row["source"]["unit"])
    if not referring or (referring["source_sha256"], referring["page"]) != (INTRO, 37):
        return None
    introduction = _page(raw, referring["document"], INTRO, 37)
    # The frozen native page inventory identifies the exact four-line item(a).
    # Changes to text or segmentation refuse above, so these positions cannot
    # silently select another passage of the original page.
    clause = introduction[5:9]
    if referring["id"] not in {u["id"] for u in clause}:
        return None
    if row["form"] != "external":
        raise ValueError("BES statement reference requires its external source role")
    docs = {u["document"] for u in raw.values() if u["source_sha256"] == RELEASE}
    if len(docs) != 1:
        raise ValueError("BES statement reference requires the unique original release edition")
    document, = docs
    cover = _page(raw, document, RELEASE, 1)
    targets = _page(raw, document, RELEASE, 37) + _page(raw, document, RELEASE, 38)
    selected = {u["unit"]:u for u in assembly["units"]}
    if len(selected) != len(assembly["units"]):
        raise ValueError("Duplicate selected occurrence identity")
    for unit in introduction[1:9] + targets:
        found = selected.get(unit["id"])
        if (found is None or found["role"] != "OPERATIVE" or found["text"] != unit["raw"]
                or not set(row["questions"]) <= set(found["questions"])
                or segments(graph, found, _raw=raw) !=
                   [{"source": anchor(unit), "start": 0, "end": len(unit["raw"])}]):
            raise ValueError("BES statement scope needs unchanged operative restriction, clause and target text")
    expected = {u["id"]:u for u in targets}
    supplied = row["targets"]
    if not isinstance(supplied,list) or len(supplied) != len(expected):
        raise ValueError("BES statement scope requires all 304 target units exactly once")
    seen = set()
    for value in supplied:
        source = value.get("source", {})
        identity = source.get("unit")
        if (identity not in expected or identity in seen or value.get("use") != identity
                or value.get("language") != "en" or source != anchor(expected[identity])):
            raise ValueError("BES statement scope target omitted, duplicated, partial or outside its declared pages")
        seen.add(identity)
    return {"profile": PROFILE, "status": "COMPLETE_RETAINED_PAGE_TARGETS",
            "target_units": len(targets), "source_sha256": RELEASE, "pages": [37,38],
            "page_text_sha256": {str(p):PAGES[(RELEASE,p)][1] for p in (37,38)},
            "source_clause": [anchor(u) for u in clause],
            "restriction": [anchor(u) for u in introduction[1:4]],
            "release_identity_and_qualification": [anchor(u) for u in cover[:5]],
            "title_difference": {"prospectus":"9H10", "release":"9M10", "silently_corrected":False},
            "independent_legal_acceptance": False,
            "limit": "Exact-source retained native page coverage; no table accuracy, authenticity or general incorporation adjudication"}
