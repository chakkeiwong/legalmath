"""Finite source expectations and hostile inputs for declaration evidence."""
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.definition_declarations import discover, reconcile

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/definition-declarations-357'
HERE = AUTH / 'attempts/basf-references/attempt-096'
CASES = json.loads((PREP / 'independent-cases.json').read_text())['cases']
CORRECTIONS = json.loads((HERE / 'development/expectation-corrections.json').read_text())


def read(name):
    return json.loads((PREP / name).read_text())


def case(ident='alias'):
    return deepcopy(next(c['request'] for c in CASES if c['id'] == ident))


@pytest.mark.parametrize('fixture', CASES, ids=[c['id'] for c in CASES])
def test_independent_pre_candidate_grammar(fixture):
    expected = deepcopy(fixture['expected'])
    for correction in CORRECTIONS['arbitrary_fixture_corrections']:
        if correction['case'] == fixture['id']:
            row = next(r for r in expected if (r['start'], r['end']) ==
                       (correction['old_start'], correction['old_end']))
            assert row['raw'] == correction['raw']
            row.update(start=correction['start'], end=correction['end'])
    report = discover(fixture['request'])
    assert [{k: n[k] for k in ('start', 'end', 'raw', 'syntax')} for n in report['names']] == expected
    if fixture['issue_required']:
        assert report['issues']
    assert not report['meaning_admitted'] and not report['scope_admitted']
    assert not report['general_recall_established'] and not report['whole_task_complete']
    for row in report['names']:
        assert row['review_required'] and not row['legal_declaration_established']
        assert row['governing_scope'] is None


def split(request, cuts):
    """Split one raw-copy fixture, retaining independently checked raw slices."""
    source = request['source']
    original = source['source_pieces'][0]
    points = sorted({0, len(source['text']), *cuts})
    source['source_pieces'] = []
    for a, b in zip(points, points[1:]):
        row = deepcopy(original)
        row.update(start=a, end=b, text=source['text'][a:b])
        row['raw_binding'].update(start=a, end=b, quote=source['text'][a:b])
        source['source_pieces'].append(row)


@pytest.mark.parametrize('part', ['token', 'opening-quote', 'closing-quote', 'cue', 'supplied-space'])
def test_transformed_declaration_is_never_raw_evidence(part):
    request = case()
    text = request['source']['text']
    a = text.index('Gesellschaft')
    spans = {'token': (a, a + 12), 'opening-quote': (a - 1, a),
             'closing-quote': (a + 12, a + 13),
             'cue': (text.index('(die') + 1, text.index('(die') + 4),
             'supplied-space': (a - 2, a - 1)}
    left, right = spans[part]
    split(request, (left, right))
    changed = next(p for p in request['source']['source_pieces'] if p['start'] == left)
    changed.update(kind='SUPPLIED_OR_TRANSFORMED', raw_binding=None)
    row = discover(request)['names'][0]
    assert row['status'] == 'UNRESOLVED_SOURCE' and row['syntax'] is None
    assert row['observed_syntax'] == 'PARENTHETICAL_NAMING'
    assert row['syntax_evidence']['source_bound'] is False


def test_generated_whitespace_is_literal_join_not_supplied_cue():
    request = case()
    a = request['source']['text'].index('Gesellschaft') - 2
    split(request, (a, a + 1))
    next(p for p in request['source']['source_pieces'] if p['start'] == a).update(
        kind='GENERATED_SEPARATOR', raw_binding=None)
    row = discover(request)['names'][0]
    assert row['status'] == 'DECLARATION_SYNTAX'
    assert any(p['kind'] == 'GENERATED_SEPARATOR' for p in row['syntax_evidence']['source_projection'])


@pytest.mark.parametrize('role', ['EXCLUDED', 'UNKNOWN', 'HEADER'])
def test_nonoperative_source_cannot_qualify_syntax(role):
    request = case()
    request['layout'][0]['role'] = role
    row = discover(request)['names'][0]
    assert row['status'] == 'NON_OPERATIVE' and row['syntax'] is None
    assert row['observed_syntax'] == 'PARENTHETICAL_NAMING'


