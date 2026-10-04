"""No historical method receipt may become current conformance by relabelling."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
import assurance_successor_revalidate as checked
from legalmath.canonical import canonical, raw_digest
from legalmath.errors import LegalMathError


@pytest.fixture
def retained(tmp_path, monkeypatch):
    def save(name, value):
        p = tmp_path/name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(canonical(value))
        return {'path': name, 'sha256': raw_digest(p.read_bytes())}
    answer = {'status': 'TRUE', 'type': 'bool', 'value': True}
    methods = []
    for kind in ('types', 'java', 'catala'):
        row = {'candidate_id': 'candidate.a', 'status': 'CHECKED'}
        if kind == 'types': row['bundle'] = save('bundle.json', {'unchanged': 'formal program'})
        else:
            row['cases'] = save(kind+'/cases.json', [{'id': 'case.a', 'snapshot': {'x': True}}])
            row['results'] = save(kind+'/results.json', [{'id': 'case.a', 'python': answer, 'java': answer}])
        methods.append({'method_id': 'method.'+kind, 'status': 'AGREES',
                        'evidence': save(kind+'/method.json', {'payload': {'rows': [row]}})})
    old = {'upstream_inputs': [{'path': 'src/legalmath/a.py', 'sha256': 'a'*64}],
           'input_manifest': save('replay-input.json', {'question': 'original'}),
           'target': {'question': 'original'}, 'target_hash': 'b'*64, 'methods': methods}
    oldref = save('old.json', old)
    dossier = {'replay': {'dossier': oldref}}
    calls = []
    monkeypatch.setattr(checked, 'implementation_files', lambda root: [
        {'path': 'src/legalmath/a.py', 'sha256': 'c'*64},
        {'path': 'src/legalmath/added.py', 'sha256': 'd'*64}])
    monkeypatch.setattr(checked, 'historical_replay', lambda *args: calls.append('history') or {'historical': True})
    def replay(root, manifest, output, jdk, **kwargs):
        assert manifest == tmp_path/'replay-input.json'
        assert output == tmp_path/'new-run'
        calls.append('runtime')
        return {'dossier': save('new.json', old), 'status': 'CHECKED'}
    monkeypatch.setattr(checked, 'run_replay', replay)
    monkeypatch.setattr(checked, 'verify', lambda *args: calls.append('current-files') or {'checked': True})
    return tmp_path, dossier, old, save, calls


def invoke(retained):
    root, dossier, _, _, _ = retained
    return checked.verify_retained(root, dossier, {'path': 'archive.zip', 'sha256': 'e'*64}, root/'new-run', root/'jdk')


def test_changed_code_requires_history_and_actual_fresh_runtime(retained):
    result = invoke(retained)
    assert retained[-1] == ['history', 'runtime']
    assert result['new_runtime_execution'] and not result['original_dossier_modified']
    assert result['changed_sources'] == ['src/legalmath/a.py']
    assert result['added_sources'] == ['src/legalmath/added.py']
    assert result['runtime_cases'] == {'method.java': 1, 'method.catala': 1}


def test_unchanged_code_uses_current_verifier_without_claiming_new_run(retained, monkeypatch):
    monkeypatch.setattr(checked, 'implementation_files', lambda root: retained[2]['upstream_inputs'])
    result = invoke(retained)
    assert retained[-1] == ['current-files']
    assert not result['new_runtime_execution']


@pytest.mark.parametrize('failure', ['target', 'program', 'cases', 'answer', 'missing_backend'])
def test_changed_target_program_domain_answer_or_backend_rejects(retained, monkeypatch, failure):
    root, _, old, save, calls = retained
    new = deepcopy(old)
    if failure == 'target': new['target'] = {'question': 'different'}
    elif failure == 'missing_backend': new['methods'].pop()
    else:
        method = new['methods'][0 if failure == 'program' else 1]
        payload = checked.read_evidence(method['evidence'], root)
        row = payload['payload']['rows'][0]
        if failure == 'program': row['bundle'] = save('changed-bundle.json', {'changed': 'formal program'})
        elif failure == 'cases': row['cases'] = save('changed-cases.json', [])
        else: row['results'] = save('changed-results.json', [{'id': 'case.a',
            'python': {'status': 'FALSE', 'type': 'bool', 'value': False},
            'java': {'status': 'FALSE', 'type': 'bool', 'value': False}}])
        method['evidence'] = save('changed-method.json', payload)
    monkeypatch.setattr(checked, 'run_replay', lambda *a, **kw: {'dossier': save('changed-new.json', new)})
    with pytest.raises(LegalMathError) as exc: invoke(retained)
    assert exc.value.code == 'E_INTEGRITY'
    assert calls == ['history']


def test_invalid_historical_evidence_blocks_reexecution(retained, monkeypatch):
    def fail(*args): raise LegalMathError('E_HASH_MISMATCH')
    monkeypatch.setattr(checked, 'historical_replay', fail)
    with pytest.raises(LegalMathError): invoke(retained)
    assert retained[-1] == []
