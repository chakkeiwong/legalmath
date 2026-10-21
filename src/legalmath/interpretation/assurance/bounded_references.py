"""Adapt bounded records to the existing request-bound source-span protocol.

The wire uses short selection IDs; expansion uses source_references.resolve and
retains the original response contract. Requirement observations have their own
schema and cannot be expanded into legal-source quotations.
"""
from copy import deepcopy

from jsonschema import validate, Draft202012Validator

from legalmath.canonical import canonical, digest
from .bounded_context import require
from . import source_references

PROTOCOL = 'bounded-source-references.v5'


def prepare(request, schema):
    selected_protocol = request.get("response_reference_profile")
    require(selected_protocol in (None, "bounded-indexed-assertions.v2"), "Unknown response-reference profile")
    protocol = selected_protocol or PROTOCOL
    binding = digest({'protocol': protocol, 'request': request, 'schema': schema})
    sources = [r for r in request.get('records', []) if r.get('kind') == 'source']
    if 'source_packet' in request:
        units = deepcopy(request['source_packet']['units'])
    else:
        units = [{'unit_id': r['id'], 'text': r['text'], 'normative': r['normative'],
                  'locator': r['locator'], 'span': None} for r in sources]
    packet = {'source_key': 'bounded.references', 'authority': 'RETAINED_SOURCE',
              'selected_slice': 'Exact delivered source fragments', 'units': units,
              'dependencies': [], 'family_ids': ['scope']}
    references = source_references.table(packet, binding, chunk_size=256) if units else None
    selectable = [row for row in references['spans'] if next(u['text'] for u in units
        if u['unit_id'] == row['unit_id']).count(next(u['text'] for u in units
        if u['unit_id'] == row['unit_id'])[row['start_codepoint']:row['end_codepoint']]) == 1] if units else []
    # Optional protocol only: a short numbered provision can fall across the
    # inherited fixed-width spans. Offer its exact unique range when no existing
    # selection is wholly inside that provision. Never modify the v1 span table.
    extra_spans = {}
    if selected_protocol:
        texts = {u["unit_id"]: u["text"] for u in units}
        available = {r["index_hash"] for r in request.get("available_source_indexes", [])}
        ranges = sorted({(b["record_id"], s["start"], s["end"], s["locator"])
            for b in request.get("verified_locator_bindings", [])
            if b["index_hash"] in available and b["record_id"] in texts
            for s in b.get("quote_ranges", [])})
        for record_id, start, end, locator in ranges:
            text = texts[record_id]
            require(type(start) is int and type(end) is int and
                    0 <= start < end <= len(text), "Invalid indexed quote range")
            if not locator or text.count(text[start:end]) != 1:
                continue
            if any(r["unit_id"] == record_id and start <= r["start_codepoint"]
                    and r["end_codepoint"] <= end for r in selectable):
                continue
            row = {"unit_id": record_id, "start_codepoint": start, "end_codepoint": end}
            span_id = "indexed." + digest({"protocol": protocol, "binding": binding, **row})
            if span_id not in extra_spans:
                extra_spans[span_id] = row
                selectable.append({"span_id": span_id, **row})
    selections = {f's{i}': row['span_id'] for i, row in enumerate(selectable)}
    # One selection is one complete contiguous quote. Cross-record support is
    # expressed by separate citation objects, never by joining span IDs.
    locators = {}
    for alias, row in zip(selections, selectable):
        matches = {span['locator'] for binding in request.get('verified_locator_bindings', [])
            if binding['record_id'] == row['unit_id']
            for span in binding.get('quote_ranges', [])
            if span['start'] <= row['start_codepoint'] and row['end_codepoint'] <= span['end']}
        locators[alias] = next(iter(matches)) if len(matches) == 1 else ''
    available_indexes = {row['index_hash'] for row in request.get('available_source_indexes', [])}
    assertion_indexes = sorted({binding['index_hash']
        for binding in request.get('verified_locator_bindings', [])
        if binding['index_hash'] in available_indexes
        for alias, row in zip(selections, selectable)
        if locators[alias] and binding['record_id'] == row['unit_id']
        and any(span['locator'] == locators[alias] and
                span['start'] <= row['start_codepoint'] and row['end_codepoint'] <= span['end']
                for span in binding.get('quote_ranges', []))})
    assertion_choices = {}
    if selected_protocol and schema.get("properties", {}).get("assertion_bindings", {}).get("maxItems") != 0:
        for alias, row in zip(selections, selectable):
            if not locators[alias]:
                continue
            text = next(u["text"] for u in units if u["unit_id"] == row["unit_id"])
            owned = sorted({b["index_hash"] for b in request.get("verified_locator_bindings", [])
                if b["index_hash"] in available_indexes and b["record_id"] == row["unit_id"]
                and any(s["locator"] == locators[alias] and s["start"] <= row["start_codepoint"]
                    and row["end_codepoint"] <= s["end"] for s in b.get("quote_ranges", []))})
            for index_hash in owned:
                assertion_choices["a"+str(len(assertion_choices))] = {"span_id":alias,
                    "index_hash":index_hash,"citation":{"record_id":row["unit_id"],
                        "quote":text[row["start_codepoint"]:row["end_codepoint"]],"locator":locators[alias]}}
    gaps = {f'g{i}': deepcopy(row) for i, row in
            enumerate(request.get('unverified_source_locators', []))}
    observations = {}
    def observe(record_id, value, path=()):
        if isinstance(value, dict):
            for key, child in value.items(): observe(record_id, child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value): observe(record_id, child, (*path, index))
        elif isinstance(value, str) and value:
            observations['m'+str(len(observations))] = {
                'record_id':record_id, 'path':list(path), 'quote':value}
    for record in request.get('records', []):
        if record.get('kind') != 'source' and 'value' in record:
            observe(record['id'], record['value'])
    identities = list(dict.fromkeys([r['id'] for r in request.get('records', [])] +
        request.get('required_considered', []) + [u['unit_id'] for u in units]))
    aliases = {f'r{i}': value for i, value in enumerate(identities)}
    reverse = {v: k for k, v in aliases.items()}
    identity_keys = {'id', 'record_id', 'unit_id', 'considered', 'required_considered', 'source_unit_ids'}

    def encode(node, field=None):
        if isinstance(node, dict): return {k: encode(v, k) for k, v in node.items()}
        if isinstance(node, list): return [encode(v, field) for v in node]
        if isinstance(node, str) and field in identity_keys: return reverse.get(node, node)
        return node

    def decode(node, field=None):
        if isinstance(node, dict): return {k: decode(v, k) for k, v in node.items()}
        if isinstance(node, list): return [decode(v, field) for v in node]
        if isinstance(node, str) and field in identity_keys: return aliases.get(node, node)
        return node

    shapes = {}
    def wire_shape(shape, field=None):
        if not isinstance(shape, dict): return deepcopy(shape)
        properties = shape.get('properties', {})
        if selected_protocol and set(properties) == {"path", "index_hash", "citation"}:
            result = {"type":"object","additionalProperties":False,"properties":{
                "path":deepcopy(properties["path"]),"assertion_id":{"type":"string",
                    "enum":list(assertion_choices) or ["NO_INDEXED_ASSERTION_AVAILABLE"]}},
                "required":["path","assertion_id"]}
            shapes[digest(shape)] = deepcopy(result)
            return result
        if field == 'considered' and shape.get('type') == 'array':
            required = request.get('required_considered', [])
            if not required:
                return {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 0}
            slots = {f'c{i}': {'type': 'string', 'enum': [reverse[rid]]}
                     for i, rid in enumerate(required)}
            return {'type': 'object', 'additionalProperties': False,
                    'properties': slots, 'required': list(slots)}
        if {'verdict', 'issues', 'support'} <= set(properties):
            # The outer output-schema root must stay an object. Put the
            # verdict-specific invariant in a nested union instead.
            rest = {key: wire_shape(value, key) for key, value in properties.items()
                    if key not in {'verdict', 'issues', 'support'}}
            decision = {key: wire_shape(properties[key], key)
                        for key in ('verdict', 'issues', 'support')}
            branches = []
            for verdict in properties['verdict']['enum']:
                selected = deepcopy(decision)
                selected['verdict']['enum'] = [verdict]
                if verdict == 'ACCEPT':
                    selected['issues']['maxItems'] = 0
                    selected['support']['minItems'] = 1
                branches.append({'type': 'object', 'additionalProperties': False,
                                 'properties': selected, 'required': list(selected)})
            result = {'type': 'object', 'additionalProperties': False,
                      'properties': {**rest, 'review': {'anyOf': branches}},
                      'required': [*rest, 'review']}
            shapes[digest(shape)] = deepcopy(result)
            return result
        if set(properties) == {'statement', 'record_id', 'path', 'quote'}:
            result = {'type':'object','additionalProperties':False,
                'properties':{'statement':deepcopy(properties['statement']),
                    'observation_id':{'type':'string','enum':list(observations) or ['NO_OBSERVATION_AVAILABLE']}},
                'required':['statement','observation_id']}
            shapes[digest(shape)] = deepcopy(result)
            return result
        if 'quote' in properties and set(properties) <= {'record_id', 'unit_id', 'quote', 'locator'}:
            result = {'type': 'object', 'additionalProperties': False,
                    'properties': {'span_id': {'type': 'string',
                        'enum': list(selections) or ['NO_SOURCE_AVAILABLE']}},
                    'required': ['span_id']}
            shapes[digest(shape)] = deepcopy(result)
            return result
        if set(properties) == {'index_hash', 'locator', 'status'}:
            result = {'type': 'object', 'additionalProperties': False,
                      'properties': {'gap_id': {'type': 'string',
                          'enum': list(gaps) or ['NO_SOURCE_GAP_AVAILABLE']}}, 'required': ['gap_id']}
            shapes[digest(shape)] = deepcopy(result)
            return result
        result = deepcopy(shape)
        if 'properties' in shape:
            result['properties'] = {k: wire_shape(v, k) for k, v in properties.items()}
        if '$defs' in shape: result['$defs'] = {k: wire_shape(v) for k, v in shape['$defs'].items()}
        if 'items' in shape: result['items'] = wire_shape(shape['items'], field)
        if field == 'source_gaps' and not gaps:
            result['maxItems'] = 0
        if field == 'observations' and not observations:
            result['maxItems'] = 0
        if field == 'assertion_bindings' and not assertion_indexes:
            result['maxItems'] = 0
        if set(properties) == {'path', 'index_hash', 'citation'}:
            result['properties']['index_hash']['enum'] = assertion_indexes or ['NO_INDEXED_SOURCE_AVAILABLE']
        for key in ('anyOf', 'oneOf', 'allOf'):
            if key in shape: result[key] = [wire_shape(v, field) for v in shape[key]]
        if field in identity_keys and shape.get('type') == 'string':
            if 'enum' in shape: result['enum'] = [reverse.get(x, x) for x in shape['enum']]
            elif aliases: result['enum'] = list(aliases)
        if set(properties) == {'id', 'status', 'findings', 'open_dependencies'}:
            # Offer the same invariant enforced by ContextRoute: an unsupported
            # finding is unresolved, even when another finding is supported.
            proposed, unresolved = deepcopy(result), deepcopy(result)
            proposed['properties']['status']['enum'] = ['PROPOSED']
            proposed['properties']['findings']['minItems'] = 1
            proposed['properties']['findings']['items']['properties']['support']['minItems'] = 1
            unresolved['properties']['status']['enum'] = ['UNRESOLVED']
            result = {'anyOf':[proposed, unresolved]}
        shapes[digest(shape)] = deepcopy(result)
        return result

    wire = encode(request)
    require(canonical(decode(wire)) == canonical(request), 'Alias transport changed original request')
    # The source text is already delivered in full. Repeated quotations in an
    # answer/review payload can be represented losslessly by codepoint ranges.
    # Observation strings and quotations outside the delivered source stay intact.
    source_text = {reverse[u['unit_id']]: u['text'] for u in units}
    def compact(node):
        if isinstance(node, dict):
            rid = node.get('record_id', node.get('unit_id'))
            quote = node.get('quote')
            if (set(node) <= {'record_id', 'unit_id', 'quote', 'locator'} and
                    isinstance(quote, str) and quote and rid in source_text and
                    source_text[rid].count(quote) == 1):
                start = source_text[rid].index(quote)
                return {**node, 'quote': {'source_slice': {'record_id': rid,
                    'start_codepoint': start, 'end_codepoint': start + len(quote)}}}
            return {k: compact(v) for k, v in node.items()}
        if isinstance(node, list): return [compact(v) for v in node]
        return node
    def expand(node):
        if isinstance(node, dict):
            if set(node) == {'source_slice'}:
                row = node['source_slice']
                return source_text[row['record_id']][row['start_codepoint']:row['end_codepoint']]
            return {k: expand(v) for k, v in node.items()}
        if isinstance(node, list): return [expand(v) for v in node]
        return node
    compacted = compact(wire)
    require(expand(compacted) == wire, 'Compact input changed a quotation')
    wire = compacted
    wire['response_reference_protocol'] = protocol
    wire['response_reference_instructions'] = (
        'Use the short response IDs already shown in records and required_considered. '
        'When the response has considered slots c0, c1 and so on, fill every slot '
        'with its offered required ID. These are the records in this request, '
        'not the considered IDs of a proposed answer being reviewed. '
        'For a review response, choose one review branch: ACCEPT has no issues '
        'and needs source support; report any defect with REJECT or UNRESOLVED. '
        'An input quote represented by source_slice is exactly the substring of the delivered '
        'record text at the supplied start/end codepoints; the end is exclusive. Read that text. '
        'For each legal-source quotation choose exactly one span_id below; never copy '
        'quotation text or invent an ID. Cite separate records with separate citation objects. '
        'Legal locators are supplied by the verified selection; never write a locator label. '
        'For source_gaps choose only a supplied gap_id. An unlisted or uncertain provision '
        'belongs in unresolved/open_dependencies without an invented numbered assertion. '
        'Use assertion_bindings only for numbered legal propositions in your own prose, '
        'with an offered source index and its indexed citation. Leave assertion_bindings '
        'empty when no indexed source is offered or no numbered proposition is made. '
        'Request, input and reference hashes are never legal source indexes. '
        'For metadata observations choose a supplied observation_id, which binds '
        'an exact string field; arrays, booleans and numbers are not quotations. '
        'An observation is never a legal-source citation. Mark a source reading '
        'UNRESOLVED if any finding lacks source support; put missing evidence in open_dependencies. '
        'A source selection proves text identity only, not that it supports your proposition. '
        'Requirement observations are not legal warrants. Keep the complete response below '
        'the stated output limit. If exhaustive findings cannot fit, mark the record UNRESOLVED '
        'and state the specific unfinished analysis in open_dependencies. Do not claim it complete.')
    wire['response_spans'] = [{'span_id': alias, 'record_id': reverse[row['unit_id']],
        'start_codepoint': row['start_codepoint'], 'end_codepoint': row['end_codepoint'],
        'legal_locator': locators[alias],
        'starts_with': next(u['text'] for u in units if u['unit_id'] == row['unit_id'])[
            row['start_codepoint']:min(row['start_codepoint']+80,row['end_codepoint'])]}
        for alias, row in zip(selections, selectable)]
    wire['response_source_gaps'] = [{'gap_id': key, **value} for key, value in gaps.items()]
    wire['response_observations'] = [{'observation_id':key, 'record_id':reverse[value['record_id']],
        'path':value['path'], 'starts_with':value['quote'][:80]} for key,value in observations.items()]
    shape = wire_shape(schema)
    if selected_protocol and assertion_choices:
        wire["response_indexed_assertions"] = [{"assertion_id":key,"index_hash":row["index_hash"],
            "span_id":row["span_id"],"record_id":reverse[row["citation"]["record_id"]],
            "legal_locator":row["citation"]["locator"]} for key,row in assertion_choices.items()]
        wire["response_reference_instructions"] += (" For an assertion binding choose assertion_id from "
            "response_indexed_assertions. The selection fixes its document, exact quote and legal locator. "
            "Its JSON pointer must identify your actual numbered proposition. Ordinary unindexed quote "
            "selections cannot be used as indexed assertions.")
    prepared = {'protocol': protocol, 'binding': binding, 'packet': packet, 'references': references,
            'selections': selections, 'locators': locators, 'gaps': gaps,
            'observations': observations,
            'aliases': aliases, 'request': wire, 'schema': shape,
            'original_request': deepcopy(request),
            'original_schema': deepcopy(schema), 'shapes': shapes,
            **({"assertion_choices":assertion_choices, "extra_spans":extra_spans} if selected_protocol else {})}
    from .phased.account_input import apply
    from .phased.account_instructions import apply as account_instructions
    from .phased.downstream_input import apply as downstream_input
    from .phased.downstream_instructions import apply as downstream_instructions
    from .phased.downstream_edits import apply as downstream_edits
    result = downstream_edits(downstream_instructions(downstream_input(account_instructions(apply(prepared)))))
    if request.get('capacity_profile') is not None:
        from .phased.capacity_policy import annotate
        result['request'] = annotate(result['request'])
    return result


