"""Run actual isolated installed payment categories CLI and compare the complete answer."""
import gzip,json,os,sys
from pathlib import Path
root,here=map(Path,sys.argv[1:3]);os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(here/'installed'),str(root)]
from scripts import prospectus_payment_categories as runner
sys.path=[p for p in sys.path if p!=str(root/'src')]
for name in list(sys.modules):
    if name=='legalmath' or name.startswith('legalmath.'):del sys.modules[name]
from legalmath.cli import main
from legalmath.prospectus.successor.contracts import digest
sys.argv=['legalmath',*runner.cli_arguments('installed-answer.json')];main()
actual=json.loads((here/'installed-answer.json').read_text())
expected=json.loads(gzip.decompress((here/'ordinary-answer.json.gz').read_bytes()))
assert actual==expected
imports={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
assert imports and all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
runner.save(here/'installed-imports.json',imports)
runner.save(here/'installed-result.json',{'status':'PASS','actual_cli':True,'complete_answer_equal':True,
    'answer_sha256':digest(actual),'installed_imports':len(imports),'cpu_gpu':'CPU;GPU intentionally hidden'})
print('PASS installed notice payment categories composition')
