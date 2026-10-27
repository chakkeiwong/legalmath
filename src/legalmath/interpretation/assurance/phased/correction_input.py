"""Opt-in exact ordered source-gap table for answer correction input."""
from copy import deepcopy
from legalmath.canonical import canonical, digest
from ..bounded_context import require

PROFILE = 'exact-correction-gap-occurrences.v1'
FIELD = 'correction_input_profile'
TABLE = 'correction_gap_table'
INSTRUCTIONS = ('payload.retained_source_gaps.gap_occurrences is an ordered list of integer '
    'indices into correction_gap_table.values. Replace each index with that complete value. '
    'Every occurrence, duplicate, status and document identity remains present; repetition '
    'is not independent evidence. Never treat a source gap as resolved by its encoding. '
    'The expansion hash binds the original complete list. All answer text and other inputs '
    'are unchanged; the ordinary response schema and legal validators still apply.')

def enabled(request):
    profile = request.get(FIELD)
    if profile is None:
        return False
    require(profile == PROFILE and request.get('task') == 'CORRECT_REVIEWED_ANSWER'
        and request.get('downstream_input_profile') == 'exact-downstream-input-32k.v1',
        'Correction gap profile outside its task', 'E_AUTHORITY')
    return True

def pack(wire):
    if not enabled(wire):
        return wire
    require(TABLE not in wire, 'Reserved correction gap table', 'E_INTEGRITY')
    gaps = wire['payload']['retained_source_gaps']
    require(isinstance(gaps, list) and all(isinstance(g, dict) and
        set(g) == {'index_hash', 'locator', 'status'} for g in gaps),
        'Unexpected retained source gap shape', 'E_INTEGRITY')
    values, identities, occurrences = [], {}, []
    for gap in gaps:
        key = canonical(gap)
        if key not in identities:
            identities[key] = len(values)
            values.append(deepcopy(gap))
        occurrences.append(identities[key])
    out = deepcopy(wire)
    out['payload']['retained_source_gaps'] = {'gap_occurrences': occurrences}
    out[TABLE] = {'profile': PROFILE, 'values': values, 'expanded_sha256': digest(gaps),
                  'instructions': INSTRUCTIONS}
    require(expand(out) == wire, 'Correction gap encoding changed content', 'E_INTEGRITY')
    return out if len(canonical(out)) < len(canonical(wire)) else wire

def expand(wire):
    require(enabled(wire), 'Missing correction gap profile', 'E_AUTHORITY')
    if TABLE not in wire:
        require(isinstance(wire['payload']['retained_source_gaps'], list),
                'Missing correction gap table', 'E_INTEGRITY')
        return deepcopy(wire)
    out = deepcopy(wire)
    table = out.pop(TABLE)
    require(set(table) == {'profile','values','expanded_sha256','instructions'}
        and table['profile'] == PROFILE and table['instructions'] == INSTRUCTIONS,
        'Changed correction gap semantics', 'E_INTEGRITY')
    selector = out['payload']['retained_source_gaps']
    require(isinstance(selector,dict) and set(selector) == {'gap_occurrences'},
        'Invalid correction gap selector', 'E_INTEGRITY')
    values, indices = table['values'], selector['gap_occurrences']
    require(isinstance(values,list) and isinstance(indices,list) and
        all(type(i) is int and 0 <= i < len(values) for i in indices) and
        set(indices) == set(range(len(values))), 'Invalid or unused correction gap index', 'E_INTEGRITY')
    require(len({canonical(v) for v in values}) == len(values),
        'Duplicate correction gap table value', 'E_INTEGRITY')
    gaps = [deepcopy(values[i]) for i in indices]
    require(digest(gaps) == table['expanded_sha256'], 'Changed correction gap occurrences', 'E_INTEGRITY')
    out['payload']['retained_source_gaps'] = gaps
    return out

def apply(prepared):
    if not enabled(prepared['original_request']):
        return prepared
    out = deepcopy(prepared)
    out['request'] = pack(out['request'])
    return out
