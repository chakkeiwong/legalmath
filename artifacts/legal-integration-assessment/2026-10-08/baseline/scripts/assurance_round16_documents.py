"""Build and preserve the unified monograph after the local implementation."""
import os
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,indent=2)+'\n')

OUT = ROOT/'artifacts/interpretation/round16'
BOOK = ROOT/'docs/monograph'
INCLUSION = '\n\\input{chapters/06f-input-meaning}\n'


def run():
    baseline=read(OUT/'baseline.json');preserved=[]
    for name,h in baseline['manuscript_files'].items():
        if Path(name).suffix not in ('.tex','.bib'):continue
        previous=(OUT/'manuscript-baseline'/name).read_text();current=(ROOT/name).read_text()
        assert sha(OUT/'manuscript-baseline'/name)==h
        if name.endswith('/06-ensemble.tex'):current=current.replace(INCLUSION,'')
        assert current==previous,name
        preserved.append(name)
    chapter=BOOK/'chapters/06-ensemble.tex'
    if INCLUSION not in chapter.read_text():chapter.write_text(chapter.read_text()+INCLUSION)
    began=time.monotonic();commands=[];out=OUT/'document-build';out.mkdir(exist_ok=True)
    for script in ('build_reader_facing_monograph.py','check_monograph.py'):
        cmd=['/home/chakwong/miniconda3/envs/tfgpu/bin/python',str(ROOT/'scripts'/script)];commands.append(cmd)
        with (out/(script+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    import fitz
    pdf=fitz.open(BOOK/'monograph.pdf');old=fitz.open(OUT/'manuscript-baseline/docs/monograph/monograph.pdf')
    assert len(old)==273 and len(pdf)>=273
    assert sha(BOOK/'monograph.pdf')==sha(ROOT/'docs/proposal/proposal.pdf')
    pages=[];render=OUT/'document-render';render.mkdir(exist_ok=True)
    title='Repairing the distinctions that a comparison can lose'
    begin=next(i for i,p in enumerate(pdf) if title in ' '.join(p.get_text().split()) and i>30)
    def chapter7(doc):
        return next(i for i,p in enumerate(doc) if i>100 and 'Chapter 7' in p.get_text())
    end=chapter7(pdf)
    for i in range(begin,end):
        target=render/f'page-{i+1:03}.png';pdf[i].get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(target)
        pages.append({'pdf_page':i+1,'image':str(target.relative_to(ROOT)),'sha256':sha(target),
                      'text':pdf[i].get_text()})
    def normalized(text):
        return '\n'.join(line for line in text.splitlines() if not re.fullmatch(r'\s*\d+\s*',line))
    old_start=chapter7(old);differences=[]
    assert len(pdf)-end==len(old)-old_start
    for j in range(len(old)-old_start):
        if normalized(old[old_start+j].get_text())!=normalized(pdf[end+j].get_text()):
            differences.append({'old_page':old_start+j+1,'new_page':end+j+1})
    assert not differences,differences
    save(render/'pages.json',pages)
    save(OUT/'document-build.json',{'status':'BUILT_RENDERED_REVIEW_PENDING','commands':commands,
        'wall_seconds':time.monotonic()-began,'baseline_pages':len(old),'pages':len(pdf),
        'companion_pages':len(fitz.open(BOOK/'technical-companion.pdf')),
        'new_section_pages':[begin+1,end],'preserved_authored_files':preserved,
        'later_pages_preserved':True,'later_text_differences_excluding_page_numbers':differences,
        'pdf_sha256':sha(BOOK/'monograph.pdf'),'new_source':'docs/monograph/chapters/06f-input-meaning.tex',
        'human_readability_acceptance':'PENDING','release_eligible':False})
    print({'pages':len(pdf),'new_section_pages':[begin+1,end],'preserved_files':len(preserved)})


if __name__=='__main__':run()
