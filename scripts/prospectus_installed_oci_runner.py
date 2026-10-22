"""Isolated installed use of the complete supplied Note20 consumer."""
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from legalmath.prospectus import basf_oci_notes, basf_equity, basf_statement
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE, ROOT = [Path(p).resolve() for p in sys.argv[1:3]]
BASE = HERE.parents[1]
PRIOR = BASE / 'basf-incorporation/attempt-003'
STATEMENT = BASE / 'basf-incorporation/attempt-002/repair'
TARGET = HERE / 'installed-results'
TARGET.mkdir(exist_ok=False)
ENV = Path(sys.executable).parent.parent.resolve()


def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name,value):
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2).encode()
    with (TARGET/name).open('xb') as stream:
        stream.write(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


modules=[basf_oci_notes,basf_equity,basf_statement,service]
proof={'python':sys.executable,'prefix':sys.prefix,'isolated':sys.flags.isolated,'sys_path':sys.path,
       'modules':{m.__name__:{'path':m.__file__,'sha256':sha(m.__file__)} for m in modules},
       'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve()==ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT/'src') for p in sys.path if p)
package=ENV/'lib/python3.11/site-packages/legalmath'
files={str(p.relative_to(package)):sha(p) for p in package.rglob('*')
       if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert files==read(HERE/'source-package.json')
save('package-files.json',files)
save('import-proof.json',proof)


def no_native(*args,**kwargs):
    raise AssertionError('Native/subprocess calls forbidden in installed frozen note consumer')


subprocess.Popen=no_native
products=read(HERE/'products.json.gz')
sp,ep,np=read(STATEMENT/'profile.json'),read(PRIOR/'profile.json'),read(HERE/'profile.json')
result=basf_oci_notes.consume(products,sp,ep,np,ROOT,expected_statement_profile_sha256=digest(sp),
                             expected_equity_profile_sha256=digest(ep),expected_profile_sha256=digest(np))
assert result==read(HERE/'note-consumer.json.gz')
assert {k:result[k] for k in ('answer','statement_review','equity_review')}==read(PRIOR/'equity-consumer.json.gz')
save('note-consumer.json.gz',result)
prior=read(PRIOR/'equity-consumer.json.gz')
observed=[]
for row in read(HERE/'actual-controls.json'):
    altered=read(HERE/'adverse-inputs'/(row['case']+'.json.gz'))
    try:
        basf_oci_notes.evaluate(products['P1']['payload']['graph'],prior,altered['profile'],ROOT,
                                expected_profile_sha256=altered['expected_profile_sha256'])
    except ValueError as error:
        observed.append({'case':row['case'],'refused':True,'repinned':row['repinned'],'reason':str(error)})
    else:
        raise AssertionError('Altered installed Note20 accepted: '+row['case'])
assert observed==read(HERE/'actual-controls.json')
save('controls.json',observed)
save('result.json',{'status':'PASS','full_output_equal':True,'earlier_outputs_unchanged':True,
                   'controls':len(observed),'exact_package_files':len(files),'native_calls':0,
                   'same_host_only':True,'independent_legal_acceptance':False})
print({'status':'PASS','controls':len(observed),'full_output_equal':True})
