"""Revalidate exact canary responses after the decoded-budget check correction."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json

from jsonschema import validate
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_service_continuation import DELAY_WORK, SERVICE_CONTINUATION_POLICY, USER
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_references import prepare, resolve

WORK = DELAY_WORK/'canary-validation'
REVIEW = WORK/'review.md'
RETRY = ('current-binding', 'live-approval', 'continuation-review')
ACQUIRE = tuple('acquire-'+q for q in QUESTIONS)
REOPEN = RETRY + ACQUIRE
MUTATED = {str(PLAN), 'scripts/legal_integration_campaign.py', 'scripts/legal_integration_current_live.py',
    'scripts/legal_integration_service_continuation.py', 'scripts/legal_mission_execution.py',
    'scripts/legal_mission_control.py'}


def archives(rows, *, mission=False):
    paths = MUTATED | ({str(PROGRAM)} if mission else set())
    return {(r['previous']['path'], r['previous']['sha256']): r['archive']
            for r in rows if r['previous']['path'] in paths}


def capture():
    """Bind all eight completed responses, including their original failures."""
    directory = DELAY_WORK/'live/canaries/calls'
    dispatch = read(ROOT/directory/'dispatch.json')
    require(set(dispatch['calls']) == {f'canary-{kind}-{q}' for q in QUESTIONS for kind in ('read', 'review')}
        and all(r['status'] in ('VALIDATED', 'FAILED') for r in dispatch['calls'].values()),
        'Canary response population is incomplete or unsettled')
    calls = {}
    for key in dispatch['calls']:
        calls[key] = {name: ref(ROOT, directory/key/(name+'.json')) for name in
                      ('request', 'schema', 'result', 'raw', 'wire-response', 'reference-binding')}
        wire = read(ROOT/calls[key]['wire-response']['path'])
        slot, rh = wire['provenance']['allowance_slot'], wire['provenance']['request_hash']
        calls[key]['provider-receipt'] = ref(ROOT, BASE/'provider-evidence'/f'{slot:04}-{rh[:16]}'/'manifest.json')
    binding = read(ROOT/BASE/'current-binding.json')
    value = {'profile': 'exact-canary-revalidation.v1', 'dispatch': ref(ROOT, directory/'dispatch.json'),
        'source': binding['source'], 'calls': calls,
        'inputs': {q: ref(ROOT, DELAY_WORK/'live/canary-inputs'/(q+'.json')) for q in QUESTIONS},
        'scope': 'Exact returned canary responses; validate again without a new model call.'}
    save(ROOT/WORK/'retained-canaries.json', value)
    return value


def revalidate(service, directory, reference):
    from scripts import legal_integration_campaign as campaign
    from legalmath.interpretation.assurance.integration_contract import read_evidence
    receipt = read_evidence(reference, ROOT)
    require(receipt['profile'] == 'exact-canary-revalidation.v1'
        and receipt['source'] == ref(ROOT, campaign.ENVELOPE), 'Canary source changed')
    dispatch = read_evidence(receipt['dispatch'], ROOT)
    product = campaign.session(directory/'revalidation', service, maximum=8)
    require(dispatch['input_hash'] == product.route.input_hash, 'Canary input identity changed')
    ledger = read(ROOT/BASE/'live-calls.json')
    outcomes = {}
    def one_question(q):
        inputs = read_evidence(receipt['inputs'][q], ROOT)
        # The new current binding must prepare exactly the same canary inputs.
        require(inputs == read(ROOT/campaign.CANARIES/(q+'.json')), 'Prepared canary changed')
        values = {}
        for kind in ('read', 'review'):
            key = f'canary-{kind}-{q}'
            files = receipt['calls'][key]
            retained = {name: read_evidence(r, ROOT) for name, r in files.items()}
            old = dispatch['calls'][key]
            request, schema = retained['request'], retained['schema']
            packet = inputs['reading']
            expected = (packet['request'], packet['schema']) if kind == 'read' else (inputs['review_request'], inputs['review_schema'])
            require((request, schema) == expected and old['identity'] == product.dispatch.request_identity(request, schema),
                'Canary request/schema/provider changed')
            require(digest(retained['result']) == old['result_hash'] and old['status'] == retained['result']['status'],
                'Original canary disposition changed')
            require(old['status'] == 'VALIDATED' or (kind == 'read'
                and retained['result'].get('error') == 'E_RESOURCE_LIMIT'
                and retained['result'].get('reason') == 'Response exceeds declared budget'),
                'Canary failed for an unreviewed reason')
            # The original review dispatch used AUDIT, before canonical JSON
            # sorted its property keys. prepare() preserves that insertion order
            # in required arrays. Reconstruct the exact original transport, while
            # still requiring equality with the retained schema.
            if kind == 'review':
                require(schema == campaign.AUDIT, 'Canary runtime review schema changed')
            prepared = prepare(request, campaign.AUDIT if kind == 'review' else schema)
            require(prepared == retained['reference-binding'], 'Canary reference expansion changed')
            wire, raw = retained['wire-response'], retained['raw']
            wire_value, value = wire['value'], raw['value']
            validate(wire_value, prepared['schema'])
            data = canonical(wire_value)
            require(len(data) <= product.route.limits.output_bytes
                and len(product.route.encode(data.decode())) <= product.route.limits.output_tokens,
                'Wire output exceeds its unchanged limit')
            require(resolve(wire_value, prepared, maximum_bytes=product.route.limits.decoded_output_bytes) == value,
                'Canary decoded output differs from retained wire output')
            proof = retained['provider-receipt']
            slot, rh = wire['provenance']['allowance_slot'], digest(prepared['request'])
            require(proof['complete_output_present'] and proof['allowance_slot'] == slot
                and proof['request_hash'] == rh == wire['provenance']['request_hash']
                and ledger['calls'][slot-1]['request_hash'] == rh, 'Canary provider receipt differs')
            provider_directory = (ROOT/files['provider-receipt']['path']).parent
            for name in ('request.json', 'schema.json', 'result.json', 'events.jsonl'):
                require(hashlib.sha256((provider_directory/name).read_bytes()).hexdigest()
                    == proof['files'][name]['retained_sha256'], 'Canary provider evidence changed')
            require(read(provider_directory/'request.json') == prepared['request']
                and read(provider_directory/'schema.json') == prepared['schema'],
                'Canary provider request/schema differs')
            require(read(provider_directory/'result.json') == wire_value, 'Retained response differs from provider output')
            events = [json.loads(line) for line in (provider_directory/'events.jsonl').read_text().splitlines() if line.strip()]
            require(any(e.get('type') == 'turn.completed' for e in events), 'Canary turn did not complete')
            validate(value, schema)
            decoded = canonical(value)
            require(len(decoded) <= product.route.limits.decoded_output_bytes
                and len(product.route.encode(decoded.decode())) <= product.route.limits.decoded_output_tokens,
                'Decoded response exceeds its unchanged limit')
            if kind == 'read':
                campaign.validate_canary_read(product, packet, value)
            else:
                require(set(value['considered']) == set(request['required_considered']), 'Canary lost source coverage')
                product.citations(value, request['records'])
                require(value['verdict'] != 'ACCEPT', 'Reviewer accepted deliberately unsupported compliance')
            values[kind] = {'status': 'VALIDATED', **raw, 'request_hash': digest(request),
                'revalidation': {'original_result': files['result'], 'wire': files['wire-response'],
                    'provider_receipt': files['provider-receipt'],
                    'evidence_class': 'REVALIDATED_EXACT_RESPONSE; NOT_A_NEW_MODEL_SAMPLE'}}
        return {'reading': values['read'], 'review': values['review'], 'passed': True}
    for q in QUESTIONS:
        try:
            outcomes[q] = one_question(q)
        except Exception as exc:
            outcomes[q] = {'passed': False, 'reason': str(getattr(exc, 'details', None) or exc)}
    save(directory/'canary-results.json', outcomes)
    return outcomes


def expected_program(old, before, revision, root, *, plan_reference=None):
    result = deepcopy(old)
    result['canary_validation_repair'] = revision
    result['protected_evidence'] += [revision[k] for k in ('review', 'baseline', 'local_review', 'canaries')]
    result['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for task in result['tasks']:
        if task['id'] not in REOPEN:
            continue
        number = len(before['tasks'][task['id']]['attempts']) + 1
        task.update(maximum_attempts=number, deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] += [revision['review'], revision['local_review']]
        if task['id'] == 'live-approval':
            task['acceptance'] = 'Same eight returned canary responses pass unchanged wire/decoded/source/review checks; zero new model calls.'
    return result


def validate_revision(program, root, *, plan_reference=None):
    revision = program['canary_validation_repair']
    require(revision.get('profile') == 'integration-canary-validation-repair.v1'
        and revision.get('prior_detours') == 33 and revision.get('additional_consolidated_revision') == 1
        and revision.get('live_calls_added') == 0 and revision.get('attempts_reset') is False
        and revision.get('user_instruction') == USER and revision.get('reopened_nodes') == list(REOPEN)
        and revision.get('service_recovery_policy') == SERVICE_CONTINUATION_POLICY,
        'Unreviewed canary validation repair')
    for key in ('review', 'baseline', 'local_review', 'canaries', 'checkpoints',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old, before = read(root/revision['prior_program']['path']), read(root/revision['prior_state']['path'])
    baseline = read(root/revision['baseline']['path'])
    require(old.get('retry_delay_repair') and not old.get('canary_validation_repair')
        and before['program_hash'] == digest(old) and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()),
        'Unsettled canary baseline')
    require(before['tasks']['semantic-preflight']['status'] == 'SUCCEEDED'
        and len(before['tasks']['semantic-preflight']['attempts']) == 8
        and before['tasks']['continuation-review']['status'] == 'SUCCEEDED', 'Semantic evidence not settled')
    for tid in ACQUIRE:
        require(before['tasks'][tid].get('dispatch_status') == 'NOT_DISPATCHED'
            and len(before['tasks'][tid]['attempts']) == 3, 'Acquisition attempt already consumed')
    require(revision['checkpoints'] == old['retry_delay_repair']['checkpoints']
        and revision['semantic_stage_maximum'] == old['retry_delay_repair']['semantic_stage_maximum'],
        'Retained semantic setup changed')
    require(len(read(root/revision['prior_ledger']['path'])['calls']) == baseline['calls'], 'Lost prior charges')
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, archives(baseline['archived']))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Canary repair changed unrelated owners or resources')
    local = read(root/revision['local_review']['path'])
    require(local.get('verdict') == 'PASS' and local.get('provider_calls') == 0, 'Missing canary repair review')
    for evidence in local['evidence']:
        verify(root, evidence)
    return {task['id']: task['maximum_attempts'] for task in program['tasks']}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a')); fcntl.flock(handle, fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            return {'registered': True, 'resumed': True}
        baseline = read(ROOT/WORK/'baseline.json')
        refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC/'mission.json', BASE/'current-binding.json', BASE/'live-calls.json'):
            require(ref(ROOT, path)['sha256'] == refs[str(path)]['sha256'], 'Baseline changed: '+str(path))
        old, state = read(ROOT/PROGRAM), read(ROOT/STATE)
        revision = {'profile': 'integration-canary-validation-repair.v1', 'prior_detours': 33,
            'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
            'user_instruction': USER, 'review': ref(ROOT, REVIEW), 'baseline': ref(ROOT, WORK/'baseline.json'),
            'local_review': ref(ROOT, WORK/'local-review.json'), 'canaries': ref(ROOT, WORK/'retained-canaries.json'),
            'checkpoints': old['retry_delay_repair']['checkpoints'],
            'semantic_stage_maximum': old['retry_delay_repair']['semantic_stage_maximum'],
            'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
            'prior_binding': refs[str(BASE/'current-binding.json')], 'prior_ledger': refs[str(BASE/'live-calls.json')],
            'reopened_nodes': list(REOPEN), 'service_recovery_policy': SERVICE_CONTINUATION_POLICY}
        program = expected_program(historical_projection(old, archives(baseline['archived'])), state, revision, ROOT)
        validate_program(program, ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING', reason='Reviewed canary revalidation; no completed response resampling')
            for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'):
                state['tasks'][tid].pop(key, None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_CANARY_VALIDATION_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT/DOC/'mission.json'), archives(baseline['archived'], mission=True))
        stage = ROOT/WORK/'registration-stage'
        save(stage/'program.json', program); save(stage/'state.json', state)
        program_ref = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage/'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=program_ref, plan=ref(ROOT, PLAN), canary_validation_repair=revision)
        for key in ('prerequisite_repair', 'execution_refresh', 'execution_recovery', 'service_continuation', 'retry_delay_repair'):
            master[key] = program[key]
        reason = 'Revalidate the same returned canary evidence with the correct decoded check; retain successful semantics and continue independent original acquisitions.'
        mission['history'].append({'id': 'integration-master-canary-validation-repair-2026-10-14',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed local canary validation correction; no model resampling or budget increase.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [program_ref, revision['review'], revision['baseline'], revision['local_review']]})
        mission['next_task_reason'] = reason; save(stage/'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage/name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC/'mission.json', 'mission.json'))]
        save(ROOT/journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 34, 'reopened_nodes': list(REOPEN), 'live_calls_added': 0}


def verification(directory=None):
    program = read(ROOT/PROGRAM); validate_program(program, ROOT)
    revision = program['canary_validation_repair']
    before, state = read(ROOT/revision['prior_state']['path']), read(ROOT/STATE)
    ledger, prior = read(ROOT/BASE/'live-calls.json'), read(ROOT/revision['prior_ledger']['path'])
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Historical attempts changed')
    require(state['tasks']['semantic-preflight'] == before['tasks']['semantic-preflight'], 'Successful semantic result changed')
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Historical charges changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    value = {'profile': 'canary-validation-verification.v1', 'old_attempts_preserved': True,
        'old_calls_preserved': True, 'calls': len(ledger['calls']), 'detours': 34,
        'execution': view['execution'], 'ready': view['ready'], 'running': view['running'],
        'blocked': view['blocked'], 'integration_complete': False,
        '_conclusion': 'Canary validation and exact histories verified; original answers and tool effects remain separate.'}
    save((directory or ROOT/WORK)/'verification.json', value)
    return value
