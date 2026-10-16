"""Optional exact input tables for typed accounts; no model calls or summaries."""
from collections import Counter
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require

PROFILE = 'exact-account-input-tables-16k.v1'
FIELDS = ('account_source_texts', 'account_input_citations', 'account_response_spans',
          'account_table_instructions')
INSTRUCTIONS = (
    'This account request uses exact input tables. In records, text.source_text_slice '
    'selects [block_id, start_codepoint, end_codepoint] from account_source_texts. '
    'The end is exclusive; read that complete substring as this record text. '
    'An input_citation selects its complete citation from account_input_citations. '
    'Repeated selections preserve repeated occurrences and their roles; they are not '
    'additional authorities. account_response_spans maps each offered span_id to '
    '[record_id, start_codepoint, end_codepoint, legal_locator], with offsets in '
    'the expanded record text. Use those span_ids for the response. Every source '
    'text and partial reading is present in this request. Partial readings remain '
    'proposals, not source authority; assess their combined support and contrary evidence.')


def citation(node):
    return (isinstance(node, dict) and 'quote' in node
        and ('record_id' in node or 'unit_id' in node)
        and set(node) <= {'record_id', 'unit_id', 'quote', 'locator'})


def pack(wire):
    require(not any(k in wire for k in FIELDS), 'Account input table field collision')
    result = deepcopy(wire)
    groups, unit_hashes, texts = {}, {}, {}
    for record in result.get('records', []):
        if record.get('kind') != 'source':
            continue
        unit = record['unit_id']
        require(unit not in unit_hashes or unit_hashes[unit] == record['unit_hash'],
            'Conflicting source unit identities')
        unit_hashes[unit] = record['unit_hash']
        require(isinstance(record['text'], str) and type(record['start']) is int
            and type(record['end']) is int and 0 <= record['start'] < record['end']
            and len(record['text']) == record['end'] - record['start'],
            'Invalid source text interval')
        require(record['id'] not in texts, 'Duplicate delivered source record')
        texts[record['id']] = record['text']
        groups.setdefault(unit, []).append(record)
    blocks = {}
    for records in groups.values():
        merged = []
        for record in sorted(records, key=lambda r: (r['start'], r['end'])):
            start, end, text = record['start'], record['end'], record['text']
            if merged and start <= merged[-1]['end']:
                previous = merged[-1]
                overlap = min(previous['end'], end) - start
                offset = start - previous['start']
                require(previous['text'][offset:offset + overlap] == text[:overlap],
                    'Conflicting overlapping source text')
                previous['text'] += text[overlap:]
                previous['end'] = max(previous['end'], end)
                previous['records'].append(record)
            else:
                merged.append({'start': start, 'end': end, 'text': text, 'records': [record]})
        for block in merged:
            key = 't' + str(len(blocks))
            blocks[key] = block['text']
            for record in block['records']:
                record['text'] = {'source_text_slice': [key,
                    record['start'] - block['start'], record['end'] - block['start']]}
    result['account_source_texts'] = blocks
    spans = {}
    for position, row in enumerate(result.pop('response_spans')):
        require(set(row) == {'span_id', 'record_id', 'start_codepoint', 'end_codepoint',
            'legal_locator', 'starts_with'} and row['span_id'] == 's' + str(position),
            'Unknown or duplicate response span shape')
        text = texts[row['record_id']]
        start, end = row['start_codepoint'], row['end_codepoint']
        require(0 <= start < end <= len(text) and row['starts_with'] == text[start:min(start + 80, end)],
            'Response span changed its source prefix')
        spans[row['span_id']] = [row['record_id'], start, end, row['legal_locator']]
    result['account_response_spans'] = spans
    counts, objects = Counter(), {}

    def count(node):
        if isinstance(node, dict):
            require(set(node) != {'input_citation'}, 'Reserved citation reference collision')
            if citation(node):
                identity = digest(node)
                counts[identity] += 1
                require(identity not in objects or objects[identity] == node, 'Citation identity collision')
                objects[identity] = node
            else:
                for child in node.values():
                    count(child)
        elif isinstance(node, list):
            for child in node:
                count(child)
    count(result.get('payload'))
    names = {key: 'q' + str(i) for i, key in enumerate(k for k in counts if counts[k] > 1)}

    def replace(node):
        if isinstance(node, dict):
            if citation(node) and digest(node) in names:
                return {'input_citation': names[digest(node)]}
            return {key: replace(child) for key, child in node.items()}
        if isinstance(node, list):
            return [replace(child) for child in node]
        return node
    if 'payload' in result:
        result['payload'] = replace(result['payload'])
    result['account_input_citations'] = {name: deepcopy(objects[key]) for key, name in names.items()}
    result['account_table_instructions'] = INSTRUCTIONS
    require(expand(result) == wire, 'Account input tables changed original content', 'E_INTEGRITY')
    return result


