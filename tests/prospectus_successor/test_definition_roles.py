"""Reviewed current roles preserve exact source mappings and historical inputs."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor.definition_roles import project

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / 'docs/implementation/prospectus-execution-authority/reviews/definition-roles-327/cases.json').read_text())['cases']


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_independently_authored_cases(case):
    request = deepcopy(case['request'])
    if case['refuse']:
        with pytest.raises(ValueError):
            project(**request)
    else:
        actual = project(**request)
        assert actual['changes'] == case['changes']
        expected = deepcopy(request['report'])
        for row in case['changes']:
            expected['source_pieces'][row['piece']]['assembly_uses'][row['use']]['role'] = row['after']
        assert actual['report'] == expected
    assert request == case['request']


def test_partial_source_slice_uses_selected_and_raw_offsets():
    request = deepcopy(CASES[0]['request'])
    request['raw_units'][0]['raw'] = 'rawNameend'
    source = request['report']['source_pieces'][0]['raw_binding']
    source.update(start=3, end=7)
    use = request['report']['source_pieces'][0]['assembly_uses'][0]
    use.update(start=2, end=6, source=deepcopy(source))
    request['assembly']['units'][0].update(text='..Name..', character_map=[
        {'start': 2, 'end': 6, 'source': deepcopy(source), 'operation': 'Text'}])
    assert project(**request)['changes'] == CASES[0]['changes']


@pytest.mark.parametrize('kind', ['duplicate-raw', 'duplicate-use', 'partition-gap', 'selected-text',
                                  'map-overlap', 'map-gap', 'source-edition', 'hidden-source', 'context'])
def test_additional_mapping_misuse(kind):
    request = deepcopy(CASES[0]['request'])
    piece = request['report']['source_pieces'][0]
    unit = request['assembly']['units'][0]
    if kind == 'duplicate-raw': request['raw_units'].append(deepcopy(request['raw_units'][0]))
    elif kind == 'duplicate-use': piece['assembly_uses'].append(deepcopy(piece['assembly_uses'][0]))
    elif kind == 'partition-gap': piece['start'] = 1
    elif kind == 'selected-text': request['assembly']['continuous_text'] = 'Other'
    elif kind == 'map-overlap': unit['character_map'].append(deepcopy(unit['character_map'][0]))
    elif kind == 'map-gap': unit['character_map'] = []
    elif kind == 'source-edition': request['raw_units'][0]['source_sha256'] = 'b' * 64
    elif kind == 'hidden-source': request['raw_units'][0]['visible'] = False
    else: piece['assembly_uses'][0]['context'] = 'different'
    with pytest.raises(ValueError):
        project(**request)
