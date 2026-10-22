"""Seal only passing current-code local evidence for adoption."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save, require
from scripts.legal_retained_acquisition_repair import IMPLEMENTATION, REVIEW, BASE, WORK

source = ref(ROOT, 'src/legalmath/interpretation/assurance/phased/retained_acquisition.py')
version = source['sha256'][:12]
entries, evidence = {}, []
for question in ('p10', 'p14', 'evidence', 'gatecoin'):
    path = WORK/('replay-'+question+'-'+version+'.json')
    value = read(ROOT/path)
    require(value['entry_result'] == 'VALIDATED' and value['provider_calls'] == 0
        and value['ledger_unchanged'] and value['implementation'] == source, 'Replay not valid: '+question)
    entries[question] = value
    evidence += [ref(ROOT,path), value['receipt']]
tests = WORK/'reviewed-tests.xml'
suite = ElementTree.parse(ROOT/tests).getroot().find('testsuite')
require(suite is not None and suite.attrib['failures'] == suite.attrib['errors'] == '0'
    and int(suite.attrib['tests']) == 71, 'Focused tests did not pass')
baseline = read(ROOT/WORK/'baseline.json')
ledger = next(r for r in baseline['archived'] if r['previous']['path'] == str(BASE/'live-calls.json'))
require(ref(ROOT, BASE/'live-calls.json') == ledger['previous'], 'Ledger changed during local correction')
for name in ('reviewed-tests.xml','registration-tests-v2.xml','implementation-review.md','replay.py','diagnose.py'):
    evidence.append(ref(ROOT, WORK/name))
evidence += [ref(ROOT, p) for p in ('tests/assurance/test_retained_acquisition_capacity.py',
    'tests/tooling/test_retained_acquisition_registration.py')]
result = dict(verdict='PASS', provider_calls=0, ledger_unchanged=True, legal_acceptance=False,
    production_entries=entries, evidence=evidence, tests_passed=71,
    implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)}, review=ref(ROOT,REVIEW),
    cpu_mode='GPU deliberately hidden', seeds='N/A: deterministic replay and regression',
    code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    plan=ref(ROOT,'docs/plans/legal-retained-acquisition-capacity-repair-2026-10-21.md'))
save(ROOT/WORK/'local-result.json', result)
print(json.dumps(dict(verdict='PASS', questions=list(entries), provider_calls=0, tests=71)))
