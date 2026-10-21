"""Lossless sharing of source text duplicated in optional tool requests."""
from copy import deepcopy
from ..bounded_context import require

TASKS = frozenset({'GENERATE_SOURCE_WARRANTED_CANDIDATES', 'STRUCTURED_CRITICISM'})
FIELD = 'tool_source_text_instructions'
INSTRUCTIONS = (
    'In source_packet.units, text.source_text_slice selects the complete source '
    'text from account_source_texts using [block_id, start_codepoint, end_codepoint]. '
    'The end is exclusive. It is exactly the same text as the matching source '
    'record, with the same unit_id. Expand every such selection before interpreting '
    'the packet. No source text or candidate has been removed.')


def pack(wire):
    if wire.get('task') not in TASKS:
        return wire
    require(FIELD not in wire, 'Reserved tool text instruction field', 'E_INTEGRITY')
    out = deepcopy(wire)
    records = {r['id']: r for r in out.get('records', [])}
    require(len(records) == len(out.get('records', [])), 'Duplicate tool source record')
    units = out['source_packet']['units']
    require(len(units) == len({u['unit_id'] for u in units})
        and set(records) == {u['unit_id'] for u in units}, 'Tool source populations differ')
    for unit in units:
        record = records[unit['unit_id']]
        selector = record['text']
        require(record.get('kind') == 'source' and isinstance(selector, dict)
            and set(selector) == {'source_text_slice'}, 'Missing exact tool source selector')
        key, start, end = selector['source_text_slice']
        require(unit['text'] == out['account_source_texts'][key][start:end],
            'Tool packet text differs from source record', 'E_INTEGRITY')
        unit['text'] = deepcopy(selector)
    out[FIELD] = INSTRUCTIONS
    require(expand(out) == wire, 'Tool sharing changed request content', 'E_INTEGRITY')
    return out


def expand(wire):
    out = deepcopy(wire)
    require(out.pop(FIELD) == INSTRUCTIONS, 'Changed tool text semantics', 'E_INTEGRITY')
    for unit in out['source_packet']['units']:
        selector = unit['text']
        require(isinstance(selector, dict) and set(selector) == {'source_text_slice'},
            'Invalid tool source selector')
        key, start, end = selector['source_text_slice']
        require(key in out['account_source_texts'] and type(start) is int and type(end) is int
            and 0 <= start < end <= len(out['account_source_texts'][key]), 'Invalid tool text range')
        unit['text'] = out['account_source_texts'][key][start:end]
    return out
