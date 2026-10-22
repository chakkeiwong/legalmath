"""Replay complete H38/current conditional answer in isolated installed tree."""
import sys,json,os
from pathlib import Path
root,here=map(Path,sys.argv[1:3]);os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(here/'installed'),str(root)]
from scripts import prospectus_h38_repair as runner
# Runner pins source imports for normal local execution; restore installed-only
# production lookup before importing the actual consumer.
sys.path=[p for p in sys.path if p!=str(root/'src')]
for name in list(sys.modules):
    if name=='legalmath' or name.startswith('legalmath.'):del sys.modules[name]
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
p,expected=runner.retained('answer');profile=runner.read(here/'conditional-profile.json')
actual=service.consume(p,root,mode='frozen',default_f_profile=profile,expected_default_f_profile_sha256=digest(profile))
assert actual==expected
imports={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
assert imports and all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
runner.save(here/'installed-result.json',{'status':'PASS','isolated':True,'complete_conditional_equal':True,'answer_sha256':digest(actual),
    'production_imports':imports,'cpu_gpu':'CPU;GPU intentionally hidden'})
print(json.dumps({'status':'PASS','complete_conditional_equal':True,'imports':len(imports)}))
