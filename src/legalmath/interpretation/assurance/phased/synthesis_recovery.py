"""Exact synthesis checkpoints; settled successes are never sampled again.

The frozen stage and cumulative charge ledger distinguish a charged no-output
failure from a request refused locally. This module grants no service authority.
"""
from copy import deepcopy
from pathlib import Path
import json
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import evidence_file, read_evidence
from ..bounded_references import prepare, resolve

PROFILE = 'bounded-phased-successor.v1'
SYNTHESIS = 'exact-synthesis-recovery.v1'
REVIEWED = 'reviewed-synthesis-recovery.v2'


def historical_request(prepared, *, reviewed=False):
    """Prove reconstruction, allowing only bijective input-alias renames.

    JSON objects lose insertion order on canonical storage. Input aliases were
    assigned in encounter order; the saved wire remains authoritative. Only the
    reviewed profile admits a permutation, and every other field must be exact.
    """
    request = deepcopy(prepared['original_request'])
    columns = prepared['request'].get('account_record_table', {}).get('columns', [])
    require(len(columns) == len(set(columns)), 'Duplicate historical synthesis columns')
    for i, row in enumerate(request.get('records', []) if columns else []):
        require(set(columns) <= set(row), 'Historical synthesis columns changed')
        request['records'][i] = {**{k: v for k, v in row.items() if k not in columns},
                               **{k: row[k] for k in columns}}
    current = prepare(request, prepared['original_schema'])
    if current != prepared and reviewed:
        # Hash renaming must precede citation renaming because the citation
        # table itself can contain those hash aliases. Output selectors and
        # their decoding maps are never renamed.
        for table, field, prefix in (('account_identity_hashes', 'identity_hash', 'h'),
                ('account_input_citations', 'input_citation', 'q')):
            new = current['request'].get(table, {})
            old = prepared['request'].get(table, {})
            if new == old:
                continue
            identities = {k: digest(v) for k, v in new.items()}
            reverse = {digest(v): k for k, v in old.items()}
            require(set(new) == set(old) == {prefix + str(i) for i in range(len(new))}
                and len(set(identities.values())) == len(new) == len(reverse)
                and set(identities.values()) == set(reverse),
                'Historical synthesis alias population changed', 'E_INTEGRITY')
            names = {k: reverse[v] for k, v in identities.items()}
            require(all(new[k] == old[names[k]] for k in new), 'Historical alias value changed')

            def rename(node):
                if isinstance(node, dict):
                    if set(node) == {field}:
                        require(node[field] in names, 'Unknown historical synthesis alias')
                        return {field: names[node[field]]}
                    return {k: rename(v) for k, v in node.items()}
                if isinstance(node, list):
                    return [rename(v) for v in node]
                return node

            current['request'] = rename(current['request'])
            current['request'][table] = deepcopy(old)
    require(current == prepared, 'Historical synthesis wire contract changed', 'E_INTEGRITY')
    return request


def no_output_receipt(held, data):
    """Check already authenticated wire bytes without regenerating old aliases."""
    from legalmath.interpretation.search.providers import transient_service_details
    events = [json.loads(line) for line in data['events.jsonl'].splitlines() if line.strip()]
    require(held.get('complete_output_present') is False and 'result.json' not in data
        and not any(e.get('type') == 'turn.completed'
            or e.get('item', {}).get('type') == 'agent_message' for e in events),
        'Historical retry contains completed or partial output', 'E_INTEGRITY')
    if 'termination.json' in data:
        ended = json.loads(data['termination.json'])
        require(ended.get('process_terminated') is True and ended.get('returncode') is not None
            and not ended.get('complete_output_present') and not ended.get('completed_turn_present'),
            'Prior synthesis timeout was not terminated', 'E_AUTHORITY')
    else:
        require(transient_service_details(events, output_present=False) is not None,
            'Prior failure lacks classified service evidence', 'E_AUTHORITY')


def composite(root, reference, account, input_hash):
    value = read_evidence(reference, root)
    require(value.get('profile') == PROFILE and value.get('input_hash') == input_hash
        and value.get('account') == account, 'Conflicting successor account checkpoint', 'E_INTEGRITY')
    read_evidence(value['synthesis'], root)
    return value


