"""Independent zero-dispatch provider preflight using the reviewed staged bytes."""
from pathlib import Path
from unittest.mock import patch
import json
import sys

ROOT = Path('/home/chakwong/python/legalmath')
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment'
sys.path.insert(0, str(WORK))
import deploy

preparation = json.loads((WORK / 'preparation.json').read_text())
baseline = json.loads((WORK / 'baseline.json').read_text())
deploy.deploy.assert_unchanged(ROOT, baseline)
stage = WORK / 'registration-stage'
binding_file = stage / ('binding-corrected.json' if (stage / 'binding-corrected.json').exists() else 'binding.json')
overrides = {ROOT / p: ROOT / pointer['path'] for p, pointer in preparation['sources'].items()}
overrides[ROOT / deploy.PLAN] = ROOT / preparation['plan']['path']
overrides.update({ROOT / deploy.PROGRAM: stage / 'program.json',
    ROOT / deploy.STATE: stage / 'state.json',
    ROOT / deploy.BASE / 'current-binding.json': binding_file})
rt, rb, exists, is_file = Path.read_text, Path.read_bytes, Path.exists, Path.is_file
deploy.staged_imports()
from scripts.legal_integration_campaign import provider
from legalmath.errors import LegalMathError
with patch.object(Path, 'read_text', lambda p, *a, **k: rt(overrides.get(p, p), *a, **k)), \
     patch.object(Path, 'read_bytes', lambda p, *a, **k: rb(overrides.get(p, p), *a, **k)), \
     patch.object(Path, 'is_file', lambda p: is_file(overrides.get(p, p))), \
     patch.object(Path, 'exists', lambda p: exists(overrides.get(p, p))):
    service = provider()
    ledger = service.check()
    assert len(ledger['calls']) == 6471 and ledger['maximum'] == 8100
    binding = json.loads(rt(binding_file))
    assert service.allowance.service_scope()[0] == binding['phase_service_scope']
    service.allowance.expected = 'deployment-must-not-dispatch'
    try:
        service.allowance.reserve('deployment-must-not-dispatch')
    except LegalMathError as exc:
        assert exc.code == 'E_AUTHORITY' and 'reviewed live continuation' in exc.details
    else:
        raise AssertionError('Activation hold failed')
deploy.deploy.assert_unchanged(ROOT, baseline)
result = dict(verdict='PASS', calls=6471, provider_calls=0,
    service_scope_preserved=True, activation_hold='VERIFIED')
(WORK / 'provider-preflight-independent.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
