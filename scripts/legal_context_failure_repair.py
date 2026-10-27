#!/usr/bin/env python3
"""Local, unpromoted correction checks for retained P14 context failures.

This command has no provider/dispatch action. It never changes retained calls,
live code, grants or bindings. A valid proposal remains a protocol simulation.
"""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-26/failure-repair'
PRIOR = ROOT / 'artifacts/legal-mission-control/2026-10-25/offline-unblock'
CANDIDATE = Path('/tmp/legalmath-unblock-v2')
PROFILE = 'p14-enforced-local-correction.v2'
PACKETS = BASE / 'enforced-packets-v2'
PACKET_INDEX = BASE / 'enforced-packets-v2.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def object_hash(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def save_retained(path, value):
    """Idempotent output; differing evidence needs a distinct reviewed path."""
    if path.exists():
        require(read(path) == value, f'Refuse to replace retained output: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def candidate_runtime():
    manifest = read(PRIOR / 'candidate-manifest.json')
    for row in manifest['files']:
        require(file_hash(CANDIDATE / row['path']) == row['after_sha256'],
                f'Candidate identity changed: {row["path"]}')
    require(file_hash(PRIOR / 'candidate.patch') == manifest['patch_sha256'],
            'Candidate patch identity changed')
    harness = CANDIDATE / 'replay_exact_context.py'
    require(file_hash(harness) == file_hash(PRIOR / 'reproduce/replay_exact_context.py'),
            'Replay harness differs from retained source')
    spec = importlib.util.spec_from_file_location('p14_retained_exact_replay', harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, loaded in tuple(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            path = getattr(loaded, '__file__', None)
            if path:
                require(Path(path).resolve().is_relative_to(CANDIDATE / 'src'),
                        f'Mixed candidate/live imports: {name}')
    return module


def classification():
    data = read(BASE / 'failure-classification.json')
    require(file_hash(ROOT / data['source_replay']) == data['source_replay_sha256'],
            'Classification replay identity changed')
    rows = data['rows']
    require(len(rows) == 23 and len({r['call'] for r in rows}) == 23,
            'Expected the exact 23 retained assignments')
    replay = read(ROOT / data['source_replay'])
    failed = {r['call']: r for r in replay['rows']
              if r['selector_simulation']['status'] == 'FAILED'}
    require(set(failed) == {r['call'] for r in rows}, 'Failure population changed')
    for row in rows:
        for key in ('request_sha256', 'raw_sha256'):
            require(row[key] == failed[row['call']][key], 'Classification input mismatch')
    return rows


def load_inputs(row):
    folder = (ROOT / row['raw_path']).resolve()
    require(folder.is_relative_to(ROOT) and folder.name == row['call'],
            'Foreign retained call directory')
    expected = {'request.json': row['request_sha256'], 'raw.json': row['raw_sha256'],
                'result.json': row['retained_result_sha256']}
    for name, digest in expected.items():
        require(file_hash(folder / name) == digest, f'Retained input changed: {name}')
    files = {name: {'path': str((folder / name).relative_to(ROOT)),
                    'sha256': file_hash(folder / name)}
             for name in ('request.json', 'raw.json', 'result.json',
                          'wire-response.json', 'schema.json')}
    request = read(folder / 'request.json')
    wire = read(folder / 'wire-response.json')['value']
    raw = read(folder / 'raw.json')['value']
    require(raw['verdict'] == row['raw_verdict'] and
            read(folder / 'result.json')['status'] == 'FAILED',
            'Retained legal result changed')
    return request, wire, raw, read(folder / 'schema.json'), files


def protocol_wire(wire):
    """Use the same explicit transformation as the retained protocol replay."""
    result = deepcopy(wire)
    for item in result['need_dispositions']:
        item['answer_evidence'] = {'answer_field': item['answer_evidence']['path']}
    return result


def permitted_edits(request, wire, aliases):
    """Only existing invalid fields; no prose, need, assertion or list deletion."""
    source_ids = [r['id'] for r in request['records'] if r['kind'] == 'source']
    sources = source_ids + [alias for alias, rid in aliases.items() if rid in source_ids]
    indexes = [r['index_hash'] for r in request.get('available_source_indexes', [])]
    edits = []

    def offer(path, old, choices, mode):
        edits.append({'path': path, 'original': deepcopy(old),
                      'choices': deepcopy(choices), 'mode': mode})

    for i, need in enumerate(wire['context_needs']):
        if need['kind'] in ('CLIENT_FACT', 'EXTERNAL_AUTHORITY'):
            for field in ('record_ids', 'locators'):
                if need[field]:
                    offer(f'/context_needs/{i}/{field}', need[field], [[]],
                          'DETERMINISTIC_IDENTIFIER_CLEARING')
        elif need['kind'] == 'SOURCE_TEXT':
            invalid = [rid for rid in need['record_ids'] if rid not in sources]
            known_non_sources = set(aliases.values()) - set(source_ids)
            if (invalid and (need['locators'] or need['query'].strip())
                    and all(aliases.get(rid, rid) in known_non_sources for rid in invalid)):
                retained = [rid for rid in need['record_ids'] if rid in sources]
                offer(f'/context_needs/{i}/record_ids', need['record_ids'], [retained],
                      'REMOVE_AUTHENTICATED_NON_SOURCE_IDS')
            else:
                for j, rid in enumerate(need['record_ids']):
                    if rid not in sources:
                        offer(f'/context_needs/{i}/record_ids/{j}', rid, sources,
                              'EXPLICIT_SOURCE_SELECTION')
            for j, locator in enumerate(need['locators']):
                if locator['index_hash'] not in indexes:
                    offer(f'/context_needs/{i}/locators/{j}/index_hash',
                          locator['index_hash'], indexes, 'EXPLICIT_DOCUMENT_SELECTION')
    rows = {r['need_id']: r for r in request['payload']['prior_needs']}
    failures = request['payload']['source_delivery_failures']
    for i, item in enumerate(wire['need_dispositions']):
        row = rows[item['need_id']]
        options = ['STILL_REQUIRED']
        if row['need_id'] not in failures:
            options.append('NOT_REQUIRED_FOR_CONDITIONAL_ANSWER')
            if row['route'] == 'SOURCE_TEXT':
                options.append('SUPPLIED_SOURCE')
            if row['route'] == 'ASSIGNMENT_MAPPING':
                options.append('MAPPING_CLARIFIED')
        if item['disposition'] not in options:
            offer(f'/need_dispositions/{i}/disposition', item['disposition'],
                  options, 'EXPLICIT_DISPOSITION_SELECTION')
    return edits


def replace_exact(value, path, expected, replacement):
    parts = path.lstrip('/').split('/')
    node = value
    for part in parts[:-1]:
        node = node[int(part)] if isinstance(node, list) else node[part]
    key = int(parts[-1]) if isinstance(node, list) else parts[-1]
    require(object_hash(node[key]) == object_hash(expected), 'Stale replacement target')
    node[key] = deepcopy(replacement)


def apply_edits(wire, allowed, replacements):
    require(isinstance(replacements, list), 'Replacements must be an ordered list')
    by_path = {row['path']: row for row in allowed}
    require(len(by_path) == len(allowed), 'Duplicate permitted edit')
    result, seen = deepcopy(wire), set()
    for change in replacements:
        require(isinstance(change, dict) and set(change) == {'path', 'value'},
                'Replacement must contain only path and value')
        path = change['path']
        require(path in by_path and path not in seen, 'Unauthorized or duplicate edit')
        rule = by_path[path]
        require(any(object_hash(change['value']) == object_hash(v)
                    for v in rule['choices']), 'Value is not an offered exact selection')
        replace_exact(result, path, rule['original'], change['value'])
        seen.add(path)
    return result


def make_packet(row, runtime):
    request, wire, raw, schema, files = load_inputs(row)
    proposed = deepcopy(request)
    proposed[runtime.exact.FIELD] = runtime.exact.PROFILE
    binding = runtime.refs.prepare(proposed, schema)
    baseline = protocol_wire(wire)
    allowed = permitted_edits(request, baseline, binding['aliases'])
    if row['lane'] == 'substantive_review':
        require(not allowed, 'Substantive case has unclassified mechanical defects')
    else:
        require(bool(allowed), 'Mechanical case has no permitted correction')
    packet = {'profile': PROFILE, 'call': row['call'], 'category': row['category'],
              'lane': row['lane'], 'inputs': files,
              'classification_sha256': file_hash(BASE / 'failure-classification.json'),
              'candidate_manifest_sha256': file_hash(PRIOR / 'candidate-manifest.json'),
              'protocol_wire_sha256': object_hash(baseline),
              'answer_sha256': object_hash(request['payload']['answer']),
              'allowed_edits': allowed, 'freeze_every_other_field': True,
              'raw_verdict': raw['verdict'], 'auto_accept': False, 'provider_calls': 0,
              'activation': 'LOCAL_ONLY_NOT_DEPLOYED',
              'qualification': 'Canonical validation is required; a valid selector is not legal support.'}
    return packet, proposed, baseline, binding, raw


def build(runtime):
    packets = []
    for row in classification():
        packet, *_ = make_packet(row, runtime)
        path = PACKETS / (row['call'] + '.json')
        save_retained(path, packet)
        packets.append({'call': row['call'], 'path': str(path.relative_to(ROOT)),
                        'sha256': file_hash(path), 'category': row['category'],
                        'editable_fields': len(packet['allowed_edits'])})
    result = {'profile': PROFILE, 'packets': packets, 'count': len(packets),
              'auto_accept': False, 'provider_calls': 0}
    save_retained(PACKET_INDEX, result)
    return {'count': len(packets), 'editable_fields': sum(r['editable_fields'] for r in packets),
            'provider_calls': 0, 'auto_accept': False}


def verify_packets(runtime):
    index = read(PACKET_INDEX)
    rows = {r['call']: r for r in classification()}
    require(len(index['packets']) == 23 and index['count'] == 23, 'Packet count mismatch')
    require({r['call'] for r in index['packets']} == set(rows), 'Packet population mismatch')
    for entry in index['packets']:
        path = ROOT / entry['path']
        require(file_hash(path) == entry['sha256'], 'Packet bytes changed')
        packet, *_ = make_packet(rows[entry['call']], runtime)
        require(read(path) == packet, 'Packet does not match authenticated inputs')
    return {'status': 'VERIFIED', 'count': 23, 'raw_and_request_hashes_unchanged': True,
            'provider_calls': 0, 'auto_accept': False}


def evaluate(row, packet, proposal, runtime, product, identity):
    expected, request, baseline, binding, raw = make_packet(row, runtime)
    require(packet == expected, 'Packet differs from authenticated reconstruction')
    require(set(proposal) == {'packet_sha256', 'replacements'}, 'Invalid proposal fields')
    require(proposal['packet_sha256'] == object_hash(packet), 'Proposal packet identity changed')
    corrected = apply_edits(baseline, packet['allowed_edits'], proposal['replacements'])
    result = {'call': row['call'], 'category': row['category'],
              'replacements': proposal['replacements'], 'raw_verdict': raw['verdict'],
              'packet_sha256': object_hash(packet), 'auto_accept': False, 'provider_calls': 0}
    try:
        value = runtime.refs.resolve(corrected, binding,
                                     maximum_bytes=identity['limits']['decoded_output_bytes'])
        for field in ('verdict', 'reason', 'issues'):
            require(value[field] == raw[field], f'Changed substantive field: {field}')
        runtime.validate(product, request, value)
        result.update(status='VALIDATED_PROTOCOL_CANDIDATE',
                      decoded_sha256=object_hash(value), context_need_count=len(value['context_needs']),
                      legal_acceptance='UNCHANGED; fresh substantive qualification remains required')
    except Exception as exc:
        result.update(status='REJECTED', error=getattr(exc, 'code', type(exc).__name__),
                      reason=str(getattr(exc, 'details', None) or
                                 getattr(exc, 'message', None) or exc)[:1400])
    return result, corrected


def check_shapes(runtime):
    verify_packets(runtime)
    product, identity = runtime.product()
    results = []
    for row in classification():
        if row['category'] != 'NEED_TYPE_SOURCE_SUBSTITUTION':
            continue
        packet = read(PACKETS / (row['call'] + '.json'))
        require(all(e['mode'] == 'DETERMINISTIC_IDENTIFIER_CLEARING'
                    for e in packet['allowed_edits']), 'Shape case needs an explicit source decision')
        proposal = {'packet_sha256': object_hash(packet),
                    'replacements': [{'path': e['path'], 'value': []}
                                     for e in packet['allowed_edits']]}
        result, wire = evaluate(row, packet, proposal, runtime, product, identity)
        target = BASE / 'shape-candidates-v2' / row['call']
        save_retained(target / 'proposal.json', proposal)
        save_retained(target / 'wire-simulation.json', wire)
        save_retained(target / 'result.json', result)
        results.append(result)
    require(len(results) == 4, 'Expected four first-error shape cases')
    summary = {'profile': PROFILE, 'kind': 'OFFLINE_SHAPE_REPAIR_NOT_LEGAL_ACCEPTANCE',
               'rows': results, 'counts': dict(Counter(r['status'] for r in results)),
               'provider_calls': 0, 'auto_accept': False}
    save_retained(BASE / 'shape-results-v2.json', summary)
    return {k: v for k, v in summary.items() if k != 'rows'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify', 'check-shapes', 'check-correction'))
    parser.add_argument('--call')
    parser.add_argument('--proposal', type=Path)
    args = parser.parse_args(argv)
    if args.action == 'check-correction':
        if not args.call or not args.proposal:
            parser.error('check-correction requires --call and --proposal')
    elif args.call or args.proposal:
        parser.error('Only check-correction accepts --call and --proposal')
    start = time.monotonic()
    runtime = candidate_runtime()
    if args.action == 'build':
        result = build(runtime)
    elif args.action == 'verify':
        result = verify_packets(runtime)
    elif args.action == 'check-shapes':
        result = check_shapes(runtime)
    else:
        verify_packets(runtime)
        rows = {r['call']: r for r in classification()}
        require(args.call in rows, 'Unknown retained assignment')
        packet = read(PACKETS / (args.call + '.json'))
        require(packet['allowed_edits'], 'Substantive review cannot use mechanical correction')
        product, identity = runtime.product()
        result, _ = evaluate(rows[args.call], packet, read(args.proposal), runtime, product, identity)
    print(json.dumps({'action': args.action, 'elapsed_seconds': time.monotonic() - start,
                      **result}, indent=2))
    return 2 if result.get('status') == 'REJECTED' else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'provider_calls': 0}))
        sys.exit(2)
