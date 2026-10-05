"""Build and render the separate closure addendum; image review is a separate action."""
import json,os,subprocess,sys,time
from scripts import run_prospectus_closure_next as m
def run():
    cmd=["latexmk","-pdf","-interaction=nonstopmode","-halt-on-error","addendum.tex"]
    start=time.monotonic()
    built=subprocess.run(cmd,cwd=m.OUT,capture_output=True,text=True,timeout=90)
    (m.OUT/"addendum-build.log").write_text(built.stdout+built.stderr)
    if built.returncode:raise ValueError("LaTeX build failed; see addendum-build.log")
    render=[m.TEXTPY,"-m","scripts.prospectus_closure_document","render"]
    rendered=subprocess.run(render,cwd=m.ROOT,capture_output=True,text=True,timeout=60)
    (m.OUT/"addendum-render.log").write_text(rendered.stdout+rendered.stderr)
    if rendered.returncode:raise ValueError("Rendering failed")
    m.write(m.OUT/"document-build.json",{"status":"PASS","command":cmd,"render_command":render,
        "wall_seconds":round(time.monotonic()-start,3),"tex_sha256":m.sha(m.OUT/"addendum.tex"),
        "pdf_sha256":m.sha(m.OUT/"addendum.pdf"),"rendered_review":"PENDING",
        "human_prose_acceptance":"PENDING"})
    print(json.dumps({"status":"PASS","pdf":"addendum.pdf","pages":len(m.read(m.OUT/"addendum-pages.json")["pages"])}))
def render():
    os.environ["CUDA_VISIBLE_DEVICES"]="-1"
    import fitz
    pdf=m.OUT/"addendum.pdf";folder=m.OUT/"addendum-pages";folder.mkdir(exist_ok=True)
    rows=[]
    with fitz.open(pdf) as doc:
        for i,page in enumerate(doc):
            path=folder/f"page-{i+1:02d}.png";page.get_pixmap(dpi=120).save(path)
            rows.append({"page":i+1,"image":str(path.relative_to(m.ROOT)),"sha256":m.sha(path),"text":page.get_text()})
    m.write(m.OUT/"addendum-pages.json",{"pdf_sha256":m.sha(pdf),"pages":rows})
    print("Rendered",len(rows),"pages; CPU only")
if __name__=="__main__":
    if sys.argv[1:]!=["render"]:raise ValueError("Use the master for document builds")
    render()
