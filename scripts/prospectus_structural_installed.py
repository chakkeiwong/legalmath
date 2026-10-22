"""Isolated installed replay; load only JSON trial inputs from the worktree."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root,attempt=map(Path,sys.argv[1:3]);package=attempt/'installed'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path.insert(0,str(package))
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

def read(path):
    value=path.read_bytes()
    return json.loads(gzip.decompress(value) if path.suffix=='.gz' else value)

def delta(base,operations):
    import copy
    result=copy.deepcopy(base)
    for operation in operations:
        path=operation['path'];target=result
        if not path:result=operation['value'];continue
        for key in path[:-1]:target=target[key]
        if operation['op']=='delete':del target[path[-1]]
        else:target[path[-1]]=operation['value']
    return result

start=time.monotonic()
base=attempt.parent/'attempt-031'
saved=read(attempt/'answer.json.gz')
p=delta(read(base/'complete-products.json.gz'),saved['products_delta'])
expected=delta(read(base/'complete-expected-answer.json.gz'),saved['answer_delta'])
assert digest(p)==saved['products_sha256'] and digest(expected)==saved['answer_sha256']
manifest=read(attempt/'package.json')['package']
actual={str(p.relative_to(package/'legalmath')):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (package/'legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert actual==manifest
answer=service.consume(p,root,mode='frozen');assert digest(answer)==digest(expected)
origins={}
for name,module in list(sys.modules.items()):
    if name=='legalmath' or name.startswith('legalmath.'):
        file=getattr(module,'__file__',None)
        if file:
            path=Path(file).resolve();assert path.is_relative_to(package),str(path)
            origins[name]=str(path.relative_to(package))
result={'status':'PASS','isolated':True,'complete_answer_equal':True,'answer_sha256':digest(answer),
        'production_imports':origins,'wall_seconds':time.monotonic()-start,'cpu_gpu':'CPU; GPU intentionally hidden'}
with (attempt/'installed-result.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='production_imports'}))
