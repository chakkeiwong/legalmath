"""A settled predecessor selects exact reuse or a named account repair.

This module grants no attempt, provider call, or legal acceptance.
"""
from copy import deepcopy
from pathlib import Path
import json
import re
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import evidence_file, read_evidence

PROFILE = 'targeted-requirement-account-recovery.v1'
KEY = re.compile(r'^(detail-[0-9]+)(?:-part-[01])*$')


def baseline_request(request, schema, *, root=None):
    """Recognize exact supported historical contracts, never infer a new one."""
    from ..bounded_product import NOTE
    from . import account_contract
    require(request.get('task') == 'ASSESS_ORIGINAL_REQUIREMENT', 'Foreign recovery task')
    if request.get('account_contract') is None:
        require(schema == NOTE and 'account_input_profile' not in request
            and 'account_capacity_profile' not in request, 'Foreign legacy recovery schema')
        return deepcopy(request), False
    require(schema in (account_contract.schema(), account_contract.provider_schema()),
        'Foreign typed recovery schema')
    original = deepcopy(request)
    for key in ('account_contract', 'account_instructions', 'response_reference_profile',
                'account_input_profile', 'account_instruction_profile', 'account_capacity_profile', 'account_output_profile'):
        original.pop(key, None)
    require(account_contract.select(original, input_profile=request.get('account_input_profile'),
        instruction_profile=request.get('account_instruction_profile'),
        capacity_profile=request.get('account_capacity_profile'), output_profile=request.get('account_output_profile')) == request,
        'Changed typed recovery instructions')
    if 'account_correction' in original:
        require(root is not None, 'Corrected account requires retained rejection evidence', 'E_INTEGRITY')
        annotation = original.pop('account_correction')
        validate_retained_correction(root, annotation, original)
    return original, True


def correction_value(retained):
    return {'instructions': 'Reassess this same assignment from the delivered sources. A prior response '
        'failed because the named free-prose fields used numbered provision labels. Describe their '
        'substantive roles in prose and preserve all required document-qualified source_gaps exactly. '
        'Do not turn missing authority into positive support. The prior response remains rejected.',
        'prior_rejected_response': deepcopy(retained['raw']), 'prose_fields': retained['prose_fields'],
        'required_source_gaps': deepcopy(retained['required_source_gaps'])}


def validate_retained_correction(root, annotation, original):
    """Recognize one evidenced correction; never discard arbitrary request fields."""
    from .account_contract import prose_fields
    from ..answer_acceptance import MENTION, BRACKET_NUMBER
    require(isinstance(annotation, dict) and isinstance(annotation.get('prior_rejected_response'), dict),
        'Unbound account correction', 'E_INTEGRITY')
    pointer = annotation['prior_rejected_response']
    raw = read_evidence(pointer, root)
    directory = Path(pointer['path']).parent
    require(Path(pointer['path']).name == 'raw.json' and KEY.fullmatch(directory.name),
        'Foreign account rejection evidence', 'E_INTEGRITY')
    request, schema, result = (read_evidence(evidence_file(Path(root) / directory / (name + '.json'), root), root)
        for name in ('request', 'schema', 'result'))
    state = read_evidence(evidence_file(Path(root) / directory.parent / 'dispatch.json', root), root)
    previous = state.get('calls', {}).get(directory.name, {})
    require('account_correction' not in request, 'Nested account correction is unsupported', 'E_INTEGRITY')
    require(previous.get('status') == result.get('status') == 'FAILED'
        and previous.get('result_hash') == digest(result)
        and result.get('request_hash') == digest(request)
        and state.get('input_hash') == original.get('input_hash')
        and result.get('reason') == 'Numbered assertion has no document/proposition binding',
        'Unsubstantiated retained account rejection', 'E_INTEGRITY')
    require(baseline_request(request, schema, root=root)[0] == original,
        'Account correction changed the rejected source or assignment', 'E_INTEGRITY')
    value = raw['value']
    fields = [p for p, text in prose_fields(value) if MENTION.search(text) or BRACKET_NUMBER.search(text)]
    retained = {'raw': pointer, 'prose_fields': fields, 'required_source_gaps': value['source_gaps']}
    require(fields and annotation == correction_value(retained),
        'Changed retained account correction', 'E_INTEGRITY')


