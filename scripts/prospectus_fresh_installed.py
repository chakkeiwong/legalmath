"""Actual isolated installed CLI for small controls and original PDF preparation."""
import gzip,json,os,sys
from pathlib import Path
root,here=map(Path,sys.argv[1:3]);name=sys.argv[3];os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(here/'installed'),str(root)]
from scripts import prospectus_fresh_preparation as runner
sys.path=[p for p in sys.path if p!=str(root/'src')]
for key in list(sys.modules):
    if key=='legalmath' or key.startswith('legalmath.'):del sys.modules[key]
from legalmath.cli import main
from legalmath.prospectus.successor.contracts import digest,read


def call(args):
    sys.argv=['legalmath',*args];main()


if name=='small-installed':
    from scripts.prospectus_preparation_fixture import create
    folder=here/'small';_,pin,expected=create(folder);previous=None
    for stage in ('P1','P2','P3','P4','P5'):
        args=['prospectus','prepare','--stage',stage,'--recipe','recipe.json','--recipe-sha256',pin,
              '--repository',str(folder),'--output',stage]
        if previous:args+=['--parents',previous+'/products.json','--parents-sha256',digest((folder/previous/'products.json').read_bytes())]
        call(args);assert read(folder/stage/(stage+'.json'))==expected[stage];previous=stage
    result={'status':'PASS','actual_cli':True,'all_five_phases_equal':True,'explicit_phase_inputs_forwarded':True}
elif name=='consume-installed':
    manifest=here/'fresh/P5/products.json'
    call(['prospectus','consume','--products',str(manifest),'--repository',str(root),'--output',str(here/'installed-answer.json'),
          '--mode','frozen','--conditional-profiles',runner.rel(runner.prior.PREP/'profiles.json'),
          '--conditional-profiles-sha256',runner.sha(runner.prior.PREP/'profiles.json')])
    actual=read(here/'installed-answer.json');expected=json.loads(gzip.decompress((runner.prior.HERE/'ordinary-answer.json.gz').read_bytes()))
    assert actual==expected
    result={'status':'PASS','actual_cli':True,'complete_answer_equal':True,'unchanged_profile_pins':True,'answer_sha256':digest(actual)}
else:
    stage=runner.PHASES[name];call(runner.cli_arguments(stage))
    actual=read(here/'fresh'/stage/(stage+'.json'))
    manifest=runner.read(runner.prior.prior.prior.PREP/'products.json')
    expected=read(root/manifest['products'][stage]['path'])
    if actual!=expected:
        runner.save(here/(name+'-difference.json'),{'actual_sha256':digest(actual),'expected_sha256':digest(expected),
            'different_top_level':[k for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k)]})
        raise AssertionError('Complete regenerated product differs;retain source-specific difference')
    result={'status':'PASS','actual_cli':True,'stage':stage,'complete_product_equal':True,
            'semantic_sha256':digest(actual),'source_reextracted':stage=='P1'}
imports={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
assert imports and all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
runner.save(here/(name+'-imports.json'),imports)
result.update(installed_imports=len(imports),cpu_gpu='CPU;GPU intentionally hidden')
runner.save(here/(name+'-result.json'),result)
print('PASS installed '+name)
