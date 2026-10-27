"""Local-only merged checkpoint verification; never dispatches a provider call."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.legal_mission_execution import read, save, ref, verify, require, digest
from scripts.legal_integration_campaign import provider
from legalmath.errors import LegalMathError

DOC = Path('docs/implementation/legal-mission-control/checkpoint-2026-10-27')
WORK = Path('artifacts/legal-mission-control/2026-10-27/git-handoff')
BASE = Path('artifacts/legal-mission-control/2026-10-13/master')
manifest = read(ROOT / DOC / 'merge-bindings.json')
binding = read(ROOT / BASE / 'current-binding.json')
previous = read(ROOT / manifest['prior_binding']['path'])
for row in manifest['changes']:
    verify(ROOT, row['archive'])
    verify(ROOT, row['current'])
    require(row['archive']['sha256'] == row['previous']['sha256'], 'Changed archived bytes')
for key in ('program', 'state', 'ledger', 'prior_stage'):
    verify(ROOT, manifest[key])
for key in ('review', 'grant_hash', 'maximum_calls', 'deadline_utc', 'time_extension',
            'effective_deadline_utc', 'execution_budget', 'product_closure', 'program'):
    require(binding[key] == previous[key], 'Authority or phase identity changed: ' + key)
pointer = read(ROOT / BASE / 'current-stage.json')
verify(ROOT, pointer)
stage = read(ROOT / pointer['path'])
old_stage = read(ROOT / manifest['prior_stage']['path'])
require(stage == dict(old_stage, binding_hash=digest(binding)), 'Unexpected stage change')
ledger_before = ref(ROOT, BASE / 'live-calls.json')
service = provider()
scope = service.allowance.service_scope()[0]
try:
    service.check()
except LegalMathError as exc:
    require(exc.code == 'E_AUTHORITY' and exc.details == 'Insufficient approved deadline for one complete call',
            'Unexpected provider integrity failure: ' + str(exc.details))
    authority = {'code': exc.code, 'reason': exc.details, 'expected': True}
else:
    raise RuntimeError('Expired authority unexpectedly accepted')
require(ref(ROOT, BASE / 'live-calls.json') == ledger_before, 'Read-only check changed charges')
xml = ET.parse(ROOT / WORK / 'postmerge-repaired-tests.xml').getroot()
suites = list(xml.iter('testsuite'))
tests = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
         for key in ('tests', 'failures', 'errors', 'skipped')}
require(tests == {'tests': 446, 'failures': 0, 'errors': 0, 'skipped': 0}, 'Unexpected test result')
result = {
    'profile': 'merged-checkpoint-verification.v1',
    'at_utc': datetime.now(timezone.utc).isoformat(),
    'source_integrity': 'PASS_THROUGH_ORDINARY_PROVIDER_DEADLINE_CHECK',
    'changed_sources': len(manifest['changes']), 'historical_bytes_preserved': True,
    'programme_state_ledger_unchanged': True, 'phase_identity_unchanged': True,
    'authority': authority, 'new_calls': 0,
    'calls_charged': len(read(ROOT / BASE / 'live-calls.json')['calls']),
    'tests': tests, 'test_manifest': ref(ROOT, WORK / 'postmerge-repaired-test-result.json'),
    'test_xml': ref(ROOT, WORK / 'postmerge-repaired-tests.xml'),
    'service_scope': scope, 'binding': ref(ROOT, BASE / 'current-binding.json'),
    'stage': pointer, 'manifest': ref(ROOT, DOC / 'merge-bindings.json'),
    'legal_acceptance': False, 'gpu': 'intentionally hidden',
}
target = ROOT / DOC / 'postmerge-verification.json'
require(not target.exists(), 'Verification already retained; inspect it instead')
save(target, result)
print(json.dumps(result, indent=2))