def metadata(root, reference, input_hash):
    value = read_evidence(reference, root)
    require(value.get('profile') in (SYNTHESIS, REVIEWED) and value.get('input_hash') == input_hash,
        'Foreign synthesis checkpoint', 'E_INTEGRITY')
    phase, dispatch, ledger = (read_evidence(value[k], root) for k in ('phase', 'dispatch', 'ledger'))
    require((phase['status'] == 'INCOMPLETE' or
        (value['profile'] == REVIEWED and phase['status'] == 'COMPLETE')) and phase['contract']['input_hash'] == input_hash
        and dispatch['input_hash'] == input_hash, 'Unsettled or foreign synthesis phase', 'E_INTEGRITY')
    stage = read_evidence(phase['admission'], root)
    require(stage.get('grant_hash') == ledger.get('grant_hash'), 'Changed synthesis grant', 'E_INTEGRITY')
    calls = phase['contract']['calls']
    require(calls and len({r['key'] for r in calls}) == len(calls)
        and all(r['key'].startswith('reduce-') for r in calls)
        and set(value['rows']) == {r['key'] for r in calls}, 'Incomplete synthesis census', 'E_INTEGRITY')
    outcome = read_evidence(phase['outcome'], root)
    if phase['status'] == 'COMPLETE':
        require(outcome.get('execution_complete') is True
            and all(r['result']['status'] == 'VALIDATED' for r in outcome['results']),
            'Complete phase contains failed synthesis', 'E_INTEGRITY')
    require(len(outcome['results']) == len(calls)
        and {r['key'] for r in outcome['results']} == set(value['rows']),
        'Incomplete synthesis outcomes', 'E_INTEGRITY')
    return value, phase, dispatch, ledger, {r['key']: r for r in outcome['results']}


def receipt(root, reference, slot, prepared):
    value = read_evidence(reference, root)
    require(value['allowance_slot'] == slot and value['request_hash'] == digest(prepared['request']),
        'Foreign synthesis provider receipt', 'E_INTEGRITY')
    parent = Path(reference['path']).parent
    require({'request.json', 'schema.json', 'events.jsonl'} <= set(value['files']),
        'Incomplete synthesis receipt', 'E_INTEGRITY')
    data = {}
    for name, item in value['files'].items():
        require(Path(name).name == name, 'Invalid receipt member', 'E_INTEGRITY')
        content = read_evidence({'path': str(parent / name), 'sha256': item['retained_sha256']},
            root, json_value=False)
        require(len(content) == item['bytes'], 'Changed receipt length', 'E_INTEGRITY')
        data[name] = content
    require(json.loads(data['request.json']) == prepared['request']
        and json.loads(data['schema.json']) == prepared['schema'],
        'Changed synthesis wire request or schema', 'E_INTEGRITY')
    return value, data