def assignment(request):
    payload = request['payload']
    while isinstance(payload, dict) and 'original_assignment' in payload:
        payload = payload['original_assignment']
    return {'task': request['task'], 'question': request['question'],
        'required_considered': request['required_considered'], 'assignment': payload}


def merge_details(previous, latest):
    """Reconcile an interrupted prefix with the authenticated complete census."""
    ids = [r['id'] for r in previous]
    new_ids = [r['id'] for r in latest]
    require(ids and len(set(ids)) == len(ids) and new_ids == ids[:len(new_ids)],
        'Interrupted account outcomes are not an original ordered prefix', 'E_INTEGRITY')
    for old, new in zip(previous, latest):
        require(old.get('requirement_hash') == new.get('requirement_hash'),
            'Interrupted account changed a requirement', 'E_INTEGRITY')
        if old['result']['status'] == 'VALIDATED':
            require(old['result'] == new['result'], 'Interrupted account changed a success', 'E_INTEGRITY')
    return deepcopy(latest + previous[len(latest):])


def build(root, directory, details, *, predecessor=None, complete_details_path=None):
    """Freeze a settled call inventory. Caller must separately settle its owner."""
    from ..bounded_product import NOTE
    root, directory = Path(root).resolve(), Path(directory).resolve()
    dispatch_ref = evidence_file(directory / 'dispatch.json', root)
    state = read_evidence(dispatch_ref, root)
    details_ref = evidence_file(directory.parent / 'requirement-details.json', root)
    require(read_evidence(details_ref, root) == details, 'Recovery account census differs from retained outcomes')
    require(state.get('calls') and all(row['status'] in ('VALIDATED', 'FAILED')
        for row in state['calls'].values()), 'Unsettled predecessor account calls', 'E_AUTHORITY')
    calls, originals, roots, contracts, corrections = {}, {}, set(), {}, {}
    inherited = load(root, predecessor, state['input_hash']) if predecessor else None
    interrupted_details = None
    origins = {}
    if inherited:
        previous_details = read_evidence(inherited['account_recovery']['details'], root)
        if {r['id'] for r in previous_details} != {r['id'] for r in details}:
            require(complete_details_path is not None, 'Interrupted census needs an explicit retained merge')
            combined = merge_details(previous_details, details)
            require(len(combined) == len(previous_details) and len(details) < len(previous_details),
                'Successor changed original requirement population')
            interrupted_details = details_ref
            from .evidence_store import save_exact
            path = Path(complete_details_path).resolve()
            require(path.is_relative_to(root) and path != root / details_ref['path'],
                'Merged census must retain its original separately')
            save_exact(path, combined)
            details, details_ref = combined, evidence_file(path, root)
        originals = deepcopy(inherited['account_recovery']['originals'])
        origins = {k: inherited.get('original_dispatches', {}).get(k, inherited['dispatch'])
                   for k in originals}
    latest = {k for k in state['calls'] if KEY.fullmatch(k)}
    for key in latest:
        references = {k: evidence_file(directory / key / (k + '.json'), root)
            for k in ('request', 'schema', 'result')}
        if inherited and key in inherited['calls']:
            require(all(read_evidence(references[n], root) == read_evidence(inherited['calls'][key][n], root)
                for n in references), 'Successor changed a successful predecessor contract')
        originals[key] = references
        origins[key] = dispatch_ref
    ids = {row['id']: row for row in details}
    require(len(ids) == len(details) and details, 'Missing or duplicate account census')
    for key, references in originals.items() if inherited else state['calls'].items():
        match = KEY.fullmatch(key)
        if not match:
            continue
        if not inherited:
            references = {k: evidence_file(directory / key / (k + '.json'), root)
                for k in ('request', 'schema', 'result')}
            originals[key] = references
            origins[key] = dispatch_ref
        previous = read_evidence(origins[key], root)['calls'][key]
        request, schema, result = (read_evidence(references[k], root)
            for k in ('request', 'schema', 'result'))
        baseline_request(request, schema, root=root)
        require(result['status'] == previous['status'] and digest(result) == previous['result_hash']
            and result['request_hash'] == digest(request), 'Changed predecessor account result')
        require(len(request['required_considered']) == 1 and request['required_considered'][0] in ids,
            'Predecessor account absent from complete requirement census')
        root_key = match.group(1)
        contract = assignment(request)
        require(root_key not in contracts or contracts[root_key] == contract,
            'Different assignments share one account root')
        contracts[root_key] = deepcopy(contract)
        originals[key] = references
        if result['status'] == 'FAILED' and result.get('reason') == 'Numbered assertion has no document/proposition binding':
            raw_ref = evidence_file(Path(root) / Path(references['request']['path']).parent / 'raw.json', root)
            raw = read_evidence(raw_ref, root)['value']
            from .account_contract import prose_fields
            from ..answer_acceptance import MENTION, BRACKET_NUMBER
            fields = [path for path, text in prose_fields(raw) if MENTION.search(text) or BRACKET_NUMBER.search(text)]
            require(fields, 'Numbered-prose rejection has no reproduced field')
            corrections[key] = {'raw': raw_ref, 'prose_fields': fields, 'required_source_gaps': deepcopy(raw['source_gaps'])}
        if previous['status'] == 'VALIDATED':
            calls[key] = references
        if ids[request['required_considered'][0]]['result']['status'] != 'VALIDATED':
            roots.add(root_key)
    require(contracts and all(row['result']['status'] in ('VALIDATED', 'FAILED') for row in details),
        'No settled account contracts')
    represented = {c['required_considered'][0] for c in contracts.values()}
    require(represented == set(ids), 'An account has no reconstructible predecessor assignment')
    require(evidence_file(directory / 'dispatch.json', root) == dispatch_ref,
        'Predecessor changed during recovery census', 'E_AUTHORITY')
    return {'profile': 'bounded-exact-checkpoint.v2', 'input_hash': state['input_hash'],
        'dispatch': dispatch_ref, 'calls': calls,
        **({'predecessor_recovery': predecessor, 'original_dispatches': origins} if inherited else {}),
        'account_recovery': {'profile': PROFILE, 'roots': sorted(roots),
            'contracts': contracts, 'originals': originals,
            'failed_calls': sorted(k for k in originals if read_evidence(origins[k], root)['calls'][k]['status'] == 'FAILED'),
            'details': details_ref, 'details_hash': digest(details), 'provider_calls_authorized': 0,
            **({'interrupted_details': interrupted_details} if interrupted_details else {}),
            **({'corrections': corrections} if corrections else {})}}


