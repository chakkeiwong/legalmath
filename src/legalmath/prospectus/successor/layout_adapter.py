"""Conservative exact-character maps from optional layout items to retained words."""
from .contracts import digest


def map_layout(raw_units, document, *, source_sha256):
    if any(u["source_sha256"] != source_sha256 for u in raw_units):
        raise ValueError("Layout source edition mismatch")
    mappings, failures = [], []
    # Keep every text label, including footnotes, headers and legal margins.
    for item in document.get("texts", []):
        text = item.get("text", "")
        marker = item.get("marker", "") if item.get("enumerated") else ""
        if marker and not text.lstrip().startswith(marker):
            text = marker + " " + text
        provenance = item.get("prov", [])
        if len(provenance) != 1:
            failures.append({"item": item.get("self_ref"), "reason": "Multi-page/missing geometry requires explicit mapping"})
            continue
        prov = provenance[0]
        page = prov["page_no"]
        box = prov["bbox"]
        left, top, right, bottom = box["l"], box["t"], box["r"], box["b"]
        if box.get("coord_origin") == "BOTTOMLEFT":
            height = document["pages"][str(page)]["size"]["height"]
            top, bottom = height-top, height-bottom
        words = []
        for unit in raw_units:
            if unit["page"] != page:
                continue
            for word in unit.get("words", []):
                x0,y0,x1,y1 = word["bbox"]
                if left <= (x0+x1)/2 <= right and top <= (y0+y1)/2 <= bottom:
                    words.append((unit, word))
        # Word font metrics can differ within a line. Use the retained line
        # order, then the original word offset; sorting word y reordered bold
        # definitions and made exact text look lost in the first trial.
        words.sort(key=lambda pair: (round(pair[0].get("bbox", pair[1]["bbox"])[1], 1),
                                     pair[0].get("bbox", pair[1]["bbox"])[0], pair[1]["start"]))
        raw_chars = [(unit["id"], word["start"]+i, char) for unit, word in words
                     for i,char in enumerate(word["text"]) if not char.isspace()]
        candidate_chars = [(i, char) for i, char in enumerate(text) if not char.isspace()]
        if not raw_chars or [r[2] for r in raw_chars] != [r[1] for r in candidate_chars]:
            failures.append({"item": item.get("self_ref"), "label": item.get("label"), "page": page,
                "reason": "Candidate characters differ from retained words or reading order", "candidate": text,
                "retained": " ".join(word["text"] for unit, word in words)})
            continue
        mappings.append({"item": item.get("self_ref"), "label": item.get("label"), "page": page,
            "text": text, "structural_marker": marker, "characters": [{"output": c[0], "unit": r[0], "source_offset": r[1], "character": r[2]}
                                         for c,r in zip(candidate_chars, raw_chars)],
            "whitespace": "Candidate whitespace is formatting; original words and boxes remain unchanged"})
    return {"version": "layout-map.v1", "source_sha256": source_sha256, "raw_units_sha256": digest(raw_units),
            "mappings": mappings, "failures": failures, "raw_replaced": False,
            "margin_attachment": "Requires explicit relation; geometric adjacency does not establish governing scope"}
