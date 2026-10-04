"""Build and install a wheel offline; inspect the installed package outside the repository."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);out=Path(parser.parse_args().out).resolve();out.mkdir(parents=True,exist_ok=False)
commands=[[sys.executable,'-m','pip','wheel',str(ROOT),'--no-deps','--no-build-isolation','--no-index','-w',str(out/'wheel')]]
for command in commands:
    with (out/'build.log').open('w') as log:subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
wheel=next((out/'wheel').glob('*.whl'))
command=[sys.executable,'-m','pip','install','--no-deps','--no-index','--target',str(out/'installed'),str(wheel)];commands.append(command)
with (out/'install.log').open('w') as log:subprocess.run(command,cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
code='''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import legalmath
assert Path(legalmath.__file__).is_relative_to(Path(sys.argv[1]))
from legalmath.interpretation import Interpretations
from legalmath.interpretation.contracts import validator,reference_policy,policy
from legalmath.api.app import create_app
for kind in ('run','policy','candidate','issue','action','coverage','evidence','report','issue-decision','review-decision'): validator(kind)
policy(reference_policy())
app=create_app(sys.argv[2],run_jobs=False)
assert '/v1/interpretations' in app.openapi()['paths']
from importlib.resources import files
assert files('legalmath').joinpath('web/templates/interpretations.html').is_file()
assert files('legalmath').joinpath('storage/migrations/002.sql').is_file()
print(json.dumps({'status':'PASSED','package':legalmath.__file__,'schemas':10,'installed_api':True,'installed_migration':True,'installed_ui':True}))
'''
command=[sys.executable,'-I','-c',code,str(out/'installed'),str(out/'installed-database')];commands.append(command)
result=subprocess.run(command,cwd=out,capture_output=True,text=True,check=True,timeout=30)
(out/'result.json').write_text(json.dumps({'result':json.loads(result.stdout),'commands':commands,'network_required':False},indent=2)+'\n')
print(result.stdout)
