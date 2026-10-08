"""Source-reviewed permutations for the pinned BASF German Option I edition.

Review and original page images:
docs/implementation/prospectus-basf-source-order/source-review-001/.
These five local corrections are not a general PDF reading-order algorithm.
"""
from .contracts import digest

DOCUMENT = "basf-base-september-2022-exchange"
BIND_FIELDS = ("id", "document", "source_sha256", "page", "raw", "bbox", "text_sha256")
# id, page, old line indices, reviewed line indices, exact old unit/geometry hash.
REVIEWED_ORDERS = (
    ("final-coupon-field", 111, (69, 64, 65, 66, 67, 68), (64, 65, 66, 67, 68, 69),
     "ed78465d7563e18a0a1f6cc56bce51ba27c0a59aff087c3e51f046e7e3174f72"),
    ("dated-call-ngn", 120, (74, 69, 70, 71, 72, 73, 75), (69, 70, 71, 72, 73, 74, 75),
     "1b1afe12142f2075448c2113f831d7ed712a800815857b1b9e21e3ba0791809b"),
    ("make-whole-ngn", 121, (29, 24, 25, 26, 27, 28, 30), (24, 25, 26, 27, 28, 29, 30),
     "801e0176ea17586a15b3ffc91fad1f53c7b10e7915cba9cf81529e9af13ae4c2"),
    ("fiscal-agent-table", 124, (8, 10, 9, 11, 12, 13, 14), (8, 9, 10, 11, 12, 13, 14),
     "dab33e66e0a3d799b158dcb49c28dbf6fa92fdafe38f6cff8b1c25a7fe1e2eb0"),
    ("canadian-agent-table", 124, (22, 24, 25, 23), (22, 23, 24, 25),
     "feb098e617e844a25966717615938722c668e7d69a6b56ec340263069b8a0854"),
)


def reviewed_order(lines):
    """Permute complete checked spans, preserving unit identity and raw bytes."""
    ordered = sorted(lines, key=lambda u: (u["page"], round(u["bbox"][1], 1), u["bbox"][0]))
    by_id = {u["id"]: u for u in ordered}
    if len(by_id) != len(ordered):
        raise ValueError("Duplicate BASF source occurrence")
    positions = {u["id"]: i for i, u in enumerate(ordered)}
    used, decisions = set(), []
    for name, page, before, after, expected in REVIEWED_ORDERS:
        old = [f"{DOCUMENT}:p{page}:l{n}" for n in before]
        new = [f"{DOCUMENT}:p{page}:l{n}" for n in after]
        if len(set(old)) != len(old) or sorted(old) != sorted(new) or used.intersection(old):
            raise ValueError("Invalid BASF reviewed permutation")
        if any(key not in by_id for key in old):
            raise ValueError("Missing BASF reviewed occurrence: " + name)
        start = positions[old[0]]
        span = ordered[start:start + len(old)]
        if [u["id"] for u in span] != old:
            raise ValueError("BASF reviewed span is no longer contiguous: " + name)
        bound = [{k: u[k] for k in BIND_FIELDS} for u in span]
        if digest(bound) != expected:
            raise ValueError("BASF reviewed text or geometry changed: " + name)
        ordered[start:start + len(old)] = [by_id[key] for key in new]
        used.update(old)
        decisions.append({"id": name, "page": page, "before": old, "after": new,
                          "source_units_sha256": expected,
                          "review": "IMPLEMENTER_SOURCE_IMAGE_REVIEW"})
    return ordered, decisions
