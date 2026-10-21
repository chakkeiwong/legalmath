import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys, json
from pathlib import Path
from copy import deepcopy
sys.path.insert(0, str(Path.cwd()))
from legalmath.interpretation.assurance.phased.synthesis_recovery import historical_request
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.errors import LegalMathError
base = Path('artifacts/legal-mission-control/2026-10-19/synthesis-continuation/live/pass-1/product/calls')
for folder in sorted(base.glob(sys.argv[1] if len(sys.argv) > 1 else 'reduce-p10-1-*')):
    saved = json.loads((folder/'reference-binding.json').read_text())
    try:
        historical_request(saved, reviewed=True)
    except LegalMathError as e:
        current = prepare(saved['original_request'], saved['original_schema'])
        new, old = current['request'].get('account_identity_hashes', {}), saved['request'].get('account_identity_hashes', {})
        if set(new.values()) == set(old.values()):
            reverse = {v:k for k,v in old.items()}
            def rename(n):
                if isinstance(n,dict):
                    if set(n) == {'identity_hash'}: return {'identity_hash': reverse[new[n['identity_hash']]]}
                    return {k:rename(v) for k,v in n.items()}
                if isinstance(n,list): return [rename(v) for v in n]
                return n
            current['request'] = rename(current['request'])
            current['request']['account_identity_hashes'] = old
        differences = []
        def diff(a,b,path=''):
            if a == b: return
            if isinstance(a,dict) and isinstance(b,dict):
                for key in set(a)|set(b): diff(a.get(key),b.get(key),path+'/'+str(key))
            elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
                for i,(x,y) in enumerate(zip(a,b)): diff(x,y,path+'/'+str(i))
            else: differences.append(dict(path=path,current=str(a)[:180],saved=str(b)[:180]))
        diff(current,saved)
        print(json.dumps(dict(key=folder.name,error=str(e.details or e),differences=differences[:40],count=len(differences)),indent=2))
        break
