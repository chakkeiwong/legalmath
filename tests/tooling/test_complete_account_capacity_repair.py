from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_input, account_instructions, account_recovery, account_output
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from scripts import legal_integration_complete_account_capacity as repair
from scripts import legal_integration_phased_live as live
from scripts.legal_mission_execution import Refused, read, ref, save, verify, historical_evidence
from tests.assurance.test_bounded_product import envelope, Scripted


def test_revision_keeps_graph_limits_successful_owners_and_attempt_prefixes():
    old, state = frozen_program_and_state()
    for q in repair.QUESTIONS:
        state['tasks']['acquire-' + q]['status'] = 'FAILED' if q in ('p14', 'gatecoin') else 'SUCCEEDED'
    revision = {k: {'path': k, 'sha256': k} for k in repair.POINTERS}
    proposed = repair.expected_program(old, state, revision, repair.ROOT)
    a = {r['id']: r for r in old['tasks']}
    b = {r['id']: r for r in proposed['tasks']}
    assert proposed['deadline_utc'] == old['deadline_utc'] and proposed['workers'] == old['workers']
    assert set(a) == set(b)
    assert set(repair.reopened(state)) == {'current-binding', 'account-qualification', 'campaign',
        'continuation-review', 'acquire-p14', 'acquire-gatecoin'}
    for tid in a:
        for key in ('requires', 'after', 'any_success', 'write_resources', 'executor', 'command'):
            assert a[tid].get(key) == b[tid].get(key)
        if tid in repair.reopened(state):
            assert b[tid]['maximum_attempts'] == len(state['tasks'][tid]['attempts']) + 1
        else:
            assert a[tid] == b[tid]


def census(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, 'dispatch_roots', lambda _: ['prior'])
    rows = []
    for i in range(2):
        path = Path('prior') / str(i) / 'calls/dispatch.json'
        save(tmp_path / path, {'calls': {'detail-0': {'status': 'VALIDATED'}}})
        archive = Path('frozen') / path
        save(tmp_path / archive, read(tmp_path / path))
        rows.append({'previous': ref(tmp_path, path), 'archive': ref(tmp_path, archive)})
    return {'dispatch_roots': ['prior'], 'dispatch_census': rows, 'archived': deepcopy(rows)}


def test_settled_census_is_exhaustive(tmp_path, monkeypatch):
    baseline = census(tmp_path, monkeypatch)
    repair.check_settled_census(tmp_path, baseline, {}, current=True)
    baseline['dispatch_census'].pop()
    with pytest.raises(Refused): repair.check_settled_census(tmp_path, baseline, {}, current=True)


@pytest.mark.parametrize('mutation', ['reserved', 'changed', 'duplicate', 'outside', 'roots'])
def test_settled_census_rejects_invalid_inputs(tmp_path, monkeypatch, mutation):
    baseline = census(tmp_path, monkeypatch)
    row = baseline['dispatch_census'][0]
    if mutation == 'reserved':
        save(tmp_path / row['previous']['path'], {'calls': {'detail-0': {'status': 'RESERVED'}}})
        save(tmp_path / row['archive']['path'], read(tmp_path / row['previous']['path']))
        row['previous'] = ref(tmp_path, row['previous']['path'])
        row['archive'] = ref(tmp_path, row['archive']['path'])
        baseline['archived'][0] = deepcopy(row)
    elif mutation == 'changed': save(tmp_path / row['previous']['path'], {'calls': {}})
    elif mutation == 'duplicate': baseline['dispatch_census'].append(deepcopy(row))
    elif mutation == 'outside': row['previous']['path'] = 'unrelated/dispatch.json'
    else: baseline['dispatch_roots'] = ['unrelated']
    with pytest.raises(Refused): repair.check_settled_census(tmp_path, baseline, {}, current=True)


