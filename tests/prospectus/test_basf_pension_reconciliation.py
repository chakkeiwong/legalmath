"""Pinned policy, independent arithmetic and actual consumer dispatch boundaries."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus import basf_pension_note as note
from legalmath.prospectus import basf_pension_reconciliation as r
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_pension_reconciliation import PRIOR, controls, load, verify


@pytest.fixture
def case(tmp_path):
    (tmp_path / 'original.pdf').write_bytes(b'fixture original report')
    (tmp_path / 'policy.png').write_bytes(b'fixture policy image')
    sha = digest((tmp_path / 'original.pdf').read_bytes())
    units = [{'id': r.DOCUMENT + ':p209:l' + str(n), 'document': r.DOCUMENT,
              'source_sha256': sha, 'raw': text, 'visible': True, 'page': 209, 'bbox': None}
             for n, text in zip(range(24, 29), r.POLICY)]
    def cell(value, *, table=False):
        literal = '–' if value is None else ('–' if value < 0 else '') + format(abs(value), ',')
        u = {'id': r.DOCUMENT + ':cell' + str(len(units)), 'document': r.DOCUMENT,
             'source_sha256': sha, 'raw': literal, 'visible': True, 'page': 204, 'bbox': None}
        units.append(u)
        source = {**anchor(u), 'page': 204, 'bbox': None}
        return {'value': value, 'kind': 'million_eur', 'unit': 'million EUR', 'literal': literal,
                **({'status': 'PRINTED_INTEGER' if value is not None else 'PRINTED_DASH_UNKNOWN',
                    'unit_basis': 'PRINTED_TABLE_UNIT'} if table else {}),
                'source': [source] if table else source}
    statement = []
    for name, values in [('pensions', (3758, 3476)), ('pension_tax', (-1256, -811)),
                         ('equity_nonrec', (83, 44)), ('nonrec', (2586, 2709))]:
        qs = {year: cell(value) for year, value in zip(('2022', '2021'), values)}
        statement.append({'id': name, 'cells': {year: {'integer_millions': q['value'],
            'literal': q['literal'], 'source': q['source']} for year, q in qs.items()}})
    net = [{'id': name, 'cells': {year: cell(value, table=True) for year, value in zip(('2022', '2021'), values)}}
           for name, values in [('actuarial', (6800, 1496)), ('return_deviation', (-2641, 1935)),
                                ('ceiling', (-431, None))]]
    baseline = {'answer': {'prior_answer': 'retain this'}, 'statement_review': {'rows': statement},
        'pension_note_review': {'tables': {'net': {'rows': net}}, 'profile': {'source': {'sha256': sha}},
                                'answer': {'prior_pension': 'retain this'}},
        'pension_explanation': {'prior_pension': 'retain this'}}
    graph = {'units': units}
    profile = {'version': 'basf-pension-reconciliation.v1', 'graph_sha256': digest(graph),
        'consumer_sha256': digest(baseline), 'source': {'document': r.DOCUMENT, 'path': 'original.pdf',
        'sha256': sha, 'image_path': 'policy.png', 'image_sha256': digest((tmp_path / 'policy.png').read_bytes()), 'page': 209},
        'policy': [anchor(u) for u in units[:5]], 'hypotheses': list(deepcopy(r.HYPOTHESES)),
        'actual_rounding_algorithm_established': False, 'selected_incorporation_reading': None}
    return graph, baseline, profile, tmp_path


def actual(case):
    graph, baseline, profile, root = case
    review = r.evaluate(graph, baseline, profile, root, expected_profile_sha256=digest(profile))
    return {**baseline, r.ADDED_KEYS[0]: review, r.ADDED_KEYS[1]: deepcopy(review['answer'])}


def test_four_dated_relations_pass_separate_integer_oracle(case):
    graph, baseline, profile, _ = case
    checked = verify(actual(case), baseline, profile, graph)
    assert [r['known_part'] for r in checked['relations']] == [30, 1, 45, 0]
    assert checked['relations'][2]['unknown_components'] == 1
    assert checked['source_questions_resolved'] is False


def test_semantic_mutations_and_repinned_profiles_are_refused(case):
    graph, baseline, profile, root = case
    checked = controls(actual(case), baseline, profile, graph, root)
    assert len(checked['controls']) == 22 and checked['permissive_checker_detected'] is True


@pytest.mark.parametrize('mutation', ['missing', 'dictionary', 'bad-fragment', 'unknown-unit',
                                    'offset', 'page', 'box', 'quote', 'digest', 'literal'])
def test_independent_oracle_refuses_bad_table_occurrences_with_repinned_baseline(case, mutation):
    graph, baseline, profile, _ = case
    q = baseline['pension_note_review']['tables']['net']['rows'][0]['cells']['2022']
    occurrence = q['source'][0]
    if mutation == 'missing': q['source'] = []
    elif mutation == 'dictionary': q['source'] = occurrence
    elif mutation == 'bad-fragment': q['source'].append('not an occurrence')
    elif mutation == 'unknown-unit': occurrence['unit'] = 'missing'
    elif mutation == 'offset': occurrence['end'] = True
    elif mutation == 'page': occurrence['page'] = 209
    elif mutation == 'box': occurrence['bbox'] = [0, 0, 1, 1]
    elif mutation == 'quote': occurrence['quote'] = '6,801'
    elif mutation == 'digest': occurrence['source_sha256'] = '0' * 64
    elif mutation == 'literal': q['literal'] = '6,801'
    profile['consumer_sha256'] = digest(baseline)
    with pytest.raises(ValueError):
        verify(actual(case), baseline, profile, graph)


def test_every_occurrence_is_checked_before_joined_literal(case):
    graph, baseline, profile, _ = case
    q = baseline['pension_note_review']['tables']['net']['rows'][0]['cells']['2022']
    q['source'].append(deepcopy(q['source'][0]))
    q['source'][1]['source_sha256'] = '0' * 64
    profile['consumer_sha256'] = digest(baseline)
    with pytest.raises(ValueError, match='source identity'):
        verify(actual(case), baseline, profile, graph)
    q['source'][1] = deepcopy(q['source'][0])
    profile['consumer_sha256'] = digest(baseline)
    with pytest.raises(ValueError, match='Complete cell literal'):
        verify(actual(case), baseline, profile, graph)


def test_fixture_source_shapes_match_retained_public_consumer(case):
    baseline = load(Path(__file__).resolve().parents[2] / PRIOR / 'pension-consumer.json.gz')
    for example in (baseline, case[1]):
        for row in r.relations(example):
            for position, q in enumerate(row['quantities']):
                table = row['id'].startswith('candidate-') and position > 0
                assert isinstance(q['source'], list if table else dict)
                if table:
                    assert q['source'] and all(isinstance(s, dict) for s in q['source'])
                    assert q['status'] == ('PRINTED_DASH_UNKNOWN' if q['value'] is None else 'PRINTED_INTEGER')
                    assert q['unit_basis'] == 'PRINTED_TABLE_UNIT'


@pytest.mark.parametrize('mutation', ['unpin', 'missing-quote', 'policy-page', 'path', 'unit', 'boolean', 'different-amount'])
def test_context_changes_refuse_even_when_profile_is_repinned(case, mutation):
    graph, baseline, profile, root = deepcopy(case)
    expected = None
    if mutation == 'unpin': expected = '0' * 64
    elif mutation == 'missing-quote': profile['policy'][0]['quote'] = 'Due to rounding'
    elif mutation == 'policy-page': profile['source']['page'] = 204
    elif mutation == 'path': profile['source']['path'] = '../outside.pdf'
    elif mutation == 'unit': baseline['pension_note_review']['tables']['net']['rows'][0]['cells']['2022']['unit'] = 'thousand EUR'
    elif mutation == 'boolean': baseline['statement_review']['rows'][0]['cells']['2022']['integer_millions'] = True
    elif mutation == 'different-amount': baseline['statement_review']['rows'][0]['cells']['2022']['integer_millions'] = 3759
    profile['consumer_sha256'] = digest(baseline)
    with pytest.raises(ValueError):
        r.evaluate(graph, baseline, profile, root, expected_profile_sha256=expected or digest(profile))


def test_public_consumer_preserves_off_output_and_reaches_optional_analysis(case, monkeypatch):
    graph, baseline, profile, root = case
    preceding = {k: v for k, v in baseline.items() if k not in ('pension_note_review', 'pension_explanation')}
    monkeypatch.setattr(note.basf_hedge_note, 'consume', lambda *_a, **_kw: deepcopy(preceding))
    monkeypatch.setattr(note, 'evaluate', lambda *_a, **_kw: deepcopy(baseline['pension_note_review']))
    args = ({'P1': {'payload': {'graph': graph}}}, {}, {}, {}, root)
    kw = {'expected_prior_profiles_sha256': 'unused', 'expected_hedge_profile_sha256': 'unused',
          'expected_profile_sha256': 'unused'}
    assert note.consume(*args, **kw) == baseline
    on = note.consume(*args, **kw, reconciliation_profile=profile,
                      expected_reconciliation_profile_sha256=digest(profile))
    assert verify(on, baseline, profile, graph)['complete_baseline_preserved'] is True
    with pytest.raises(ValueError, match='profile required'):
        note.consume(*args, **kw, expected_reconciliation_profile_sha256=digest(profile))
