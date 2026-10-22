"""Independent source expectations, arbitrary grammar and adverse provenance."""
from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import reference_mentions as module, service
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/reference-mentions-355'
CASES = json.loads((PREP / 'independent-cases.json').read_text())['cases']


def request(text):
    raw = {'unit': 'unit', 'document': 'document', 'source_sha256': 'a' * 64,
           'start': 0, 'end': len(text), 'quote': text}
    return {'version': 'reference-mention-request.v1', 'text': text, 'text_sha256': digest(text.encode()),
        'source_pieces': [{'start': 0, 'end': len(text), 'text': text, 'kind': 'EXACT_SOURCE_COPY', 'raw_binding': raw}],
        'raw_units': [{'id': 'unit', 'document': 'document', 'source_sha256': 'a' * 64,
                       'raw': text, 'text_sha256': digest(text.encode())}], 'section_headers': []}


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_independent_literal_grammar(case):
    result = module.discover(request(case['text']))
    assert [{k: row[k] for k in ('start', 'end', 'raw', 'kind')} for row in result['mentions']] == case['expected']
    assert bool(result['issues']) == case['issue_required']
    assert all(r['target'] is None and r['review_required'] for r in result['mentions'])
    assert result['general_recall_established'] is result['target_resolution_established'] is False


def test_complete_original_record_spans_and_raw_projection():
    req = json.loads((PREP / 'request.json').read_text())
    expected = json.loads((PREP / 'expected.json').read_text())
    actual = module.discover(req)
    index = {(r['start'], r['end'], r['kind']): r for r in actual['mentions']}
    assert len({r['record'] for r in expected['records']}) == 60
    for row in expected['records']:
        found = index[(row['start'], row['end'], row['kind'])]
        assert found['raw'] == row['raw'] and found['source_projection'] == row['source_projection']


@pytest.mark.parametrize('kind', ['selected-hash', 'piece-gap', 'piece-end', 'raw-hash', 'raw-offset',
    'raw-quote', 'raw-identity', 'unknown-unit', 'duplicate-unit', 'transformed-copy', 'false-raw-copy',
    'extra-target', 'extra-expected', 'bool-offset', 'header-prose', 'header-unknown', 'wrong-version'])
def test_tampering_refused(kind):
    req = request('Siehe § 27.')
    piece, unit = req['source_pieces'][0], req['raw_units'][0]
    if kind == 'selected-hash': req['text_sha256'] = '0' * 64
    elif kind == 'piece-gap': piece['start'] = 1
    elif kind == 'piece-end': piece['end'] += 1
    elif kind == 'raw-hash': unit['text_sha256'] = '0' * 64
    elif kind == 'raw-offset': piece['raw_binding']['end'] -= 1
    elif kind == 'raw-quote': piece['raw_binding']['quote'] += '!'
    elif kind == 'raw-identity': piece['raw_binding']['source_sha256'] = 'b' * 64
    elif kind == 'unknown-unit': piece['raw_binding']['unit'] = 'absent'
    elif kind == 'duplicate-unit': req['raw_units'].append(deepcopy(unit))
    elif kind == 'transformed-copy': piece['kind'] = 'SUPPLIED_OR_TRANSFORMED'
    elif kind == 'false-raw-copy': piece['raw_binding'] = None
    elif kind == 'extra-target': req['targets'] = ['§ 28']
    elif kind == 'extra-expected': req['expected'] = []
    elif kind == 'bool-offset': piece['start'] = False
    elif kind == 'header-prose': req['section_headers'] = [{'start': 0, 'end': len(req['text']), 'unit': 'unit'}]
    elif kind == 'header-unknown': req['section_headers'] = [{'start': 6, 'end': 10, 'unit': 'absent'}]
    elif kind == 'wrong-version': req['version'] = 'wrong'
    with pytest.raises(ValueError):
        module.discover(req)


def test_transform_is_discovered_without_raw_copy_claim():
    req = request('Siehe § 27.')
    req['source_pieces'][0].update(kind='SUPPLIED_OR_TRANSFORMED', raw_binding=None)
    report = module.discover(req)
    assert report['mentions'][0]['source_projection'][0]['source'] is None
    assert report['mentions'][0]['raw_copy_complete'] is False


def test_explicit_exact_header_only():
    req = request('§ 71')
    assert len(module.discover(req)['mentions']) == 1
    req['section_headers'] = [{'start': 0, 'end': 4, 'unit': 'unit'}]
    assert module.discover(req)['mentions'] == []
    assert module.discover(req)['issues'] == []


def test_cli_routing_uses_public_discovery(tmp_path):
    source, output = tmp_path / 'request.json', tmp_path / 'result.json'
    req = request('Siehe § 27.')
    source.write_text(json.dumps(req))
    parser = ArgumentParser()
    service.configure(parser)
    args = parser.parse_args(['discover-references', '--request', str(source), '--output', str(output)])
    receipt = service.dispatch(args)
    assert json.loads(output.read_text()) == module.discover(req)
    assert receipt['mentions'] == 1
