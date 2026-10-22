"""Project reviewed current occurrence roles into retained definition provenance."""
from copy import deepcopy
from .anchors import fields
from .contracts import digest
from .definition_discovery import require

VERSION = 'definition-current-roles.v1'
KEY = 'definition_role_projection'
SOURCE_KEYS = ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')
ROLES = {'UNKNOWN', 'HEADER', 'OPERATIVE', 'EXCLUDED'}


def _index(rows, key):
    require(isinstance(rows, list), 'Occurrence list required')
    result = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get(key), str)
                and row[key] and row[key] not in result, 'Distinct occurrence identities required')
        result[row[key]] = row
    return result


def _source(value, raw):
    require(isinstance(value, dict) and set(SOURCE_KEYS) <= value.keys(), 'Exact raw source required')
    source = {k: value[k] for k in SOURCE_KEYS}
    unit = raw.get(source['unit'])
    require(unit is not None and unit.get('visible', True) is True, 'Raw source unavailable')
    require((unit['document'], unit['source_sha256']) == (source['document'], source['source_sha256']),
            'Raw source edition changed')
    a, b = source['start'], source['end']
    require(type(a) is int and type(b) is int and 0 <= a < b <= len(unit['raw'])
            and unit['raw'][a:b] == source['quote'], 'Raw source interval or quotation changed')
    return source


def _mapping(unit, raw):
    require(isinstance(unit.get('text'), str) and isinstance(unit.get('character_map'), list),
            'Explicit current occurrence character map required')
    result = []
    for row in unit['character_map']:
        if row.get('operation') not in ('Text', 'Field') or row.get('source') is None:
            continue
        source = _source(row['source'], raw)
        a, b = row['start'], row['end']
        require(type(a) is int and type(b) is int and 0 <= a < b <= len(unit['text'])
                and unit['text'][a:b] == source['quote'], 'Current character map differs from raw text')
        result.append((a, b, source))
    return result


def project(report, raw_units, assembly, approved):
    """Validate each retained use before updating only its explicit role field."""
    raw, units = _index(raw_units, 'id'), _index(assembly['units'], 'unit')
    require(isinstance(approved, dict), 'Reviewed transitions required')
    for identity, transition in approved.items():
        fields(transition, {'before', 'after'}, {'before', 'after'})
        require(identity in units and transition['before'] in ROLES and transition['after'] in ROLES
                and units[identity]['role'] == transition['after'], 'Reviewed current role differs')
    result, changes, maps = deepcopy(report), [], {}
    require(isinstance(report.get('source_pieces'), list), 'Retained source partition required')
    offset, selected_text = 0, []
    for number, piece in enumerate(result['source_pieces']):
        a, b, text = piece['start'], piece['end'], piece['text']
        require(type(a) is int and type(b) is int and a == offset and b > a
                and isinstance(text, str) and len(text) == b - a, 'Source partition changed')
        offset = b
        selected_text.append(text)
        require(isinstance(piece['assembly_uses'], list), 'Source occurrence uses required')
        if piece['kind'] != 'EXACT_SOURCE_COPY':
            require(piece['kind'] in ('SUPPLIED_OR_TRANSFORMED', 'GENERATED_SEPARATOR')
                    and piece['raw_binding'] is None and not piece['assembly_uses'],
                    'Supplied or generated text cannot acquire a raw quotation')
            continue
        source = _source(piece['raw_binding'], raw)
        require(source['quote'] == text, 'Source partition quotation changed')
        seen = set()
        for index, use in enumerate(piece['assembly_uses']):
            identity = use['unit']
            unit = units.get(identity)
            require(unit is not None, 'Selected occurrence missing')
            start, end = use['start'], use['end']
            require(type(start) is int and type(end) is int and 0 <= start < end <= len(unit['text'])
                    and unit['text'][start:end] == text, 'Occurrence text or interval changed')
            require((identity, start, end) not in seen, 'Duplicate retained source use')
            seen.add((identity, start, end))
            require(_source(use['source'], raw) == source, 'Occurrence raw binding differs')
            for key in ('context', 'questions', 'language'):
                require(key not in use or use[key] == unit.get(key), 'Occurrence context changed')
            if identity not in maps:
                maps[identity] = _mapping(unit, raw)
            parts = []
            for left, right, mapped in maps[identity]:
                lo, hi = max(start, left), min(end, right)
                if lo < hi:
                    require(all(mapped[k] == source[k] for k in ('unit', 'document', 'source_sha256'))
                            and mapped['start'] + lo - left == source['start'] + lo - start,
                            'Character map points to a different raw occurrence')
                    parts.append((lo, hi))
            cursor = start
            for lo, hi in sorted(parts):
                require(lo == cursor, 'Character map has an overlap or gap')
                cursor = hi
            require(cursor == end, 'Occurrence has no complete exact character map')
            before, after = use['role'], unit['role']
            require(before in ROLES and after in ROLES, 'Unknown occurrence role')
            if before != after:
                require(approved.get(identity) == {'before': before, 'after': after},
                        'Unreviewed occurrence role transition')
                changes.append({'piece': number, 'use': index, 'unit': identity, 'before': before, 'after': after})
                use['role'] = after
    if 'continuous_text' in assembly:
        require(''.join(selected_text) == assembly['continuous_text'], 'Selected contract text changed')
    return {'report': result, 'changes': changes}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    from . import structural_roles, definition_scopes
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'structural_profile_sha256',
            'legal_truth_established'}
    fields(profile, keys, keys)
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
            and profile['products_sha256'] == digest(products)
            and profile['ordinary_answer_sha256'] == digest(ordinary)
            and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            and KEY not in ordinary, 'Pinned current-role profile or prior answer changed')
    require(profile['structural_profile_sha256'] == structural_roles.PROFILE_SHA256
            and profile['legal_truth_established'] is False, 'Only registered source roles are admitted')
    p1, p2, p3 = (products[k]['payload'] for k in ('P1', 'P2', 'P3'))
    assembly, graph = p2['assembly'], p1['graph']
    spec = structural_roles.verify(graph, assembly, p1['request'].get('structural_roles'))
    require(spec is not None, 'Registered structural review required')
    retained = ordinary.get('definition_sources')
    original = definition_scopes.specification(structural=True)
    require(retained is not None and retained == p3.get('definition_sources')
            and retained['source_pieces'] == original['source_pieces']
            and retained['bindings'] == original['bindings'], 'Retained definition provenance changed')
    approved = {r['unit']: {'before': r['before']['role'], 'after': 'HEADER'} for r in spec['decisions']}
    projected = project(retained, graph['units'], assembly, approved)
    history = {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
        'prior_definition_report_sha256': digest(retained),
        'current_definition_report_sha256': digest(projected['report']),
        'assembly_sha256': digest(assembly), 'structural_profile_sha256': digest(spec),
        'changes': projected['changes'], 'source_text_preserved': True,
        'meaning_and_scope_preserved': True, 'legal_truth_established': False}
    return {'definition_sources': projected['report'], KEY: history}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    projection = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    expected = {**ordinary, **projection}
    expected['report_sha256'] = digest({k: v for k, v in expected.items() if k != 'report_sha256'})
    require(answer == expected, 'Current definition answer differs from exact reviewed role delta')
    return {'status': 'PASS', 'role_changes': len(projection[KEY]['changes']),
            'only_reviewed_role_delta': True, 'legal_truth_established': False}
