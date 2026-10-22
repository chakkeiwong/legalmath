"""Compose reviewed layout views with lexical labels and exact raw provenance."""
from copy import deepcopy
import gzip
import io
import json
import math
from pathlib import Path
from .anchors import fields
from .contracts import bound_path, digest
from .definition_discovery import require
from .layout_adapter import project_layout
from .unicode_labels import discover

VERSION = 'layout-label-review.v1'
KEY = 'layout_label_review'


def _box(value):
    require(isinstance(value, (list, tuple)) and len(value) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in value)
            and 0 <= value[0] < value[2] <= 1000000
            and 0 <= value[1] < value[3] <= 1000000, 'Known finite positive geometry required')
    return value


def _segment(unit, a, b):
    return {'unit': unit['id'], 'start': a, 'end': b, 'quote': unit['raw'][a:b]}


def review(request):
    keys = {'raw_units', 'raw_units_sha256', 'source_sha256', 'language', 'quotation_convention', 'layout'}
    fields(request, keys, keys)
    require(isinstance(request['source_sha256'], str) and len(request['source_sha256']) == 64
            and all(c in '0123456789abcdef' for c in request['source_sha256'])
            and isinstance(request['language'], str) and request['language'],
            'Explicit source hash and language required')
    units = request['raw_units']
    require(isinstance(units, list) and 1 <= len(units) <= 4096
            and all(isinstance(u, dict) for u in units), 'Bounded raw source units required')
    require(digest(units) == request['raw_units_sha256'], 'Raw source-unit identity changed')
    by_id = {}
    total_chars = total_words = 0
    for unit in units:
        require(isinstance(unit.get('id'), str) and unit['id'] and unit['id'] not in by_id,
                'Distinct raw source identities required')
        by_id[unit['id']] = unit
        require(unit.get('source_sha256') == request['source_sha256']
                and unit.get('language') == request['language']
                and unit.get('visible') is True, 'Source edition, language or visibility changed')
        require(type(unit.get('page')) is int and unit['page'] > 0
                and isinstance(unit.get('raw'), str), 'Known page and original raw text required')
        _box(unit.get('bbox'))
        words = unit.get('words')
        require(isinstance(words, list) and words and all(isinstance(w, dict) for w in words),
                'Native raw word geometry required')
        last = 0
        for word in words:
            _box(word.get('bbox'))
            a, b = word.get('start'), word.get('end')
            require(type(a) is int and type(b) is int and last <= a < b <= len(unit['raw'])
                    and unit['raw'][a:b] == word.get('text'), 'Raw word text or offsets changed')
            last = b
        total_chars += len(unit['raw']); total_words += len(words)
    require(total_chars <= 100000 and total_words <= 20000, 'Raw page domain limit exceeded')
    layout = request['layout']
    fields(layout, {'texts'}, {'texts'})
    items = layout['texts']
    require(isinstance(items, list) and 1 <= len(items) <= 16, 'Bounded explicit layout regions required')
    for item in items:
        fields(item, {'self_ref', 'label', 'text', 'prov'}, {'self_ref', 'label', 'text', 'prov'})
        require(isinstance(item['self_ref'], str) and item['self_ref']
                and isinstance(item['text'], str) and len(item['text']) <= 100000
                and isinstance(item['label'], str), 'Explicit layout identity/text required')
        prov = item['prov']
        require(isinstance(prov, list) and len(prov) == 1, 'One-page provenance per layout region required')
        fields(prov[0], {'page_no', 'bbox'}, {'page_no', 'bbox'})
        page, box = prov[0]['page_no'], prov[0]['bbox']
        require(type(page) is int and page in {u['page'] for u in units}, 'Region page outside supplied source')
        fields(box, {'l', 't', 'r', 'b', 'coord_origin'}, {'l', 't', 'r', 'b', 'coord_origin'})
        require(box['coord_origin'] == 'TOPLEFT', 'Explicit top-left geometry required')
        left, top, right, bottom = _box([box[k] for k in ('l', 't', 'r', 'b')])
        # Existing projection selects word centers. This interface requires
        # whole-word selection, so a crop cannot quietly bisect a source word.
        for unit in units:
            if unit['page'] != page:
                continue
            for word in unit['words']:
                x0, y0, x1, y1 = word['bbox']
                intersects = max(left, x0) < min(right, x1) and max(top, y0) < min(bottom, y1)
                require(not intersects or left <= x0 < x1 <= right and top <= y0 < y1 <= bottom,
                        'Layout boundary bisects a source word')
    projected = project_layout(units, layout, source_sha256=request['source_sha256'])
    require(not projected['failures'], 'Source projection refused: ' + str(projected['failures']))
    regions = []
    used = {identity: set() for identity in by_id}
    selected, generated = [], []
    for view in projected['mappings']:
        text = view['text']
        charmap = {}
        for char in view['characters']:
            at, identity, offset = char['output'], char['unit'], char['source_offset']
            require(type(at) is int and 0 <= at < len(text) and at not in charmap
                    and identity in by_id and type(offset) is int
                    and 0 <= offset < len(by_id[identity]['raw'])
                    and text[at] == char['character'] == by_id[identity]['raw'][offset],
                    'Projection character differs from original source')
            require(offset not in used[identity], 'Overlapping source-character ownership')
            used[identity].add(offset); charmap[at] = (identity, offset)
        separators = set()
        for previous, current in zip(view['segments'], view['segments'][1:]):
            at = previous['output_end']
            require(current['output_start'] == at + 1 and text[at] == '\n',
                    'Undeclared projection separator')
            separators.add(at)
        require(set(range(len(text))) - set(charmap) == separators, 'Incomplete projection map')
        generated.extend({'item': view['item'], 'start': at, 'end': at + 1, 'text': '\n'}
                         for at in sorted(separators))
        selected.extend({k: s[k] for k in ('unit', 'start', 'end', 'quote')} for s in view['segments'])
        labels = discover({'text': text, 'text_sha256': digest(text.encode()),
            'language': request['language'], 'quotation_convention': request['quotation_convention'],
            'regions': [{'id': view['item'], 'language': request['language'],
                         'selected': True, 'start': 0, 'end': len(text)}]})

        def provenance(row):
            pieces = []; formatting = []
            for at in range(row['start'], row['end']):
                if at in separators:
                    formatting.append({'start': at, 'end': at + 1, 'text': '\n'})
                    continue
                identity, offset = charmap[at]
                if pieces and pieces[-1]['unit'] == identity and pieces[-1]['end'] == offset:
                    pieces[-1]['end'] += 1
                    pieces[-1]['quote'] += by_id[identity]['raw'][offset]
                else:
                    pieces.append(_segment(by_id[identity], offset, offset + 1))
            return {'label': row['label'], 'output_span': [row['start'], row['end']],
                    'source_pieces': pieces, 'formatting_spans': formatting}

        regions.append({'item': view['item'], 'page': view['page'], 'labels': labels,
            'name_provenance': [provenance(row) for row in labels['names']],
            'use_provenance': [provenance(row) for row in labels['uses']]})
    excluded = []
    for unit in units:
        cursor = 0
        while cursor < len(unit['raw']):
            if cursor in used[unit['id']]:
                cursor += 1
                continue
            start = cursor
            while cursor < len(unit['raw']) and cursor not in used[unit['id']]:
                cursor += 1
            excluded.append(_segment(unit, start, cursor))
    require(sum(s['end'] - s['start'] for s in selected + excluded) == total_chars,
            'Original source characters were lost or duplicated')
    return {'version': VERSION, 'source_sha256': request['source_sha256'],
        'raw_units_sha256': request['raw_units_sha256'], 'projection': projected, 'regions': regions,
        'source_accounting': {'selected': selected, 'excluded': excluded, 'generated': generated,
            'original_characters': total_chars, 'accounted_for': True},
        'raw_replaced': False, 'scope_admitted': False, 'meaning_admitted': False,
        'extraction_completeness_established': False,
        'layout_basis': 'SUPPLIED_REVIEWED_REGIONS; not automatic margin classification'}


