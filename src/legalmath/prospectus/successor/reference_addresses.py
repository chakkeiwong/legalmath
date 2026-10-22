"""Source-bound structural paragraph addresses in a declared German grammar.

Destinations are printed containers, not an adjudication of their legal meaning.
The resolver never reads the manually reviewed reference destinations.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from .anchors import fields
from .contracts import digest
from .reference_scope import current_headers, projection, require

VERSION = 'reference-addresses.v1'
KEY = 'reference_addresses'
SPEC_SHA256 = 'fe69372c7a0cd2b1ba0897dd0183bdb39d2a5520e8607d4e3fe0928081b58643'
LETTERS = tuple('abcdefgh')
ROMANS = ('i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
          'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx')
LABEL = re.compile(r'^(?:\[\((?P<wrapped>[0-9]+|[a-z]|[ivxlcdm]+)\)\]|'
                   r'\((?P<plain>[0-9]+|[a-z]|[ivxlcdm]+)\)|\[(?P<square>[0-9]+|[a-z]|[ivxlcdm]+)\])(?=\s|$)')
LIMITS = {'nodes': 2048, 'expanded_paths': 64, 'numeric_label': 999}


def level(label):
    if isinstance(label, str) and label.isascii() and label.isdecimal():
        if 1 <= int(label) <= LIMITS['numeric_label'] and str(int(label)) == label:
            return 0
    if label in LETTERS:
        return 1
    if label in ROMANS:
        return 2
    raise ValueError('Unsupported paragraph label')


def complete_path(path, parent):
    require(isinstance(path, list) and path and len(path) <= 3, 'Unsupported address depth')
    levels = [level(x) for x in path]
    require(levels == list(range(levels[0], levels[0] + len(path))), 'Nonconsecutive address levels')
    first = levels[0]
    prefix = [x for x in parent if level(x) < first]
    if first == 2:
        require(prefix and level(prefix[-1]) == 1, 'Roman item has no letter parent')
    # An unnumbered section may contain letter paragraphs at its root.
    result = prefix + path
    require(len(result) <= 3, 'Unsupported inherited depth')
    return result


def expanded_paths(paths, connectors, enclosing_path):
    require(isinstance(paths, list) and paths and len(paths) <= LIMITS['expanded_paths']
            and len(connectors) == len(paths) - 1, 'Malformed paragraph list')
    previous = complete_path(paths[0], enclosing_path)
    result = [previous]
    for connector, path in zip(connectors, paths[1:]):
        require(connector in (',', 'und', 'oder', 'und/oder', 'bis'), 'Unsupported list connector')
        current = complete_path(path, previous)
        if connector == 'bis':
            require(current[:-1] == previous[:-1] and level(current[-1]) == level(previous[-1]),
                    'Range crosses paragraph parents')
            kind = level(current[-1])
            order = tuple(str(i) for i in range(1, LIMITS['numeric_label'] + 1)) if kind == 0 else (LETTERS if kind == 1 else ROMANS)
            left, right = order.index(previous[-1]), order.index(current[-1])
            require(left < right and right - left < LIMITS['expanded_paths'], 'Reversed or excessive paragraph range')
            result.extend(previous[:-1] + [x] for x in order[left + 1:right + 1])
        else:
            result.append(current)
        require(len(result) <= LIMITS['expanded_paths'], 'Expanded paragraph list exceeds bound')
        previous = current
    return result


def body_projection(text, pieces, raw_units, operations, start, end):
    result, cursor = [], start
    for index, piece in enumerate(pieces):
        left, right = max(start, piece['start']), min(end, piece['end'])
        if left >= right:
            continue
        require(left == cursor, 'Paragraph body has a source gap or overlap')
        if piece['kind'] != 'SUPPLIED_OR_TRANSFORMED':
            result.extend(projection(text, pieces, raw_units, left, right))
        else:
            require(piece.get('raw_binding') is None and piece.get('operation') == 'SUBSTITUTE'
                    and piece['text'] == text[piece['start']:piece['end']],
                    'Transformed paragraph text has an invalid source classification')
            replaced = piece.get('replaced_raw_interval')
            basis = piece.get('basis')
            require(isinstance(replaced, dict) and isinstance(basis, dict) and basis,
                    'Transformed paragraph text lacks its retained basis')
            matches = [operation for operation in operations
                       if operation.get('start') == replaced.get('start')
                       and operation.get('end') == replaced.get('end')
                       and operation.get('old') == replaced.get('quote')
                       and operation.get('new') == piece['text']
                       and operation.get('basis') == basis]
            require(len(matches) == 1, 'Paragraph transformation differs from current construction')
            result.append({'piece_index': index, 'selected_start': left, 'selected_end': right,
                'text': text[left:right], 'kind': piece['kind'], 'source': None,
                'transformation': {'operation': deepcopy(matches[0]), 'basis': deepcopy(basis),
                    'replaced_raw_interval': deepcopy(replaced),
                    'piece_start': piece['start'], 'piece_end': piece['end'],
                    'raw_quotation_established': False}})
        cursor = right
    require(cursor == end, 'Paragraph body projection incomplete')
    return result


def source_model(products, ordinary):
    assembly = products['P2']['payload']['assembly']
    text = assembly['continuous_text']
    units = {u['unit']: u for u in assembly['units']}
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    pieces = ordinary['definition_sources']['source_pieces']
    headers = current_headers(text, pieces, units, raw)
    nodes, issues = [], []
    parents = {}
    for piece in pieces:
        source = piece.get('raw_binding')
        if not source:
            continue
        unit = units.get(source['unit'])
        require(unit is not None, 'Selected source lacks current assembly unit')
        document, context = source['document'], unit['context']
        applicable = [h for h in headers if h['document'] == document and h['context'] == context
                      and h['end'] <= piece['start']]
        if not applicable:
            continue
        header = max(applicable, key=lambda h: h['start'])
        match = LABEL.match(piece['text'])
        if not match:
            continue
        label = next(v for v in match.groupdict().values() if v is not None)
        key = (document, context, header['start'])
        parent = parents.get(key, [])
        try:
            kind = level(label)
            # In the supported hierarchy (i) starts Roman children. After (h)
            # it could instead be the next letter, which this grammar refuses.
            require(not (label == 'i' and parent and 'h' in parent), 'Ambiguous letter/Roman i')
            path = complete_path([label], parent)
            require(unit['role'] in ('HEADER', 'OPERATIVE', 'UNKNOWN'), 'Unsupported paragraph source role')
        except ValueError as error:
            issues.append({'start': piece['start'], 'label': label, 'reason': str(error),
                           'document': document, 'context': context, 'section_start': header['start']})
            # Do not let an unsupported heading silently extend a previous body.
            parents[key] = []
            continue
        parents[key] = path
        mapped = projection(text, pieces, raw, piece['start'], piece['end'])
        require(len(mapped) == 1 and mapped[0]['source'] is not None, 'Heading must be exactly source-bound')
        require(unit['source']['document'] == document and unit['source']['page'] == raw[source['unit']]['page'],
                'Current heading identity differs')
        require(unit['original_sha256'] == raw[source['unit']]['text_sha256'] == digest(raw[source['unit']]['raw'].encode()),
                'Current heading raw hash differs')
        maps = unit.get('character_map')
        if maps is not None:
            require(any(m.get('source') and all(m['source'].get(k) == source[k] for k in ('unit', 'document', 'source_sha256'))
                        and m['source']['start'] <= source['start'] < source['end'] <= m['source']['end']
                        and unit['text'][m['start'] + source['start'] - m['source']['start']:
                                         m['start'] + source['end'] - m['source']['start']] == piece['text']
                        for m in maps), 'Current heading character map differs')
        else:
            require(unit['text'] == raw[source['unit']]['raw'], 'Unmapped modified heading')
        nodes.append({'section': header['section'], 'path': path, 'start': piece['start'],
                      'unit': source['unit'], 'document': document, 'context': context,
                      'section_start': header['start'], 'printed_label': match.group(),
                      'heading_source': deepcopy(source), 'heading_role': unit['role']})
        require(len(nodes) <= LIMITS['nodes'], 'Paragraph index exceeds bound')
    for node in nodes:
        boundaries = [h['start'] for h in headers if h['start'] > node['start']]
        boundaries += [n['start'] for n in nodes if n['start'] > node['start']
                       and (n['section_start'] != node['section_start'] or len(n['path']) <= len(node['path']))]
        boundaries += [i['start'] for i in issues if i['start'] > node['start']]
        end = min(boundaries, default=len(text))
        node['end'] = end
        node['text_sha256'] = digest(text[node['start']:end].encode())
        node['source_projection'] = body_projection(text, pieces, raw, assembly['operations'], node['start'], end)
        node['unknown_source_units'] = sorted({p['source']['unit'] for p in node['source_projection']
                                             if p['source'] and units[p['source']['unit']]['role'] == 'UNKNOWN'})
        node['legal_meaning_established'] = False
    return text, pieces, raw, nodes, issues


def compound_groups(text, contexts, candidates):
    require(len(contexts) == len(candidates), 'Context/candidate coverage differs')
    out, pos = [], 0
    while pos < len(contexts):
        row, candidate = contexts[pos], candidates[pos]
        require(row['paragraph_start'] == candidate['start'], 'Context/candidate order differs')
        group = {'contexts': [row], 'paths': deepcopy(candidate['paths']),
                 'connectors': deepcopy(candidate['connectors']),
                 'syntax_complete': candidate['syntax_complete']}
        if pos + 1 < len(contexts):
            following, following_candidate = contexts[pos + 1], candidates[pos + 1]
            if (row['suffix_section'] and row['suffix_section'] == following['prefix_section']
                    and following['start'] < row['end'] <= following['paragraph_start']
                    and text[row['end']:following['paragraph_start']].isspace()
                    and len(candidate['paths']) == 1 and len(candidate['paths'][0]) == 1
                    and level(candidate['paths'][0][0]) == 1
                    and len(following_candidate['paths']) == 1 and len(following_candidate['paths'][0]) == 1
                    and level(following_candidate['paths'][0][0]) == 0
                    and not candidate['connectors'] and not following_candidate['connectors']
                    and row['enclosing_header'] == following['enclosing_header']
                    and not row['statute'] and not following['statute']):
                group['contexts'].append(following)
                group['paths'] = [following_candidate['paths'][0] + candidate['paths'][0]]
                group['syntax_complete'] = candidate['syntax_complete'] and following_candidate['syntax_complete']
                pos += 1
        out.append(group)
        pos += 1
    return out


def resolve(group, nodes):
    first = group['contexts'][0]
    if first['statute']:
        return {'status': 'EXTERNAL_STATUTE', 'paths': [], 'targets': [], 'issues': [],
                'reason': 'Statutory text, edition and application require separate evidence'}
    try:
        require(group['syntax_complete'] is True and not any(r['issues'] for r in group['contexts']),
                'Unresolved citation syntax')
        header = first['enclosing_header']
        require(header is not None, 'Citation has no reviewed enclosing section')
        section = first['explicit_section'] or header['section']
        source_nodes = [n for n in nodes if n['document'] == header['document'] and n['context'] == header['context']
                        and n['section_start'] == header['start'] and n['start'] <= first['paragraph_start'] < n['end']]
        parent = max(source_nodes, key=lambda n: len(n['path']))['path'] if source_nodes else []
        if section != header['section']:
            parent = []
        paths = expanded_paths(group['paths'], group['connectors'], parent)
        targets = []
        for path in paths:
            matches = [n for n in nodes if n['document'] == header['document'] and n['context'] == header['context']
                       and n['section'] == section and n['path'] == path]
            require(len(matches) == 1, 'Missing or nonunique structural address')
            targets.append(deepcopy(matches[0]))
        return {'status': 'STRUCTURAL_ADDRESS', 'section': section, 'paths': paths, 'targets': targets,
                'issues': [], 'reason': 'Unique printed container in the declared hierarchy; legal meaning remains separate'}
    except ValueError as error:
        return {'status': 'UNRESOLVED', 'paths': [], 'targets': [], 'issues': [str(error)],
                'reason': 'The declared grammar does not establish a unique structural address'}


def content(products, ordinary):
    text, pieces, raw, nodes, issues = source_model(products, ordinary)
    groups = compound_groups(text, ordinary['reference_scope_context']['contexts'],
                             ordinary['paragraph_reference_discovery']['discovery']['candidates'])
    rows = []
    for group in groups:
        contexts = group['contexts']
        start, end = min(r['start'] for r in contexts), max(r['end'] for r in contexts)
        row = {'paragraph_starts': [r['paragraph_start'] for r in contexts], 'start': start, 'end': end,
               'raw': text[start:end], 'statute': contexts[0]['statute'],
               'source_projection': projection(text, pieces, raw, start, end),
               'connectors': group['connectors'], 'logical_meaning_established': False,
               'legal_meaning_established': False, 'review_required': True, **resolve(group, nodes)}
        if issues and row['status'] == 'STRUCTURAL_ADDRESS':
            # Unsupported heading syntax could change the hierarchy or boundaries.
            row.update(status='UNRESOLVED', targets=[], paths=[], issues=['Unsupported source hierarchy'])
        rows.append(row)
    return {'references': rows, 'index': nodes, 'index_issues': issues,
            'prior_answer_preserved': True, 'original_semantic_targets_preserved': True,
            'automatic_legal_interpretation': False, 'legal_truth_established': False,
            'whole_task_complete': False, 'general_recall_established': False,
            'supported_domain': 'Declared numeric/letter/Roman hierarchy in source-bound selected German text',
            'remaining': ['statutory edition and applicability', 'definition-specific semantic subsets',
                          'unlisted grammar and implicit anaphora', 'general definition discovery',
                          'original source-to-answer acceptance']}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'specification_sha256',
            'whole_task_complete', 'legal_truth_established'}
    fields(profile, keys, keys)
    spec = json.loads(Path(__file__).with_name('reference_addresses_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec) == SPEC_SHA256, 'Address specification differs')
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
            and profile['specification_sha256'] == SPEC_SHA256
            and profile['products_sha256'] == digest(products) == spec['products_sha256']
            and profile['ordinary_answer_sha256'] == digest(ordinary) == spec['ordinary_answer_sha256']
            and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            and KEY not in ordinary and profile['whole_task_complete'] is False
            and profile['legal_truth_established'] is False, 'Pinned structural address baseline differs')
    return {KEY: {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
                  'ordinary_answer_sha256': digest(ordinary), **content(products, ordinary)}}


def verify_answer(actual, ordinary, profile, products, root, *, expected_profile_sha256):
    expected = {**ordinary, **evaluate(products, ordinary, profile, root,
                                      expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256'] = digest({k: v for k, v in expected.items() if k != 'report_sha256'})
    require(actual == expected, 'Complete structural address answer differs')
    return {'status': 'PASS', 'whole_answer_equal': True, 'legal_truth_established': False}