def load(root, reference, input_hash):
    value = read_evidence(reference, root)
    config = value.get('account_recovery', {})
    require(value.get('profile') == 'bounded-exact-checkpoint.v2'
        and value.get('input_hash') == input_hash and config.get('profile') == PROFILE
        and config.get('provider_calls_authorized') == 0,
        'Foreign account recovery checkpoint', 'E_INTEGRITY')
    state = read_evidence(value['dispatch'], root)
    require(state.get('input_hash') == input_hash and all(r['status'] != 'RESERVED'
        for r in state['calls'].values()), 'Unsettled account recovery predecessor', 'E_AUTHORITY')
    expected = {k for k in state['calls'] if KEY.fullmatch(k)}
    origins = {k: value['dispatch'] for k in expected}
    if value.get('predecessor_recovery'):
        inherited = load(root, value['predecessor_recovery'], input_hash)
        if config.get('interrupted_details'):
            require(read_evidence(config['details'], root) == merge_details(
                read_evidence(inherited['account_recovery']['details'], root),
                read_evidence(config['interrupted_details'], root)),
                'Changed interrupted-account census merge', 'E_INTEGRITY')
        require({r['id'] for r in read_evidence(config['details'], root)} ==
            {r['id'] for r in read_evidence(inherited['account_recovery']['details'], root)},
            'Composite recovery changed original requirement population')
        inherited_keys = set(inherited['account_recovery']['originals'])
        origins = {k: inherited.get('original_dispatches', {}).get(k, inherited['dispatch']) for k in inherited_keys} | origins
        expected |= inherited_keys
        require(value.get('original_dispatches') == origins, 'Changed composite dispatch origins')
        require(set(config.get('originals', {})) == expected,
            'Recovery omits a predecessor request', 'E_INTEGRITY')
        for key in inherited_keys:
            if key not in state['calls']:
                require(config['originals'][key] == inherited['account_recovery']['originals'][key],
                    'Changed inherited original account')
            elif key in inherited['calls']:
                require(all(read_evidence(config['originals'][key][n], root) ==
                    read_evidence(inherited['calls'][key][n], root) for n in ('request', 'schema', 'result')),
                    'Changed inherited successful account')
    else:
        require('interrupted_details' not in config, 'Interrupted census has no predecessor', 'E_INTEGRITY')
        require('original_dispatches' not in value, 'Unreviewed composite dispatch origins')
    # A composite frontier can give hundreds of accounts the same journal.
    # Parse each exact journal once in this invocation; verify its bytes again
    # before returning. No validated object survives this mutation boundary.
    dispatches = {(value['dispatch']['path'], value['dispatch']['sha256']): state}
    for pointer in origins.values():
        identity = (pointer['path'], pointer['sha256'])
        if identity not in dispatches:
            dispatches[identity] = read_evidence(pointer, root)
    states = {k: dispatches[(origins[k]['path'], origins[k]['sha256'])]['calls'][k]
              for k in expected}
    require(all(saved.get('input_hash') == input_hash for saved in dispatches.values()),
        'Composite recovery changed source input')
    require(set(config['originals']) == expected and set(value['calls']) == {
        k for k in expected if states[k]['status'] == 'VALIDATED'},
        'Recovery omits a predecessor request')
    require(set(config['failed_calls']) == {k for k in expected if states[k]['status'] == 'FAILED'},
        'Recovery changed the failure census')
    contracts = {}
    for key, references in config['originals'].items():
        request, schema, result = (read_evidence(references[k], root)
            for k in ('request', 'schema', 'result'))
        prior = states[key]
        require(prior['status'] in ('VALIDATED', 'FAILED'), 'Unsettled composite account origin')
        require(result['status'] == prior['status'] and digest(result) == prior['result_hash']
            and result['request_hash'] == digest(request), 'Recovery predecessor bytes changed')
        baseline_request(request, schema, root=root)
        root_key = KEY.fullmatch(key).group(1)
        contract = assignment(request)
        require(root_key not in contracts or contracts[root_key] == contract,
            'Inconsistent retained account assignment')
        contracts[root_key] = contract
        if prior['status'] == 'VALIDATED':
            require(value['calls'][key] == references, 'Successful recovery source changed')
    require(config['contracts'] == contracts and set(config['roots']) <= set(contracts)
        and len(config['roots']) == len(set(config['roots'])), 'Recovery root census changed')
    details = read_evidence(config['details'], root)
    ids = {r['id']: r for r in details}
    require(len(ids) == len(details) and digest(details) == config['details_hash']
        and all(r['result']['status'] in ('VALIDATED', 'FAILED') for r in details),
        'Changed or unsettled requirement outcome census')
    require({c['required_considered'][0] for c in contracts.values()} == set(ids),
        'Recovery omits an original account')
    require(set(config['roots']) == {key for key, c in contracts.items()
        if ids[c['required_considered'][0]]['result']['status'] == 'FAILED'},
        'Recovery roots do not equal the failed account population')
    for key, correction in config.get('corrections', {}).items():
        require(key in config['failed_calls'], 'Correction cannot resample a successful account')
        require(correction['raw'] == evidence_file(Path(root) /
            Path(config['originals'][key]['request']['path']).parent / 'raw.json', root),
            'Correction changed its original rejected response')
        result = read_evidence(config['originals'][key]['result'], root)
        raw = read_evidence(correction['raw'], root)['value']
        from .account_contract import prose_fields
        from ..answer_acceptance import MENTION, BRACKET_NUMBER
        require(result.get('reason') == 'Numbered assertion has no document/proposition binding'
            and correction['required_source_gaps'] == raw['source_gaps']
            and correction['prose_fields'] == [p for p,t in prose_fields(raw) if MENTION.search(t) or BRACKET_NUMBER.search(t)],
            'Unsubstantiated account correction')
    from .account_receipt import checked
    for key, entry in value.get('completed_account_receipts', {}).items():
        checked(root, value, key, entry)
    for path, sha256 in dispatches:
        read_evidence({'path': path, 'sha256': sha256}, root, json_value=False)
    return value


