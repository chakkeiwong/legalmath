"""Replay source-equivalent conditional option from verified installed bytes."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root,attempt=map(Path,sys.argv[1:3]);base=attempt.parent/'attempt-036';package=base/'installed'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path.insert(0,str(package))
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus import basf_default_f_current as current

def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def delta(base,operations):
    from copy import deepcopy
    result=deepcopy(base)
    for op in operations:
        path=op['path'];target=result
        if not path:result=op['value'];continue
        for key in path[:-1]:target=target[key]
        if op['op']=='delete':del target[path[-1]]
        else:target[path[-1]]=op['value']
    return result

start=time.monotonic();original=attempt.parent/'attempt-031';saved=read(base/'answer.json.gz')
p=delta(read(original/'complete-products.json.gz'),saved['products_delta'])
ordinary=delta(read(original/'complete-expected-answer.json.gz'),saved['answer_delta'])
retained=read(attempt/'answer-delta.json.gz');expected=delta(ordinary,retained['answer_delta'])
assert digest(p)==saved['products_sha256'] and digest(ordinary)==saved['answer_sha256']
assert digest(expected)==retained['answer_sha256']
profile=read(root/'docs/implementation/prospectus-execution-authority/reviews/current-conditional-296/profile.json')
manifest=read(base/'package.json')['package']
actual={str(p.relative_to(package/'legalmath')):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (package/'legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert actual==manifest
answer=service.consume(p,root,mode='frozen',default_f_profile=profile,expected_default_f_profile_sha256=digest(profile))
assert digest(answer)==digest(expected)
verification=current.verify_answer(answer,ordinary,profile,expected_profile_sha256=digest(profile))
assert verification['checked_answers']==192
origins={}
for name,module in list(sys.modules.items()):
    if name=='legalmath' or name.startswith('legalmath.'):
        file=getattr(module,'__file__',None)
        if file:
            path=Path(file).resolve();assert path.is_relative_to(package),str(path)
            origins[name]=str(path.relative_to(package))
result={'status':'PASS','isolated':True,'complete_conditional_answer_equal':True,'checked_answers':192,
        'answer_sha256':digest(answer),'production_imports':origins,'wall_seconds':time.monotonic()-start,
        'cpu_gpu':'CPU; GPU intentionally hidden'}
with (attempt/'installed-result.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='production_imports'}))