def checked_row(root, context, key, *, identity=None, request=None, schema=None, limits=None, ancestors=()):
    value, phase, dispatch, ledger, outcomes = context
    signature = digest(value)
    require(signature not in ancestors and len(ancestors) < 20, 'Cyclic synthesis lineage', 'E_INTEGRITY')
    row = value['rows'][key]
    saved_request, saved_schema, prepared, result = (read_evidence(row[k], root)
        for k in ('request', 'schema', 'reference_binding', 'result'))
    require(isinstance(prepared, dict) and 'original_request' in prepared
        and 'original_schema' in prepared and 'request' in prepared and 'schema' in prepared,
        'Malformed synthesis wire binding', 'E_INTEGRITY')
    saved_request = historical_request(prepared, reviewed=value['profile'] == REVIEWED)
    require(saved_request == read_evidence(row['request'], root)
        and saved_schema == prepared['original_schema'],
        'Synthesis wire reconstruction changed', 'E_INTEGRITY')
    # historical_request proved all decoding maps and schema exactly equal.
    # resolve revalidates construction; only request-side alias names may differ.
    decoder = prepare(saved_request, saved_schema)
    old = dispatch['calls'].get(key, {})
    expected = digest({'request': saved_request, 'schema': saved_schema,
        'provider_binding': value['provider_binding']})
    contract = next(r for r in phase['contract']['calls'] if r['key'] == key)
    require(old.get('identity') == contract['identity'] == expected
        and old.get('status') in ('VALIDATED', 'FAILED')
        and old['status'] == result['status'] and old['result_hash'] == digest(result)
        and outcomes[key].get('dispatch_result_hash') == old['result_hash']
        and outcomes[key]['result'] == result, 'Changed synthesis dispatch/result identity', 'E_INTEGRITY')
    wire_hash = digest(prepared['request'])
    slots = [i for i, charge in enumerate(ledger['calls'], 1)
        if charge.get('stage_hash') == phase['admission']['sha256'] and charge['request_hash'] == wire_hash]
    earlier = row.get('prior_transport_receipts', [])
    require(isinstance(earlier, list)
        and row['slot'] == (slots[-1] if slots else None)
        and ([r.get('slot') for r in earlier] == slots[:-1])
        and (not earlier or value['profile'] == REVIEWED),
        'Synthesis charge census changed', 'E_INTEGRITY')
    for attempt in earlier:
        held, data = receipt(root, attempt['receipt'], attempt['slot'], prepared)
        no_output_receipt(held, data)
    if slots:
        require(row.get('receipt'), 'Missing charged synthesis receipt', 'E_INTEGRITY')
        held, data = receipt(root, row['receipt'], slots[-1], prepared)
        if result['status'] == 'VALIDATED':
            require(held['complete_output_present'] is True and 'result.json' in data,
                'Successful synthesis lacks complete provider output', 'E_INTEGRITY')
            maximum = limits.decoded_output_bytes if limits is not None else 2_000_000
            require(resolve(json.loads(data['result.json']), decoder, maximum_bytes=maximum) == result['value']
                and result['provenance']['allowance_slot'] == slots[-1]
                and result['provenance']['request_hash'] == wire_hash,
                'Successful synthesis decode or provenance changed', 'E_INTEGRITY')
            disposition = 'RETAIN_EXACT_SUCCESS'
        elif held['complete_output_present'] is True:
            from .downstream_instructions import PROFILE as INSTRUCTIONS, REASONS, failure_paths
            edit = key in value.get('edit_corrections', {})
            require(value.get('instruction_profile') == INSTRUCTIONS and row.get('raw')
                and result.get('error') == 'E_INTEGRITY'
                and (edit or result.get('reason') in REASONS)
                and 'result.json' in data, 'Unreviewed completed synthesis rejection', 'E_INTEGRITY')
            raw = read_evidence(row['raw'], root)
            maximum = limits.decoded_output_bytes if limits is not None else 2_000_000
            require(resolve(json.loads(data['result.json']), decoder, maximum_bytes=maximum) == raw['value']
                and raw['provenance']['allowance_slot'] == slots[-1]
                and raw['provenance']['request_hash'] == wire_hash,
                'Rejected synthesis raw output changed', 'E_INTEGRITY')
            if edit:
                from .downstream_edits import PROFILE as EDIT_PROFILE, FIELD
                from .downstream_instructions import validate_correction
                from legalmath.errors import LegalMathError
                require(value.get('edit_profile') == EDIT_PROFILE
                    and FIELD not in saved_request and 'downstream_response_correction' in saved_request
                    and result['reason'] == 'Formatting correction changed unaffected prose or evidence',
                    'Unreviewed failed-correction successor', 'E_AUTHORITY')
                prior = metadata(root, value['edit_corrections'][key], value['input_hash'])
                require(prior[0]['provider_binding'] == value['provider_binding']
                    and prior[3]['grant_hash'] == ledger['grant_hash']
                    and ledger['calls'][:len(prior[3]['calls'])] == prior[3]['calls'],
                    'Correction predecessor changed provider or charges', 'E_INTEGRITY')
                rejected, _ = checked_row(root, prior, key, identity=expected, request=saved_request,
                    schema=saved_schema, limits=limits, ancestors=(*ancestors, signature))
                require(rejected['status'] == 'FAILED' and rejected['reason'] in REASONS
                    and prior[0]['rows'][key]['disposition'] == 'COMPLETED_RESPONSE_REJECTED',
                    'Correction predecessor was not the original rejection', 'E_INTEGRITY')
                try:
                    validate_correction(saved_request, raw['value'])
                except LegalMathError as exc:
                    require(exc.code == result['error'] and str(exc.details or exc) == result['reason'],
                        'Failed correction no longer reproduces', 'E_INTEGRITY')
                else:
                    require(False, 'Failed correction was silently accepted', 'E_INTEGRITY')
            else:
                require(failure_paths(raw['value']), 'Missing original citation defect', 'E_INTEGRITY')
            disposition = 'COMPLETED_RESPONSE_REJECTED'
        else:
            if key in value.get('diagnostic_reassessments', {}):
                from .synthesis_reassessment import checked
                require(value['profile'] == REVIEWED, 'Unreviewed diagnostic exception', 'E_AUTHORITY')
                checked(root, value, key)
                events = [json.loads(line) for line in data['events.jsonl'].splitlines() if line.strip()]
                require(any(e.get('type') == 'turn.failed' for e in events)
                    and not any(e.get('type') == 'turn.completed' or
                        e.get('item',{}).get('type') == 'agent_message' for e in events),
                    'Original diagnostic predecessor was not terminal and output-free')
            elif key in value.get('terminal_499_replays', []):
                from legalmath.interpretation.search.providers import transient_service_details
                require(value['profile'] == REVIEWED, 'Unreviewed cancellation recovery', 'E_AUTHORITY')
                events=[json.loads(line) for line in data['events.jsonl'].splitlines() if line.strip()]
                details = transient_service_details(events, output_present=False, allow_terminal_499=True)
                require(details is not None and '499' in details['message'],
                    'Cancellation lacks terminal no-output service evidence','E_AUTHORITY')
            else:
                no_output_receipt(held, data)
            disposition = 'CHARGED_NO_OUTPUT_FAILURE'
    elif result['status'] == 'VALIDATED':
        require(row.get('predecessor') and row.get('receipt') is None,
            'Reused synthesis lacks predecessor evidence', 'E_INTEGRITY')
        prior = metadata(root, row['predecessor'], value['input_hash'])
        prior_value, _, _, prior_ledger, _ = prior
        require(value['provider_binding'] == prior_value['provider_binding']
            and ledger['grant_hash'] == prior_ledger['grant_hash']
            and ledger['calls'][:len(prior_ledger['calls'])] == prior_ledger['calls'],
            'Synthesis lineage changed provider or cumulative charges', 'E_INTEGRITY')
        inherited, _ = checked_row(root, prior, key, identity=expected, request=saved_request,
            schema=saved_schema, limits=limits, ancestors=(*ancestors, signature))
        provenance = {'manifest': row['predecessor'], 'result': prior_value['rows'][key]['result'],
            'evidence_class': 'RETAINED_EXACT_SYNTHESIS; NOT_A_NEW_MODEL_SAMPLE'}
        require(inherited['status'] == 'VALIDATED' and result == inherited
            and old.get('retained_initial') == provenance,
            'Changed retained synthesis result or provenance', 'E_INTEGRITY')
        disposition = 'RETAIN_EXACT_SUCCESS'
    else:
        require(result['status'] == 'FAILED' and row.get('receipt') is None
            and result.get('error') == 'E_RESOURCE_LIMIT'
            and 'service circuit open' in result.get('reason', ''),
            'Unsent synthesis lacks local refusal evidence', 'E_INTEGRITY')
        disposition = 'UNSENT_LOCAL_SERVICE_REFUSAL'
    require(row['disposition'] == disposition, 'Synthesis disposition changed', 'E_INTEGRITY')
    if identity is not None:
        next_request = successor_request(root, value, key)
        next_identity = digest({'request': next_request, 'schema': saved_schema,
            'provider_binding': value['provider_binding']})
        require(identity == next_identity and request == next_request and schema == saved_schema,
            'Successful or pending synthesis contract changed; resampling forbidden', 'E_INTEGRITY')
    return result, slots


