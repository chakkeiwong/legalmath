"""Check registration's archived predecessor without claiming the repair passed."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scripts.legal_integration_synthesis_resolution import ROOT, WORK, PROGRAM, projection
from scripts.legal_mission_execution import read, save, ref, validate_program, historical_evidence

started = time.monotonic()
baseline = read(ROOT/WORK/'baseline.json')
archived = {r['previous']['path']:r['archive'] for r in baseline['archived']}
old = read(ROOT/archived[str(PROGRAM)]['path'])
with historical_evidence(ROOT,projection(baseline)):
    validate_program(old,ROOT)
value = dict(verdict='PASS',question='Can registration validate the exact archived predecessor?',
    provider_calls=0,wall_seconds=time.monotonic()-started,baseline=ref(ROOT,WORK/'baseline.json'),
    command=[sys.executable,*sys.argv],legal_acceptance=False)
save(ROOT/WORK/'validation-2/predecessor-check.json',value)
print(__import__('json').dumps(value))