def correction(root, reference, key, input_hash):
    value = load(root, reference, input_hash)
    retained = value['account_recovery'].get('corrections', {}).get(key)
    if retained is None:
        return None
    return correction_value(retained)


def validate_provider(root, value, provider_binding):
    for key, references in value['account_recovery']['originals'].items():
        state = read_evidence(value.get('original_dispatches', {}).get(key, value['dispatch']), root)
        request, schema = (read_evidence(references[k], root) for k in ('request', 'schema'))
        require(state['calls'][key]['identity'] == digest({'request': request,
            'schema': schema, 'provider_binding': provider_binding}),
            'Recovery provider or source identity changed', 'E_INTEGRITY')


def use_typed(root, reference, key, request, input_hash):
    value = load(root, reference, input_hash)
    match = KEY.fullmatch(key)
    require(match is not None, 'Account recovery cannot introduce an unrelated task')
    config = value['account_recovery']
    root_key = match.group(1)
    require(config['contracts'].get(root_key) == assignment(request),
        'Account recovery changed the source assignment or original question', 'E_INTEGRITY')
    if key in value['calls']:
        previous = value['calls'][key]
        old = read_evidence(previous['request'], root)
        original, typed = baseline_request(old, read_evidence(previous['schema'], root), root=root)
        restore_record_order(original, request)
        return typed
    require(root_key in config['roots'], 'Unlisted account recovery root', 'E_AUTHORITY')
    if key in config['originals']:
        old = read_evidence(config['originals'][key]['request'], root)
        # Combination sources may change when repaired children cite different
        # evidence. Leaf requests preserve their delivered source exactly.
        if not isinstance(old['payload'], dict) or 'partial_source_readings' not in old['payload']:
            require(old['records'] == request['records'], 'Recovery changed a failed leaf source', 'E_INTEGRITY')
    return True


