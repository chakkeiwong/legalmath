from copy import deepcopy
import gzip
import json

import pytest

from legalmath.prospectus import native_text_choice as choice
from legalmath.prospectus.successor.contracts import TextUnit, VERSION, digest
from legalmath.prospectus.successor.service import seal


def compressed(path, value):
    path.write_bytes(gzip.compress(json.dumps(value, ensure_ascii=False).encode(), mtime=0))


@pytest.fixture
def example(tmp_path):
    source = tmp_path / 'source.pdf'
    source.write_bytes(b'synthetic source bytes for source identity tests')
    (tmp_path / 'page.png').write_bytes(b'synthetic render identity')
    hashed = digest(source.read_bytes())
    render = digest((tmp_path / 'page.png').read_bytes())
    doc = {'id': 'd', 'path': 'source.pdf', 'sha256': hashed, 'page_count': 2,
           'language': 'ar', 'authority': 'synthetic test evidence'}
    bundle = {'instrument_id': 'test', 'purpose': 'review',
              **{k: '2026-10-15T00:00:00+08:00' for k in ('issue_date', 'effective_at', 'known_at')},
              'documents': [doc]}
    request = {'version': VERSION, 'bundle': bundle}
    units = []
    for p, raw in ((1, 'Article 9 old'), (2, 'Section 4')):
        u = TextUnit(f'd:p{p}:l0', 'd', hashed, p, 0, raw, [0, 0, 99, 10],
                     f'd:p{p}:b0', 'ar', 'pdftotext-bbox-layout').json()
        u.update(visible=True, words=[])
        units.append(u)
    graph = {'version': 'source-graph.v2', 'bundle_sha256': digest(bundle),
             'documents': [{**doc, 'visible': True}], 'units': units, 'unit_count': 2,
             'references': choice._references(units), 'unresolved': []}
    p1 = seal('P1', bundle, {'request': digest(request)}, {'request': request, 'graph': graph})
    texts = ['  Article 4 https://www.example.test/  ', 'نشرة إصدار']
    words = []
    blocks = []
    for bi, raw in enumerate(texts):
        if bi:
            blocks.append({'type': 1, 'number': 1, 'bbox': [0, 20, 10, 30]})
        blocks.append({'type': 0, 'number': bi * 2, 'lines': [
            {'bbox': [0, bi * 40, 99, bi * 40 + 15], 'wmode': 0, 'dir': [1, 0],
             'spans': [{'text': raw}]}]})
        for wi, word in enumerate(raw.split()):
            words.append([wi * 20, bi * 40, wi * 20 + 19, bi * 40 + 15, word, bi, 0, wi])
    observation = {'page': 1, 'source_sha256': hashed, 'text': '\n'.join(texts) + '\n',
                   'rotation': 0, 'display_rect': [0, 0, 100, 100],
                   'native_dict': {'blocks': blocks}, 'words': words}
    compressed(tmp_path / 'native.json.gz', observation)
    inspection = {'source_sha256': hashed, 'pages': 2, 'pymupdf_version': 'test-profile',
                  'native_ocr_quality_evaluated': False, 'selected_pages': [1],
                  'renders': [{'page': 1, 'sha256': render}]}
    (tmp_path / 'inspection.json').write_text(json.dumps(inspection))
    selection = {'version': choice.VERSION, 'source_product_sha256': p1['sha256'], 'document': 'd',
        'inspection_path': 'inspection.json', 'inspection_sha256': digest((tmp_path / 'inspection.json').read_bytes()),
        'pages': [{'page': 1, 'path': 'native.json.gz', 'sha256': digest((tmp_path / 'native.json.gz').read_bytes()),
                   'render_path': 'page.png', 'render_sha256': render}],
        'reason': 'Explicit test selection', 'independent_legal_acceptance': False}
    return p1, selection, observation, tmp_path


def execute(example, pin=None):
    p1, selection, _, root = example
    return choice.select_pages(p1, selection, root, expected_selection_sha256=pin or digest(selection))


def test_full_line_spacing_url_and_image_block_ordinals_preserved(example):
    p1, selection, observation, _ = example
    before = deepcopy(p1)
    result = execute(example)
    graph = result['payload']['graph']
    selected = [u for u in graph['units'] if u['page'] == 1]
    assert '\n'.join(u['raw'] for u in selected) + '\n' == observation['text']
    assert 'https://www.example.test/' in selected[0]['raw']
    assert selected[1]['native_observation']['dictionary_block'] == 2
    assert selected[1]['native_observation']['word_block'] == 1
    assert all(u['raw'][w['start']:w['end']] == w['text'] for u in selected for w in u['words'])
    assert p1 == before
    assert graph['units'][-1] == p1['payload']['graph']['units'][-1]
    assert graph['native_text_choice']['baseline_source_product_sha256'] == p1['sha256']
    assert not graph['native_text_choice']['independent_legal_acceptance']
    assert not graph['native_text_choice']['page_complete']


