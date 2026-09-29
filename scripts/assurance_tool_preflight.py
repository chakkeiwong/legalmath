"""Execute bounded local import/binary checks and retain tool identity."""
from argparse import ArgumentParser
from pathlib import Path
import importlib
import importlib.metadata
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'.localresources/assurance-tools'


def ocr_environment():
    env=dict(os.environ)
    env['LD_LIBRARY_PATH']=str(BASE/'ocr/usr/lib/x86_64-linux-gnu')+os.pathsep+env.get('LD_LIBRARY_PATH','')
    matches=list((BASE/'ocr/usr/share/tesseract-ocr').glob('*/tessdata'))
    if len(matches)!=1:raise ValueError('Exactly one local OCR data directory required')
    env['TESSDATA_PREFIX']=str(matches[0]);env['CUDA_VISIBLE_DEVICES']='-1'
    return env


def inspect_tools():
    rows=[]
    for package,module in [('docling','docling'),('pypdf','pypdf'),('pdfplumber','pdfplumber'),
                           ('pytesseract','pytesseract'),('cvc5','cvc5'),('clingo','clingo'),
                           ('inspect-ai','inspect_ai'),('reportlab','reportlab'),('torch','torch')]:
        try:
            importlib.import_module(module);version=importlib.metadata.version(package)
            if package=='torch' and '+cpu' not in version:raise ValueError('Expected a pinned CPU torch build')
            rows.append({'tool':package,'status':'AVAILABLE','version':version})
        except Exception as exc:rows.append({'tool':package,'status':'UNAVAILABLE','error':str(exc)})
    commands=[('tesseract',[str(BASE/'ocr/usr/bin/tesseract'),'--version']),
              ('pdftotext',['/usr/bin/pdftotext','-v']),('pdftoppm',['/usr/bin/pdftoppm','-v']),
              ('javac',[str(ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1/bin/javac'),'-version'])]
    for name,argv in commands:
        try:
            r=subprocess.run(argv,capture_output=True,text=True,timeout=20,env=ocr_environment() if name=='tesseract' else None,check=True)
            rows.append({'tool':name,'status':'AVAILABLE','version':(r.stdout+r.stderr).splitlines()[0]})
        except Exception as exc:rows.append({'tool':name,'status':'UNAVAILABLE','error':str(exc)})
    for filename in ('pitest-1.20.3.jar','pitest-entry-1.20.3.jar','pitest-command-line-1.20.3.jar','junit-4.13.2.jar','hamcrest-core-1.3.jar',
                     'commons-text-1.13.1.jar','commons-lang3-3.17.0.jar'):
        rows.append({'tool':filename,'status':'AVAILABLE' if (BASE/'jars'/filename).is_file() else 'UNAVAILABLE'})
    for name in ('tool-lock.json','model-lock.json'):
        try:
            value=json.loads((BASE/name).read_text());root=BASE/'models' if name=='model-lock.json' else BASE
            for filename,expected in value['files'].items():
                with (root/filename).open('rb') as stream:
                    actual=hashlib.file_digest(stream,'sha256').hexdigest()
                if actual!=expected:raise ValueError('Changed tool/model file: '+filename)
            rows.append({'tool':name,'status':'AVAILABLE','verified_files':len(value['files'])})
        except Exception as exc:rows.append({'tool':name,'status':'UNAVAILABLE','error':str(exc)})
    ra=Path('/home/chakwong/python/ResearchAssistant/src/research_assistant/ingest/pdf_extract.py')
    rows.append({'tool':'ResearchAssistant','status':'AVAILABLE' if ra.is_file() else 'UNAVAILABLE',
                 'shared_backend':'Poppler; not an independent OCR model'})
    return {'status':'PASS' if all(r['status']=='AVAILABLE' for r in rows) else 'MISSING_REQUIRED_TOOLS',
            'tools':rows,'cpu_only':True,'release_eligible':False,
            'deferred':['Tweety/s(CASP): clingo selected for finite graph check','KeY: scoped JML obligations required',
                        'MAPIE: independently labelled calibration corpus required','Catala: separate worktree integration pending']}


if __name__=='__main__':
    p=ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--required',action='store_true');a=p.parse_args()
    result=inspect_tools();out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if a.required and result['status']!='PASS':raise SystemExit(1)
