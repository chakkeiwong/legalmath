"""Source-qualified annual policies and events reach normal statement output."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import pytest

from legalmath.prospectus.successor import statement_cells
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_annual_group_reading import PROFILE, FIELD
from scripts.prospectus_annual_group_checks import check, mutations, CASES

FIXTURE = Path(__file__).parent / 'fixtures/bes_annual2010_statement_cells_v7.json.gz'


def supplied():
    fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    graph = fixture['graph']
    return graph, {'version': 'source-statement-cells.v1', 'profile': PROFILE, 'document': 'bes-2010-en',
        'graph_sha256': digest(graph), 'reading': fixture['reading'],
        'review': {'kind': 'DEVELOPMENT', 'reviewer': 'inspected original source', 'reason': 'Attributed historical statements'}}


def test_complete_reading_and_existing_meanings():
    graph, reading = supplied()
    answer = statement_cells.explain(statement_cells.admit(graph, reading))
    assert check(answer[FIELD], graph)['entities'] == 145
    old = json.loads(gzip.decompress((FIXTURE.parent / 'bes_annual2010_statement_cells_v6.json.gz').read_bytes()))['reading']
    for key in ('primary_statements', 'eps_cash_notes', 'capital_notes', 'basis_estimates_pronouncements', 'consolidation_assets_subsequent_events', 'remaining_accounting_policies', 'income_notes_and_group_context'):
        assert answer[key] == old[key]
    assert not answer['source_context']['all_notes_read']
    assert not answer['independent_financial_acceptance']


def test_method_tokens_left_of_boundary_and_combined_occurrence():
    from scripts.prospectus_annual_group_reading import reading as build
    graph, supplied_reading = supplied()
    value=build(graph)
    rows={r['id']:r for r in value['entities']}
    assert rows['p99-l379']['fields']['method']['value']=='FULL_CONSOLIDATION'
    assert rows['p99-l379']['fields']['economic_interest']['percent']=='100.00'
    assert rows['p99-l376']['fields']['method']['value']=='FULL_CONSOLIDATION'


@pytest.mark.parametrize('index', range(len(CASES) + 29))
def test_material_alterations_are_rejected(index):
    graph, reading = supplied()
    name, changed = list(mutations(reading['reading'][FIELD]))[index]
    with pytest.raises(ValueError):
        check(changed, graph)
    reading['reading'][FIELD] = changed
    with pytest.raises(ValueError, match='reading differs'):
        statement_cells.admit(graph, reading)


@pytest.mark.parametrize('change', ['omit-page', 'alter-text', 'wrong-source', 'hidden', 'duplicate'])
def test_source_corruption_refused(change):
    graph, reading = supplied()
    graph = deepcopy(graph)
    unit = next(u for u in graph['units'] if u['page'] == 100)
    if change == 'omit-page':
        graph['units'] = [u for u in graph['units'] if u['page'] != 100]
    elif change == 'alter-text':
        unit['raw'] = 'Control is determined solely by majority ownership.'
    elif change == 'wrong-source':
        unit['source_sha256'] = '0' * 64
    elif change == 'hidden':
        unit['visible'] = False
    else:
        graph['units'].append(deepcopy(unit))
    reading['graph_sha256'] = digest(graph)
    with pytest.raises(ValueError, match='original pages|Duplicate'):
        statement_cells.admit(graph, reading)