@pytest.mark.parametrize('q', ['p14', 'p10'])
@pytest.mark.parametrize('prepare', [True, False])
def test_actual_route_preserves_successful_paths_and_selects_capacity_only_for_failures(monkeypatch, q, prepare):
    from scripts import legal_product_completion as completion
    recoveries = {i: {'path': i, 'sha256': i} for i in ('p10', 'p14')}
    revision = {'failed_questions': ['p14'], 'recoveries': recoveries,
        'output_profile': account_output.PROFILE,
        'common_directories': {'p14': 'new/common/p14', 'p10': 'old/common/p10'},
        'live_directories': {'p14': 'new', 'p10': 'old'}}
    program = {repair.KEY: revision, 'account_instruction_repair': {}, 'lossless_account_repair': {}}
    # These switches are tested as presence as well as truthy profile data.
    program['account_instruction_repair'] = {'profile': 'inherited'}
    program['lossless_account_repair'] = {'profile': 'inherited'}
    monkeypatch.setattr(live, 'configure', lambda: SimpleNamespace(ENVELOPE=Path('envelope.json')))
    monkeypatch.setattr(live, 'read', lambda path: program if path == live.ROOT / live.PROGRAM else
        {'original_questions': [{'question_id': q}]} if path.name == 'envelope.json' else
        {'deadline_utc': '2026-10-18T00:00:00+00:00'})
    monkeypatch.setattr(live, 'ref', lambda *args: {'path': str(args[-1]), 'sha256': 'identity'})
    monkeypatch.setattr(live, 'tokenizer', lambda *_: list)
    monkeypatch.setattr(live, 'phase_admit', lambda *_: None)
    monkeypatch.setattr(completion, 'run_product', lambda *args, **kwargs: (args, kwargs))
    args, options = live.product_route(q, None, object(), preparation_only=prepare)
    base = 'new' if q == 'p14' else 'old'
    assert args[1] == live.ROOT / (base + '/common/' + q if prepare else base + '/arms/' + q + '/baseline')
    assert options['shared_prefix'] == (None if prepare else live.ROOT / base / 'common' / q / 'calls')
    assert options['bounded_requirement_account_recovery'] == recoveries[q]
    assert options['bounded_requirement_account_input_profile'] == account_encoding.PROFILE
    assert options['bounded_requirement_account_instruction_profile'] == account_instructions.PROFILE
    assert options.get('bounded_requirement_account_capacity_profile') == (account_input.CAPACITY_PROFILE if q == 'p14' else None)
    assert options.get('bounded_requirement_account_output_profile') == (account_output.PROFILE if q == 'p14' else None)


