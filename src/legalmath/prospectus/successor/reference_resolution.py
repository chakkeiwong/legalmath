"""Resolve a finite printed-address grammar without reviewed destinations.

The separate reconciliation API preserves authored semantic targets. A printed
container and an intersecting source anchor do not establish legal equivalence.
"""
from copy import deepcopy
import re

from .contracts import digest
from . import reference_mentions as mentions
from .paragraph_references import discover as paragraphs
from .reference_addresses import LABEL, complete_path, expanded_paths

require, fields = mentions.require, mentions.fields
VERSION = 'reference-resolution-report.v1'
COORDINATION = re.compile(r'\s*(?:,\s*(?:(?:und/oder|und|oder)\s*)?|(?:und/oder|und|oder)\s*)', re.I)


def validate(request):
    fields(request, ('version', 'source', 'layout'), 'Resolution request')
    require(request['version'] == 'reference-resolution-request.v1', 'Resolution version differs')
    text, _ = mentions.validate(request['source'])
    require(isinstance(request['layout'], list) and len(request['layout']) <= mentions.LIMITS['units'],
            'Bounded layout required')
    layout = {}
    for row in request['layout']:
        fields(row, ('unit', 'context', 'role'), 'Layout row')
        require(isinstance(row['unit'], str) and row['unit'] not in layout, 'Unique layout unit required')
        require(isinstance(row['context'], str) and row['context'], 'Layout context required')
        require(row['role'] in ('HEADER', 'OPERATIVE', 'EXCLUDED', 'UNKNOWN'), 'Unsupported layout role')
        layout[row['unit']] = row
    require(set(layout) == {u['id'] for u in request['source']['raw_units']}, 'Layout/source coverage differs')
    return text, layout


def identities(projection, layout):
    return {(p['source']['document'], layout[p['source']['unit']]['context'])
            for p in projection if p['source']}


def fully_bound(text, projection):
    # Generated whitespace may join literal source fragments. Supplied text,
    # including supplied whitespace, never becomes raw evidence.
    return all(p['source'] is not None or
               (p['kind'] == 'GENERATED_SEPARATOR' and text[p['start']:p['end']].isspace())
               for p in projection)


def source_index(request, text, layout):
    source = request['source']
    pieces = source['source_pieces']
    headers, nodes, issues, parents = [], [], [], {}
    for row in source['section_headers']:
        meta = layout[row['unit']]
        require(meta['role'] == 'HEADER', 'Section label lacks header role')
        raw = next(p['raw_binding'] for p in pieces if p['start'] == row['start'] and p['end'] == row['end'])
        headers.append({**row, 'section': re.search(r'[0-9]+', text[row['start']:row['end']]).group(),
                        'document': raw['document'], 'context': meta['context']})
    headers.sort(key=lambda h: h['start'])
    for header in headers:
        boundaries = [h['start'] for h in headers if h['start'] > header['start']]
        boundaries += [p['start'] for p in pieces if p['raw_binding'] and p['start'] > header['start']
                       and (p['raw_binding']['document'], layout[p['raw_binding']['unit']]['context']) !=
                       (header['document'], header['context'])]
        header['body_end'] = min(boundaries, default=len(text))

    def enclosing(position, document, context):
        found = [h for h in headers if h['end'] <= position < h['body_end']
                 and h['document'] == document and h['context'] == context]
        return found[0] if len(found) == 1 else None

    for piece in pieces:
        raw = piece['raw_binding']
        if raw is None:
            continue
        meta = layout[raw['unit']]
        header = enclosing(piece['start'], raw['document'], meta['context'])
        match = LABEL.match(piece['text'])
        if header is None or match is None:
            continue
        label = next(v for v in match.groupdict().values() if v is not None)
        key = header['start']
        parent = parents.get(key, [])
        try:
            require(meta['role'] in ('HEADER', 'OPERATIVE', 'UNKNOWN'), 'Unsupported paragraph source role')
            require(not (label == 'i' and 'h' in parent), 'Ambiguous letter/Roman i')
            path = complete_path([label], parent)
        except ValueError as error:
            issues.append({'start': piece['start'], 'label': label, 'reason': str(error),
                           'section_start': key, 'document': raw['document'], 'context': meta['context']})
            parents[key] = []
            continue
        parents[key] = path
        nodes.append({'section': header['section'], 'path': path, 'start': piece['start'],
                      'unit': raw['unit'], 'document': raw['document'], 'context': meta['context'],
                      'section_start': key, 'printed_label': match.group(), 'heading_source': deepcopy(raw)})
        require(len(nodes) <= 2048, 'Printed index exceeds bound')
    for node in nodes:
        header = next(h for h in headers if h['start'] == node['section_start'])
        boundaries = [header['body_end']]
        boundaries += [n['start'] for n in nodes if n['start'] > node['start']
                       and (n['section_start'] != node['section_start'] or len(n['path']) <= len(node['path']))]
        boundaries += [i['start'] for i in issues if i['start'] > node['start']]
        node['end'] = min(boundaries)
    containers = [{**{k: h[k] for k in ('section', 'start', 'unit', 'document', 'context')},
                   'path': [], 'end': h['body_end'], 'section_start': h['start'],
                   'printed_label': text[h['start']:h['end']]} for h in headers] + nodes
    for node in containers:
        node['id'] = digest(node)
        node['text_sha256'] = digest(text[node['start']:node['end']].encode())
        node['source_projection'] = mentions.projection(source, node['start'], node['end'])
        node['legal_meaning_established'] = False
    return headers, nodes, containers, issues, enclosing


