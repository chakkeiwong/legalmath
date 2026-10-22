"""Annual reported accounting conditions survive the actual statement adapter."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import statement_cells
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_annual_basis_checks import check, mutations

FILE = Path(__file__).parent / 'fixtures/bes_annual2010_statement_cells_v3.json.gz'


def fixture():
    obj = json.loads(gzip.decompress(FILE.read_bytes()))
    g = obj['graph']
    return g, {'version': 'source-statement-cells.v1', 'profile': 'bes-annual2010-statements-basis-estimates.v3',
               'graph_sha256': digest(g), 'document': 'bes-2010-en', 'reading': obj['reading'],
               'review': {'kind': 'DEVELOPMENT', 'reviewer': 'original annual source reading',
                          'reason': 'Attributed report statements; no independent legal or financial acceptance'}}


def test_meanings_reach_normal_statement_explanation():
    graph, supplied = fixture()
    answer = statement_cells.explain(statement_cells.admit(graph, supplied))
    proof = check(answer['basis_estimates_pronouncements'], graph)
    assert proof['judgment_topics'] == 7
    assert proof['adopted_pronouncements'] == 8 and proof['pending_pronouncements'] == 6
    assert not answer['source_context']['all_notes_read']
    assert not answer['independent_financial_acceptance']
    assert answer['legal_dependency_resolution'] == 'UNCHANGED'
    old = json.loads(gzip.decompress((FILE.parent / 'bes_annual2010_statement_cells_v2.json.gz').read_bytes()))
    for field in ('primary_statements', 'eps_cash_notes', 'capital_notes'):
        assert answer[field] == old['reading'][field]


@pytest.mark.parametrize('index', range(18))
def test_changed_qualifier_rejected_by_semantic_check_and_production(index):
    graph, supplied = fixture()
    name, changed = list(mutations(supplied['reading']['basis_estimates_pronouncements']))[index]
    with pytest.raises(ValueError):
        check(changed, graph)
    supplied['reading']['basis_estimates_pronouncements'] = changed
    with pytest.raises(ValueError, match='reading differs'):
        statement_cells.admit(graph, supplied)


@pytest.mark.parametrize('change', ['omit-note-page', 'alter-source-text', 'wrong-edition', 'hidden', 'duplicate'])
def test_source_corruption_cannot_keep_the_profile(change):
    graph, supplied = fixture()
    graph = deepcopy(graph)
    unit = next(u for u in graph['units'] if u['page'] == 185)
    if change == 'omit-note-page':
        graph['units'] = [u for u in graph['units'] if u['page'] != 185]
    elif change == 'alter-source-text':
        unit['raw'] += ' changed'
    elif change == 'wrong-edition':
        unit['source_sha256'] = '0' * 64
    elif change == 'hidden':
        unit['visible'] = False
    else:
        graph['units'].append(deepcopy(unit))
    supplied['graph_sha256'] = digest(graph)
    with pytest.raises(ValueError, match='original pages|Duplicate'):
        statement_cells.admit(graph, supplied)
