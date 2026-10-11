"""One-off retained-source inspection; not a product source parser."""

import hashlib
import html
import json
import shutil
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCES = {
    "23EC53": "docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2023).json",
    "26EC22": "docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json",
    "26EC23": ".localresources/sfc/26EC23.json",
}


def normalize(text):
    return " ".join(html.unescape(text).split())


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.li_stack = []
        self.p_stack = []
        self.sup_stack = []
        self.units = []
        self.notes = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            for li in self.li_stack:
                li["contains_nested_li"] = True
            self.li_stack.append({"li_index": len(self.units) + len(self.li_stack) + 1, "chunks": [], "contains_nested_li": False})
        elif tag == "p":
            self.p_stack.append({"chunks": [], "first_sup": None})
        elif tag == "sup":
            first = bool(self.p_stack) and not "".join(self.p_stack[-1]["chunks"]).strip()
            self.sup_stack.append({"chunks": [], "first": first})

    def handle_endtag(self, tag):
        if tag == "sup" and self.sup_stack:
            sup = self.sup_stack.pop()
            if sup["first"] and self.p_stack:
                self.p_stack[-1]["first_sup"] = normalize("".join(sup["chunks"]))
        elif tag == "p" and self.p_stack:
            p = self.p_stack.pop()
            num = p["first_sup"]
            if num and num.isdigit():
                self.notes.append({"footnote": num, "text": normalize("".join(p["chunks"]))})
        elif tag == "li" and self.li_stack:
            li = self.li_stack.pop()
            li["text"] = normalize("".join(li.pop("chunks")))
            self.units.append(li)

    def handle_data(self, data):
        for li in self.li_stack:
            li["chunks"].append(data)
        for p in self.p_stack:
            p["chunks"].append(data)
        for sup in self.sup_stack:
            sup["chunks"].append(data)


def inspect(name, path):
    source = ROOT / path
    raw = source.read_bytes()
    doc = json.loads(raw)
    parser = Blocks()
    parser.feed(doc["html"])
    paragraphs = sorted(parser.units, key=lambda li: li["li_index"])
    notes = parser.notes
    record = {
        "refNo": doc["refNo"],
        "title": doc["title"],
        "releasedDate": doc["releasedDate"],
        "source_path": path,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "units": paragraphs,
        "footnotes": notes,
        "extraction": "stdlib HTMLParser; text-node concatenation and whitespace normalization; original JSON retained; not qualified product units",
    }
    (OUT / f"{name}-inspection.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    shutil.copyfile(source, OUT / f"{name}-retained.json")
    print(json.dumps({"source": name, "paragraphs": len(paragraphs), "nested_li": any(x["contains_nested_li"] for x in paragraphs), "footnotes": len(notes), "releasedDate": doc["releasedDate"], "sha256": record["sha256"]}))
    return record


def main():
    records = {name: inspect(name, path) for name, path in SOURCES.items()}
    older, newer = records["23EC53"], records["26EC22"]
    changes = [
        {"paragraph": before["li_index"], "old": before["text"], "new": after["text"]}
        for before, after in zip(older["units"], newer["units"])
        if before["text"] != after["text"]
    ]
    comparison = {
        "old": older["sha256"],
        "new": newer["sha256"],
        "paragraph_count_equal": len(older["units"]) == len(newer["units"]),
        "changed_paragraphs": changes,
        "footnotes_equal": older["footnotes"] == newer["footnotes"],
        "limitation": "Normalized retained text comparison; does not prove legal equivalence or current source completeness.",
    }
    (OUT / "edition-comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"changed_paragraphs": [x["paragraph"] for x in changes], "footnotes_equal": comparison["footnotes_equal"]}))
    for path, target in [
        ("docs/implementation/legal-mission-control/mission.json", "mission-before.json"),
        ("artifacts/legal-mission-control/2026-10-10/live-pilot-400/authorization.json", "authorization-before.json"),
    ]:
        destination = OUT / target
        if not destination.exists():
            shutil.copyfile(ROOT / path, destination)
    (OUT / "inspection-run.json").write_text(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(), "interpreter": sys.executable, "sources": {name: record["sha256"] for name, record in records.items()}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
