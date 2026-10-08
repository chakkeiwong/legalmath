"""Render the repaired narrative and retain the inspected source-page images."""
from pathlib import Path
import hashlib
import json
import shutil
import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-repair-2026-10-06/document-review"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, phrase, count in (("monograph", "What the executed repairs establish", 5),
                                ("technical-companion", "Current repair receipts", 2)):
        source = ROOT / "docs/monograph" / (name + ".pdf")
        doc = fitz.open(source)
        matches = [i for i, page in enumerate(doc) if phrase in page.get_text()]
        if len(matches) != 1:
            raise ValueError("Expected one changed section: " + name)
        start = matches[0]
        chosen = range(max(0,start-1),min(start+count,len(doc)))
        rows.append({"document": str(source.relative_to(ROOT)),
                     "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                     "physical_pages": [i+1 for i in chosen]})
        for i in chosen:
            doc[i].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(OUT / (name + "-%d.png" % (i+1)))
        for batch in range(0,len(chosen),4):
            sheet = Image.new("RGB",(1400,2000),"#dddddd")
            draw = ImageDraw.Draw(sheet)
            for j,i in enumerate(list(chosen)[batch:batch+4]):
                image = Image.open(OUT / (name + "-%d.png" % (i+1)))
                image.thumbnail((680,950))
                x = (j%2)*700 + (700-image.width)//2
                y = (j//2)*1000 + 30
                sheet.paste(image,(x,y))
                draw.text((x,y-20),"Physical page %d" % (i+1),fill="black")
            sheet.save(OUT / (name + "-sheet-%d.png" % (batch//4+1)))
    for name in ("prospectus-basf-bracket-112.png", "prospectus-basf-bracket-113.png", "prospectus-basf-range-12.png"):
        # A checkout contains the inspected source images. Temporary renders are
        # needed only for the initial capture, not for reproducing the review.
        if not (OUT / name).is_file():
            shutil.copyfile(Path("/tmp") / name, OUT / name)
    manifest = {"documents": rows, "images": {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob("*.png")},
                "review": "See REVIEW.md for the actual visual inspection and source findings"}
    (OUT / "rendered-pages.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(rows,indent=2))


if __name__ == "__main__":
    main()
