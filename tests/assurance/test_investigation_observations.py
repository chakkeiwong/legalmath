from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.qualification import prospective as ledger
from legalmath.interpretation.assurance import investigation_observations as obs
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.integration_contract import evidence_file
from tests.search.support import FunctionProvider
from tests.catala.backend_support import TOOLCHAIN
from tests.search.test_formal import AT
from .test_integration import source, settings
from .test_successor_workflow import complete_responder


@pytest.fixture(scope='module')
def execution():
    root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix='whole-observation-', dir=root/'artifacts') as directory:
        runner = CompleteInvestigation(root, directory, FunctionProvider(complete_responder),
            root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings(),
            maximum_scoped_actions=12, scoped_rounds=1, machine_qualification=True, catala=TOOLCHAIN)
        document = source()
        document['data'] += '  名義'.encode('utf-8')
        first = runner.run([document], 'Selected gift control — 利益')
        from legalmath.interpretation.search.formal import bundle, snapshots
        packet = loads((root/first['packet']['path']).read_bytes())
        candidates = loads((root/first['candidates']['path']).read_bytes())
        cases = {cid: [{'id': 'mathematical.'+str(i), 'snapshot': snapshot,
                       'valid_at': AT, 'known_at': AT}
                      for i, snapshot in enumerate(snapshots([bundle(reading, packet, AT)], AT, maximum=2))]
                 for cid, reading in candidates.items()}
        result = runner.run([document], 'Selected gift control — 利益', qualification_cases=cases)
        ref = loads((Path(directory)/'current.json').read_bytes())
        yield root, runner, result, ref


def window(tmp_path, monkeypatch, execution, **changes):
    from datetime import datetime, timedelta, timezone
    _, runner, dossier, _ = execution
    location = Path(dossier['core']['interpretation']['directory'])
    envelope = loads((location.parent.parent/'journal.json').read_bytes())
    started = datetime.fromtimestamp(envelope['value']['started_ms']/1000, timezone.utc)
    def before(seconds): return (started-timedelta(seconds=seconds)).isoformat()
    monkeypatch.setattr(ledger, 'now', lambda: before(60))
    spec = obs.freeze(tmp_path/'window', runner, ['synthetic-test-only'],
                      ends_at=(started+timedelta(days=1)).isoformat())
    monkeypatch.setattr(ledger, 'now', lambda: before(10))
    item = {'task_id': 'future.fixture', 'family': 'synthetic-test-only',
            'source_hash': obs.source_identity(dossier['binding']['sources']),
            'question_hash': digest(dossier['binding']['question']),
            'published_at': before(40), 'first_seen_at': before(30), **changes}
    selected = obs.admit(tmp_path/'window', spec['window_hash'], item, runner)
    monkeypatch.setattr(ledger, 'now', lambda: datetime.now(timezone.utc).isoformat())
    return tmp_path/'window', spec, selected


def test_full_method_binds_live_dispatcher_settings_and_stages(execution):
    _, runner, result, _ = execution
    bound = result['binding']['investigation_method']
    assert bound == obs.method(runner)
    assert bound['provider']['live'] is False
    assert bound['machine_qualification']
    assert bound['source_processing']['files']
    assert bound['limits']['outer']['maximum_per_issue'] == 3
    assert bound['transports']['readable_input'] == 'NOT_ENABLED_IN_COMPLETE_INVESTIGATION'
    checked = obs.check_stages(runner.root, result, bound, runner)
    assert checked['candidate_count'] == len(checked['qualifications']) > 0
    assert checked['legal_correctness'] == 'NOT_ESTABLISHED'
    assert all(q['summary']['executed_target_cases'] > 0 for q in checked['qualifications'])


def test_observation_rechecks_actual_qualification_and_retains_denominator(tmp_path, monkeypatch, execution):
    root, runner, dossier, ref = execution
    directory, spec, _ = window(tmp_path, monkeypatch, execution)
    pending = obs.report(directory, spec['window_hash'])
    assert pending['pending'] == 1 and pending['observed'] == 0
    event = obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)
    assert event['summary']['investigation_revision'] == dossier['revision']
    assert len(event['summary']['qualifications']) == len(dossier['qualifications'])
    result = obs.report(directory, spec['window_hash'], expected_head=event['event_hash'])
    assert result['observed'] == 1 and result['pending'] == 0
    assert result['observed_complete'] == 1
    assert not result['human_quality_evidence']
    with pytest.raises(LegalMathError):
        obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)