def test_actual_qualification_result_is_reused_by_normal_note_in_same_product(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance.bounded_references import prepare
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    from legalmath.interpretation.assurance.bounded_context import Limits
    env = envelope()
    options = dict(limits=Limits(), maximum_calls=8100,
        maximum_corrections=1, active_questions=['p14'], requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_instruction_profile=account_instructions.PROFILE)
    prior = BoundedProduct(tmp_path, tmp_path / 'prior', Scripted(fail_at=2), env, list, **options)
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    question = env['original_questions'][0]
    payload = {'original_assignment': {'assignment': 'Preserve both'},
        'partial_source_readings': [{'conclusion': 'Duty'}, {'conclusion': 'Exception'}]}
    good = prior.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, payload, ['o1'])
    failed = prior.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', question, records, payload, ['o2'])
    details = [{'id': 'o1', 'result': good}, {'id': 'o2', 'result': failed}]
    save(tmp_path / 'prior/requirement-details.json', details)
    recovery = account_recovery.build(tmp_path, tmp_path / 'prior/calls', details)
    save(tmp_path / 'recovery.json', recovery)
    pointer = evidence_file(tmp_path / 'recovery.json', tmp_path)
    options.update(requirement_account_recovery=pointer,
        requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
        requirement_account_output_profile=account_output.PROFILE)
    provider = Scripted()
    admissions = []
    admit = lambda name: lambda phase, count: admissions.append((name, phase, count)) or {'name': name, 'phase': phase, 'count': count}
    product = PhasedProduct(tmp_path, tmp_path / 'common', provider, env, list,
        phase_admit=admit('qualification'), phase_identity='binding', **options)
    request = account_contract.select(product.request('ASSESS_ORIGINAL_REQUIREMENT', question, records,
        payload=payload, expected=['o2']), input_profile=account_encoding.PROFILE,
        instruction_profile=account_instructions.PROFILE, capacity_profile=account_input.CAPACITY_PROFILE,
        output_profile=account_output.PROFILE)
    schema = account_contract.provider_schema()
    save(tmp_path / 'request.json', request)
    save(tmp_path / 'schema.json', schema)
    save(tmp_path / 'prepared.json', prepare(request, schema))
    legacy = deepcopy(request); legacy.pop('account_capacity_profile'); legacy.pop('account_output_profile')
    save(tmp_path / 'refused.json', {'request': legacy, 'schema': schema})
    case = {'question': 'p14', 'key': 'detail-1', 'request': ref(tmp_path, 'request.json'),
        'schema': ref(tmp_path, 'schema.json'), 'prepared': ref(tmp_path, 'prepared.json'),
        'original_refusal': ref(tmp_path, 'refused.json'), 'measurement': product.dispatch.measure(request, schema)}
    save(tmp_path / 'case.json', case)
    program = {repair.KEY: {'qualification_input': ref(tmp_path, 'case.json'), 'common_directories': {'p14': 'common'},
        'output_profile': account_output.PROFILE,
        'recoveries': {'p14': pointer}}, 'prerequisite_repair': {'source': {'path': 'envelope.json'}}}
    save(tmp_path / repair.PROGRAM, program)
    save(tmp_path / 'envelope.json', env)
    monkeypatch.setattr(repair, 'ROOT', tmp_path)
    monkeypatch.setattr(repair, 'TOKENIZER', Path('unused-tokenizer'))
    monkeypatch.setattr(live, 'phase_admit', admit)
    monkeypatch.setattr(repair, 'ref', lambda root, path: {'path': str(path), 'sha256': 'binding'}
        if path == repair.BASE / 'current-binding.json' else ref(root, path))
    from legalmath.interpretation.assurance import bounded_context
    monkeypatch.setattr(bounded_context, 'tokenizer', lambda _: list)
    outcome = repair.qualify_accounts(provider)
    assert outcome['_node_status'] == 'SUCCEEDED'
    assert len(provider.requests) == 1
    ordinary = PhasedProduct(tmp_path, tmp_path / 'common', provider, env, list,
        phase_admit=admit('acquisition'), phase_identity='binding', **options)
    ordinary.install_dispatch_admission()
    reused = ordinary.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', question,
        [r for r in ordinary.route.records.values() if r['kind'] == 'source'], payload, ['o2'])
    assert reused['status'] == 'VALIDATED' and len(provider.requests) == 1
    assert len(admissions) == 1


def test_deferred_evidence_keeps_its_unused_sixth_attempt():
    old, state = frozen_program_and_state()
    assert state['tasks']['acquire-evidence']['status'] == 'BLOCKED'
    revision = {k: {'path': k, 'sha256': k} for k in repair.POINTERS}
    proposed = repair.expected_program(old, state, revision, repair.ROOT)
    before = next(n for n in old['tasks'] if n['id'] == 'acquire-evidence')
    after = next(n for n in proposed['tasks'] if n['id'] == 'acquire-evidence')
    assert len(state['tasks']['acquire-evidence']['attempts']) == 5
    assert before['maximum_attempts'] == after['maximum_attempts'] == 6
    assert state['tasks']['acquire-evidence']['attempts'] == frozen_program_and_state()[1]['tasks']['acquire-evidence']['attempts']