def resolve(request):
    """Derive printed destinations using source and explicit layout facts only."""
    text, layout = validate(request)
    source = request['source']
    discovery = mentions.discover(source)
    headers, nodes, containers, issues, enclosing = source_index(request, text, layout)
    citations = paragraphs(text, text_sha256=source['text_sha256'])['candidates']
    law = {}
    rows = discovery['mentions']
    for row in rows:
        tail = mentions.LAW_TAIL.search(row['raw'])
        if row['kind'] == 'NAMED_LAW_REFERENCE' or tail:
            law[row['id']] = {'mention': row['id'], 'start': row['start'] + (tail.start() if tail else 0),
                              'end': row['end'], 'shared': False,
                              'source_bound': fully_bound(text, row['source_projection'])}
    # A final statute qualifier also qualifies immediately coordinated citations.
    # It never propagates across a document/context or unrelated prose.
    for index in range(len(rows) - 2, -1, -1):
        row, following = rows[index:index + 2]
        if (row['kind'] == following['kind'] == 'SECTION_REFERENCE' and following['id'] in law
                and COORDINATION.fullmatch(text[row['end']:following['start']])
                and identities(row['source_projection'], layout) == identities(following['source_projection'], layout)
                and len(identities(row['source_projection'], layout)) == 1):
            law[row['id']] = {**law[following['id']], 'shared': True}

    resolved = []
    for row in rows:
        outcome = {'status': None, 'section': None, 'paths': [], 'target_ids': [], 'issues': [],
                   'law_qualifier': deepcopy(law.get(row['id']))}
        kind = row['kind']
        identity = identities(row['source_projection'], layout)
        if not fully_bound(text, row['source_projection']) or len(identity) != 1:
            outcome.update(status='UNRESOLVED_SOURCE', issues=['Citation is not wholly raw-bound within one context'])
        elif kind == 'IMPLICIT_REFERENCE':
            outcome['status'] = 'UNRESOLVED_IMPLICIT'
        elif kind == 'UNSPECIFIED_LAW_REFERENCE':
            outcome['status'] = 'UNRESOLVED_UNSPECIFIED_LAW'
        elif row['id'] in law:
            if law[row['id']]['source_bound']:
                outcome['status'] = 'EXTERNAL_LAW_REFERENCE'
            else:
                outcome.update(status='UNRESOLVED_SOURCE', issues=['Statutory qualifier lacks complete raw binding'])
        else:
            document, context = next(iter(identity))
            header = enclosing(row['start'], document, context)
            if header is None:
                outcome.update(status='UNRESOLVED_CONTEXT', issues=['No enclosing source section'])
            else:
                try:
                    require(row['end'] <= header['body_end'], 'Citation crosses section boundary')
                    section_tokens = list(mentions.SECTION.finditer(row['raw']))
                    require(len(section_tokens) <= 1, 'Unsupported compound section syntax')
                    section = re.search(r'[0-9]+[a-z]?', section_tokens[0].group()).group() if section_tokens else header['section']
                    matches = [h for h in headers if h['document'] == document and h['context'] == context and h['section'] == section]
                    require(len(matches) == 1, 'Missing or nonunique section address')
                    require(not any(i['section_start'] in (header['start'], matches[0]['start']) for i in issues),
                            'Unsupported source hierarchy')
                    local = [n for n in nodes if n['section_start'] == header['start']
                             and n['start'] <= row['start'] < n['end']]
                    parent = max(local, key=lambda n: len(n['path']))['path'] if local and section == header['section'] else []
                    parts = [c for c in citations if row['start'] <= c['start'] < c['end'] <= row['end']]
                    if len(parts) == 2:
                        first, second = parts
                        require(kind == 'PARAGRAPH_REFERENCE' and re.search(r'\bdieses\s+§', row['raw'])
                                and all(c['syntax_complete'] and not c['connectors'] and len(c['paths']) == 1
                                        and len(c['paths'][0]) == 1 for c in parts), 'Unsupported compound paragraph syntax')
                        require(first['paths'][0][0] in tuple('abcdefgh') and second['paths'][0][0].isdecimal(),
                                'Unsupported self-reference hierarchy')
                        paths = expanded_paths([second['paths'][0] + first['paths'][0]], [], parent)
                    elif len(parts) == 1:
                        require(parts[0]['syntax_complete'], 'Incomplete paragraph syntax')
                        paths = expanded_paths(parts[0]['paths'], parts[0]['connectors'], parent)
                    else:
                        require(kind == 'SECTION_REFERENCE' and len(section_tokens) == 1, 'Unsupported address syntax')
                        position, direct = section_tokens[0].end(), []
                        while component := mentions.COMPONENT.match(row['raw'], position):
                            direct.append(component.group().strip()[1:-1])
                            position = component.end()
                        require(not row['raw'][position:].strip(), 'Unsupported section suffix')
                        paths = expanded_paths([direct], [], parent) if direct else [[]]
                    targets = []
                    for path in paths:
                        found = [n for n in containers if n['document'] == document and n['context'] == context
                                 and n['section'] == section and n['path'] == path]
                        require(len(found) == 1, 'Missing or nonunique structural address')
                        targets.append(found[0]['id'])
                    outcome.update(status='SECTION_CONTAINER' if paths == [[]] else 'STRUCTURAL_ADDRESS',
                                   section=section, paths=paths, target_ids=targets)
                except ValueError as error:
                    outcome.update(status='UNRESOLVED_STRUCTURE', issues=[str(error)])
        resolved.append({**deepcopy(row), 'resolution': outcome})
    result = {'version': VERSION, 'request_sha256': digest(request), 'text_sha256': source['text_sha256'],
              'discovery_sha256': discovery['report_sha256'], 'mentions': resolved, 'index': containers,
              'index_issues': issues, 'discovery_issues': discovery['issues'],
              'legal_truth_established': False, 'general_recall_established': False,
              'document_authenticity_established': False, 'whole_task_complete': False,
              'supported_domain': 'Finite printed numeric/letter/Roman addresses; source-only supplied layout',
              'remaining': ['implicit referents', 'definition scope', 'statutory edition and applicability',
                            'legal meaning', 'unlisted citation grammar']}
    return {**result, 'report_sha256': digest(result)}


