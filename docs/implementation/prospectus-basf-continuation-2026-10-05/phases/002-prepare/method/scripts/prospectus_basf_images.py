"""Render source review contact sheets using the installed Pillow environment."""
import sys, json
from pathlib import Path
from PIL import Image, ImageDraw
folder = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parents[1]
rows = json.loads((folder/"prepared.json").read_text())
for offset in range(0,len(rows),4):
    subset = rows[offset:offset+4]
    sheet = Image.new("RGB",(1800,2520),"#dddddd")
    draw = ImageDraw.Draw(sheet)
    for i,row in enumerate(subset):
        image = Image.open(root/row["image"]).convert("RGB")
        image.thumbnail((880,1210))
        x,y = (i%2)*900,(i//2)*1260
        sheet.paste(image,(x,y+35))
        draw.text((x+5,y+8), row["document"]+" PDF "+str(row["page"]),fill="black")
    sheet.save(folder/f"contact-{offset//4+1:02d}.png")
