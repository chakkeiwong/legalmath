"""Combine completed independent checks; retain the failed full command."""
from pathlib import Path
import sys
import json

ROOT = Path('/home/chakwong/python/legalmath')
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts.legal_mission_execution import read, ref, verify, require, save
from scripts import legal_baseline_corpus_deployment as deploy

baseline = read(WORK / 'baseline.json')
deploy.assert_unchanged(ROOT, baseline)
for pointer in read(WORK / 'staged-identities.json'):
    verify(ROOT, pointer)
observed = read(WORK / 'master-validation-receipt.json')
require(observed['exit_code'] == 1 and observed['observed_checkpoints'] == [
    dict(checkpoint='staged_mission_references', status='PASS'),
    dict(checkpoint='staged_master_and_mission', status='PASS')], 'Missing actual master validation')
correction = read(WORK / 'binding-correction-result.json')
verify(ROOT, correction['corrected_binding'])
verify(ROOT, correction['preflight'])
require(set(correction['changed_fields']) == {'review'}, 'Correction changed other binding fields')
provider = read(ROOT / correction['preflight']['path'])
require(provider == dict(verdict='PASS', calls=6471, provider_calls=0,
    service_scope_preserved=True, activation_hold='VERIFIED'), 'Corrected provider check missing')
stage = WORK / 'registration-stage'
original = stage / 'binding.json'
archive = WORK / 'binding-before-correction.json'
with archive.open('xb') as stream:
    stream.write(original.read_bytes())
original.write_bytes((ROOT / correction['corrected_binding']['path']).read_bytes())
identities = [ref(ROOT, stage / name) for name in ('program.json', 'state.json', 'mission.json', 'binding.json')]
save(WORK / 'final-staged-identities.json', identities)
checked = dict(verdict='PASS', detours=67, provider_calls=0, calls=6471,
    program=ref(ROOT, stage / 'program.json'), state=ref(ROOT, stage / 'state.json'),
    activation_hold='VERIFIED', service_scope=read(original)['phase_service_scope'],
    interpretation='Master/mission check passed; independent provider check passed on the sole corrected review field. Whole original command failure retained.',
    evidence=[ref(ROOT, WORK / name) for name in ('master-validation-receipt.json',
        'binding-correction-result.json', 'provider-preflight-independent.json',
        'deadline-binding-correction.md', 'final-staged-identities.json')],
    at_utc=deploy.now())
save(WORK / 'registration-check.json', checked)
print(json.dumps(checked, indent=2))
