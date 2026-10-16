from copy import deepcopy
import pytest
from scripts import legal_integration_repair_execution as repair
from scripts.legal_mission_execution import read, Refused
from legalmath.interpretation.assurance.phased.downstream_edits import PROFILE
from tests.tooling.test_synthesis_correction_scope import corrected


def editable(root, monkeypatch):
    revision, spec, put = corrected(root, monkeypatch)
    combined = read(root / revision['synthesis_successors']['gatecoin']['path'])
    checkpoint = read(root / combined['synthesis']['path'])
    keys = revision['response_correction_keys']
    checkpoint.update(edit_profile=PROFILE, edit_corrections={keys[0]: {'path': 'original-rejection.json'}})
    combined['synthesis'] = put('edit-synthesis.json', checkpoint)
    pointer = put('edit-combined.json', combined)
    replay = read(root / revision['successor_replay']['path'])
    replay.update(composite=pointer, wire_schema_preserved=False, changed_wire_schema_keys=keys,
        unchanged_wire_schemas=2, original_rejections_reproduced=keys, edit_slots_verified=True)
    revision.update(downstream_edit_profile=PROFILE, response_edit_keys=keys,
        synthesis_successors={'gatecoin': pointer}, successor_replay=put('edit-replay.json', replay))
    for name in ('downstream_edit_profile', 'response_edit_keys', 'synthesis_successors', 'successor_replay'):
        spec[name] = deepcopy(revision[name])
    return revision, spec, put


def test_schema_amendment_is_explicit_and_single_request_only(tmp_path, monkeypatch):
    revision, spec, _ = editable(tmp_path, monkeypatch)
    repair.validate_synthesis_successor(tmp_path, revision, spec)


@pytest.mark.parametrize('change', ['profile', 'key', 'hidden_schema', 'extra_schema', 'count',
    'lost_original_rejection', 'slots', 'false_unchanged', 'lost_revision'])
def test_unreviewed_edit_amendment_is_refused(tmp_path, monkeypatch, change):
    revision, spec, put = editable(tmp_path, monkeypatch)
    replay = read(tmp_path / revision['successor_replay']['path'])
    if change == 'profile': revision['downstream_edit_profile'] = 'unknown'
    elif change == 'key': revision['response_edit_keys'] = ['other']
    elif change == 'hidden_schema': replay['changed_wire_schema_keys'] = []
    elif change == 'extra_schema': replay['changed_wire_schema_keys'] = ['reduce-gatecoin-0-11', 'other']
    elif change == 'count': replay['unchanged_wire_schemas'] = 1
    elif change == 'lost_original_rejection': replay['original_rejections_reproduced'] = []
    elif change == 'slots': replay['edit_slots_verified'] = False
    elif change == 'false_unchanged': replay['wire_schema_preserved'] = True
    else: revision.pop('downstream_edit_profile')
    revision['successor_replay'] = put('changed-edit-replay.json', replay)
    for name in ('downstream_edit_profile', 'response_edit_keys', 'successor_replay'):
        if name in revision: spec[name] = deepcopy(revision[name])
    with pytest.raises(Refused): repair.validate_synthesis_successor(tmp_path, revision, spec)
