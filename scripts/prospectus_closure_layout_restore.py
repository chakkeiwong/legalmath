"""Restore a verified CPU Docling binary profile and model in empty locations."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT/'.localresources/prospectus/closure-runtime/layout-profile'
BASE = ROOT/'docs/implementation/prospectus-integration-closure/layout-restoration'
APP = ROOT/'.venv/bin/python'
PROFILE = Path('/tmp/prospectus-adoption-tools/lib/python3.11/site-packages')
MODELS = Path('/tmp/prospectus-adoption-models')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path, data):
    path.write_text(json.dumps(data,indent=2)+'\n')


WORKER = '''import hashlib,importlib.metadata,json,os,sys
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='-1'
root,models,output,revision=map(str,sys.argv[1:])
sys.path[:0]=[str(Path(root)/'src'),root]
from docling.document_converter import DocumentConverter,PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions,LayoutOptions
from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
from docling.datamodel.layout_model_specs import DOCLING_LAYOUT_V2
from legalmath.prospectus.successor import source_graph
from legalmath.prospectus.successor.layout_adapter import project_layout
data=json.loads((Path(root)/'docs/implementation/prospectus-adoption/phases/A3/attempt-008/layout-input.json').read_text())['pages'][0]
pdf=Path(root)/data['path']
assert hashlib.sha256(pdf.read_bytes()).hexdigest()==data['sha256']
options=PdfPipelineOptions(do_ocr=False,do_table_structure=False,document_timeout=180,
    artifacts_path=Path(models),accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU,num_threads=4),
    layout_options=LayoutOptions(model_spec=DOCLING_LAYOUT_V2.model_copy(update={'revision':revision})))
converter=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
converted=converter.convert(pdf,page_range=(112,112))
if str(converted.status)!='ConversionStatus.SUCCESS':
    raise ValueError('Restored layout did not complete: '+str(converted.status))
document=converted.document.export_to_dict()
units,_,_=source_graph.pdf_units(pdf,{'id':data['document'],'sha256':data['sha256'],'language':'de'})
units=[u for u in units if u['page']==112]
projection=project_layout(units,document,source_sha256=data['sha256'])
out=Path(output)
out.mkdir()
(out/'docling.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\\n')
(out/'projection.json').write_text(json.dumps(projection,ensure_ascii=False,indent=2)+'\\n')
print(json.dumps({'docling':importlib.metadata.version('docling'),'torch':importlib.metadata.version('torch'),
    'prefix':sys.prefix,'model_path':models,'source':data,'regions':len(projection['mappings']),
    'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1'}))
'''


def main():
    folder = BASE/f'attempt-{len(list(BASE.glob("attempt-*")))+1:03d}'
    folder.mkdir(parents=True)
    start = time.monotonic()
    env = {k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
    env.update(CUDA_VISIBLE_DEVICES='-1',PYTHONNOUSERSITE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
               HF_DATASETS_OFFLINE='1',PIP_NO_INDEX='1',TOKENIZERS_PARALLELISM='false')
    method = sha(__file__)
    commands = []
    write(folder/'started.json',{'method_sha256':method,'budget_seconds':600,'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1'})
    def expired(signum,frame):
        raise TimeoutError('600-second restoration budget exhausted')
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(600)
    def run(label,argv):
        remaining = max(1,600-(time.monotonic()-start))
        value = subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,timeout=min(240,remaining))
        (folder/(label+'.log')).write_bytes(value.stdout+value.stderr)
        commands.append({'name':label,'argv':list(map(str,argv)),'returncode':value.returncode})
        if value.returncode:
            raise ValueError(label+' failed; see retained log')
        return value.stdout
    try:
        run('baseline-dependencies',[PROFILE.parents[2]/'bin/python','-m','pip','check'])
        model_receipt = json.loads((ROOT/'docs/implementation/prospectus-adoption/tool-setup/layout-model/receipt.json').read_text())
        for row in model_receipt['files']:
            if sha(row['file'])!=row['sha256']:
                raise ValueError('Historical model bytes changed')
        records = {}
        for prefix,base in [('packages',PROFILE),('models',MODELS)]:
            for path in sorted(base.rglob('*')):
                if '__pycache__' in path.parts or path.suffix=='.pyc' or not path.is_file():
                    continue
                if path.is_symlink():
                    raise ValueError('Snapshot requires explicit treatment of symlink: '+str(path))
                records[prefix+'/'+str(path.relative_to(base))]={'sha256':sha(path),'bytes':path.stat().st_size}
        if sum(r['bytes'] for r in records.values())>3_000_000_000:
            raise ValueError('Profile exceeds declared storage budget')
        RESOURCE.mkdir(parents=True,exist_ok=True)
        archive = RESOURCE/'profile.tar'
        manifest = RESOURCE/'files.json'
        if archive.exists() or manifest.exists():
            if not archive.is_file() or not manifest.is_file() or json.loads(manifest.read_text())['files']!=records:
                raise ValueError('Existing profile missing or differs; preserve it and review a new profile')
            if sha(archive)!=json.loads(manifest.read_text())['archive_sha256']:
                raise ValueError('Profile archive changed')
        else:
            with tarfile.open(archive,'w') as stream:
                for name in records:
                    prefix,relative=name.split('/',1)
                    stream.add((PROFILE if prefix=='packages' else MODELS)/relative,arcname=name,recursive=False)
            write(manifest,{'files':records,'archive_sha256':sha(archive),'model_revision':model_receipt['revision']})
        shutil.copy2(manifest,folder/'profile-manifest.json')
        normalized = []
        with tempfile.TemporaryDirectory(prefix='closure-layout-restored-') as temporary:
            base = Path(temporary)
            probe = base/'probe.py'
            probe.write_text(WORKER)
            for trial in range(2):
                runtime = base/'runtime'
                run(f'venv-{trial}',[APP,'-m','venv',runtime])
                site = runtime/'lib/python3.11/site-packages'
                model_root = base/'models'
                with tarfile.open(archive,'r') as stream:
                    for member in stream:
                        if member.name not in records or not member.isfile():
                            raise ValueError('Unexpected archive member')
                        prefix,relative = member.name.split('/',1)
                        parent = site if prefix=='packages' else model_root
                        target = (parent/relative).resolve()
                        if not target.is_relative_to(parent.resolve()):
                            raise ValueError('Archive member escapes restore directory')
                        target.parent.mkdir(parents=True,exist_ok=True)
                        with stream.extractfile(member) as source, target.open('wb') as destination:
                            shutil.copyfileobj(source,destination)
                        target.chmod(member.mode)
                        if sha(target)!=records[member.name]['sha256']:
                            raise ValueError('Restored file differs')
                run(f'pip-check-{trial}',[runtime/'bin/python','-m','pip','check'])
                output = folder/f'run-{trial}'
                run(f'layout-{trial}',[runtime/'bin/python','-I',probe,ROOT,model_root,output,model_receipt['revision']])
                projection = json.loads((output/'projection.json').read_text())
                target = json.loads((ROOT/'docs/implementation/prospectus-integration-repair/layout-003/margin-target.json').read_text())
                # Every designated raw definition line must occur in a mapped region.
                mapped = json.dumps(projection['mappings'])
                if any(s['unit'] not in mapped for s in target['edge']['to']):
                    raise ValueError('Restored layout lost a designated shared definition')
                normalized.append(projection)
                if trial==0:
                    (model_root/'ds4sd--docling-layout-old/model.safetensors').unlink()
                    if all((model_root/name.split('/',1)[1]).is_file() for name in records if name.startswith('models/')):
                        raise ValueError('Missing model control did not remove its file')
                    shutil.rmtree(runtime)
                    shutil.rmtree(model_root)
            if normalized[0]!=normalized[1]:
                raise ValueError('Restored layout source mappings differ')
        if sha(__file__)!=method:
            raise ValueError('Restoration method changed')
        result={'status':'PASS','restorations':2,'missing_model_restored':True,'regions':len(normalized[0]['mappings']),
                'profile':'Verified binary snapshot; same-host Python/system libraries','automatic_legal_scope':False,
                'native_confinement':False,'fresh_wheel_installation':False}
    except (Exception,KeyboardInterrupt) as exc:
        result={'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
    finally:
        signal.alarm(0)
    result.update(commands=commands,method_sha256=method,wall_seconds=time.monotonic()-start,
        plan='docs/plans/prospectus-layout-restoration-2026-10-09.md',python=sys.version,
        cpu_gpu='CPU; CUDA_VISIBLE_DEVICES=-1',seeds='Pinned CPU layout baseline; no ranking inference',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    write(folder/'result.json',result)
    write(folder/'manifest.json',{'files':{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}})
    print(json.dumps({'directory':str(folder.relative_to(ROOT)),'status':result['status'],'error':result.get('error')}))
    if result['status']!='PASS':
        raise SystemExit(1)


if __name__=='__main__':
    main()
