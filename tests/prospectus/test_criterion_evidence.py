"""Evidence lifecycle tests; domain proof is checked by the actual H1 trial."""
from copy import deepcopy

import pytest

from tests.prospectus.test_execution_authority import authority, result_files
from legalmath.prospectus import build_contract
from legalmath.prospectus.execution_authority import CODE, digest, file_hash, read, write


def revise(a, change):
    p = deepcopy(a.spec()[0])
    baseline = digest(p)
    p['revision'] += 1
    change(p)
    name = 'review-' + str(p['revision']) + '.json'
    write(a.root / 'proposal.json', p)
    write(a.root / name, {'baseline': baseline, 'changes': 'Criterion lifecycle fixture',
        'skeptical_audit': 'Domain validation separate from state transitions',
        'evidence_contract': 'Retain only unchanged independently validated criterion',
        'scope_unchanged': True, 'budget_unchanged': True, 'delivery_scope_changed': True,
        'delivery_authorization': p['build_contract']['authorization'], 'original_obligations_preserved': True})
    return a.revise('proposal.json', name)


def setup(a, monkeypatch):
    method = 'src/legalmath/prospectus/criterion_evidence.py'
    (a.root / method).write_text('# criterion evidence fixture\n')
    monkeypatch.setitem(build_contract.VALIDATORS, 'pension-rounding.v1', ('source', 'pension-rounding'))
    monkeypatch.setattr(build_contract, 'validate_submission',
                        lambda _r, _a, t, _p: list(t.get('build_criteria_scope', [])))

    def configure(p):
        original = deepcopy(p['tasks'][1])
        for name in build_contract.DEFERRED:
            p['tasks'].append({**deepcopy(original), 'id': name, 'repair_of': 'readers'})
            p['obligations'][1]['tasks'].append(name)
        p['build_contract'] = {'version': 'general-build.v2',
            'authorization': {'path': 'dossier.md', 'sha256': file_hash(a.root / 'dossier.md')},
            'required_tasks': ['source', 'readers'], 'deferred_tasks': dict(build_contract.DEFERRED),
            'real_case': 'AFTER_GENERAL_BUILD', 'external_opinion_required': False,
            'cdm_receiver': None, 'portability': 'DEFERRED',
            'claim': 'CONDITIONAL_CORRECTNESS_IN_DECLARED_SUPPORTED_DOMAIN',
            'criteria': {'source': [
                {'id': 'pension-rounding', 'basis': 'NAMED_CONDITIONAL_CHECK',
                 'validator': 'pension-rounding.v1', 'description': 'Finite proof'},
                {'id': 'remaining', 'basis': 'ORIGINAL_TASK_ACCEPTANCE',
                 'validator': None, 'description': 'Original source work'}]}}
        p['tasks'][0].update(build_criteria_scope=['pension-rounding'],
            inputs=['source.txt', method, *CODE],
            build_criterion_lineage={'pension-rounding': {
                'version': 'criterion-evidence.v1', 'files': ['source.txt'], 'trees': ['src/legalmath']}})
    revise(a, configure)
    admitted = a.admit()
    attempt = result_files(a, admitted)
    state = a.record(admitted['attempt'])
    assert len(state['current_build']['verified_criteria']) == 1
    assert not state['current_build']['complete'] and not state['program_complete']
    return attempt


def count(a):
    return len(a.status()['current_build']['verified_criteria'])


def test_criterion_survives_scheduling_refinement_and_unrelated_record(authority, monkeypatch):
    setup(authority, monkeypatch)
    revise(authority, lambda p: p['tasks'][0].update(
        reason='Next source gap', title='Continue source meaning', build_criteria_scope=[]))
    assert count(authority) == 1
    admission = authority.admit()
    assert count(authority) == 1
    result_files(authority, admission)
    state = authority.record(admission['attempt'])
    assert count(authority) == 1 and not state['current_build']['complete']
    assert state['tasks'][0]['state'] == 'RESULT_RECORDED'


@pytest.mark.parametrize('mutation', ['source', 'method', 'added-file', 'deleted-file',
    'output', 'admission', 'contract', 'criterion', 'task-acceptance', 'dependencies', 'missing-contract'])
def test_changed_proof_never_remains_current(authority, monkeypatch, mutation):
    attempt = setup(authority, monkeypatch)
    if mutation in {'source', 'method'}:
        (authority.root / ('source.txt' if mutation == 'source' else CODE[0])).write_text('changed\n')
    elif mutation == 'added-file':
        (authority.root / 'src/legalmath/additional.py').write_text('changed\n')
    elif mutation == 'deleted-file':
        (authority.root / 'src/legalmath/prospectus/criterion_evidence.py').unlink()
    elif mutation in {'output', 'admission'}:
        path = attempt / ('result.json' if mutation == 'output' else 'admission.json')
        write(path, read(path) | {'tampered': True})
    elif mutation == 'contract':
        revise(authority, lambda p: p['tasks'][0]['build_criterion_lineage']['pension-rounding']['files'].append('src/legalmath/prospectus/criterion_evidence.py'))
    elif mutation == 'missing-contract':
        revise(authority, lambda p: p['tasks'][0].pop('build_criterion_lineage'))
    elif mutation == 'criterion':
        revise(authority, lambda p: p['build_contract']['criteria']['source'][0].update(description='Different proof'))
    elif mutation == 'task-acceptance':
        revise(authority, lambda p: p['tasks'][0].update(acceptance='Different substantive acceptance'))
    else:
        revise(authority, lambda p: p['tasks'][0].update(depends_on=['readers']))
    # Missing required source code makes the whole specification invalid; it
    # must not return an accepted criterion by falling back to old evidence.
    if mutation == 'deleted-file':
        with pytest.raises(ValueError, match='Missing retained'):
            authority.status()
    else:
        assert count(authority) == 0


@pytest.mark.parametrize('outcome', ['REJECT', 'INTERRUPT', 'RECORD-without-acceptance'])
def test_failed_recheck_cannot_resurrect_older_success(authority, monkeypatch, outcome):
    setup(authority, monkeypatch)
    revise(authority, lambda p: p['tasks'][0].update(reason='Recheck same criterion'))
    admission = authority.admit()
    if outcome == 'RECORD-without-acceptance':
        monkeypatch.setattr(build_contract, 'validate_submission', lambda *a: [])
        result_files(authority, admission)
        authority.record(admission['attempt'])
    else:
        with authority.lock():
            authority.append(outcome, task='source', attempt=admission['attempt'], reason='Actual failed recheck fixture')
    assert count(authority) == 0


def test_unadmitted_new_tree_file_cannot_receive_receipt(authority, monkeypatch):
    setup(authority, monkeypatch)
    revise(authority, lambda p: p['tasks'][0].update(reason='Recheck'))
    admission = authority.admit()
    (authority.root / 'src/legalmath/late.py').write_text('# not frozen at admission\n')
    result_files(authority, admission)
    authority.record(admission['attempt'])
    assert authority.events()[-2]['kind'] == 'REJECT' or count(authority) == 0
    assert count(authority) == 0
