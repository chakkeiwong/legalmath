from copy import deepcopy
import pytest
from scripts import legal_mission_control as control
from tests.tooling.test_legal_mission_control import records


def test_refresh_matches_separate_status_and_admission_with_one_validation(records, monkeypatch):
    mission, tools = records
    expected_status = control.status(mission, tools)
    expected_admission = control.admit(mission, tools)
    before = deepcopy((mission, tools))
    original = control.validate
    validations = []

    def validate(*args, **kwargs):
        validations.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(control, 'validate', validate)
    result = control.refresh(mission, tools)
    assert result['status'] == expected_status
    assert result['admission'] == expected_admission
    assert len(validations) == 1
    assert (mission, tools) == before
    mission['original_obligation_ids'].pop()
    with pytest.raises(control.Refused, match='Original denominator changed'):
        control.refresh(mission, tools)
    assert len(validations) == 2