@pytest.mark.parametrize('field,value', [('scoped_rounds', 2), ('reference_protocol', 'different'),
                                       ('machine_qualification', False)])
def test_reconfigured_method_cannot_observe_old_dossier(tmp_path, monkeypatch, execution, field, value):
    _, runner, _, ref = execution
    directory, spec, _ = window(tmp_path, monkeypatch, execution)
    monkeypatch.setattr(runner, field, value)
    with pytest.raises(LegalMathError):
        obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)
    assert obs.report(directory, spec['window_hash'])['observed'] == 0


def test_repaired_window_keeps_task_but_rejects_confirmation(tmp_path, monkeypatch, execution):
    _, runner, _, ref = execution
    directory, spec, _ = window(tmp_path, monkeypatch, execution)
    obs.repair(directory, spec['window_hash'], runner, reason='Synthetic repair mark')
    with pytest.raises(LegalMathError):
        obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)
    report = obs.report(directory, spec['window_hash'])
    assert report['repaired'] and report['submitted'] == 1 and report['pending'] == 1


@pytest.mark.parametrize('change', [{'source_hash': 'a'*64}, {'question_hash': 'b'*64}])
def test_other_source_or_question_cannot_borrow_observation(tmp_path, monkeypatch, execution, change):
    _, runner, _, ref = execution
    directory, spec, _ = window(tmp_path, monkeypatch, execution, **change)
    with pytest.raises(LegalMathError):
        obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)


def test_missing_stage_cannot_hide_behind_complete_dossier_summary(execution):
    root, runner, original, _ = execution
    dossier = deepcopy(original)
    dossier['evidence'] = [r for r in dossier['evidence'] if not r['path'].endswith('/authority-resolutions.json')]
    with pytest.raises(LegalMathError):
        obs.check_stages(root, dossier, obs.method(runner), runner)


def test_old_component_window_cannot_be_presented_as_whole_method(tmp_path, monkeypatch, execution):
    _, runner, dossier, ref = execution
    monkeypatch.setattr(ledger, 'now', lambda: '2026-01-01T00:00:00Z')
    spec = ledger.freeze(tmp_path/'component', digest(obs.method(runner)), ['test'], ends_at='2026-01-04T00:00:00Z')
    with pytest.raises((LegalMathError, FileNotFoundError)):
        obs.frozen_method(tmp_path/'component', spec['window_hash'])


def test_development_source_stays_ineligible(tmp_path, monkeypatch, execution):
    _, runner, dossier, _ = execution
    monkeypatch.setattr(ledger, 'now', lambda: '2026-01-01T00:00:00Z')
    source_hash = obs.source_identity(dossier['binding']['sources'])
    spec = obs.freeze(tmp_path/'window', runner, ['test'], ends_at='2026-01-04T00:00:00Z',
                      development_sources=[source_hash])
    monkeypatch.setattr(ledger, 'now', lambda: '2026-01-03T00:00:00Z')
    item = {'task_id': 'development', 'family': 'test', 'source_hash': source_hash,
            'question_hash': digest(dossier['binding']['question']),
            'published_at': '2026-01-02T00:00:00Z', 'first_seen_at': '2026-01-02T01:00:00Z'}
    selected = obs.admit(tmp_path/'window', spec['window_hash'], item, runner)
    assert selected['status'] == 'INELIGIBLE' and 'DEVELOPMENT_SOURCE' in selected['reasons']
    with pytest.raises(LegalMathError): obs.admit(tmp_path/'window', spec['window_hash'], item, runner)


@pytest.mark.parametrize('part', ['implementation_identity', 'source_processing_identity'])
def test_parser_or_extractor_change_invalidates_frozen_observation(tmp_path, monkeypatch, execution, part):
    _, runner, _, ref = execution
    directory, spec, _ = window(tmp_path, monkeypatch, execution)
    original = getattr(obs, part)
    if part == 'implementation_identity':
        monkeypatch.setattr(obs, part, lambda: 'c'*64)
    else:
        monkeypatch.setattr(obs, part, lambda path: {**original(path), 'profile': 'changed-extractor'})
    with pytest.raises(LegalMathError):
        obs.observe(directory, spec['window_hash'], 'future.fixture', ref, runner)
    assert obs.report(directory, spec['window_hash'])['pending'] == 1


