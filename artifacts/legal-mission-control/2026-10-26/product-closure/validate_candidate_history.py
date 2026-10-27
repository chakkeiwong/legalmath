"""Verify all existing history with only the equivalent Unicode predicate changed."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys,time
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import legalmath.canonical as baseline
spec=importlib.util.spec_from_file_location('legalmath.canonical_candidate',
    '/tmp/legalmath-product-closure-20261026/src/legalmath/canonical.py')
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
sample=json.loads((ROOT/'artifacts/legal-mission-control/2026-10-23/p14-optional-quote/live/arms/p14/baseline/calls/dispatch.json').read_text())
timings={}
for name,module in [('baseline',baseline),('candidate',candidate)]:
    started=time.perf_counter();outputs=[module.digest(sample) for _ in range(3)]
    timings[name]=dict(seconds=time.perf_counter()-started,hashes=outputs)
assert timings['baseline']['hashes']==timings['candidate']['hashes']
baseline._check=candidate._check
from scripts.legal_mission_execution import read,validate_program
program_path=ROOT/'docs/implementation/legal-mission-control/integration-master.json'
before=program_path.read_bytes();started=time.perf_counter()
value=validate_program(read(program_path),ROOT)
assert before==program_path.read_bytes(),'Program changed during benchmark'
result=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,
    program_sha256=hashlib.sha256(before).hexdigest(),full_validation_seconds=time.perf_counter()-started,
    same_input_digest_timing=timings,validated_tasks=len(value),
    method='Full current recursive validator; equivalent surrogate predicate only; no cache or skipped checks')
with (WORK/'candidate-history-validation.json').open('x') as stream:json.dump(result,stream,indent=2)
print(json.dumps(result,indent=2))
