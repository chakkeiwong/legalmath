"""Optional geometric relation suggestions; never admitted legal dependencies."""
from collections import defaultdict
import math
import re
from statistics import median

from .contracts import digest
from .occurrences import anchor

PROFILE = "enumerated-row-candidates.v1"
SCOPED_PROFILE = "explicit-scope-candidates.v2"
_MARKER = re.compile(r"\([ivxlcdm]+\)", re.IGNORECASE)
_NOTE = re.compile(r"^Note\s+that\b", re.IGNORECASE)


def _valid_box(box):
    return (isinstance(box, (list, tuple)) and len(box) == 4
            and all(type(x) in (int, float) and math.isfinite(x) for x in box)
            and box[0] < box[2] and box[1] < box[3])


def _spans(units):
    return [anchor(u, 0, len(u["raw"])) for u in sorted(units, key=lambda u: (u["order"], u["id"]))]


def _extent(units, top, height):
    """Stop a candidate region at the first large vertical gap, retaining ties."""
    selected = []
    bottom = top
    for unit in sorted(units, key=lambda u: (u["bbox"][1], u["bbox"][0], u["id"])):
        if unit["bbox"][1] - bottom > 2.25 * height:
            break
        selected.append(unit)
        bottom = max(bottom, unit["bbox"][3])
    return selected


def discover(graph, profile=PROFILE):
    if profile not in (PROFILE, SCOPED_PROFILE):
        raise ValueError("Unsupported relation discovery profile")
    units = graph["units"]
    if len({u["id"] for u in units}) != len(units):
        raise ValueError("Duplicate source occurrence in relation discovery")
    pages = defaultdict(list)
    for unit in units:
        if unit["text_sha256"] != digest(unit["raw"].encode()):
            raise ValueError("Source text changed before relation discovery")
        pages[(unit["document"], unit["source_sha256"], unit["page"])].append(unit)
    candidates, diagnostics = [], []

    def propose(kind, left, right, marker):
        edge = {"kind": kind, "from": _spans(left), "to": _spans(right),
                "row_marker": anchor(marker, 0, len(marker["raw"])),
                "scope": "Candidate within one printed enumerated row",
                "basis": "RAW_TEXT_AND_GEOMETRY; NO REVIEWED_TARGET_INPUT",
                "status": "REQUIRES_REVIEW", "legal_scope_established": False}
        candidates.append({"id": "relation-candidate:" + digest(edge), **edge})

    for (document, source, page), raw in sorted(pages.items()):
        info = {"document": document, "source_sha256": source, "page": page}
        if any(not _valid_box(u.get("bbox")) or
               any(not _valid_box(w.get("bbox")) for w in u.get("words", [])) for u in raw):
            diagnostics.append({**info, "reason": "UNKNOWN_OR_INVALID_PAGE_GEOMETRY", "proposed": 0})
            continue
        # Ignore isolated scan-edge punctuation only for candidate selection;
        # every original unit remains in the source graph and its accounting.
        content = [u for u in raw if any(c.isalnum() for c in u["raw"])]
        if not content:
            diagnostics.append({**info, "reason": "NO_TEXT_FOR_ROW_GRAMMAR", "proposed": 0})
            continue
        height = median(u["bbox"][3] - u["bbox"][1] for u in content)
        markers = sorted((u for u in content if _MARKER.fullmatch(u["raw"].strip())),
                         key=lambda u: (u["bbox"][1], u["bbox"][0], u["id"]))
        before = len(candidates)
        # Distinct marker columns are independent table candidates.
        columns = []
        for marker in markers:
            column = next((c for c in columns if abs(c[0]["bbox"][0] - marker["bbox"][0]) <= .5 * height), None)
            if column is None:
                columns.append([marker])
            else:
                column.append(marker)
        for column in columns:
            seeds = []
            for marker in column:
                first = sorted((u for u in content if u["bbox"][0] > marker["bbox"][2]
                                and abs(u["bbox"][1] - marker["bbox"][1]) <= .5 * height),
                               key=lambda u: (u["bbox"][0], u["id"]))
                pairs = [(b["bbox"][0] - a["bbox"][2], b["bbox"][0]) for a, b in zip(first, first[1:])]
                if pairs:
                    gap, start = max(pairs)
                    if gap >= height:
                        seeds.append(start)
            # Require a uniquely supported repeated value column. An isolated
            # largest gap is insufficient to distinguish a cell from prose.
            clusters = []
            for start in sorted(seeds):
                cluster = next((c for c in clusters if abs(median(c) - start) <= .5 * height), None)
                if cluster is None:
                    clusters.append([start])
                else:
                    cluster.append(start)
            supported = [c for c in clusters if len(c) >= 2]
            if len(supported) != 1:
                continue
            split = median(supported[0]) - .5 * height
            for index, marker in enumerate(column):
                top = marker["bbox"][1]
                stop = column[index + 1]["bbox"][1] - .5 * height if index + 1 < len(column) else math.inf
                region = [u for u in content if u["bbox"][0] > marker["bbox"][2]
                          and top - .5 * height <= u["bbox"][1] < stop]
                # A source unit crossing the inferred column is ambiguous.
                if any(u["bbox"][0] < split < u["bbox"][2] for u in region):
                    continue
                left = _extent([u for u in region if u["bbox"][2] <= split], top, height)
                right = _extent([u for u in region if u["bbox"][0] >= split], top, height)
                if not left or not right or not _spans(left)[-1]["quote"].rstrip().endswith(":"):
                    continue
                notes = [u for u in right if _NOTE.match(u["raw"].lstrip())]
                if len(notes) > 1:
                    continue
                qualifier = []
                if notes:
                    note_top = notes[0]["bbox"][1]
                    qualifier = [u for u in right if u["bbox"][1] >= note_top - .5 * height]
                    right = [u for u in right if u not in qualifier]
                if not right:
                    continue
                propose("label-value", left, right, marker)
                if qualifier:
                    propose("qualifies", qualifier, right, marker)
        diagnostics.append({**info, "reason": "BOUNDED_ROW_GRAMMAR_ONLY",
                            "proposed": len(candidates) - before})
    limits = ["Enumerated two-column rows and English Note that only",
              "OCR errors remain in exact raw quotations",
              "Candidates do not establish complete cells or governing legal scope",
              "No independent legal acceptance or answer promotion"]
    if profile == SCOPED_PROFILE:
        from .relation_scope import scoped_candidates
        scoped, scope_diagnostics = scoped_candidates(graph)
        candidates.extend(scoped)
        diagnostics.extend(scope_diagnostics)
        limits[0] = "Enumerated rows, explicit English regulatory-rating paragraphs and German all-option margins only"
    return {"version": profile, "source_graph_sha256": digest(graph),
            "candidates": sorted(candidates, key=lambda c: c["id"]), "diagnostics": diagnostics,
            "accepted_relations": [], "legal_scope_inferred": False,
            "limits": limits}