def test_partial_successor_preparation_resumes_once_and_never_resets(tmp_path):
    scope = {'profile': 'reviewed-shared-phase-service.v1', 'prior_replacements': {'path': 'old', 'sha256': 'old'}}
    replacements = {'maximum': 48, 'charges': list(range(48))}
    circuit = {'path': 'old-circuit', 'sha256': 'frozen'}
    save(tmp_path / 'service/scope.json', scope)
    first = repair.retain_successor_files(tmp_path, Path('service'), scope, replacements, circuit)
    assert repair.retain_successor_files(tmp_path, Path('service'), scope, replacements, circuit) == first
    retained = read(tmp_path / 'service/service-recovery.json')
    assert retained['charges'] == replacements['charges'] and retained['maximum'] == 48
    assert retained['stage_hash'] == first['sha256']
    changed = read(tmp_path / 'service/service-circuit.json')
    changed.update(open=True, consecutive_failures=1, failed_slots=[2200])
    save(tmp_path / 'service/service-circuit.json', changed)
    with pytest.raises(Refused):
        repair.retain_successor_files(tmp_path, Path('service'), scope, replacements, circuit)
    assert read(tmp_path / 'service/service-circuit.json') == changed


def frozen_program_and_state():
    baseline = read(repair.ROOT / repair.WORK / 'baseline.json')
    pointers = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    return (read(repair.ROOT / pointers[str(repair.PROGRAM)]['path']),
            read(repair.ROOT / pointers[str(repair.STATE)]['path']))


def test_nested_historical_review_uses_identical_archive_only_in_scope(tmp_path):
    source = Path('source.py')
    (tmp_path / source).write_text('old source\n')
    original = ref(tmp_path, source)
    (tmp_path / 'archive.py').write_text('old source\n')
    archived = ref(tmp_path, 'archive.py')
    save(tmp_path / 'sealed.json', {'evidence': [original]})
    sealed = ref(tmp_path, 'sealed.json')
    (tmp_path / source).write_text('new source\n')
    mapping = {(original['path'], original['sha256']): archived}
    with historical_evidence(tmp_path, mapping):
        verify(tmp_path, read(tmp_path / 'sealed.json')['evidence'][0])
        verify(tmp_path, ref(tmp_path, source))
        assert ref(tmp_path, 'sealed.json') == sealed
        with pytest.raises(Refused):
            verify(tmp_path, {**original, 'sha256': 'unmatched'})
        other = tmp_path / 'other'; other.mkdir()
        (other / source).write_text('different root\n')
        with pytest.raises(Refused): verify(other, original)
    with pytest.raises(Refused): verify(tmp_path, original)
    with pytest.raises(RuntimeError):
        with historical_evidence(tmp_path, mapping):
            raise RuntimeError('restore after failure')
    with pytest.raises(Refused): verify(tmp_path, original)
    (tmp_path / 'archive.py').write_text('corrupt archive\n')
    with pytest.raises(Refused):
        with historical_evidence(tmp_path, mapping): pass
    with pytest.raises(Refused):
        with historical_evidence(tmp_path, {(source.as_posix(), 'wrong'): ref(tmp_path, 'archive.py')}): pass


def test_actual_registration_candidate_validates_without_state_or_ledger_changes():
    paths = (repair.PROGRAM, repair.STATE, repair.DOC / 'mission.json',
        repair.BASE / 'live-calls.json', repair.BASE / 'current-binding.json')
    before = {str(path): ref(repair.ROOT, path) for path in paths}
    program, state, revision = repair.registration_candidate()
    assert program[repair.KEY] == revision
    assert state == frozen_program_and_state()[1]
    assert {str(path): ref(repair.ROOT, path) for path in paths} == before
    # A historical mapping must not survive predecessor validation.
    baseline = read(repair.ROOT / repair.WORK / 'baseline.json')
    row = next(r for r in baseline['archived'] if r['previous']['path'] ==
        'src/legalmath/interpretation/assurance/phased/account_recovery.py')
    with pytest.raises(Refused): verify(repair.ROOT, row['previous'])
