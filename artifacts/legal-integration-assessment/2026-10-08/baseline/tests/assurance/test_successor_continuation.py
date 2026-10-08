from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_continuation import reviewed_continuation, LIMITS
from run_assurance_successor import save, sha, read
from legalmath.errors import LegalMathError


def fixture(root):
    d = root / 'study'; d.mkdir()
    grant = root / 'grant.json'; save(grant, {'authorized_calls': 500})
    def ref(name, value):
        p = root / name
        if isinstance(value, str): p.write_text(value)
        else: save(p, value)
        return {'path': name, 'sha256': sha(p)}
    review = ref('review.md', 'Checked continuation with unchanged semantic limits')
    tests = ref('checks.xml', '<testsuite tests="1" failures="0" errors="0" skipped="0"/>')
    source = ref('sources.json', {'tasks': [{'task_id': 'a'}, {'task_id': 'b'}]})
    allocation = ref('allocation.json', {'shared_source_freeze_sha256': source['sha256']})
    result = ref('result.json', {'execution_complete': False, 'tasks': [{'task_id': 'a'}, {'task_id': 'b'}],
        'allocation': {'shared_source_freeze_sha256': source['sha256']}})
    failed = ref('failed.json', {'phase': 'S8', 'status': 'FAILED', 'outputs': {result['path']: result['sha256']}})
    scheduling = {'receipt': ref('scheduling.json', {'workers': 4}), 'workers': 4, 'continuation_id': 'original'}
    amendment = {'profile': 'bounded-investigation-continuation.v1', 'limits': LIMITS,
                 'refund_reservations': False, 'grant_sha256': sha(grant),
                 'scheduling_receipt': scheduling['receipt'], 'review': review,
                 'focused_tests': tests, 'failed_phase': failed, 'study_result': result,
                 'allocation': allocation, 'source_freeze': source}
    save(d / 'continuation-amendment-001.json', amendment)
    return d, grant, scheduling


def test_bound_repair_has_new_identity_but_keeps_original_scheduling_and_grant(tmp_path):
    d, grant, scheduling = fixture(tmp_path); before = grant.read_bytes()
    result = reviewed_continuation(d, tmp_path, grant, scheduling)
    assert result['continuation_id'] != scheduling['continuation_id']
    assert result['workers'] == 4 and not result['study_promotion'] and grant.read_bytes() == before
    assert result == reviewed_continuation(d, tmp_path, grant, scheduling)


@pytest.mark.parametrize('mutation', ['review', 'test', 'failure', 'result', 'grant', 'limit', 'refund', 'running', 'denominator'])
def test_detached_or_relaxed_continuation_cannot_authorize_work(tmp_path, mutation):
    d, grant, scheduling = fixture(tmp_path); p = d / 'continuation-amendment-001.json'; a = read(p)
    if mutation in ('review', 'test', 'failure', 'result', 'grant'):
        target = {'review':'review.md','test':'checks.xml','failure':'failed.json','result':'result.json','grant':'grant.json'}[mutation]
        (tmp_path / target).write_text('changed')
    elif mutation == 'limit': a['limits']['pair_perspective_calls'] = 7
    elif mutation == 'refund': a['refund_reservations'] = True
    elif mutation == 'running':
        f = tmp_path / 'failed.json'; v = read(f); v['status'] = 'RUNNING'; save(f, v); a['failed_phase']['sha256'] = sha(f)
    else:
        f = tmp_path / 'sources.json'; save(f, {'tasks': [{'task_id': 'a'}]}); a['source_freeze']['sha256'] = sha(f)
    save(p, a)
    with pytest.raises(LegalMathError): reviewed_continuation(d, tmp_path, grant, scheduling)


def test_absent_amendment_does_not_change_original_investigation(tmp_path):
    scheduling = {'continuation_id': 'original'}
    assert reviewed_continuation(tmp_path, tmp_path, tmp_path/'absent', scheduling) is scheduling


@pytest.mark.parametrize('controlled', [True, False])
def test_owned_stop_can_continue_but_an_unexplained_missing_result_cannot(tmp_path, controlled):
    d, grant, scheduling = fixture(tmp_path); p = d/'continuation-amendment-001.json'; a = read(p)
    del a['study_result']
    f = tmp_path/'failed.json'; v = read(f)
    if controlled: v['error'] = 'CONTROLLED_IMPLEMENTATION_REPAIR_HALT'
    save(f, v); a['failed_phase']['sha256'] = sha(f); save(p, a)
    if controlled: assert reviewed_continuation(d, tmp_path, grant, scheduling)['continuation_id'] != 'original'
    else:
        with pytest.raises(LegalMathError): reviewed_continuation(d, tmp_path, grant, scheduling)


def test_interrupted_scoped_work_completes_in_new_revision_without_repeating_success(tmp_path, monkeypatch):
    from copy import deepcopy
    from tests.assurance.test_round16 import scoped_fixture
    from tests.assurance.test_successor_grants import grant
    from legalmath.canonical import digest
    from legalmath.interpretation.search.providers import CodexProvider, Completion
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    from assurance_successor_resume import ResumingCodex
    packet, claims, candidates, questions, value = scoped_fixture()
    allowance, _ = grant(tmp_path, 10)
    directory = tmp_path/'ensemble'
    issued = []
    def dispatch(self, request, schema, settings):
        slot = self.allowance.reserve(digest(request)); issued.append(slot)
        if slot == 2:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Controlled interrupted transport')
        return Completion(deepcopy(value), {'allowance_slot':slot,
            'provider_route_hash':digest(self.routing), 'request_hash':digest(request)})
    monkeypatch.setattr(CodexProvider, 'complete', dispatch)
    olddir = directory/'revisions/old/scoped'
    first = investigate(packet, claims, candidates, questions, CodexProvider(allowance=allowance),
                        olddir, maximum_rounds=1, maximum_actions=6)
    assert first['status'] == 'DISPATCH_BLOCKED' and issued == [1,2]
    before = (olddir/'model/journal.json').read_bytes()
    provider = ResumingCodex(allowance=allowance, prior_directory=directory)
    result = investigate(packet, claims, candidates, questions, provider,
                         directory/'revisions/reviewed/scoped', maximum_rounds=1, maximum_actions=6)
    assert not result['pending_pairs'] and not result['pairs_with_unassessed_dimensions']
    assert issued == [1,2,3] and allowance.verify()['used'] == 3
    assert result['batches'][0]['attempts'][0]['status'] == 'VALIDATED_PROPOSAL'
    assert (olddir/'model/journal.json').read_bytes() == before
