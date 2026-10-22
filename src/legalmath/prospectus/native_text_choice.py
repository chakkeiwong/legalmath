"""Explicit retained native-page selection; no inferred language correctness."""
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path

from .successor.anchors import fields
from .successor.contracts import TextUnit, bound_path, digest, validate_request
from .successor.service import seal, verify
from .successor.source_graph import REFERENCE

VERSION = 'retained-native-page-choice.v1'
METHOD = 'retained-pymupdf-native-lines.v1'
MAX_OBSERVATION_BYTES = 16 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _box(value):
    return (isinstance(value, (list, tuple)) and len(value) == 4
            and all(type(x) in (int, float) and math.isfinite(x) for x in value)
            and value[0] < value[2] and value[1] < value[3])


def _file(root, name, expected):
    require(isinstance(name, str) and name and not Path(name).is_absolute(),
            'Relative retained file required')
    path = bound_path(root, name)
    require(path.is_file() and digest(path.read_bytes()) == expected,
            'Retained source, render or observation changed')
    return path


def page_units(observation, document, *, evidence_sha256, image_sha256):
    """Preserve every observed line character and account for every word.

    The supported observation profile numbers word blocks by text-block ordinal.
    Dictionary numbers include images; both numbers remain explicit provenance.
    Exact text/ordinal/geometry checks refuse incompatible observations.
    """
    page = observation.get('page')
    require(type(page) is int and 1 <= page <= document['page_count'], 'Invalid original page')
    require(observation.get('source_sha256') == document['sha256'], 'Foreign native source edition')
    rect = observation.get('display_rect')
    require(_box(rect) and rect[:2] == [0, 0] and observation.get('rotation') == 0,
            'This profile requires an unrotated displayed page')
    data = observation.get('native_dict')
    require(isinstance(data, dict) and isinstance(data.get('blocks'), list), 'Native dictionary required')
    require(isinstance(observation.get('text'), str) and isinstance(observation.get('words'), list),
            'Complete native page text and words required')
    groups = {}
    for word in observation['words']:
        require(isinstance(word, list) and len(word) == 8 and _box(word[:4])
                and 0 <= word[0] < word[2] <= rect[2] and 0 <= word[1] < word[3] <= rect[3]
                and isinstance(word[4], str) and bool(word[4])
                and all(type(v) is int and v >= 0 for v in word[5:]), 'Invalid native word')
        groups.setdefault((word[5], word[6]), []).append(word)
    blocks = data['blocks']
    require(all(isinstance(b, dict) and b.get('type') in (0, 1)
                and type(b.get('number')) is int for b in blocks), 'Unsupported native block')
    require(len({b['number'] for b in blocks}) == len(blocks), 'Duplicate native block number')
    units, raw_lines = [], []
    for text_block, block in enumerate(b for b in blocks if b['type'] == 0):
        require(isinstance(block.get('lines'), list) and block['lines'], 'Missing native block lines')
        for line_number, line in enumerate(block['lines']):
            require(_box(line.get('bbox')) and line.get('wmode') == 0
                    and isinstance(line.get('spans'), list) and line['spans'], 'Unsupported native line')
            require(all(isinstance(s, dict) and isinstance(s.get('text'), str) for s in line['spans']),
                    'Native span text required')
            raw = ''.join(s['text'] for s in line['spans'])
            raw_lines.append(raw)
            key = (text_block, line_number)
            words, cursor = [], 0
            for ordinal, word in enumerate(groups.pop(key, [])):
                require(word[7] == ordinal, 'Missing, duplicate or reordered native word ordinal')
                start = raw.find(word[4], cursor)
                require(start >= cursor and not raw[cursor:start].strip(),
                        'Unmapped native line characters or changed word')
                end = start + len(word[4])
                words.append({'text': word[4], 'start': start, 'end': end, 'bbox': word[:4],
                              'native_ordinal': word[5:]})
                cursor = end
            require(not raw[cursor:].strip(), 'Native line has unaccounted text')
            index = len(units)
            unit = TextUnit(f"{document['id']}:p{page}:native:l{index}", document['id'],
                document['sha256'], page, index, raw, line['bbox'],
                f"{document['id']}:p{page}:native:b{text_block}", document['language'], METHOD).json()
            unit.update(words=words, visible=document['visible'], image_sha256=image_sha256,
                native_observation={'sha256': evidence_sha256, 'dictionary_block': block['number'],
                    'word_block': text_block, 'line': line_number, 'direction': line.get('dir'),
                    'writing_mode': line['wmode'], 'order': 'RETAINED_EXTRACTION_ORDER; NOT_INDEPENDENT_READING'})
            units.append(unit)
    require(not groups, 'Orphan native word group')
    require(units and '\n'.join(raw_lines) + '\n' == observation['text'],
            'Native line reconstruction differs from full retained page text')
    require(sum(len(u['words']) for u in units) == len(observation['words']), 'Native word denominator changed')
    return units


def _references(units):
    refs, headings = [], {}
    for unit in units:
        for match in REFERENCE.finditer(unit['raw']):
            refs.append({'id': unit['id'] + f':ref:{match.start()}', 'document': unit['document'],
                'source_sha256': unit['source_sha256'], 'unit': unit['id'], 'text': match.group(),
                'target': match.group(1) or match.group(2), 'start': match.start(),
                'end': match.end(), 'status': 'UNRESOLVED'})
        heading = REFERENCE.match(unit['raw'].lstrip())
        if heading:
            headings.setdefault((unit['document'], heading.group(1) or heading.group(2)), []).append(unit['id'])
    for ref in refs:
        ref['candidates'] = [u for u in headings.get((ref['document'], ref['target']), []) if u != ref['unit']]
    return refs