def test_references_rebuild_against_selected_occurrences(example):
    graph = execute(example)['payload']['graph']
    assert {r['target'] for r in graph['references']} == {'4'}
    assert all(r['unit'] != 'd:p1:l0' for r in graph['references'])
    assert next(r for r in graph['references'] if r['unit'] == 'd:p2:l0')['candidates'] == ['d:p1:native:l0']


@pytest.mark.parametrize('case', ['missing_word', 'duplicate_word', 'reordered_word', 'changed_word',
    'orphan_word', 'dictionary_instead_of_text_ordinal', 'missing_line', 'changed_page_text',
    'uncovered_character', 'duplicate_block', 'nan_box', 'outside_box', 'rotation', 'vertical',
    'foreign_source', 'page_boolean', 'word_boolean', 'changed_line', 'missing_span'])
def test_invalid_native_observation_refuses_even_with_updated_file_pin(example, case):
    _, selection, observation, root = example
    if case == 'missing_word': observation['words'].pop()
    elif case == 'duplicate_word': observation['words'].append(deepcopy(observation['words'][-1]))
    elif case == 'reordered_word': observation['words'][:2] = reversed(observation['words'][:2])
    elif case == 'changed_word': observation['words'][0][4] = 'wrong'
    elif case == 'orphan_word': observation['words'][0][5] = 99
    elif case == 'dictionary_instead_of_text_ordinal': observation['words'][-1][5] = 2
    elif case == 'missing_line': observation['native_dict']['blocks'][-1]['lines'] = []
    elif case == 'changed_page_text': observation['text'] += 'unrecorded'
    elif case == 'uncovered_character':
        observation['native_dict']['blocks'][0]['lines'][0]['spans'][0]['text'] += '!'
    elif case == 'duplicate_block': observation['native_dict']['blocks'][1]['number'] = 0
    elif case == 'nan_box': observation['words'][0][0] = float('nan')
    elif case == 'outside_box': observation['words'][0][2] = 101
    elif case == 'rotation': observation['rotation'] = 90
    elif case == 'vertical': observation['native_dict']['blocks'][0]['lines'][0]['wmode'] = 1
    elif case == 'foreign_source': observation['source_sha256'] = '0' * 64
    elif case == 'page_boolean': observation['page'] = True
    elif case == 'word_boolean': observation['words'][0][7] = False
    elif case == 'changed_line': observation['words'][0][6] = 99
    else: observation['native_dict']['blocks'][0]['lines'][0]['spans'] = []
    compressed(root / 'native.json.gz', observation)
    selection['pages'][0]['sha256'] = digest((root / 'native.json.gz').read_bytes())
    with pytest.raises(ValueError): execute(example)


@pytest.mark.parametrize('case', ['source_changed', 'render_changed', 'observation_changed',
    'inspection_changed', 'selection_pin', 'wrong_baseline', 'duplicate_page', 'wrong_document',
    'absolute_path', 'path_escape', 'false_independence', 'stale_interpretation', 'duplicate_unit',
    'modified_baseline', 'empty_pages', 'wrong_page', 'bad_reason', 'already_selected'])
def test_identity_and_selection_controls(example, case):
    p1, selection, _, root = example
    pin = None
    if case.endswith('_changed'):
        path = {'source_changed': 'source.pdf', 'render_changed': 'page.png',
                'observation_changed': 'native.json.gz', 'inspection_changed': 'inspection.json'}[case]
        (root / path).write_bytes(b'changed')
    elif case == 'selection_pin': pin = '0' * 64
    elif case == 'wrong_baseline': selection['source_product_sha256'] = '0' * 64
    elif case == 'duplicate_page': selection['pages'].append(deepcopy(selection['pages'][0]))
    elif case == 'wrong_document': selection['document'] = 'foreign'
    elif case == 'absolute_path': selection['pages'][0]['path'] = str(root / 'native.json.gz')
    elif case == 'path_escape': selection['pages'][0]['path'] = '../native.json.gz'
    elif case == 'false_independence': selection['independent_legal_acceptance'] = True
    elif case == 'stale_interpretation': p1['payload']['request']['clauses'] = []
    elif case == 'duplicate_unit': p1['payload']['graph']['units'].append(deepcopy(p1['payload']['graph']['units'][0]))
    elif case == 'modified_baseline': p1['payload']['graph']['units'][0]['raw'] += '!'
    elif case == 'empty_pages': selection['pages'] = []
    elif case == 'wrong_page': selection['pages'][0]['page'] = 2
    elif case == 'bad_reason': selection['reason'] = ''
    elif case == 'already_selected': p1['payload']['graph']['native_text_choice'] = {}
    with pytest.raises(ValueError): execute(example, pin)