def _read(root, relative, limit, checksum):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(),
            'Repository-relative retained evidence required')
    with bound_path(root, relative).open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit and digest(data) == checksum, 'Retained source size or bytes changed')
    return data


def source_request(row, root):
    keys = {'id', 'product_path', 'product_file_sha256', 'pdf_path', 'source_sha256',
            'image_path', 'image_sha256', 'document', 'page', 'raw_units_sha256',
            'language', 'quotation_convention', 'layout', 'review_reason'}
    fields(row, keys, keys)
    require(isinstance(row['id'], str) and row['id']
            and isinstance(row['document'], str) and row['document']
            and type(row['page']) is int and row['page'] > 0
            and isinstance(row['review_reason'], str) and row['review_reason'].strip(),
            'Explicit source identity and reviewed layout reason required')
    _read(root, row['pdf_path'], 64 * 1024**2, row['source_sha256'])
    _read(root, row['image_path'], 8 * 1024**2, row['image_sha256'])
    compressed = _read(root, row['product_path'], 16 * 1024**2, row['product_file_sha256'])
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            data = stream.read(64 * 1024**2 + 1)
        require(len(data) <= 64 * 1024**2, 'Retained product expanded-byte bound exceeded')
        product = json.loads(data)
    except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Explicit retained gzip JSON product required') from error
    from .service import verify
    payload = verify(product, 'P1')
    require(isinstance(payload, dict) and isinstance(payload.get('graph'), dict)
            and isinstance(payload['graph'].get('units'), list)
            and all(isinstance(u, dict) and 'document' in u and 'page' in u
                    for u in payload['graph']['units']), 'Retained P1 source graph required')
    units = [u for u in payload['graph']['units']
             if u['document'] == row['document'] and u['page'] == row['page']]
    return {'raw_units': units, **{k: deepcopy(row[k]) for k in
        ('raw_units_sha256', 'source_sha256', 'language', 'quotation_convention', 'layout')}}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'sources',
            'scope_admitted', 'meaning_admitted'}
    fields(profile, keys, keys)
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
            and profile['products_sha256'] == digest(products)
            and profile['ordinary_answer_sha256'] == digest(ordinary)
            and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            and KEY not in ordinary, 'Pinned layout-label profile or complete prior answer changed')
    require(profile['scope_admitted'] is False and profile['meaning_admitted'] is False,
            'Layout and lexical review cannot admit legal scope or meaning')
    rows = profile['sources']
    require(isinstance(rows, list) and 1 <= len(rows) <= 4 and all(isinstance(r, dict) for r in rows),
            'Bounded retained source list required')
    identities = [r.get('id') for r in rows]
    require(all(isinstance(i, str) and i for i in identities) and len(set(identities)) == len(identities),
            'Distinct retained source identities required')
    reports = [{'source': deepcopy(row), 'report': review(source_request(row, root))} for row in rows]
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'sources': reports,
        'raw_replaced': False, 'scope_admitted': False, 'meaning_admitted': False,
        'source_authority_established': False, 'translation_equivalence_established': False}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    require(answer.get('report_sha256') == digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            and {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
                == {k: v for k, v in ordinary.items() if k != 'report_sha256'},
            'Layout labels changed complete prior answer or seal')
    require(answer.get(KEY) == evaluate(products, ordinary, profile, root,
                                       expected_profile_sha256=expected_profile_sha256),
            'Layout-label answer differs from retained source reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'sources': len(profile['sources'])}
