"""Isolated execution of the original-requirement assessor from its fresh wheel."""
from pathlib import Path
import json, os, sys
root,here,prep=map(Path,sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path.insert(0,str(here/'installed'))
from legalmath.prospectus import reference_requirements as module
sys.argv=['reference_requirements','--repository',str(root),'--evidence',str(prep/'evidence.json'),
          '--output',str(here/'installed-assessment.json')]
module.main()
actual=module.read(here/'installed-assessment.json');expected=module.read(here/'assessment.json')
assert actual==expected,'Installed original-requirement assessment differs'
imports={n:m.__file__ for n,m in sys.modules.items() if (n=='legalmath' or n.startswith('legalmath.')) and getattr(m,'__file__',None)}
assert 'legalmath.prospectus.reference_requirements' in imports
assert all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
for name,value in [('installed-imports.json',imports),('installed-result.json',
    {'status':'PASS','complete_assessment_equal':True,'installed_imports':len(imports),'report_sha256':actual['report_sha256']})]:
    with (here/name).open('x') as stream:json.dump(value,stream,indent=2)
