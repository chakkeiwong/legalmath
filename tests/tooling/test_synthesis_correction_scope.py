from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import read, Refused
from legalmath.interpretation.assurance.phased.downstream_instructions import PROFILE
from tests.tooling.test_synthesis_continuation_scope import fixture


def corrected(root, monkeypatch):
    revision, spec, put = fixture(root, monkeypatch)
    combined = read(root / revision['synthesis_successors']['gatecoin']['path'])
    checkpoint = read(root / combined['synthesis']['path'])
    key = 'reduce-gatecoin-0-11'
    checkpoint['rows'][key] = {'disposition': 'COMPLETED_RESPONSE_REJECTED'}
    checkpoint['instruction_profile'] = PROFILE
    combined['synthesis'] = put('correctable-synthesis.json', checkpoint)
    pointer = put('correctable-combined.json', combined)
    replay = read(root / revision['successor_replay']['path'])
    replay.update(composite=pointer, exact_contracts=3, reproduced_rejections=[key],
        original_evidence_preserved=True, wire_schema_preserved=True, first_missing_key='reduce-gatecoin-0-9')
    revision.update(downstream_instruction_profile=PROFILE, response_correction_keys=[key],
        synthesis_successors={'gatecoin': pointer}, successor_replay=put('correctable-replay.json', replay))
    revision['service_continuation']['maximum_response_corrections'] = 1
    for name in ('downstream_instruction_profile', 'response_correction_keys',
            'synthesis_successors', 'successor_replay', 'service_continuation'):
        spec[name] = deepcopy(revision[name])
    return revision, spec, put


def test_one_reviewed_correction_is_distinct_from_one_transport_redispatch(tmp_path, monkeypatch):
    revision, spec, _ = corrected(tmp_path, monkeypatch)
    repair.validate_synthesis_successor(tmp_path, revision, spec)


@pytest.mark.parametrize('change', ['profile', 'population', 'extra_correction', 'not_reproduced',
    'changed_evidence', 'changed_schema', 'wrong_first'])
def test_unreviewed_response_changes_refused(tmp_path, monkeypatch, change):
    revision, spec, put = corrected(tmp_path, monkeypatch)
    replay = read(tmp_path / revision['successor_replay']['path'])
    if change == 'profile': revision['downstream_instruction_profile'] = 'unreviewed'
    elif change == 'population': revision['response_correction_keys'] = []
    elif change == 'extra_correction': revision['service_continuation']['maximum_response_corrections'] = 2
    elif change == 'not_reproduced': replay['reproduced_rejections'] = []
    elif change == 'changed_evidence': replay['original_evidence_preserved'] = False
    elif change == 'changed_schema': replay['wire_schema_preserved'] = False
    else: replay['first_missing_key'] = 'reduce-gatecoin-0-11'
    revision['successor_replay'] = put('altered-replay.json', replay)
    for name in ('downstream_instruction_profile', 'response_correction_keys',
            'successor_replay', 'service_continuation'):
        spec[name] = deepcopy(revision[name])
    with pytest.raises(Refused): repair.validate_synthesis_successor(tmp_path, revision, spec)