def successor_request(root, value, key):
    """Only reviewed missing requests get guidance; successful requests stay exact."""
    row = value['rows'][key]
    request = read_evidence(row['request'], root)
    profile = value.get('instruction_profile')
    if profile is None or row['disposition'] in ('RETAIN_EXACT_SUCCESS', 'CHARGED_NO_OUTPUT_FAILURE'):
        return request
    from .downstream_instructions import PROFILE as INSTRUCTIONS, annotate, failure_paths
    require(profile == INSTRUCTIONS, 'Unknown successor instructions', 'E_AUTHORITY')
    correction = None
    if row['disposition'] == 'COMPLETED_RESPONSE_REJECTED':
        raw = read_evidence(row['raw'], root)
        result = read_evidence(row['result'], root)
        if key in value.get('edit_corrections', {}):
            from .downstream_edits import PROFILE as EDIT_PROFILE, FIELD
            from .downstream_instructions import base_request
            require(value.get('edit_profile') == EDIT_PROFILE and FIELD not in request
                and 'downstream_response_correction' in request,
                'Repeated or unreviewed edit correction', 'E_AUTHORITY')
            revised = annotate(base_request(request))
            revised[FIELD] = {**deepcopy(request['downstream_response_correction']),
                'profile': EDIT_PROFILE, 'failed_request_sha256': digest(request),
                'failed_correction': row['raw'], 'failed_correction_rejection': row['result']}
            return revised
        correction = {'prior_request_sha256': digest(request), 'rejected_raw': row['raw'],
            'rejection': row['result'], 'reason': result['reason'],
            'prior_candidate': deepcopy(raw['value']), 'failure_paths': failure_paths(raw['value'])}
    else:
        require(row['disposition'] == 'UNSENT_LOCAL_SERVICE_REFUSAL',
            'Unreviewed synthesis correction', 'E_AUTHORITY')
    return annotate(request, correction=correction)