def resolve(value, prepared, *, maximum_bytes):
    require(prepared == prepare(prepared['original_request'], prepared['original_schema']),
            'Response-reference binding changed')
    from .phased.downstream_edits import FIELD, expand
    if FIELD in prepared['original_request']:
        return expand(value, prepared, maximum_bytes=maximum_bytes)
    validate(value, prepared['schema'])
    from .phased.account_encoding import decode_selectors
    value = decode_selectors(value, prepared)
    remaining = maximum_bytes
    def walk(node, shape, field=None):
        nonlocal remaining
        if field == 'considered' and isinstance(node, dict):
            required = prepared['original_request'].get('required_considered', [])
            require(len(node) == len(required), 'Wrong considered-slot population')
            return [prepared['aliases'][node[f'c{i}']] for i in range(len(required))]
        if '$ref' in shape:
            require(shape['$ref'].startswith('#/$defs/'), 'Unsupported response reference')
            return walk(node, prepared['original_schema']['$defs'][shape['$ref'].split('/')[-1]], field)
        if 'anyOf' in shape:
            options = [s for s in shape['anyOf'] if Draft202012Validator(
                {**prepared['shapes'].get(digest(s), s), '$defs': prepared['schema'].get('$defs', {})}).is_valid(node)]
            require(bool(options), 'Invalid response union')
            return walk(node, options[0], field)
        properties = shape.get('properties', {})
        if prepared["protocol"] == "bounded-indexed-assertions.v2" and set(properties) == {"path","index_hash","citation"}:
            choice = prepared["assertion_choices"].get(node["assertion_id"])
            require(choice is not None,"No indexed assertion was offered")
            result = {"path":node["path"],"index_hash":choice["index_hash"],"citation":deepcopy(choice["citation"])}
            remaining -= len(canonical(result))
            require(remaining >= 0, "Assertion expansion exceeds output bound", "E_RESOURCE_LIMIT")
            return result
        if isinstance(node, dict) and {'verdict', 'issues', 'support'} <= set(properties):
            require('review' in node, 'Missing nested review decision')
            node = {**{key: item for key, item in node.items() if key != 'review'},
                    **node['review']}
        if isinstance(node, dict) and set(properties) == {'statement', 'record_id', 'path', 'quote'}:
            result = {**deepcopy(prepared['observations'][node['observation_id']]), 'statement':node['statement']}
            remaining -= len(canonical(result))
            require(remaining >= 0, 'Observation expansion exceeds output bound', 'E_RESOURCE_LIMIT')
            return result
        if isinstance(node, dict) and 'quote' in properties and set(properties) <= {'record_id', 'unit_id', 'quote', 'locator'}:
            require(prepared['references'] is not None, 'No legal sources were delivered')
            selected = {'span_ids': [prepared['selections'][node['span_id']]]}
            span_id = selected["span_ids"][0]
            if span_id in prepared.get("extra_spans", {}):
                row = prepared["extra_spans"][span_id]
                text = next(u["text"] for u in prepared["packet"]["units"]
                    if u["unit_id"] == row["unit_id"])
                exact = text[row["start_codepoint"]:row["end_codepoint"]]
                require(exact and text.count(exact) == 1, "Ambiguous indexed selection")
                quote = {"unit_id": row["unit_id"], "quote": exact}
            else:
                quote = source_references.resolve(selected, prepared['references'], prepared['packet'], prepared['binding'])
            key = 'record_id' if 'record_id' in properties else 'unit_id'
            result = {key: quote['unit_id'], 'quote': quote['quote']}
            if 'locator' in properties: result['locator'] = prepared['locators'][node['span_id']]
            remaining -= len(canonical(result))
            require(remaining >= 0, 'Reference expansion exceeds output bound', 'E_RESOURCE_LIMIT')
            return result
        if isinstance(node, dict) and set(properties) == {'index_hash', 'locator', 'status'}:
            require(node['gap_id'] in prepared['gaps'], 'No such source gap was offered')
            return deepcopy(prepared['gaps'][node['gap_id']])
        if isinstance(node, dict):
            return {k: walk(v, properties.get(k, {}), k) for k, v in node.items()}
        if isinstance(node, list): return [walk(v, shape.get('items', {}), field) for v in node]
        if isinstance(node, str) and field in {'id', 'record_id', 'record_ids', 'unit_id', 'considered', 'source_unit_ids'}:
            return prepared['aliases'].get(node, node)
        return node
    result = walk(value, prepared['original_schema'])
    require(len(canonical(result)) <= maximum_bytes, 'Expanded output exceeds byte limit', 'E_RESOURCE_LIMIT')
    validate(result, prepared['original_schema'])
    return result