def select_pages(source, selection, root, *, expected_selection_sha256):
    """Return a separately sealed P1; keep the original product unchanged."""
    keys = {'version', 'source_product_sha256', 'document', 'inspection_path',
            'inspection_sha256', 'pages', 'reason', 'independent_legal_acceptance'}
    fields(selection, keys, keys)
    require(digest(selection) == expected_selection_sha256 and selection['version'] == VERSION,
            'Pinned native selection changed')
    require(selection['independent_legal_acceptance'] is False
            and isinstance(selection['reason'], str) and selection['reason'].strip(),
            'Explicit reason and unreviewed status required')
    payload = verify(source, 'P1')
    request, original = payload['request'], payload['graph']
    bundle = validate_request(request)
    verify(source, 'P1', bundle, {'request': digest(request)})
    require(set(request) == {'version', 'bundle'} and not bundle.get('dependencies'),
            'Select native pages before any occurrence-bound interpretation or dependency admission')
    require(source['sha256'] == selection['source_product_sha256']
            and original['bundle_sha256'] == digest(bundle), 'Baseline native product differs')
    require(not any(k in original for k in ('layout', 'corrections', 'native_text_choice')),
            'Select from an original unmodified source product')
    units = original['units']
    require(len(units) == len({u['id'] for u in units})
            and all(u['text_sha256'] == digest(u['raw'].encode()) for u in units),
            'Duplicate or changed baseline source occurrence')
    docs = [d for d in original['documents'] if d['id'] == selection['document']]
    require(len(docs) == 1 and docs[0]['visible'], 'One visible source document required')
    doc = docs[0]
    for document in bundle['documents']:
        _file(root, document['path'], document['sha256'])
    inspection = json.loads(_file(root, selection['inspection_path'], selection['inspection_sha256']).read_text())
    require(inspection['source_sha256'] == doc['sha256'] and inspection['pages'] == doc['page_count']
            and isinstance(inspection.get('pymupdf_version'), str)
            and inspection['native_ocr_quality_evaluated'] is False, 'Native inspection source/profile differs')
    pages = selection['pages']
    require(isinstance(pages, list) and pages, 'Selected native pages required')
    numbers = [p.get('page') for p in pages]
    require(all(type(n) is int and 1 <= n <= doc['page_count'] for n in numbers)
            and numbers == sorted(set(numbers)), 'Distinct ordered original pages required')
    require(set(numbers) <= set(inspection['selected_pages']), 'Page absent from inspected native selection')
    renders = {r['page']: r for r in inspection['renders']}
    replacements, observations = {}, []
    for page in pages:
        fields(page, {'page', 'path', 'sha256', 'render_path', 'render_sha256'},
               {'page', 'path', 'sha256', 'render_path', 'render_sha256'})
        number = page['page']
        require(any(u['document'] == doc['id'] and u['page'] == number for u in units),
                'Selected page absent from baseline')
        path = _file(root, page['path'], page['sha256'])
        require(path.stat().st_size <= MAX_OBSERVATION_BYTES, 'Native observation exceeds bound')
        with gzip.open(path, 'rb') as stream:
            data = stream.read(MAX_OBSERVATION_BYTES + 1)
        require(len(data) <= MAX_OBSERVATION_BYTES, 'Expanded native observation exceeds bound')
        observation = json.loads(data)
        require(observation['page'] == number, 'Native page identity differs')
        _file(root, page['render_path'], page['render_sha256'])
        require(number in renders and renders[number]['sha256'] == page['render_sha256'],
                'Render identity differs from retained inspection')
        replacements[number] = page_units(observation, doc, evidence_sha256=page['sha256'],
                                          image_sha256=page['render_sha256'])
        observations.append({**page, 'units': len(replacements[number]),
                             'words': len(observation['words']), 'text_sha256': digest(observation['text'].encode())})
    graph = deepcopy(original)
    selected_units, emitted = [], set()
    for unit in graph['units']:
        if unit['document'] == doc['id'] and unit['page'] in replacements:
            if unit['page'] not in emitted:
                selected_units.extend(replacements[unit['page']])
                emitted.add(unit['page'])
        else:
            selected_units.append(unit)
    require(len(selected_units) == len({u['id'] for u in selected_units}), 'Selected occurrence identity collision')
    graph['units'] = selected_units
    graph['unit_count'] = len(selected_units)
    graph['references'] = _references(selected_units)
    choice = {'version': VERSION, 'baseline_source_product_sha256': source['sha256'],
        'baseline_source_graph_sha256': digest(original), 'selection_sha256': expected_selection_sha256,
        'document': doc['id'], 'pages': observations, 'reason': selection['reason'],
        'pymupdf_version': inspection['pymupdf_version'], 'native_execution': 'RETAINED_OBSERVATIONS_ONLY',
        'baseline_retained_separately': True, 'default_changed': False, 'page_complete': False,
        'document_complete': False, 'independent_legal_acceptance': False,
        'language_and_reading_order': 'NOT_INDEPENDENTLY_EVALUATED'}
    graph['native_text_choice'] = choice
    for document in graph['documents']:
        if document['id'] == doc['id']:
            document['native_text_choice'] = choice
    return seal('P1', bundle, {'request': digest(request)}, {'request': deepcopy(request), 'graph': graph})


def consume_selected(products, baseline, selection, root, *, expected_selection_sha256):
    """Verify the exact selected source again before the ordinary consumer."""
    from .successor.service import consume
    expected = select_pages(baseline, selection, root, expected_selection_sha256=expected_selection_sha256)
    require(expected == products['P1'], 'Selected source product differs from pinned native observations')
    answer = consume(products, root, include_artifacts=True)
    return {'answer': answer, 'native_text_choice': deepcopy(expected['payload']['graph']['native_text_choice'])}
