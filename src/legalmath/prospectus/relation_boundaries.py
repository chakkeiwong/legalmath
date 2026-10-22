"""Optional geometric limits on v2 suggestions, preserving original lineage."""
from collections import defaultdict
from copy import deepcopy
from statistics import median

from .successor.contracts import digest
from .successor.occurrences import anchor
from .successor.relation_discovery import discover, SCOPED_PROFILE

PROFILE = 'geometrically-bounded-suggestions.v3'


def _connected(values, units, height):
    """Require one horizontal component, without guessing which text is noise."""
    boxes = sorted((units[a['unit']]['bbox'] for a in values), key=lambda b: b[0])
    right = boxes[0][2]
    for box in boxes[1:]:
        if box[0] - right > 2.25 * height:
            return False
        right = max(right, box[2])
    return True


def discover_bounded(graph):
    """Derive suggestions from raw graph only; no review labels are consumed.

    Unknown marker text is stopping evidence, not a corrected transcription.
    Every baseline suggestion receives unchanged/bounded/abstained lineage.
    Legal interpretation and accepted relations remain outside this API.
    """
    original = discover(graph, SCOPED_PROFILE)
    units = {u['id']: u for u in graph['units']}
    pages = defaultdict(list)
    for unit in units.values():
        if any(c.isalnum() for c in unit['raw']):
            pages[(unit['document'], unit['source_sha256'], unit['page'])].append(unit)
    candidates, lineage = [], []
    for old in original['candidates']:
        row = {'original_id': old['id'], 'original_sha256': digest(old),
               'status': 'UNCHANGED', 'candidate_id': old['id'],
               'removed': [], 'boundary': None, 'reason': 'Existing suggestion preserved'}
        candidate = deepcopy(old)
        if 'row_marker' in old:
            marker = units[old['row_marker']['unit']]
            content = pages[(marker['document'], marker['source_sha256'], marker['page'])]
            height = median(u['bbox'][3] - u['bbox'][1] for u in content)
            x0, y0, x1, _ = marker['bbox']
            # Both a same-column malformed marker and an outdented parent label
            # stop the row. Text correction/recognition is intentionally absent.
            boundaries = [u for u in content if u['bbox'][1] > y0 + .5*height
                          and u['bbox'][0] <= x1 and u['bbox'][2] >= x0 - .5*height]
            boundary = min(boundaries, key=lambda u: (u['bbox'][1],u['bbox'][0],u['id'])) if boundaries else None
            if boundary:
                stop = boundary['bbox'][1] - .5*height
                removed = [a for side in ('from','to') for a in old[side]
                           if units[a['unit']]['bbox'][1] >= stop]
                if removed:
                    row.update(boundary=anchor(boundary), removed=removed)
                    for side in ('from','to'):
                        candidate[side] = [a for a in old[side] if a not in removed]
                    if old['kind'] == 'qualifies':
                        # Trimming a qualification can change its meaning even
                        # when the surviving fragment is grammatically complete.
                        row.update(status='ABSTAINED', candidate_id=None,
                                   reason='Boundary intersects qualification; no qualifier clipping')
                    elif (not candidate['from'] or not candidate['to'] or
                          not candidate['from'][-1]['quote'].rstrip().endswith(':')):
                        row.update(status='ABSTAINED', candidate_id=None,
                                   reason='Boundary leaves an incomplete label or value')
                    else:
                        candidate['boundary_evidence'] = anchor(boundary)
                        candidate['boundary_profile'] = PROFILE
                        candidate['id'] = 'relation-candidate:' + digest({k:v for k,v in candidate.items() if k != 'id'})
                        row.update(status='BOUNDED', candidate_id=candidate['id'],
                                   reason='Both endpoints stop before next marker-column source unit')
            if row['status'] != 'ABSTAINED' and not _connected(candidate['to'], units, height):
                row.update(status='ABSTAINED', candidate_id=None,
                           reason='Disconnected value components; no OCR correction inferred')
        if row['status'] != 'ABSTAINED':
            candidates.append(candidate)
        lineage.append(row)
    return {'version': PROFILE, 'source_graph_sha256': digest(graph),
            'baseline_discovery_sha256': digest(original),
            'candidates': sorted(candidates,key=lambda c:c['id']),
            'lineage': sorted(lineage,key=lambda r:r['original_id']),
            'diagnostics': deepcopy(original['diagnostics']),
            'accepted_relations': [], 'legal_scope_inferred': False,
            'limits': ['Optional exposed-development row limiter; no independent acceptance',
                       'Disconnected legitimate values can abstain; recall is not established',
                       'Raw OCR unchanged; transcription concerns persist',
                       'Existing v2 recognition and geometry limits remain']}


def consume_with_suggestions(products, root, bank=None):
    """Reconsume actual products and attach separate optional suggestions."""
    from .successor.service import consume
    answer = consume(products, root, bank, include_artifacts=True)
    suggestions = discover_bounded(products['P1']['payload']['graph'])
    return {'answer': answer, 'suggestions': suggestions,
            'relation_admission_performed': False, 'independent_legal_acceptance': False}
