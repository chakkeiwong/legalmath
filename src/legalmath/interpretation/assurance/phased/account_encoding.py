"""Optional lossless wire representation for exact typed requirement accounts.

Source content is unchanged. This module grants neither calls nor larger limits.
"""
from collections import Counter
from copy import deepcopy
from ..bounded_context import require

PROFILE = 'exact-account-structure-integer-16k.v2'
STRUCTURE = (
    'Source record table: metadata holds identical fields shared by source unit; '
    'columns names every remaining per-record field. A row starts with metadata_id, '
    'followed by one value for each column. Merge that metadata with those fields. '
    'Response spans: for each record, regular=[first_span_number,record_length,256] '
    'offers first the whole record then contiguous 256-codepoint slices with the '
    'last slice ending at record_length. Alias numbers increase by one in that '
    'order. The default legal_locator is empty. Explicit rows contain all '
    '[span_id,record_id,start_codepoint,end_codepoint,legal_locator] exceptions. '
    'Every offered span is exact and must be used as a complete contiguous quote. '
    'No source or partial reading is removed.')
SELECTORS = (
    'An output span_id is an integer n selecting the original alias s followed by n. '
    'Only integers in the declared inclusive bounds are permitted. Each selected span '
    'retains the exact record, quotation, locator and source identity. In the request, '
    'each identity_hash alias selects its exact value in account_identity_hashes; '
    'this is a lossless identity abbreviation, not a separate authority.')
FIELDS = ('account_record_table', 'account_span_recipes', 'account_structure_instructions',
          'account_identity_hashes', 'account_integer_citation_instructions')


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for child in node:
            yield from strings(child)
    elif isinstance(node, dict):
        for child in node.values():
            yield from strings(child)


def pack(value):
    """Pack an already exact-table request and its wire schema."""
    out = deepcopy(value)
    request = out['request']
    require(not any(k in request for k in FIELDS), 'Reserved account encoding field')
    records = request.get('records', [])
    spans = request['account_response_spans']
    # Empty source sets keep the existing no-citation contract exactly.
    if not records or not spans:
        return out
    require(set(spans) == {'s' + str(i) for i in range(len(spans))},
        'Nonconsecutive offered span aliases')
    groups = {}
    for record in records:
        groups.setdefault(record['unit_id'], []).append(record)
    shared = set.intersection(*(set(r) for r in records))
    shared = {k for k in shared if all(all(r[k] == rows[0][k] for r in rows)
        for rows in groups.values())} - {'id', 'text', 'start', 'end'}
    columns = [k for k in records[0] if k not in shared]
    require(all(set(r) - shared == set(columns) for r in records),
        'Heterogeneous account record fields')
    names = {unit: 'u' + str(i) for i, unit in enumerate(groups)}
    request['account_record_table'] = {
        'metadata': {names[unit]: {k: rows[0][k] for k in rows[0] if k in shared}
            for unit, rows in groups.items()}, 'columns': columns,
        'rows': [[names[r['unit_id']], *[r[k] for k in columns]] for r in records]}
    del request['records']
    regular, explicit = {}, []
    for record in records:
        rows = [(k, v) for k, v in spans.items() if v[0] == record['id']]
        length = record['end'] - record['start']
        desired = [(0, length), *[(i, min(i + 256, length)) for i in range(0, length, 256)]]
        first = int(rows[0][0][1:]) if rows else -1
        expected = [('s' + str(first + i), [record['id'], a, b, ''])
            for i, (a, b) in enumerate(desired)]
        if len(set(desired)) == len(desired) and rows == expected:
            regular[record['id']] = [first, length, 256]
        else:
            explicit.extend([[key, *row] for key, row in rows])
    request.pop('account_response_spans')
    request['account_span_recipes'] = {'regular': regular, 'explicit': explicit}
    request['account_structure_instructions'] = STRUCTURE
    citations = []

    def share(node):
        if isinstance(node, dict):
            if set(node.get('properties', {})) == {'span_id'}:
                citations.append(deepcopy(node))
                return {'$ref': '#/$defs/ExactCitation'}
            return {k: share(v) for k, v in node.items()}
        if isinstance(node, list):
            return [share(v) for v in node]
        return node

    shape = share(out['response_schema'])
    require(citations and all(c == citations[0] for c in citations)
        and 'ExactCitation' not in shape.get('$defs', {}), 'Conflicting citation schemas')
    definition = citations[0]
    choices = definition['properties']['span_id']['enum']
    require(choices == ['s' + str(i) for i in range(len(spans))], 'Changed citation choice set')
    definition['properties']['span_id'] = {'type': 'integer', 'minimum': 0, 'maximum': len(spans) - 1}
    shape.setdefault('$defs', {})['ExactCitation'] = definition
    out['response_schema'] = shape
    counts = Counter(strings(request))
    selected = [s for s, count in counts.items() if count > 1 and len(s) == 64
        and all(c in '0123456789abcdef' for c in s)]
    hashes = {'h' + str(i): s for i, s in enumerate(selected)}
    reverse = {v: k for k, v in hashes.items()}

    def abbreviate(node):
        if isinstance(node, str) and node in reverse:
            return {'identity_hash': reverse[node]}
        if isinstance(node, dict):
            require(set(node) != {'identity_hash'}, 'Reserved identity hash field')
            return {k: abbreviate(v) for k, v in node.items()}
        if isinstance(node, list):
            return [abbreviate(v) for v in node]
        return node

    out['request'] = abbreviate(request)
    out['request']['account_identity_hashes'] = hashes
    out['request']['account_integer_citation_instructions'] = SELECTORS
    require(expand(out) == value, 'Account encoding changed original content', 'E_INTEGRITY')
    return out


