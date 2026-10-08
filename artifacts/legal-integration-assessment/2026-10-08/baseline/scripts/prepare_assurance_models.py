"""Cache only Docling's layout model during the approved installation phase."""
from pathlib import Path
import hashlib
import inspect
import json
import os

os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'.localresources/assurance-tools'


def main():
    lock=BASE/'model-lock.json'
    if lock.exists():
        value=json.loads(lock.read_text())
        for name,expected in value['files'].items():
            if hashlib.sha256((BASE/'models'/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('Cached model identity changed: '+name)
        return
    from docling.utils.model_downloader import download_models
    signature=inspect.signature(download_models)
    switches={k:False for k in signature.parameters if k.startswith('with_')}
    if 'with_layout' not in switches:
        raise ValueError('Docling downloader interface changed; inspect before enabling any model download')
    switches['with_layout']=True
    destination=BASE/'models'
    download_models(output_dir=destination,**switches)
    paths=[p for p in destination.rglob('*') if p.is_file() and '.cache' not in p.parts]
    if not paths:raise ValueError('Layout model download produced no files')
    lock.write_text(json.dumps({'switches':switches,'files':{
        str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'limits':['Layout model only; table structure, generative picture descriptions and model OCR disabled.']},indent=2)+'\n')


if __name__=='__main__':main()
