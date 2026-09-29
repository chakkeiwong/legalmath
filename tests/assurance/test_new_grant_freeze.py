"""The operational future freeze uses checked source and spends no request."""
import json
from pathlib import Path
import sys

import pytest

from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.diversity import save
from tests.search.support import FunctionProvider

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import freeze_assurance_future as driver


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    from legalmath.interpretation.search import providers
    out = tmp_path/'artifacts/assurance-new-grant/2026-09-29'; out.mkdir(parents=True)
    predecessor = out/'prior.json'
    save(predecessor, {'maximum': 1, 'calls': [{'request_hash': 'a'*64, 'issued_at_ns': '1'}]})
    save(out/'grant.json', {'schema': 'legalmath.additional-grant.v1', 'grant_id': 'synthetic.future.freeze',
        'authorization': 'Synthetic freeze test; no model requests permitted', 'authorized_calls': 500,
        'predecessor': {'path': 'prior.json', 'sha256': raw_digest(predecessor.read_bytes())},
        'ledger': 'live-allowance.json'})
    phase = out/'F4/attempt-01'; phase.mkdir(parents=True)
    save(phase/'manifest.json', {'status': 'PASSED', 'result': {'snapshot': str(ROOT)}})
    script = ROOT/'scripts/freeze_assurance_future.py'
    save(phase/'snapshot.json', {'inputs': {'scripts/freeze_assurance_future.py': raw_digest(script.read_bytes())}})
    save(out/'state.json', {'phases': {'F4': [{'path': str((phase/'manifest.json').relative_to(tmp_path)),
        'sha256': raw_digest((phase/'manifest.json').read_bytes())}]}})
    old = tmp_path/'artifacts/assurance-successor/2026-09-28'; old.mkdir(parents=True)
    source = old/'source.json'; source.write_bytes(b'Synthetic source bytes, not a circular.')
    save(old/'study-source-freeze.json', {'tasks': [{'sources': [
        {'path': str(source.relative_to(tmp_path)), 'sha256': raw_digest(source.read_bytes())}]}]})
    def provider(*, allowance):
        def forbidden(request): raise AssertionError('Freezing must not call a model')
        value = FunctionProvider(forbidden); value.allowance = allowance
        return value
    monkeypatch.setattr(providers, 'CodexProvider', provider)
    monkeypatch.setattr(driver, 'SNAPSHOT', ROOT)
    return tmp_path, out


def test_operational_freeze_excludes_actual_raw_development_bytes_without_spending(prepared):
    root, out = prepared
    first = driver.freeze(root)
    result = json.loads((out/'future-window-result.json').read_text())
    assert first['live_calls'] == 0 and first['development_sources'] == 1
    assert result['report']['submitted'] == 0 and result['report']['observed'] == 0
    assert result['report']['scope'] == 'legalmath.whole-investigation-observation.v1'
    assert result['grant']['used'] == 0 and not (out/'live-allowance.json').exists()
    again = driver.freeze(root)
    assert again['window_hash'] == first['window_hash']


def test_changed_snapshot_cannot_freeze_a_passing_label(prepared):
    root, out = prepared
    snapshot = out/'F4/attempt-01/snapshot.json'
    value = json.loads(snapshot.read_text()); value['inputs']['scripts/freeze_assurance_future.py'] = '0'*64
    save(snapshot, value)
    with pytest.raises(RuntimeError, match='Tested snapshot changed'):
        driver.freeze(root)
    assert not (out/'whole-method-window').exists()
