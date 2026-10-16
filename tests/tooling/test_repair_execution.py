"""Preserve original owners, budgets and failures across bounded repair rounds."""
from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import Refused, read


def inputs():
    baseline = read(repair.ROOT / repair.WORK / 'round-1/baseline.json')
    archived = {r['previous']['path']: r['archive']['path'] for r in baseline['archived']}
    old = read(repair.ROOT / archived[str(repair.PROGRAM)])
    before = read(repair.ROOT / archived[str(repair.STATE)])
    owners = ['current-binding', 'acquire-p14', 'acquire-gatecoin', 'continuation-review']
    revision = {k: {'path': k, 'sha256': k} for k in repair.POINTERS}
    revision.update(prior_detours=43, repair_ids=['R1', 'R2'],
        round_reopened_nodes=owners, reopened_nodes=owners,
        attempt_increments={k: 1 for k in owners},
        resolved_vetoes=deepcopy(before['continuation_vetoes']))
    authority = read(repair.ROOT / repair.WORK / 'authorization.json')
    return old, before, revision, authority


def test_only_named_attempts_increase_and_original_graph_stays():
    old, before, revision, authority = inputs()
    repair.validate_allocation(old, before, revision, authority)
    proposed = repair.expected_program(old, before, revision, repair.ROOT)
    assert proposed['deadline_utc'] == old['deadline_utc']
    assert proposed['workers'] == old['workers']
    for a, b in zip(old['tasks'], proposed['tasks']):
        if a['id'] not in revision['round_reopened_nodes']:
            assert a == b
        else:
            assert b['maximum_attempts'] == a['maximum_attempts'] + 1
            for key in ('requires', 'after', 'any_success', 'write_resources', 'command', 'acceptance'):
                assert a.get(key) == b.get(key)


@pytest.mark.parametrize('bad', [-1, 0, 1.2, True, '1'])
def test_nonpositive_or_noninteger_increments_refused(bad):
    old, before, revision, authority = inputs()
    revision['attempt_increments']['acquire-p14'] = bad
    with pytest.raises(Refused): repair.validate_allocation(old, before, revision, authority)


@pytest.mark.parametrize('mutation', ['detours', 'success', 'duplicate', 'foreign_veto', 'foreign_owner', 'repair_limit'])
def test_unauthorized_scope_changes_refused(mutation):
    old, before, revision, authority = inputs()
    if mutation == 'detours': revision['prior_detours'] = 45
    elif mutation == 'success':
        revision['round_reopened_nodes'].append('campaign')
    elif mutation == 'duplicate': revision['round_reopened_nodes'].append('acquire-p14')
    elif mutation == 'foreign_veto': revision['resolved_vetoes'][0]['scope'] = ['acquire-p14']
    elif mutation == 'foreign_owner': revision['attempt_increments']['absent'] = 1
    else: revision['repair_ids'] = ['R' + str(i) for i in range(1, 12)]
    with pytest.raises(Refused): repair.validate_allocation(old, before, revision, authority)


def test_future_round_requires_exact_predecessor_and_cumulative_owners():
    old, before, revision, authority = inputs()
    old[repair.KEY] = deepcopy(revision)
    revision['prior_detours'] = 44
    revision['round_reopened_nodes'] = ['current-binding']
    revision['attempt_increments'] = {'current-binding': 1}
    revision['repair_ids'] += ['R3']
    repair.validate_allocation(old, before, revision, authority)
    revision['prior_detours'] = 43
    with pytest.raises(Refused): repair.validate_allocation(old, before, revision, authority)


def test_state_preserves_charges_attempts_successes_and_foreign_vetoes():
    old, before, revision, authority = inputs()
    foreign = {'code': 'E_AUTHORITY', 'reason': 'Independent authority refusal', 'scope': ['acquire-p10'], 'evidence': []}
    before['continuation_vetoes'].append(foreign)
    frozen = deepcopy(before)
    proposed = repair.expected_program(old, before, revision, repair.ROOT)
    state = repair.project_state(before, proposed, revision, 'test')
    assert before == frozen
    assert state['continuation_vetoes'] == [foreign]
    assert state['resolved_continuation_vetoes'][-1]['veto'] == revision['resolved_vetoes'][0]
    for tid, row in before['tasks'].items():
        assert state['tasks'][tid]['attempts'] == row['attempts']
        if tid not in revision['round_reopened_nodes']: assert state['tasks'][tid] == row
    with pytest.raises(Refused): repair.project_state(state, proposed, revision, 'again')


def test_running_owner_prevents_transition():
    old, before, revision, _ = inputs()
    before['tasks']['acquire-p14']['status'] = 'RUNNING'
    with pytest.raises(Refused): repair.project_state(before, old, revision, 'test')