def test_missing_candidate_qualification_cannot_be_dropped(execution):
    root, runner, original, _ = execution
    dossier = deepcopy(original)
    dossier['qualifications'].pop()
    dossier['component_refs']['qualifications'].pop()
    with pytest.raises(LegalMathError):
        obs.check_stages(root, dossier, obs.method(runner), runner)


def test_incomplete_investigation_is_retained_as_incomplete(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    with TemporaryDirectory(prefix='incomplete-observation-', dir=root/'artifacts') as directory:
        runner = CompleteInvestigation(root, directory, FunctionProvider(complete_responder),
            root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings(),
            maximum_scoped_actions=1, scoped_rounds=1, machine_qualification=True, catala=TOOLCHAIN)
        dossier = runner.run([source()], 'Selected gift control')
        assert not dossier['execution_complete'] and dossier['scoped']['pending_pairs']
        ref = loads((Path(directory)/'current.json').read_bytes())
        selected = (root, runner, dossier, ref)
        window_dir, spec, _ = window(tmp_path, monkeypatch, selected)
        event = obs.observe(window_dir, spec['window_hash'], 'future.fixture', ref, runner)
        assert event['summary']['pending_scoped_pairs']
        result = obs.report(window_dir, spec['window_hash'])
        assert result['observed_incomplete'] == 1 and result['observed_complete'] == 0
        assert result['submitted'] == 1


def test_extra_context_cannot_disguise_primary_development_source(execution):
    _, _, dossier, _ = execution
    sources = deepcopy(dossier['binding']['sources'])
    primary = obs.source_identity(sources)
    assert primary == sources[0]['sha256']
    sources.append({'url': 'https://example.invalid/extra-context', 'media_type': 'text/html', 'sha256': 'd'*64})
    assert obs.source_identity(sources) == primary


def test_same_caps_on_another_spending_ledger_are_a_different_method(tmp_path, monkeypatch, execution):
    from types import SimpleNamespace
    _, runner, _, _ = execution
    allowance = SimpleNamespace(maximum=500, reservation_ceiling=500, slice_maximum=120,
        path=tmp_path/'grant-ledger.json', slice_path=tmp_path/'original-arm.json', grant_bytes=b'fixed-grant')
    monkeypatch.setattr(runner.provider, 'allowance', allowance, raising=False)
    original = obs.method(runner)
    allowance.slice_path = tmp_path/'renamed-arm.json'
    assert digest(obs.method(runner)) != digest(original)


def test_prior_completed_investigation_cannot_count_as_new_observation(tmp_path, monkeypatch, execution):
    from datetime import datetime, timedelta, timezone
    _, runner, dossier, ref = execution
    before = datetime.now(timezone.utc)
    monkeypatch.setattr(ledger, 'now', lambda: before.isoformat())
    spec = obs.freeze(tmp_path/'late-window', runner, ['synthetic-test-only'],
                      ends_at=(before+timedelta(days=1)).isoformat())
    monkeypatch.setattr(ledger, 'now', lambda: (before+timedelta(seconds=4)).isoformat())
    item = {'task_id': 'borrowed.old.run', 'family': 'synthetic-test-only',
        'source_hash': obs.source_identity(dossier['binding']['sources']),
        'question_hash': digest(dossier['binding']['question']),
        'published_at': (before+timedelta(seconds=1)).isoformat(),
        'first_seen_at': (before+timedelta(seconds=2)).isoformat()}
    assert obs.admit(tmp_path/'late-window', spec['window_hash'], item, runner)['status'] == 'PENDING'
    with pytest.raises(LegalMathError) as error:
        obs.observe(tmp_path/'late-window', spec['window_hash'], 'borrowed.old.run', ref, runner)
    assert error.value.code == 'E_STALE_REVIEW'
    assert obs.report(tmp_path/'late-window', spec['window_hash'])['pending'] == 1