def merge(intervals):
    result = []
    for left, right in sorted(intervals):
        if result and left <= result[-1][1]:
            result[-1] = (result[-1][0], max(right, result[-1][1]))
        else:
            result.append((left, right))
    return result


def raw_intervals(projection):
    result = {}
    for piece in projection:
        anchor = piece['source']
        if anchor:
            key = tuple(anchor[k] for k in ('unit', 'document', 'source_sha256'))
            result.setdefault(key, []).append((anchor['start'], anchor['end']))
    return {k: merge(v) for k, v in result.items()}


def source_relation(anchor, projection, text):
    key = tuple(anchor[k] for k in ('unit', 'document', 'source_sha256'))
    intervals = raw_intervals(projection)
    same = intervals.get(key, [])
    left, right = anchor['start'], anchor['end']
    intersection = any(max(a, left) < min(b, right) for a, b in same)
    if not intersection:
        return 'NO_SOURCE_RELATION'
    mention_covers = any(a <= left < right <= b for a, b in same)
    anchor_covers = (fully_bound(text, projection) and set(intervals) == {key}
                     and all(left <= a < b <= right for a, b in same))
    if mention_covers and anchor_covers:
        return 'EXACT_SOURCE_MATCH'
    if anchor_covers:
        return 'REVIEWED_SOURCE_CONTAINS_MENTION'
    if mention_covers:
        return 'MENTION_CONTAINS_REVIEWED_SOURCE'
    return 'PARTIAL_SOURCE_INTERSECTION'


