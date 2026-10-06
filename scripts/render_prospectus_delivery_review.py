"""Render changed manuscript pages and BASF source details for visual inspection."""
from pathlib import Path
import json
import fitz
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/implementation/prospectus-successor-2026-10-06/document-review"


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    import sys
    if len(sys.argv)>1:
        import base64,io
        names={"book1":"monograph-sheet-1.png","book2":"monograph-sheet-2.png","basf112":"basf-112.png","basf129":"basf-129.png"}
        recorded=json.loads((OUT/"rendered-pages.json").read_text())
        names.update({f"page{n}":f"monograph-{n}.png" for n in recorded["monograph_physical_pages"]})
        names.update({f"companion{n}":f"companion-{n}.png" for n in recorded.get("companion_physical_pages",[])})
        pic=Image.open(OUT/names[sys.argv[1]])
        buffer=io.BytesIO();pic.save(buffer,format="JPEG",quality=75)
        print(base64.b64encode(buffer.getvalue()).decode())
        return
    book=fitz.open(ROOT/"docs/monograph/monograph.pdf")
    starts=[i for i,p in enumerate(book) if "From selected terms to a qualified prospectus" in p.get_text() and len(p.get_text())>1500]
    start=starts[-1]
    end=next((i for i in range(start+1,len(book))
              if "Marketing rules require exceptions and judgment" in book[i].get_text()),
             min(len(book)-1,start+7))
    pages=list(range(max(0,start-1),end+1))
    for i in pages:
        pix=book[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5))
        pix.save(OUT/f"monograph-{i+1}.png")
    for batch in range(0,len(pages),4):
        chosen=pages[batch:batch+4]
        sheet=Image.new("RGB",(1400,2000),"#dddddd")
        draw=ImageDraw.Draw(sheet)
        for j,i in enumerate(chosen):
            pic=Image.open(OUT/f"monograph-{i+1}.png")
            pic.thumbnail((680,950))
            x=(j%2)*700+(700-pic.width)//2;y=(j//2)*1000+30
            sheet.paste(pic,(x,y));draw.text((x,y-20),f"Physical page {i+1}",fill="black")
        sheet.save(OUT/f"monograph-sheet-{batch//4+1}.png")
    companion=fitz.open(ROOT/"docs/monograph/technical-companion.pdf")
    appendix=[i for i,p in enumerate(companion) if "Campaign completion" in p.get_text()]
    if len(appendix)!=1:raise ValueError("Expected one prospectus appendix opening")
    companion_pages=list(range(appendix[0],min(len(companion),appendix[0]+2)))
    for i in companion_pages:
        companion[i].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f"companion-{i+1}.png")
    basf=fitz.open(ROOT/"docs/prospectus/evidence-closure/requests/037-basf-base-september-2022-exchange/response.bin")
    for i in (108,110,112,119,122,129,133):
        basf[i-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f"basf-{i}.png")
    (OUT/"rendered-pages.json").write_text(json.dumps({"monograph_physical_pages":[i+1 for i in pages],
        "basf_physical_pages":[108,110,112,119,122,129,133],
        "companion_physical_pages":[i+1 for i in companion_pages]},indent=2)+"\n")
    print(json.dumps({"monograph_pages":[i+1 for i in pages],"companion_pages":[i+1 for i in companion_pages],"output":str(OUT)}))


if __name__=="__main__":main()
