"""Finite service continuation preserves the spent automatic retry allowance."""
from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import save, ref, read, Refused
from legalmath.interpretation.assurance.phased import synthesis_recovery


def fixture(root, monkeypatch):
    def put(name, value):
        save(root / name, value)
        return ref(root, name)
    scope = put('scope.json', {'profile': 'test'})
    circuit = put('service-circuit.json', {'open': True, 'stage_hash': scope['sha256'], 'failed_slots': [2218]})
    replacements = put('service-recovery.json', {'maximum': 48, 'charges': list(range(48))})
    binding = put('binding.json', {'phase_service_scope': scope})
    ledger = put('ledger.json', {'calls': [1]})
    account = put('account.json', {'input_hash': 'source'})
    synthesis = put('synthesis.json', {'input_hash': 'source', 'ledger': ledger, 'rows': {
        'reduce-gatecoin-0-0': {'disposition': 'RETAIN_EXACT_SUCCESS', 'slot': 2217},
        'reduce-gatecoin-0-9': {'disposition': 'CHARGED_NO_OUTPUT_FAILURE', 'slot': 2218}}})
    monkeypatch.setattr(synthesis_recovery, 'load', lambda root, reference, input_hash: read(root / reference['path']))
    combined = put('combined.json', {'profile': synthesis_recovery.PROFILE, 'input_hash': 'source',
        'account': account, 'synthesis': synthesis})
    replay = put('replay.json', {'verdict': 'PASS', 'provider_calls': 0, 'ledger_unchanged': True,
        'composite': combined, 'exact_contracts': 2, 'exact_successes': 1, 'production_reconstruction': True})
    service = {'profile': 'one-explicit-synthesis-continuation.v1', 'maximum_explicit_redispatches': 1,
        'automatic_replacements': 0, 'question': 'gatecoin', 'prior_scope': scope,
        'prior_circuit': circuit, 'prior_replacements': replacements, 'failed_slot': 2218,
        'failed_key': 'reduce-gatecoin-0-9'}
    revision = {'service_continuation': service, 'synthesis_successors': {'gatecoin': combined},
        'successor_replay': replay, 'prior_binding': binding, 'prior_ledger': ledger,
        'recoveries': {'gatecoin': account}, 'round_reopened_nodes': ['current-binding', 'continuation-review'] +
            ['acquire-' + q for q in repair.QUESTIONS],
        'attempt_increments': {'current-binding': 1, 'continuation-review': 1, 'acquire-gatecoin': 1}}
    spec = {k: deepcopy(revision[k]) for k in ('service_continuation', 'synthesis_successors', 'successor_replay')}
    spec['execution_scope'] = 'exact-synthesis-service-continuation'
    return revision, spec, put


def test_exact_one_retry_preserves_other_unused_attempts(tmp_path, monkeypatch):
    revision, spec, _ = fixture(tmp_path, monkeypatch)
    repair.validate_synthesis_successor(tmp_path, revision, spec)


@pytest.mark.parametrize('change', ['extra_retry', 'replacement', 'foreign_slot', 'foreign_key',
    'foreign_scope', 'closed_circuit', 'lost_charges', 'new_ledger', 'unreviewed', 'extra_attempt', 'lost_branch'])
def test_unreviewed_continuations_refused(tmp_path, monkeypatch, change):
    revision, spec, put = fixture(tmp_path, monkeypatch)
    service = revision['service_continuation']
    if change == 'extra_retry': service['maximum_explicit_redispatches'] = 2
    elif change == 'replacement': service['automatic_replacements'] = 1
    elif change == 'foreign_slot': service['failed_slot'] = 2217
    elif change == 'foreign_key': service['failed_key'] = 'reduce-gatecoin-0-0'
    elif change == 'foreign_scope': service['prior_scope'] = put('foreign.json', {})
    elif change == 'closed_circuit':
        circuit = read(tmp_path / service['prior_circuit']['path']); circuit['open'] = False
        service['prior_circuit'] = put('closed.json', circuit)
    elif change == 'lost_charges': service['prior_replacements'] = put('lost.json', {'maximum': 48, 'charges': []})
    elif change == 'new_ledger': revision['prior_ledger'] = put('other-ledger.json', {})
    elif change == 'unreviewed': spec['execution_scope'] = 'local-settlement-only'
    elif change == 'extra_attempt': revision['attempt_increments']['acquire-p10'] = 1
    elif change == 'lost_branch': revision['round_reopened_nodes'].remove('acquire-evidence')
    spec['service_continuation'] = deepcopy(service)
    with pytest.raises(Refused): repair.validate_synthesis_successor(tmp_path, revision, spec)