def validate_graph(request, graph):
    fields(graph, ('version', 'references', 'raw_units'), 'Reviewed graph')
    require(graph['version'] == 'reviewed-reference-graph.v1', 'Reviewed graph version differs')
    require(isinstance(graph['references'], list) and len(graph['references']) <= 2048, 'Bounded reviewed edges required')
    require(isinstance(graph['raw_units'], list) and len(graph['raw_units']) <= 10000, 'Bounded reviewed units required')
    original = {u['id']: u for u in request['source']['raw_units']}
    units = {}
    for unit in graph['raw_units']:
        fields(unit, ('id', 'document', 'source_sha256', 'raw', 'text_sha256'), 'Reviewed raw unit')
        require(isinstance(unit['id'], str) and unit['id'] and unit['id'] not in units, 'Unique reviewed unit required')
        require(isinstance(unit['document'], str) and unit['document'] and mentions.checksum(unit['source_sha256']),
                'Reviewed unit identity differs')
        require(isinstance(unit['raw'], str) and len(unit['raw']) <= 100000
                and digest(unit['raw'].encode()) == unit['text_sha256'], 'Reviewed raw hash differs')
        require(unit['id'] not in original or unit == original[unit['id']], 'Graph/source raw unit differs')
        units[unit['id']] = unit
    identifiers, count = set(), 0
    for edge in graph['references']:
        fields(edge, ('id', 'source', 'targets'), 'Reviewed edge')
        require(isinstance(edge['id'], str) and edge['id'] and edge['id'] not in identifiers, 'Unique reviewed edge required')
        identifiers.add(edge['id'])
        require(isinstance(edge['targets'], list), 'Reviewed targets must be a list')
        count += len(edge['targets']) + 1
        require(count <= 10000, 'Reviewed anchor bound exceeded')
        for anchor in [edge['source'], *edge['targets']]:
            fields(anchor, ('unit', 'document', 'source_sha256', 'start', 'end', 'quote'), 'Reviewed anchor')
            require(isinstance(anchor['unit'], str) and anchor['unit'] in units, 'Reviewed anchor unit missing')
            unit = units[anchor['unit']]
            a, b = anchor['start'], anchor['end']
            require(mentions.integer(a) and mentions.integer(b) and 0 <= a < b <= len(unit['raw']), 'Reviewed offsets differ')
            require(anchor['document'] == unit['document'] and anchor['source_sha256'] == unit['source_sha256']
                    and unit['raw'][a:b] == anchor['quote'], 'Reviewed raw anchor differs')


def reconcile(request, report, graph):
    """Check every reviewed edge, preserving partial source/target relationships."""
    require(report == resolve(request), 'Resolution differs from recomputed source-only report')
    validate_graph(request, graph)
    index = {n['id']: n for n in report['index']}
    edges = []
    for edge in graph['references']:
        matches = []
        for row in report['mentions']:
            relation = source_relation(edge['source'], row['source_projection'], request['source']['text'])
            if relation == 'NO_SOURCE_RELATION':
                continue
            targets = []
            for anchor in edge['targets']:
                comparisons = []
                all_projection = []
                for ident in row['resolution']['target_ids']:
                    projection = index[ident]['source_projection']
                    all_projection.extend(projection)
                    key = tuple(anchor[k] for k in ('unit', 'document', 'source_sha256'))
                    intervals = raw_intervals(projection).get(key, [])
                    contained = any(a <= anchor['start'] < anchor['end'] <= b for a, b in intervals)
                    intersects = any(max(a, anchor['start']) < min(b, anchor['end']) for a, b in intervals)
                    comparisons.append({'container': ident, 'relation': 'CONTAINED_IN_PRINTED_DESTINATION' if contained
                                        else 'PARTIAL_PRINTED_INTERSECTION' if intersects else 'OUTSIDE_PRINTED_DESTINATION'})
                key = tuple(anchor[k] for k in ('unit', 'document', 'source_sha256'))
                union = raw_intervals(all_projection).get(key, [])
                contained = any(a <= anchor['start'] < anchor['end'] <= b for a, b in union)
                intersects = any(max(a, anchor['start']) < min(b, anchor['end']) for a, b in union)
                union_relation = ('NO_PRINTED_DESTINATION' if not comparisons else
                                  'CONTAINED_IN_PRINTED_DESTINATION_UNION' if contained else
                                  'PARTIAL_PRINTED_UNION_INTERSECTION' if intersects else 'OUTSIDE_PRINTED_DESTINATION_UNION')
                targets.append({'anchor': deepcopy(anchor), 'printed_destinations': comparisons,
                                'union_relation': union_relation, 'no_printed_destination': not comparisons})
            matches.append({'mention': row['id'], 'source_relation': relation, 'targets': targets,
                            'semantic_equivalence_established': False})
        edges.append({'reviewed_edge': deepcopy(edge), 'matches': matches, 'no_source_relation': not matches,
                      'legal_meaning_established': False})
    covered = {m['mention'] for e in edges for m in e['matches']}
    result = {'version': 'reference-graph-reconciliation.v1', 'request_sha256': digest(request),
              'resolution_sha256': report['report_sha256'], 'reviewed_graph_sha256': digest(graph),
              'edges': edges, 'mentions_without_reviewed_source_relation': [r['id'] for r in report['mentions'] if r['id'] not in covered],
              'reviewed_targets_preserved': True, 'source_resolution_unchanged': True,
              'semantic_equivalence_established': False, 'legal_truth_established': False,
              'whole_task_complete': False}
    return {**result, 'report_sha256': digest(result)}