def expand(value):
    out = deepcopy(value)
    request = out['request']
    if 'account_record_table' not in request:
        require(not any(k in request for k in FIELDS), 'Incomplete account encoding')
        return out
    require(request.pop('account_integer_citation_instructions') == SELECTORS, 'Changed integer semantics')
    table = request.pop('account_identity_hashes')
    used = set()

    def restore(node):
        if isinstance(node, dict):
            if set(node) == {'identity_hash'}:
                key = node['identity_hash']
                require(key in table, 'Unknown identity hash alias')
                used.add(key)
                return table[key]
            return {k: restore(v) for k, v in node.items()}
        if isinstance(node, list):
            return [restore(v) for v in node]
        return node

    request = restore(request)
    require(used == set(table), 'Unused identity hash alias')
    out['request'] = request
    require(request.pop('account_structure_instructions') == STRUCTURE, 'Changed record semantics')
    table = request.pop('account_record_table')
    records = []
    require(len(table['columns']) == len(set(table['columns'])), 'Duplicate record field')
    for name, *cells in table['rows']:
        require(len(cells) == len(table['columns']) and name in table['metadata'], 'Invalid record row')
        fields = dict(zip(table['columns'], cells))
        metadata = table['metadata'][name]
        require(not set(fields) & set(metadata), 'Record metadata overwrites a field')
        records.append({**metadata, **fields})
    request['records'] = records
    recipes = request.pop('account_span_recipes')
    spans = {}
    for rid, (first, length, step) in recipes['regular'].items():
        require(type(first) is int and first >= 0 and type(length) is int and length > 0
            and type(step) is int and step == 256, 'Invalid regular span recipe')
        intervals = [(0, length), *[(i, min(i + step, length)) for i in range(0, length, step)]]
        for i, (a, b) in enumerate(intervals):
            key = 's' + str(first + i)
            require(key not in spans, 'Duplicate span alias')
            spans[key] = [rid, a, b, '']
    for key, *row in recipes['explicit']:
        require(key not in spans and len(row) == 4, 'Invalid explicit span')
        spans[key] = row
    require(set(spans) == {'s' + str(i) for i in range(len(spans))}, 'Changed span population')
    request['account_response_spans'] = spans
    definition = out['response_schema']['$defs'].pop('ExactCitation')
    if not out['response_schema']['$defs']:
        del out['response_schema']['$defs']
    require(definition['properties']['span_id'] ==
        {'type': 'integer', 'minimum': 0, 'maximum': len(spans) - 1}, 'Changed selector bounds')
    definition['properties']['span_id'] = {'type': 'string', 'enum': ['s' + str(i) for i in range(len(spans))]}

    def restore_schema(node):
        if node == {'$ref': '#/$defs/ExactCitation'}:
            return deepcopy(definition)
        if isinstance(node, dict):
            return {k: restore_schema(v) for k, v in node.items()}
        if isinstance(node, list):
            return [restore_schema(v) for v in node]
        return node

    out['response_schema'] = restore_schema(out['response_schema'])
    return out


def decode_selectors(value, prepared):
    if 'account_integer_citation_instructions' not in prepared['request']:
        return value
    choices = prepared['selections']

    def walk(node):
        if isinstance(node, dict):
            if set(node) == {'span_id'}:
                number = node['span_id']
                require(type(number) is int and 's' + str(number) in choices,
                    'Invalid request-bound integer selector')
                return {'span_id': 's' + str(number)}
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    return walk(value)
