#!/usr/bin/env python3
"""Render the complete Markdown bond report as a readable, checked PDF.

Only presentation changes: expand the four-column inventory to numbered
entries and use the archived source URLs for portable prospectus hyperlinks.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import unicodedata

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'docs/implementation/bond-loss-absorption-classification'
BUILD=DIRECTORY/'pdf-build'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    result=subprocess.run(command,cwd=BUILD,text=True,capture_output=True,timeout=120)
    if result.returncode:
        raise RuntimeError(' '.join(command)+'\n'+result.stdout[-4000:]+'\n'+result.stderr[-4000:])
    return result


def text_key(text):
    text=unicodedata.normalize('NFKC',text).replace('\u00ad','')
    return ''.join(c.casefold() for c in text if c.isalnum())


def main():
    started=time.monotonic()
    BUILD.mkdir(exist_ok=True)
    source=DIRECTORY/'results.md'
    data=json.loads((DIRECTORY/'results.json').read_text())
    config=json.loads((DIRECTORY/'execution/delivery-config.json').read_text())
    source_urls={}
    for folder,_,*inventory_name in config['source_sets']:
        inventory=ROOT/'docs/prospectus'/folder/(inventory_name[0] if inventory_name else 'issue-inventory.json')
        for doc in json.loads(inventory.read_text())['documents'].values():
            source_urls[(ROOT/doc['original']).resolve()]=doc['url']
    links=[]
    def portable_link(match):
        label,target=match.group(1,2)
        if target.startswith(('http://','https://','#')):
            return match.group(0)
        local=(DIRECTORY/target).resolve()
        if not local.exists():
            raise ValueError('Missing report link: '+target)
        url=source_urls.get(local,target)
        links.append({'label':label,'original_target':target,'pdf_target':url})
        return '['+label+']('+url+')'
    original=source.read_text()
    portable=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',portable_link,original)
    lines=[];entries=[];table_count=0
    for line in portable.splitlines():
        if line.startswith('| Bond |'):
            table_count+=1
            continue
        if line.startswith('| --- |'):
            continue
        if line.startswith('| '):
            cells=[c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells)!=4:
                raise ValueError('Unexpected inventory columns')
            title,identity,answer,reason=cells
            entries.append(cells)
            lines += ['','```{=latex}',r'\begin{minipage}{\linewidth}','```','',
                      '### '+str(len(entries))+'. '+title,'',
                      '**ISIN / identity:** '+identity,'',
                      '**Result:** '+answer,'',reason,'',
                      '```{=latex}',r'\end{minipage}',r'\par\addvspace{1.1em}','```','']
        else:
            lines.append(line)
    if table_count!=1 or len(entries)!=len(data['results']):
        raise ValueError('Incomplete inventory conversion')
    if [r[0] for r in entries]!=[r['title'] for r in data['results']]:
        raise ValueError('Markdown and JSON series differ')
    printable=BUILD/'report.md'
    printable.write_text('\n'.join(lines)+'\n')
    header=BUILD/'header.tex'
    header.write_text(r'''\pagestyle{plain}
\hypersetup{pdftitle={Bond-by-bond loss-absorption results}}
\setlength{\emergencystretch}{3em}
\widowpenalty=10000
\clubpenalty=10000
''')
    command=['pandoc',str(printable),'--from=markdown','--to=latex','--standalone',
             '--pdf-engine=xelatex','--include-in-header='+str(header),
             '-V','geometry:a4paper,margin=20mm,headsep=7mm','-V','fontsize:11pt',
             '-V','mainfont:DejaVu Serif','-V','sansfont:DejaVu Sans',
             '-V','colorlinks:true','-V','linkcolor:blue','-V','urlcolor:blue',
             '-M','pagetitle:Bond-by-bond loss-absorption results',
             '-o',str(BUILD/'report.tex')]
    run(command)
    latex=['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','report.tex']
    for _ in range(2):
        run(latex)
    log=(BUILD/'report.log').read_text(errors='replace')
    problems=[line for line in log.splitlines() if
              'Overfull' in line or 'Missing character' in line or 'undefined references' in line]
    if problems:
        raise ValueError('PDF typography/reference warnings: '+repr(problems))
    pdf=BUILD/'report.pdf'
    reader=PdfReader(pdf)
    pages=[]
    for number,page in enumerate(reader.pages,1):
        page_text=page.extract_text() or ''
        body,separator,footer=page_text.rpartition('\n')
        if not separator or footer.strip()!=str(number):
            raise ValueError('Unexpected page footer; inspect extraction before comparing content')
        pages.append(body)
    text='\n'.join(pages)
    (BUILD/'rendered-text.txt').write_text(text)
    key=text_key(text)
    # Compare every field, not merely the number of headings. Remove Markdown
    # link syntax while retaining its visible label for the text comparison.
    missing=[]
    for index,cells in enumerate(entries,1):
        for field,cell in zip(('bond','identity','answer','reason'),cells):
            visible=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',cell)
            if text_key(visible) not in key:
                missing.append([index,field])
    for paragraph in re.split(r'\n\s*\n',portable):
        if paragraph.startswith('|') or not paragraph.strip():
            continue
        visible=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',paragraph)
        if text_key(visible) not in key:
            missing.append(['prose',visible[:70]])
    if missing:
        raise ValueError('PDF text lost report content: '+repr(missing))
    final=DIRECTORY/'results.pdf'
    shutil.copyfile(pdf,final)
    manifest={'source':str(source.relative_to(ROOT)),'source_sha256':sha(source),
              'data_sha256':sha(DIRECTORY/'results.json'),'pdf':str(final.relative_to(ROOT)),
              'pdf_sha256':sha(final),'pages':len(reader.pages),'bond_entries':len(entries),
              'all_report_fields_and_prose_preserved':True,'layout_warnings':problems,
              'prospectus_hyperlinks':links,'commands':[command,latex,latex],
              'renderer_sha256':sha(Path(__file__)),'wall_seconds':time.monotonic()-started,
              'visual_inspection':'PENDING','legal_correctness':'NOT_CERTIFIED_BY_PDF_BUILD'}
    (BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('commands','prospectus_hyperlinks')},indent=2))


if __name__=='__main__':
    main()