def expand(packed):
    result = deepcopy(packed)
    require(result.pop('account_table_instructions') == INSTRUCTIONS, 'Changed account table semantics')
    blocks = result.pop('account_source_texts')
    spans = result.pop('account_response_spans')
    citations = result.pop('account_input_citations')
    used_blocks, texts = set(), {}
    for record in result.get('records', []):
        if record.get('kind') != 'source':
            continue
        require(set(record['text']) == {'source_text_slice'}, 'Invalid source text reference')
        key, start, end = record['text']['source_text_slice']
        require(key in blocks and type(start) is int and type(end) is int
            and 0 <= start < end <= len(blocks[key]), 'Missing or invalid source text block')
        record['text'] = blocks[key][start:end]
        require(len(record['text']) == record['end'] - record['start'], 'Source slice changed length')
        texts[record['id']] = record['text']
        used_blocks.add(key)
    require(used_blocks == set(blocks), 'Unassigned source text block')
    result['response_spans'] = []
    require(set(spans) == {'s' + str(i) for i in range(len(spans))}, 'Changed response span identities')
    for key in ('s' + str(i) for i in range(len(spans))):
        rid, start, end, locator = spans[key]
        require(rid in texts and type(start) is int and type(end) is int
            and 0 <= start < end <= len(texts[rid]), 'Invalid offered response span')
        result['response_spans'].append({'span_id': key, 'record_id': rid,
            'start_codepoint': start, 'end_codepoint': end, 'legal_locator': locator,
            'starts_with': texts[rid][start:min(start + 80, end)]})
    used_citations = set()

    def restore(node):
        if isinstance(node, dict):
            if set(node) == {'input_citation'}:
                key = node['input_citation']
                require(key in citations and citation(citations[key]), 'Missing input citation')
                used_citations.add(key)
                return deepcopy(citations[key])
            return {key: restore(child) for key, child in node.items()}
        if isinstance(node, list):
            return [restore(child) for child in node]
        return node
    if 'payload' in result:
        result['payload'] = restore(result['payload'])
    require(used_citations == set(citations), 'Unassigned input citation')
    return result


def apply(prepared):
    original = prepared['original_request']
    if original.get('account_input_profile') is None:
        return prepared
    from . import account_encoding
    require(original['account_input_profile'] in (PROFILE, account_encoding.PROFILE) and
        original.get('account_contract') == 'typed-requirement-account.v1' and
        original['task'] == 'ASSESS_ORIGINAL_REQUIREMENT' and
        prepared['protocol'] == 'bounded-indexed-assertions.v2',
        'Account input profile outside its declared contract')
    result = deepcopy(prepared)
    result['request'] = pack(prepared['request'])
    if original['account_input_profile'] == account_encoding.PROFILE:
        packed = account_encoding.pack({'request': result['request'], 'response_schema': result['schema']})
        result['request'], result['schema'] = packed['request'], packed['response_schema']
    return result


COMBINATION_INPUT_TOKENS = 16384
CAPACITY_PROFILE = 'complete-two-child-account-32k.v1'
CAPACITY_INPUT_TOKENS = 32768


def validate_capacity(request, profile):
    """Select a finite optional envelope without changing content or encoding."""
    from .account_encoding import PROFILE as STRUCTURE_PROFILE
    payload = request.get('payload')
    require(profile == CAPACITY_PROFILE
        and request.get('account_input_profile') == STRUCTURE_PROFILE
        and request.get('account_contract') == 'typed-requirement-account.v1'
        and request.get('response_reference_profile') == 'bounded-indexed-assertions.v2'
        and request.get('task') == 'ASSESS_ORIGINAL_REQUIREMENT'
        and isinstance(payload, dict) and 'original_assignment' in payload
        and isinstance(payload.get('partial_source_readings'), list)
        and len(payload['partial_source_readings']) == 2
        and all(isinstance(child, dict) and child for child in payload['partial_source_readings']),
        'Account capacity selection outside its exact two-child contract', 'E_AUTHORITY')


def input_token_limit(request, limits):
    """Only an explicit typed combination can use the larger, optional bound."""
    if request.get('downstream_input_profile') is not None:
        from .downstream_input import input_token_limit as downstream_limit
        return downstream_limit(request, limits)
    capacity = request.get('account_capacity_profile')
    if capacity is not None:
        validate_capacity(request, capacity)
    if request.get('account_input_profile') is None:
        return limits.input_tokens
    from .account_encoding import PROFILE as STRUCTURE_PROFILE
    require(request['account_input_profile'] in (PROFILE, STRUCTURE_PROFILE) and
        request.get('account_contract') == 'typed-requirement-account.v1' and
        request.get('response_reference_profile') == 'bounded-indexed-assertions.v2' and
        request.get('task') == 'ASSESS_ORIGINAL_REQUIREMENT',
        'Account input bound outside its explicit scope', 'E_AUTHORITY')
    require(limits.input_tokens == 12000, 'Account capacity profile has a different baseline', 'E_AUTHORITY')
    if capacity is not None:
        return CAPACITY_INPUT_TOKENS
    payload = request.get('payload')
    if isinstance(payload, dict) and 'partial_source_readings' in payload:
        require('original_assignment' in payload and isinstance(payload['partial_source_readings'], list)
            and len(payload['partial_source_readings']) == 2,
            'Account capacity profile requires an exact two-child combination', 'E_AUTHORITY')
        return COMBINATION_INPUT_TOKENS
    return limits.input_tokens