def retained_contract(root, reference, key, request, input_hash):
    """Return the exact successful selected contract after checking its base."""
    value = load(root, reference, input_hash)
    require(KEY.fullmatch(key) is not None, 'Invalid retained account key')
    row = value['calls'].get(key)
    if row is None:
        return None
    old, schema = (read_evidence(row[k], root) for k in ('request', 'schema'))
    original, typed = baseline_request(old, schema, root=root)
    restore_record_order(original, request)
    return old, schema, typed


def restore_record_order(original, request):
    """Authenticate an order-only difference, returning the historical base.

    JSON object key order can change traversal order when source_records walks
    saved child responses. Record order is restored only after complete records,
    unique IDs, and every other request field agree. The caller still reuses the
    exact historical request, schema and response; no successful call is sampled.
    """
    message = 'Successful account request changed; resampling is forbidden'
    populations = []
    for candidate in (original, request):
        records = candidate.get('records')
        require(isinstance(records, list) and all(isinstance(r, dict)
            and isinstance(r.get('id'), str) for r in records), message, 'E_INTEGRITY')
        population = {r['id']: r for r in records}
        require(len(population) == len(records), message, 'E_INTEGRITY')
        populations.append(population)
    require(populations[0] == populations[1], message, 'E_INTEGRITY')
    restored = deepcopy(request)
    restored['records'] = deepcopy(original['records'])
    require(restored == original, message, 'E_INTEGRITY')
    return restored


def has_retained_children(root, reference, key, input_hash):
    value = load(root, reference, input_hash)
    require(KEY.fullmatch(key) is not None, 'Invalid recovery partition key')
    return any(k.startswith(key + '-part-') for k in value['account_recovery']['originals'])