@pytest.mark.parametrize('dimension', ['context', 'document'])
def test_syntax_cannot_bridge_independent_source_contexts(dimension):
    request = case()
    a = request['source']['text'].index('Gesellschaft')
    split(request, (a,))
    other = deepcopy(request['source']['raw_units'][0])
    other['id'] = 'independent'
    if dimension == 'document':
        other['document'] = 'independent'
    request['source']['raw_units'].append(other)
    row = request['source']['source_pieces'][-1]['raw_binding']
    row.update(unit=other['id'], document=other['document'])
    request['layout'].append({'unit': other['id'], 'role': 'OPERATIVE',
                              'context': 'independent' if dimension == 'context' else request['layout'][0]['context']})
    actual = discover(request)['names'][0]
    assert actual['source_bound']
    assert actual['status'] == 'UNRESOLVED_SOURCE' and actual['syntax'] is None


@pytest.mark.parametrize('mutation', ['text-hash', 'raw-hash', 'document-hash', 'offset',
                                    'boolean-offset', 'quote', 'gap', 'layout', 'language'])
def test_malformed_source_is_refused(mutation):
    request = case()
    source = request['source']
    if mutation == 'text-hash':
        source['text_sha256'] = '0' * 64
    elif mutation == 'raw-hash':
        source['raw_units'][0]['text_sha256'] = '0' * 64
    elif mutation == 'document-hash':
        source['raw_units'][0]['source_sha256'] = 'invalid'
    elif mutation == 'offset':
        source['source_pieces'][0]['raw_binding']['end'] -= 1
    elif mutation == 'boolean-offset':
        source['source_pieces'][0]['raw_binding']['start'] = False
    elif mutation == 'quote':
        source['source_pieces'][0]['raw_binding']['quote'] += '!'
    elif mutation == 'gap':
        source['source_pieces'][0]['start'] = 1
    elif mutation == 'layout':
        request['layout'] = []
    else:
        request['language'] = 'en'
    with pytest.raises(ValueError):
        discover(request)


def small_lineage(request):
    text = request['source']['text']
    a = text.index('Gesellschaft')
    return {'version': 'reviewed-definition-lineage.v1',
            'text_sha256': request['source']['text_sha256'], 'source_answer_sha256': 'a' * 64,
            'records': [{'id': 'reviewed', 'original_record_sha256': 'b' * 64,
                         'forms': ['Gesellschaft'], 'declarations': [{'start': 0, 'end': len(text), 'quote': text}],
                         'reading': 'A supplied conditional reading, not detector input.'}],
            'naming_tokens': [{'record': 'reviewed', 'start': a, 'end': a + 12, 'raw': 'Gesellschaft'}],
            'uses': [{'record': 'reviewed', 'start': a, 'end': a + 12, 'quote': 'Gesellschaft',
                      'origin': 'ORIGINAL', 'disposition': 'RETAINED_REVIEW'}],
            'dependencies': [{'record': 'reviewed', 'use_indices': [0],
                              'remaining_premises': ['Governing scope and actual facts remain open.']}]}


def test_reconciliation_does_not_change_discovery_or_reading():
    request = case()
    report = discover(request)
    lineage = small_lineage(request)
    original = deepcopy(lineage)
    answer = reconcile(request, report, lineage)
    assert answer['retained_lineage'] == original == lineage
    lineage['records'][0]['reading'] = 'A competing supplied reading.'
    alternate = reconcile(request, report, lineage)
    assert alternate['discovery_sha256'] == answer['discovery_sha256']
    assert alternate['reviewed_lineage_sha256'] != answer['reviewed_lineage_sha256']
    assert discover(request) == report
    assert answer['records'][0]['remaining_premises'] == original['dependencies'][0]['remaining_premises']


@pytest.mark.parametrize('mutation', ['syntax', 'source', 'restriction', 'claim'])
def test_forged_report_refused_even_with_new_hash(mutation):
    request = case()
    report = discover(request)
    if mutation == 'syntax':
        report['names'][0]['syntax'] = 'DEFINING_VERB'
    elif mutation == 'source':
        report['names'][0]['source_projection'][0]['source']['quote'] += '!'
    elif mutation == 'restriction':
        report['restrictions'] = [{'governing_scope_established': True}]
    else:
        report['legal_truth_established'] = True
    report['report_sha256'] = digest({k: v for k, v in report.items() if k != 'report_sha256'})
    with pytest.raises(ValueError, match='source-only'):
        reconcile(request, report, small_lineage(request))


@pytest.mark.parametrize('mutation', ['source', 'answer-hash', 'record-hash', 'duplicate-record',
                                    'excerpt', 'token-quote', 'token-offset', 'token-form',
                                    'duplicate-token', 'use-quote', 'use-record', 'dependency-record',
                                    'dependency-index'])
