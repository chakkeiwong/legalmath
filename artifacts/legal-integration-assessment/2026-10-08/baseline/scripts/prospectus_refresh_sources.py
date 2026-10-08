"""Fail-closed, source-bound development admission utilities."""
from pathlib import Path
from collections import Counter
import hashlib, json, math, re, xml.etree.ElementTree as ET

def norm(text):
    return re.sub(r"\s+", " ", text).strip()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def anchor(row, document, page, quote):
    require(type(page) is int and 1 <= page <= len(document["pages"]), "Invalid anchor page")
    text = norm(document["pages"][page - 1]["text"])
    quote = norm(quote)
    require(bool(quote) and text.count(quote) == 1, "Anchor absent or ambiguous: " + quote[:100])
    start = text.index(quote)
    return {"document": row["id"], "original": row["original"],
            "source_sha256": row["sha256"], "text": row["text"],
            "text_sha256": row["text_sha256"], "page": page,
            "start": start, "end": start + len(quote), "quote": quote}

def replay(value, root):
    for field, key in (("original", "source_sha256"), ("text", "text_sha256")):
        path = (Path(root) / value[field]).resolve()
        require(path.is_relative_to(Path(root).resolve()), "Anchor outside worktree")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == value[key], "Anchor file changed")
    doc = json.loads((Path(root) / value["text"]).read_text())
    require(doc["source_sha256"] == value["source_sha256"], "Wrong derivative original")
    page, start, end = value["page"], value["start"], value["end"]
    require(type(page) is int and type(start) is int and type(end) is int, "Noninteger anchor locator")
    require(1 <= page <= len(doc["pages"]) and 0 <= start < end, "Anchor locator out of range")
    require(norm(doc["pages"][page-1]["text"])[start:end] == value["quote"], "Anchor text changed")

def checked_choice(text, label):
    """Checkbox glyph and full label must be adjacent; bare labels never select."""
    matches = re.findall(r"([\uf078\uf06f☒☐])\s*" + re.escape(label) + r"(?=\s|$)", norm(text))
    require(len(matches) == 1, "Missing or ambiguous checkbox label: " + label)
    return matches[0] in ("\uf078", "☒")

def yes_no(text, english, german):
    text = norm(text)
    pattern = re.escape(english) + r"\s+(Yes|No)\s+" + re.escape(german) + r"\s+(Ja|Nein)(?=\s|$)"
    found = re.findall(pattern, text)
    require(len(found) == 1, "Missing or ambiguous bilingual selection: " + english)
    en, de = found[0]
    require((en == "Yes") == (de == "Ja"), "Conflicting bilingual selection")
    return en == "Yes"

def region_extract(xml, *, page_number, split, body_end, languages=("de", "en"), line_tolerance=0.75):
    """Partition every PDF word, without OCR/translation or language guessing."""
    require(type(page_number) is int and page_number > 0, "Invalid PDF page")
    require(languages == ("de", "en"), "Unreviewed language/region mapping")
    require(all(type(v) in (int,float) and math.isfinite(v) for v in (split, body_end, line_tolerance)),
            "Nonfinite region geometry")
    require(line_tolerance == 0.75, "Unreviewed line tolerance")
    doc = ET.fromstring(xml)
    pages = [e for e in doc.iter() if e.tag.rsplit("}",1)[-1] == "page"]
    require(len(pages) == 1, "Expected exactly one physical page")
    pg = pages[0]; width, height = float(pg.attrib["width"]), float(pg.attrib["height"])
    require(all(math.isfinite(v) for v in (width,height)) and 0 < split < width and 0 < body_end < height,
            "Invalid region dimensions")
    tokens = []
    for node in pg.iter():
        if node.tag.rsplit("}",1)[-1] != "word":
            continue
        coords = [float(node.attrib[k]) for k in ("xMin","yMin","xMax","yMax")]
        x0,y0,x1,y1 = coords
        require(all(math.isfinite(v) for v in coords) and 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height,
                "Invalid word geometry")
        text = "".join(node.itertext())
        require(bool(text.strip()), "Empty word token")
        if y0 >= body_end:
            region = "footer"
        else:
            require(y1 < body_end, "Word crosses footer boundary")
            require(x1 < split or x0 > split, "Word crosses column boundary")
            region = "de" if x1 < split else "en"
        tokens.append({"id": len(tokens), "text": text, "bbox": coords, "region": region})
    require(tokens, "No text tokens")
    footer = [t for t in tokens if t["region"] == "footer"]
    require([t["text"] for t in footer] == [str(page_number)], "Footer is not solely the physical page label")
    result = {}
    for lang in languages:
        words = sorted([t for t in tokens if t["region"] == lang], key=lambda t:(t["bbox"][1],t["bbox"][0]))
        require(words, "Missing language column")
        lines = []
        for word in words:
            if not lines or word["bbox"][1] - lines[-1]["y"] > line_tolerance:
                lines.append({"y":word["bbox"][1], "words":[]})
            lines[-1]["words"].append(word)
        chunks, order, offset, out_lines = [], [], 0, []
        for line in lines:
            ordered = sorted(line["words"], key=lambda w:w["bbox"][0])
            for left,right in zip(ordered,ordered[1:]):
                require(left["bbox"][2] <= right["bbox"][0] + 0.05, "Overlapping text within line")
            phrase = " ".join(w["text"] for w in ordered)
            ids = [w["id"] for w in ordered]; order.extend(ids)
            out_lines.append({"start":offset,"end":offset+len(phrase),"word_ids":ids})
            chunks.append(phrase); offset += len(phrase)+1
        result[lang] = {"text":"\n".join(chunks), "word_ids":order, "lines":out_lines}
    assigned = result["de"]["word_ids"] + result["en"]["word_ids"] + [t["id"] for t in footer]
    require(Counter(assigned) == Counter(range(len(tokens))), "Lost or duplicated source word")
    return {"page":page_number,"width":width,"height":height,"split":split,"body_end":body_end,
            "line_tolerance":line_tolerance,"columns":result,"words":tokens,
            "footer_word_ids":[t["id"] for t in footer],"all_words_assigned_once":True,
            "automatic_ocr_performed":False,"translation_performed":False}

def verify_region(expected, xml):
    actual = region_extract(xml, page_number=expected["page"], split=expected["split"],
                            body_end=expected["body_end"], line_tolerance=expected["line_tolerance"])
    require(actual == expected, "Region text/word map changed")
    return actual
