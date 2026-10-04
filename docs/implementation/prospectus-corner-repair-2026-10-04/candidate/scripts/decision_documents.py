"""Build the unified monograph and preserve the pre-round substantive content."""
from pathlib import Path
import json
import os
import re
import subprocess
from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.diversity import save
ROOT=Path(__file__).resolve().parents[1]
PY=Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')

def run(out):
    out=Path(out);book=ROOT/'docs/monograph'
    baseline=json.loads((ROOT/'artifacts/interpretation/round13/document-baseline.json').read_text())
    changed=[];missing=[]
    for name,sha in baseline['files'].items():
        path=ROOT/name
        if not path.exists():missing.append(name)
        elif raw_digest(path.read_bytes())!=sha:changed.append(name)
    # The protected baseline also captured the build's expanded TeX output.
    # Its change is required by the added input, not an authored-source deletion.
    allowed=['docs/monograph/references.bib','docs/monograph/chapters/06-ensemble.tex',
             'docs/monograph/review/reader-facing/monograph-expanded.tex']
    if missing or set(changed)-set(allowed):raise ValueError('Unreviewed substantive manuscript changes')
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'}
    commands=[[str(PY),str(ROOT/'scripts/build_reader_facing_monograph.py')],
              [str(PY),str(ROOT/'scripts/check_monograph.py')]]
    for i,command in enumerate(commands):
        with (out/('build-'+str(i)+'.log')).open('w') as log:
            subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    info=subprocess.check_output(['pdfinfo',str(book/'monograph.pdf')],text=True)
    pages=int(re.search(r'Pages:\s+(\d+)',info).group(1))
    same=(book/'monograph.pdf').read_bytes()==(ROOT/'docs/proposal/proposal.pdf').read_bytes()
    if pages<baseline['previous_pages'] or not same:raise ValueError('Book shrinkage or proposal alias mismatch')
    subprocess.run(['pdftotext','-layout',str(book/'monograph.pdf'),str(out/'text.txt')],check=True)
    text=(out/'text.txt').read_text();title='A certificate requirement is a different question'
    pages_text=text.split('\f');locations=[i+1 for i,t in enumerate(pages_text) if title in t]
    value={'status':'PRESERVED_AND_BUILT','previous_pages':baseline['previous_pages'],'pages':pages,
           'proposal_alias_identical':same,'changed_existing_sources':changed,'new_unit':'chapters/06c-typed-decisions.tex',
           'new_unit_page_locations':locations,'commands':commands,'human_readability_review':'PENDING',
           'source_integrity':'Original source files unchanged except an added input and appended bibliography entries',
           'release_eligible':False}
    save(out/'result.json',value);return value