def rewrite(root, reference, key, request, schema, input_hash, *, limits=None):
    from . import synthesis_catalog
    if read_evidence(reference, root).get('profile') == synthesis_catalog.PROFILE:
        pointer=synthesis_catalog.selected(root,reference,key,input_hash)
        return rewrite(root,pointer,key,request,schema,input_hash,limits=limits) if pointer else None
    context = metadata(root, reference, input_hash)
    value, phase, dispatch, _, _ = context
    if key not in value['rows']:
        prefixes = {r['key'].rsplit('-', 1)[0] + '-' for r in phase['contract']['calls']}
        require(not any(key.startswith(p) for p in prefixes) and key not in dispatch['calls'],
            'Unreviewed synthesis key in retained phase', 'E_INTEGRITY')
        return None
    checked_row(root, context, key, limits=limits)
    row = value['rows'][key]
    saved_request = read_evidence(row['request'], root)
    from .downstream_instructions import base_request
    original = base_request(saved_request)
    reconstructed = deepcopy(request)
    if reconstructed != original and value['profile'] == REVIEWED:
        # Stored response dictionaries have sorted keys. Rewalking their
        # citations can permute these derived lists; restore only exact
        # populations to their authenticated historical order.
        for field, identity_fields in (('records', ('id',)),
                ('verified_locator_bindings', ('record_id', 'index_hash'))):
            current, prior = reconstructed.get(field), original.get(field)
            if current == prior:
                continue
            require(isinstance(current, list) and isinstance(prior, list),
                'Historical synthesis list missing', 'E_INTEGRITY')
            identities = [tuple(r.get(k) for k in identity_fields) for r in current]
            require(len(set(identities)) == len(current)
                and sorted(map(digest, current)) == sorted(map(digest, prior)),
                'Historical synthesis source or locator population changed', 'E_INTEGRITY')
            reconstructed[field] = deepcopy(prior)
    require(reconstructed == original and schema == read_evidence(row['schema'], root),
        'Reconstruction changed original synthesis evidence', 'E_INTEGRITY')
    return successor_request(root, value, key)


