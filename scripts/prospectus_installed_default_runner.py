"""Separate bounded isolated installed answer and control replays."""
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from legalmath.prospectus import basf_default_f,basf_body_coverage,basf_hedge_note
from legalmath.prospectus.successor import service,predicates
from legalmath.prospectus.successor.contracts import digest

HERE,ROOT=[Path(p).resolve() for p in sys.argv[1:3]];mode=sys.argv[3]
assert mode in ('answer','controls')
TARGET=HERE/('installed-'+mode);TARGET.mkdir(exist_ok=False)
ENV=Path(sys.executable).parent.parent.resolve()


def read(p):
    raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)


def save(name,value):
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2).encode()
    with (TARGET/name).open('xb') as stream:stream.write(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


modules=[basf_default_f,basf_body_coverage,basf_hedge_note,service,predicates]
proof={'python':sys.executable,'prefix':sys.prefix,'isolated':sys.flags.isolated,'sys_path':sys.path,
       'modules':{m.__name__:{'path':m.__file__,'sha256':sha(m.__file__)} for m in modules},
       'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve()==ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in modules)
assert all(not Path(p).resolve().is_relative_to(ROOT/'src') for p in sys.path if p)
package=ENV/'lib/python3.11/site-packages/legalmath'
files={str(p.relative_to(package)):sha(p) for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
assert files==read(HERE/'source-package.json');save('package-files.json',files);save('import-proof.json',proof)


def no_native(*args,**kwargs):raise AssertionError('Native children forbidden in frozen default(f) consumer')


subprocess.Popen=no_native
p=read(HERE/'products.json.gz');prior=read(HERE/'baseline-consumer.json.gz')
if mode=='answer':
    old=read(HERE/'prior-profiles.json');profile=read(HERE/'profile.json')
    r=basf_default_f.consume(p,old,profile,ROOT,expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(profile))
    assert r==read(HERE/'default-consumer.json.gz') and {k:r[k] for k in prior}==prior
    save('default-consumer.json.gz',r)
    result={'status':'PASS','full_output_equal':True,'earlier_outputs_unchanged':True,'native_calls':0,'same_host_only':True}
else:
    assert read(HERE/'installed-answer/result.json')['status']=='PASS'
    observed=[]
    for row in read(HERE/'actual-controls.json'):
        v=read(HERE/'adverse-inputs'/(row['case']+'.json.gz'))
        try:basf_default_f.evaluate(p,prior,v['profile'],ROOT,expected_profile_sha256=v['expected_profile_sha256'])
        except ValueError as error:observed.append({'case':row['case'],'refused':True,'repinned':row['repinned'],'reason':str(error)})
        else:raise AssertionError('Altered installed default(f) accepted: '+row['case'])
    assert observed==read(HERE/'actual-controls.json');save('controls.json',observed)
    result={'status':'PASS','controls':len(observed),'native_calls':0,'same_host_only':True}
save('result.json',result);print(result)
