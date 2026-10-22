"""Isolated installed replay of the complete conditional majority answer."""
import os,sys
from pathlib import Path
root,here=map(Path,sys.argv[1:3]);os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(here/'installed'),str(root)]
from scripts import prospectus_majority_application as runner
sys.path=[p for p in sys.path if p!=str(root/'src')]
for name in list(sys.modules):
    if name=='legalmath' or name.startswith('legalmath.'):del sys.modules[name]
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
products,ordinary,expected=runner.retained();profile=runner.read(runner.PREP/'profile.json')
default=runner.read(runner.prior.HERE/'conditional-profile.json')
actual=service.consume(products,root,mode='frozen',default_f_profile=default,
    expected_default_f_profile_sha256=digest(default),majority_profile=profile,expected_majority_profile_sha256=digest(profile))
assert actual==expected
imports={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
assert imports and all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
runner.save(here/'installed-imports.json',imports)
runner.save(here/'installed-result.json',{'status':'PASS','complete_answer_equal':True,
    'answer_sha256':digest(actual),'installed_imports':len(imports),'cpu_gpu':'CPU;GPU intentionally hidden'})
print('PASS complete installed answer')