def load(root, reference, input_hash, *, provider_binding=None, limits=None):
    from . import synthesis_catalog
    if read_evidence(reference, root).get('profile') == synthesis_catalog.PROFILE:
        return synthesis_catalog.load(root,reference,input_hash,provider_binding=provider_binding,limits=limits)
    context = metadata(root, reference, input_hash)
    value, phase, _, ledger, _ = context
    if value.get('diagnostic_reassessments') or value.get('terminal_499_replays'):
        cancellations = value.get('terminal_499_replays', [])
        require(value['profile'] == REVIEWED
            and set(value.get('diagnostic_reassessments',{})) <= set(value['rows'])
            and isinstance(cancellations, list) and len(cancellations) == len(set(cancellations))
            and set(cancellations) <= set(value['rows'])
            and not set(cancellations) & set(value.get('diagnostic_reassessments',{})),
            'Unreviewed synthesis recovery scope','E_AUTHORITY')
        if cancellations:
            review = read_evidence(value['terminal_service_review'], root)
            require(review.get('profile') == 'exact-terminal-synthesis-review.v1'
                and review.get('verdict') == 'PASS' and review.get('provider_calls_authorized') == 0
                and review.get('maximum_successor_attempts_per_key') == 1
                and review.get('approved') == {k:value['rows'][k]['result'] for k in cancellations},
                'Unbound finite cancellation recovery review', 'E_AUTHORITY')
    if value.get('instruction_profile') is not None:
        from .downstream_instructions import PROFILE as INSTRUCTIONS
        require(value['instruction_profile'] == INSTRUCTIONS, 'Unknown synthesis instruction profile', 'E_AUTHORITY')
    if value.get('edit_profile') or value.get('edit_corrections'):
        from .downstream_edits import PROFILE as EDIT_PROFILE
        edits = value.get('edit_corrections', {})
        require(value.get('edit_profile') == EDIT_PROFILE and len(edits) == 1
            and set(edits) <= set(value['rows'])
            and all(value['rows'][k]['disposition'] == 'COMPLETED_RESPONSE_REJECTED' for k in edits),
            'Unreviewed edit-correction population', 'E_AUTHORITY')
    if provider_binding is not None:
        require(provider_binding == value['provider_binding'], 'Synthesis provider changed', 'E_INTEGRITY')
    used = []
    for key in value['rows']:
        _, slots = checked_row(root, context, key, limits=limits)
        successor_request(root, value, key)
        used += slots
    charged = [i for i, row in enumerate(ledger['calls'], 1)
        if row.get('stage_hash') == phase['admission']['sha256']]
    require(sorted(used) == charged, 'Unaccounted synthesis charge', 'E_INTEGRITY')
    return value


def retained(root, reference, key, request, schema, identity, input_hash, *, limits=None):
    from . import synthesis_catalog
    if read_evidence(reference, root).get('profile') == synthesis_catalog.PROFILE:
        pointer=synthesis_catalog.selected(root,reference,key,input_hash)
        return retained(root,pointer,key,request,schema,identity,input_hash,limits=limits) if pointer else None
    context = metadata(root, reference, input_hash)
    value, phase, dispatch, _, _ = context
    if key not in value['rows']:
        # A new reduction level may proceed. The sealed phase's key population
        # cannot be extended, renamed, or replaced by an unrecorded call.
        prefixes = {r['key'].rsplit('-', 1)[0] + '-' for r in phase['contract']['calls']}
        require(not any(key.startswith(p) for p in prefixes) and key not in dispatch['calls'],
            'Unreviewed synthesis key in retained phase', 'E_INTEGRITY')
        return None
    result, _ = checked_row(root, context, key, identity=identity, request=request,
        schema=schema, limits=limits)
    if result['status'] != 'VALIDATED':
        if key not in value.get('diagnostic_reassessments', {}):
            return None  # Exact recovery is eligible; provider authority remains separate.
        from .synthesis_reassessment import checked
        result = checked(root, value, key)
    return deepcopy(result), {'manifest': reference, 'result': value['rows'][key]['result'],
        'evidence_class': 'RETAINED_EXACT_SYNTHESIS; NOT_A_NEW_MODEL_SAMPLE'}