def test_invalid_reviewed_lineage_refused(mutation):
    request = case()
    lineage = small_lineage(request)
    if mutation == 'source':
        lineage['text_sha256'] = '0' * 64
    elif mutation == 'answer-hash':
        lineage['source_answer_sha256'] = 'unknown'
    elif mutation == 'record-hash':
        lineage['records'][0]['original_record_sha256'] = 'unknown'
    elif mutation == 'duplicate-record':
        lineage['records'].append(deepcopy(lineage['records'][0]))
    elif mutation == 'excerpt':
        lineage['records'][0]['declarations'][0]['quote'] += '!'
    elif mutation == 'token-quote':
        lineage['naming_tokens'][0]['raw'] += '!'
    elif mutation == 'token-offset':
        lineage['naming_tokens'][0]['start'] -= 1
    elif mutation == 'token-form':
        lineage['records'][0]['forms'] = ['something else']
    elif mutation == 'duplicate-token':
        lineage['naming_tokens'].append(deepcopy(lineage['naming_tokens'][0]))
    elif mutation == 'use-quote':
        lineage['uses'][0]['quote'] += '!'
    elif mutation == 'use-record':
        lineage['uses'][0]['record'] = 'unknown'
    elif mutation == 'dependency-record':
        lineage['dependencies'][0]['record'] = 'unknown'
    else:
        lineage['dependencies'][0]['use_indices'] = [1]
    with pytest.raises(ValueError):
        reconcile(request, discover(request), lineage)


def test_all_original_naming_tokens_and_complete_current_lineage():
    request, lineage = read('request.json'), read('lineage.json')
    report = discover(request)
    actual = {(n['start'], n['end']): n for n in report['names']}
    expected = read('expected.json')
    assert set(actual) == {(n['start'], n['end']) for n in expected['tokens']}
    corrections = {(c['start'], c['end']): c for c in CORRECTIONS['original_source_status']}
    for row in expected['tokens']:
        found = actual[row['start'], row['end']]
        assert found['raw'] == row['raw']
        assert found['source_projection'] == row['source_projection']
        assert found['observed_syntax'] == row['syntax']
        correction = corrections.get((row['start'], row['end']))
        assert found['syntax'] == (correction['syntax'] if correction else row['syntax'])
        assert found['status'] == (correction['status'] if correction else 'DECLARATION_SYNTAX')
    assert Counter(n['status'] for n in report['names']) == {'DECLARATION_SYNTAX': 45, 'UNRESOLVED_SOURCE': 2}
    assert [{k: r[k] for k in ('start', 'end', 'raw')} for r in report['restrictions']] == expected['restrictions']
    assert all(r['resolved_extent'] is None for r in report['restrictions'])
    reconciled = reconcile(request, report, lineage)
    assert reconciled['retained_lineage'] == lineage
    assert len(reconciled['records']) == 62
    assert Counter(u['origin'] for u in lineage['uses']) == {'ORIGINAL': 610, 'SUPPLEMENTAL': 2}
    for row, original in zip(reconciled['records'], lineage['records']):
        assert row['record'] == original['id'] and row['retained_record_sha256'] == digest(original)
        dependency = next(d for d in lineage['dependencies'] if d['record'] == row['record'])
        assert row['remaining_premises'] == dependency['remaining_premises']
    assert not reconciled['meaning_changed'] and not reconciled['governing_scope_resolved']
    assert not reconciled['premises_removed'] and not reconciled['whole_task_complete']


def test_actual_cli_uses_this_worktree_and_matches_apis(tmp_path):
    request = case()
    lineage = small_lineage(request)
    paths = {n: tmp_path / (n + '.json') for n in ('request', 'lineage', 'discovery', 'reconciliation')}
    paths['request'].write_text(json.dumps(request))
    paths['lineage'].write_text(json.dumps(lineage))
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src')}
    prefix = [sys.executable, '-m', 'legalmath.cli', 'prospectus']
    for command, extra, output in [
        ('discover-definition-declarations', [], 'discovery'),
        ('reconcile-definition-declarations', ['--discovery', str(paths['discovery']), '--lineage', str(paths['lineage'])], 'reconciliation')]:
        result = subprocess.run(prefix + [command, '--request', str(paths['request']), *extra,
                                          '--output', str(paths[output])], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
    report = discover(request)
    assert json.loads(paths['discovery'].read_text()) == report
    assert json.loads(paths['reconciliation'].read_text()) == reconcile(request, report, lineage)
