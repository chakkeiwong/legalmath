"""Completion-only diagnosis for bounded account repair; never grants calls."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
from legalmath.canonical import digest
from ..bounded_context import require
from ..bounded_references import prepare
from ..integration_contract import evidence_file, read_evidence
from . import account_recovery

PROFILE = 'bounded-account-failure-recovery.v1'
NUMBERED = 'Numbered assertion has no document/proposition binding'


def normalized_wire(request):
    value = deepcopy(request)
    hashes = value.pop('account_identity_hashes', {})
    def expand(node):
        if isinstance(node, dict):
            if set(node)=={'identity_hash'}:
                require(node['identity_hash'] in hashes,'Unknown wire identity alias')
                return hashes[node['identity_hash']]
            return {k:expand(v) for k,v in node.items()}
        if isinstance(node,list):return [expand(v) for v in node]
        return node
    value=expand(value)
    if 'account_record_table' in value:
        table=value.pop('account_record_table');columns=table['columns']
        require(len(columns)==len(set(columns)),'Duplicate wire columns')
        records=[]
        for name,*cells in table['rows']:
            require(len(cells)==len(columns) and not set(columns)&set(table['metadata'][name]),'Invalid wire table')
            records.append({**table['metadata'][name],**dict(zip(columns,cells))})
        value['records']=records
    return value


def checked_wire(root, pointer, request, schema):
    old=read_evidence(pointer,root); current=prepare(request,schema)
    require({k:v for k,v in old.items() if k!='request'}=={k:v for k,v in current.items() if k!='request'}
        and normalized_wire(old['request'])==normalized_wire(current['request']),
        'Retained wire changes source, assignment, schema or decoding maps')
    return old


def replay_wire(root, checkpoint, key, request, schema):
    value=read_evidence(checkpoint,root)
    if value.get('failure_recovery',{}).get('actions',{}).get(key)!='EXACT_NO_OUTPUT_REPLAY':
        return None
    pointer=value['recoverable_failures'][key]['wire_binding']
    return checked_wire(root,pointer,request,schema)


def invalid_request_receipts(root, provider_directory, request, schema, binding):
    """Authenticate terminal rejection of this exact production wire packet."""
    root, base = Path(root), Path(provider_directory)
    wire = checked_wire(root,binding,request,schema)
    wanted = digest(wire['request'])
    receipts = []
    ledger = json.loads((root/base/'live-calls.json').read_text())
    origin=Path(binding['path']).parent
    dispatch=json.loads((root/origin.parent/'dispatch.json').read_text())['calls'][origin.name]
    started=datetime.fromisoformat(dispatch['at']).timestamp()
    for slot, charge in enumerate(ledger['calls'], 1):
        if charge['request_hash'] != wanted:
            continue
        if int(charge['issued_at_ns']) / 1e9 < started:
            continue  # Historical responses belong to their retained earlier attempt.
        folder = root/base/'provider-evidence'/f'{slot}-{wanted[:16]}'
        pointer = evidence_file(folder/'manifest.json', root)
        manifest = read_evidence(pointer, root)
        require(manifest['allowance_slot'] == slot and manifest['request_hash'] == wanted
            and manifest['complete_output_present'] is False, 'Rejected request has output or different charge')
        contents = {}
        for name, entry in manifest['files'].items():
            require(Path(name).name == name, 'Unsafe provider receipt filename')
            data = (folder/name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == entry['retained_sha256'], 'Provider receipt changed')
            contents[name] = data
        require(json.loads(contents['request.json']) == wire['request']
            and json.loads(contents['schema.json']) == wire['schema'], 'Rejected wire contract differs')
        events = [json.loads(line) for line in contents['events.jsonl'].splitlines() if line.strip()]
        require(any(e.get('type') == 'turn.failed' for e in events)
            and not any(e.get('type') == 'turn.completed' or e.get('item', {}).get('type') == 'agent_message'
                        for e in events), 'Rejection is not terminal and output-free')
        errors = [str(e.get('message','')) for e in events if e.get('type') == 'error']
        errors += [str(e.get('error',{}).get('message','')) for e in events if e.get('type') == 'turn.failed']
        require(errors and all('invalid_request' in e for e in errors)
            and not any(re.search(r'safety|cannot comply|unauthori[sz]ed|authentication|quota', e, re.I) for e in errors),
            'Failure is not the reviewed generic invalid_request')
        receipts.append(pointer)
        break  # The first charged packet after this reservation is this attempt.
    require(receipts, 'Missing exact no-output invalid-request receipt')
    return receipts


def diagnose(root, checkpoint, *, provider_directory, predecessor=None):
    """Choose one correction/replay per failed key, retaining all other roots."""
    root = Path(root)
    value = deepcopy(checkpoint)
    config = value['account_recovery']
    previous = read_evidence(predecessor, root).get('failure_recovery', {}) if predecessor else {}
    spent = set(previous.get('attempted_keys', []))
    current = read_evidence(value['dispatch'], root)['calls']
    spent.update(k for k in previous.get('actions', {}) if k in current)
    actions, held, failures = {}, set(), {}
    for key in config['failed_calls']:
        refs = config['originals'][key]
        request, result = (read_evidence(refs[n], root) for n in ('request','result'))
        schema = read_evidence(refs['schema'], root)
        reason = str(result.get('reason',''))
        root_key = account_recovery.KEY.fullmatch(key).group(1)
        category = 'UNREVIEWED_FAILURE'
        from . import account_gap_preservation
        entry = value.get('completed_account_receipts', {}).get(key)
        if entry and entry.get('profile') == account_gap_preservation.PROFILE:
            account_gap_preservation.checked(root, value, key, entry)
            category = 'REVIEWED_GAP_PRESERVATION_REASSESSMENT'
            actions[key] = 'REASSESS_COMPLETE_RESPONSE'
        elif reason == NUMBERED:
            category = 'REFERENCE_FORMAT'
            if key not in spent and 'account_correction' not in request:
                actions[key] = 'CORRECT_REFERENCE_FORMAT'
        elif result.get('error') == 'E_DEPENDENCY' and 'invalid_request' in reason:
            category = 'PROVIDER_INVALID_REQUEST_CAUSE_UNKNOWN'
            if key not in spent:
                binding=evidence_file(root/Path(refs['request']['path']).parent/'reference-binding.json',root)
                receipts = invalid_request_receipts(root, provider_directory, request, schema,binding)
                value.setdefault('recoverable_failures', {})[key] = dict(result=refs['result'], receipts=receipts,wire_binding=binding)
                actions[key] = 'EXACT_NO_OUTPUT_REPLAY'
        if key not in actions:
            held.add(root_key)
        failures[key] = dict(category=category, action=actions.get(key,'HOLD_FOR_REVIEW'),
            result=refs['result'], root=root_key)
    # An exhausted child prevents its parent. Other roots remain independently repairable.
    actions = {k:a for k,a in actions.items() if account_recovery.KEY.fullmatch(k).group(1) not in held}
    config['held_roots'] = sorted(held)
    value['recoverable_failures'] = {k:v for k,v in value.get('recoverable_failures',{}).items() if k in actions}
    value['failure_recovery'] = dict(profile=PROFILE, actions=actions, attempted_keys=sorted(spent),
        failures=failures, provider_directory=str(provider_directory), provider_calls_authorized=0,
        maximum_repairs_per_request=1, held_roots=sorted(held))
    for key, row in failures.items():
        if key not in actions: row['action'] = 'HOLD_FOR_REVIEW'
    return value


def validate(root, value):
    policy = value['failure_recovery']
    require(policy['profile'] == PROFILE and policy['provider_calls_authorized'] == 0
        and policy['maximum_repairs_per_request'] == 1, 'Unknown bounded failure recovery')
    stripped = deepcopy(value)
    stripped.pop('failure_recovery')
    stripped.pop('recoverable_failures', None)
    stripped['account_recovery'].pop('held_roots', None)
    expected = diagnose(root, stripped, provider_directory=policy['provider_directory'],
        predecessor=value.get('predecessor_recovery'))
    require(value == expected, 'Failure recovery changed its authenticated finite diagnosis')


def held_result(root, reference, key, request, input_hash):
    value = read_evidence(reference, root)
    if key not in value['account_recovery'].get('held_roots', []):
        return None
    value = account_recovery.load(root, reference, input_hash)
    require(account_recovery.assignment(request) == value['account_recovery']['contracts'][key],
        'Held failure changed its original requirement')
    identifier = request['required_considered'][0]
    details = read_evidence(value['account_recovery']['details'], root)
    result = next(r['result'] for r in details if r['id'] == identifier)
    require(result['status'] == 'FAILED', 'Held failure cannot replace success')
    return deepcopy(result)
