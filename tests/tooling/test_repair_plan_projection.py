from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import Refused, ref


def fixture(tmp_path):
    archived = tmp_path / 'before/plan.md'
    archived.parent.mkdir()
    archived.write_text('Retained plan bytes.')
    pointer = ref(tmp_path, archived)
    original = {'path': str(repair.PLAN), 'sha256': pointer['sha256']}
    value = {'protected_evidence': [original, original],
        'tasks': [{'id': 'task', 'maximum_attempts': 2}]}
    return value, pointer, archived


def test_repeated_plan_references_use_one_verified_archive(tmp_path):
    value, pointer, _ = fixture(tmp_path)
    before = deepcopy(value)
    projected = repair.project_retained_plan(value, tmp_path, pointer)
    assert projected['protected_evidence'] == [pointer, pointer]
    assert projected['tasks'] == value['tasks']
    assert value == before


def test_projection_never_hides_unrelated_graph_or_reference_changes(tmp_path):
    value, pointer, _ = fixture(tmp_path)
    baseline = repair.project_retained_plan(value, tmp_path, pointer)
    changed = deepcopy(value)
    changed['tasks'][0]['maximum_attempts'] += 1
    assert repair.project_retained_plan(changed, tmp_path, pointer) != baseline
    changed = deepcopy(value)
    changed['protected_evidence'][0] = {'path': str(repair.PLAN), 'sha256': '0' * 64}
    assert repair.project_retained_plan(changed, tmp_path, pointer) != baseline


def test_changed_archive_bytes_are_refused(tmp_path):
    value, pointer, path = fixture(tmp_path)
    path.write_text('Changed historical bytes.')
    with pytest.raises(Refused):
        repair.project_retained_plan(value, tmp_path, pointer)