def replay_wire(root, reference, key, request, schema, input_hash, *, limits=None):
    """Eligible unchanged missing synthesis uses its authenticated old wire."""
    from . import synthesis_catalog
    value = read_evidence(reference, root)
    if value.get('profile') != PROFILE or not key.startswith('reduce-'):
        return None
    pointer = value['synthesis']
    if read_evidence(pointer, root).get('profile') == synthesis_catalog.PROFILE:
        pointer = synthesis_catalog.selected(root, pointer, key, input_hash)
        if pointer is None:
            return None
    context = metadata(root, pointer, input_hash)
    value = context[0]
    if key not in value['rows']:
        return None
    row = value['rows'][key]
    identity = digest({'request': request, 'schema': schema, 'provider_binding': value['provider_binding']})
    result, _ = checked_row(root, context, key, identity=identity, request=request, schema=schema, limits=limits)
    require(result['status'] != 'VALIDATED' and key not in value.get('diagnostic_reassessments', {}),
        'Successful synthesis must not be dispatched', 'E_AUTHORITY')
    if request != read_evidence(row['request'], root):
        return None  # Explicitly reviewed instruction correction has a new wire.
    return read_evidence(row['reference_binding'], root)


def build(root, phase_reference, dispatch_reference, ledger_reference, provider_binding, provider_directory,
          *, instruction_profile=None, edit_corrections=None, profile=SYNTHESIS):
    require(profile in (SYNTHESIS, REVIEWED), 'Unknown synthesis recovery profile', 'E_AUTHORITY')
    phase, dispatch, ledger = (read_evidence(p, root) for p in
        (phase_reference, dispatch_reference, ledger_reference))
    directory = Path(dispatch_reference['path']).parent
    rows = {}
    for contract in phase['contract']['calls']:
        key = contract['key']
        row = {name: evidence_file(Path(root) / directory / key / filename, root)
            for name, filename in (('request', 'request.json'), ('schema', 'schema.json'),
                ('result', 'result.json'))}
        previous = dispatch['calls'][key]
        if previous.get('retained_initial'):
            row['predecessor'] = deepcopy(previous['retained_initial']['manifest'])
            prior = read_evidence(row['predecessor'], root)
            row['reference_binding'] = deepcopy(prior['rows'][key]['reference_binding'])
        else:
            row['reference_binding'] = evidence_file(Path(root) / directory / key / 'reference-binding.json', root)
        wire_hash = digest(read_evidence(row['reference_binding'], root)['request'])
        slots = [i for i, charge in enumerate(ledger['calls'], 1)
            if charge.get('stage_hash') == phase['admission']['sha256'] and charge['request_hash'] == wire_hash]
        require(len(slots) <= 1 or profile == REVIEWED, 'Repeated synthesis charge', 'E_INTEGRITY')
        row['slot'] = slots[-1] if slots else None
        row['receipt'] = evidence_file(Path(root) / provider_directory /
            f'{slots[-1]:04}-{wire_hash[:16]}' / 'manifest.json', root) if slots else None
        if len(slots) > 1:
            row['prior_transport_receipts'] = [{'slot': slot, 'receipt': evidence_file(Path(root) /
                provider_directory / f'{slot:04}-{wire_hash[:16]}' / 'manifest.json', root)}
                for slot in slots[:-1]]
        complete = bool(row['receipt'] and read_evidence(row['receipt'], root)['complete_output_present'])
        row['disposition'] = ('RETAIN_EXACT_SUCCESS' if previous['status'] == 'VALIDATED'
            else 'COMPLETED_RESPONSE_REJECTED' if complete
            else 'CHARGED_NO_OUTPUT_FAILURE' if slots else 'UNSENT_LOCAL_SERVICE_REFUSAL')
        if row['disposition'] == 'COMPLETED_RESPONSE_REJECTED':
            row['raw'] = evidence_file(Path(root) / directory / key / 'raw.json', root)
        rows[key] = row
    from .downstream_edits import PROFILE as EDIT_PROFILE
    return {'profile': profile, 'input_hash': phase['contract']['input_hash'],
        'phase': phase_reference, 'dispatch': dispatch_reference, 'ledger': ledger_reference,
        'provider_binding': deepcopy(provider_binding), 'rows': rows,
        **({'edit_profile': EDIT_PROFILE, 'edit_corrections': deepcopy(edit_corrections)} if edit_corrections else {}),
        **({'instruction_profile': instruction_profile} if instruction_profile is not None else {})}
