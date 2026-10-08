"""Finite role-level continuation of the original 492-pair coverage program."""
import argparse
from collections import Counter
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2 as fidelity
from legalmath.interpretation.assurance import scoped_investigation as scoped
from legalmath.interpretation.assurance import executable_references_v2 as executable
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.interpretation.assurance.integrated import implementation_identity
from legalmath.interpretation.assurance.optional_tools import ToolSession
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider, Completion
from scripts import legal_coverage_candidates as codec
from scripts import legal_integration_coverage as prior
from scripts.legal_integration_tools import ProductToolBackend

ROOT = prior.ROOT
BASE = prior.OUT
OUT = BASE / 'additional-200-calls-100-repairs'
PLAN = ROOT / 'docs/plans/legal-integration-coverage-resumption.md'
DEADLINE = prior.DEADLINE
AUTHORIZATION = 'you have 100 more repairs and 200 more calls. continue'
ACTIONS = ('resume-check', 'resume-test', 'resume-execute', 'resume-status', 'resume-verify', 'resume-repair')
FILES = list(dict.fromkeys([*prior.FILES, 'scripts/legal_coverage_candidates.py',
    'scripts/legal_coverage_resume.py', 'tests/assurance/test_coverage_resume.py']))
TESTS = [*prior.TESTS, 'tests/assurance/test_coverage_resume.py']
read, save, immutable = prior.read, prior.save, prior.immutable


def ref(path):
    return {'path': str(Path(path).relative_to(ROOT)), 'sha256': raw_digest(Path(path).read_bytes())}


def checked(item):
    path = ROOT / item['path']
    if raw_digest(path.read_bytes()) != item['sha256']:
        raise LegalMathError('E_INTEGRITY', details='Changed evidence: ' + item['path'])
    return path


class ResumeAllowance(GrantedAllowance):
    def __init__(self, batch, role, purpose='combined', grant_path=None):
        self.grant_path = Path(grant_path or OUT / 'authorization.json')
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = read(self.grant_path)
        self.path = self.grant_path.parent / 'allowance.json'
        self.maximum = self.reservation_ceiling = 200
        self.batch, self.role, self.purpose = batch, role, purpose
        self.verify()

    def verify(self):
        g = self.grant
        if (self.grant_path.read_bytes() != self.grant_bytes or
                g.get('schema') != 'legalmath.coverage-resumption-grant.v1' or
                g.get('authorization') != AUTHORIZATION or g.get('maximum') != 200 or
                g.get('repair_maximum') != 100 or g.get('deadline_epoch') != DEADLINE or
                not g.get('predecessor') or type(self.batch) is not int or not 17 <= self.batch <= 40 or
                self.role not in scoped.PERSPECTIVES or self.purpose not in ('combined', 'repair')):
            raise LegalMathError('E_AUTHORITY', details='Changed resumption grant')
        for item in g['predecessor']:
            checked(item)
        value = read(self.path) if self.path.exists() else {'maximum': 200, 'calls': []}
        if (set(value) != {'maximum', 'calls'} or value['maximum'] != 200 or
                not isinstance(value['calls'], list) or len(value['calls']) > 200):
            raise LegalMathError('E_INTEGRITY', details='Invalid resumption ledger')
        for row in value['calls']:
            if (set(row) != {'batch', 'role', 'purpose', 'request_hash', 'issued_at_ns'} or
                    type(row['batch']) is not int or not 17 <= row['batch'] <= 40 or
                    row['role'] not in scoped.PERSPECTIVES or row['purpose'] not in ('combined', 'repair') or
                    not isinstance(row['request_hash'], str) or not re.fullmatch('[a-f0-9]{64}', row['request_hash']) or
                    not isinstance(row['issued_at_ns'], str) or not row['issued_at_ns'].isdigit()):
                raise LegalMathError('E_INTEGRITY', details='Invalid resumption reservation')
        return {'grant_id': g['schema'], 'grant_hash': raw_digest(self.grant_bytes),
                'maximum': 200, 'used': len(value['calls']), 'deadline_epoch': DEADLINE}

    def reserve(self, request_hash):
        if not isinstance(request_hash, str) or not re.fullmatch('[a-f0-9]{64}', request_hash):
            raise LegalMathError('E_SCHEMA')
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = self.verify()
            if state['used'] >= 200 or time.time() + 5 >= DEADLINE:
                raise LegalMathError('E_RESOURCE_LIMIT', details='New grant or original expiry exhausted')
            value = read(self.path) if self.path.exists() else {'maximum': 200, 'calls': []}
            value['calls'].append({'batch': self.batch, 'role': self.role, 'purpose': self.purpose,
                'request_hash': request_hash, 'issued_at_ns': str(time.time_ns())})
            temporary = self.path.with_suffix('.tmp')
            temporary.write_bytes(canonical(value)); temporary.replace(self.path)
            return len(value['calls'])


class CandidateProvider(CodexProvider):
    provider_id = codec.PROFILE

    def __init__(self, directory, expected_dispatch=None, timeout_limit=300, **kwargs):
        super().__init__(**kwargs)
        self.directory = Path(directory)
        self.expected_dispatch = expected_dispatch
        if timeout_limit not in (300, 450) or (timeout_limit != 300 and expected_dispatch is None):
            raise LegalMathError('E_SCHEMA', details='Extended cap needs a request-bound reviewed recovery')
        self.timeout_limit = timeout_limit

    def complete(self, request, schema, settings):
        wire, output_schema, binding = codec.prepare(request, schema)
        if self.expected_dispatch is not None and self.expected_dispatch != {
                'request_hash': digest(wire), 'schema_hash': digest(output_schema)}:
            raise LegalMathError('E_INTEGRITY', details='Recovery request or schema differs from reviewed dispatch')
        target = self.directory / digest(request)
        if (target / 'started.json').exists():
            raise LegalMathError('E_JOB_STATE', details='Uncertain prior dispatch cannot be repeated')
        immutable(target / 'original-request.json', request)
        immutable(target / 'original-schema.json', schema)
        immutable(target / 'binding.json', binding)
        immutable(target / 'output-schema.json', output_schema)
        immutable(target / 'wire-request.json', wire)
        if len(canonical(wire)) > settings.max_input_bytes:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Candidate-bound request exceeds input cap')
        seconds = min(settings.timeout_seconds, self.timeout_limit, int(DEADLINE - time.time()))
        if seconds < 5:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Original deadline exhausted')
        immutable(target / 'started.json', {'wire_hash': digest(wire), 'request_hash': digest(request)})
        print(json.dumps({'dispatch': self.allowance.purpose, 'batch': self.allowance.batch,
            'perspective': self.allowance.role, 'new_grant_calls_before': self.allowance.verify()['used'],
            'request_bytes': len(canonical(wire))}), flush=True)
        answer = super().complete(wire, output_schema, settings.model_copy(update={'timeout_seconds': seconds}))
        immutable(target / 'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
        value = codec.resolve(answer.value, request, schema, binding)
        immutable(target / 'expanded-response.json', value)
        return Completion(value, {**answer.provenance, 'response_hash': digest(value),
            'candidate_response_profile': codec.PROFILE, 'candidate_binding': ref(target / 'binding.json'),
            'wire_response_hash': answer.provenance['response_hash']})


def review_path():
    return sorted(OUT.glob('review-v*.json'), key=lambda p: int(p.stem.rsplit('v', 1)[1]))[-1]


def check_review():
    review = read(review_path())
    for key in ('plan', 'authorization', 'predecessor', 'source_manifest'):
        checked(review[key])
    for row in read(checked(review['source_manifest'])):
        checked(row['live']); checked(row['copy'])
    if review.get('previous_review'):
        previous = read(checked(review['previous_review']))
        for row in read(checked(previous['source_manifest'])):
            if ref(checked(row['copy']))['sha256'] != row['live']['sha256']:
                raise LegalMathError('E_INTEGRITY', details='Previous reviewed source snapshot changed')
    if review.get('recovery'):
        spec = read(checked(review['recovery']))
        checked(spec['note']); checked(spec['previous']); checked(spec['transport'])
    if (review['implementation'] != implementation_identity() or
            review['route'] != CodexProvider().routing or review['backend'] != ProductToolBackend().identity()):
        raise LegalMathError('E_STALE_REVIEW', details='Method, route or tools changed')
    ResumeAllowance(17, 'qualification-first').verify()
    repairs = read(OUT / 'repairs.json')
    if repairs['maximum'] != 100 or len(repairs['repairs']) > 100:
        raise LegalMathError('E_INTEGRITY', details='Repair ceiling changed')
    return review


def historical():
    checkpoint = read(OUT / 'predecessor-checkpoint.json')
    for item in checkpoint.values():
        checked(item)
    old_review = read(checked(checkpoint['review']))
    # Compare historical source to its frozen copy, not a changed entry point.
    copies = {}
    for row in read(checked(checkpoint['source_manifest'])):
        copied = checked(row['copy'])
        if raw_digest(copied.read_bytes()) != row['live']['sha256']:
            raise LegalMathError('E_INTEGRITY', details='Historical snapshot differs from its original source')
        copies[row['live']['path']] = row['copy']
    for item in old_review['files']:
        if item['path'] not in copies or copies[item['path']]['sha256'] != item['sha256']:
            raise LegalMathError('E_INTEGRITY', details='Historical review is not backed by its source snapshot')
    inputs = read(BASE / 'inputs.json'); spec = read(BASE / 'partition.json')
    checked(old_review['inputs']); checked(old_review['partition'])
    rows = read(checked(checkpoint['batches']))
    for row in rows:
        receipt = read(checked(row['receipt']))
        if receipt != row['value']:
            raise LegalMathError('E_INTEGRITY')
        base = BASE / 'batches' / receipt['arm'] / f"{receipt['batch']:02}"
        actual, _ = prior.latest_receipt(base)
        if actual != receipt:
            raise LegalMathError('E_INTEGRITY', details='Historical selected receipt changed')
        if receipt.get('result'):
            result = read(checked(receipt['result']))
            if prior.validate_result(result, inputs, spec['batches'][receipt['batch']]) != receipt['complete']:
                raise LegalMathError('E_INTEGRITY', details='Historical completion claim changed')
            prior.verify_journal(checked(row['receipt']).parent / 'scoped/model')
    return inputs, spec, rows


def selected_roles(rows):
    selected = {}
    for row in rows:
        receipt = row['value']
        if receipt['arm'] != 'combined' or not receipt.get('result'):
            continue
        for batch in read(checked(receipt['result']))['batches']:
            proposals = iter(batch['proposals'])
            for attempt in batch['attempts']:
                if attempt['status'] == 'VALIDATED_PROPOSAL':
                    selected[(receipt['batch'], attempt['role'])] = {
                        'proposal': next(proposals), 'receipt': row['receipt'], 'origin': 'predecessor'}
    return selected


def role_directory(batch, role):
    return OUT / 'roles' / f'{batch:02}' / role


def role_valid(proposal, inputs, pairs):
    value = fidelity.validate(proposal, inputs['packet'], inputs['claims'], inputs['candidates'], inputs['questions'], pairs)
    return all(r[k]['status'] != 'UNASSESSED' for r in value['checks'] for k in
               ('source_support', 'question_relation', 'executable_correspondence', 'authority'))


def record_repair(reason, evidence, *, kind='response-recovery'):
    path = OUT / 'repairs.json'
    value = read(path)
    if value['maximum'] != 100 or len(value['repairs']) >= 100:
        raise LegalMathError('E_RESOURCE_LIMIT', details='New repair grant exhausted')
    entry = {'id': len(value['repairs']) + 1, 'kind': kind, 'reason': reason,
             'evidence': evidence, 'recorded_epoch': time.time()}
    value['repairs'].append(entry); save(path, value)
    return entry


def role_tools(directory):
    recovery = read(directory / 'started.json').get('recovery')
    if recovery is None:
        return directory / 'tools'
    spec = read(checked(recovery))
    return role_tools(checked(spec['previous']).parent)


def verify_role(path, inputs, pairs):
    receipt = read(path)
    for item in receipt['evidence']:
        checked(item)
    if receipt.get('proposal') is not None:
        if role_valid(receipt['proposal'], inputs, pairs) != receipt['complete']:
            raise LegalMathError('E_INTEGRITY', details='Role completion changed')
    elif receipt['complete']:
        raise LegalMathError('E_INTEGRITY', details='Complete role has no proposal')
    binding = read(path.parent / 'model/journal.json')['value']['binding']
    EvidenceJournal(path.parent / 'model', binding['inputs'], **{k: binding[k] for k in
        ('maximum_actions', 'maximum_per_issue', 'deadline_seconds')}).report()
    if receipt.get('tools'):
        report = ToolSession(ProductToolBackend(), role_tools(path.parent)).report()
        if report != read(checked(receipt['tools'])):
            raise LegalMathError('E_INTEGRITY', details='Tool report changed')
    return receipt


def latest_role(folder, inputs, pairs):
    """Verify every attempt and fail closed on an interrupted or unselected one."""
    attempts = sorted(folder.glob('attempt-*'))
    if [p.name for p in attempts] != [f'attempt-{i:02}' for i in range(1, len(attempts) + 1)]:
        raise LegalMathError('E_INTEGRITY', details='Noncontiguous role recovery history')
    paths = [folder / 'receipt.json', *[p / 'receipt.json' for p in attempts]]
    previous = None
    for index, path in enumerate(paths):
        if not path.is_file():
            raise LegalMathError('E_JOB_STATE', details='Role attempt has no receipt; no automatic redispatch')
        value = verify_role(path, inputs, pairs)
        if (value['batch'], value['role']) != (int(folder.parent.name), folder.name):
            raise LegalMathError('E_INTEGRITY', details='Foreign role receipt')
        if index:
            start = read(path.parent / 'started.json')
            spec = read(checked(start['recovery']))
            if (spec['previous'] != ref(paths[index - 1]) or spec['attempt'] != index or
                    (spec['batch'], spec['role']) != (value['batch'], value['role']) or previous['complete']):
                raise LegalMathError('E_INTEGRITY', details='Invalid role successor')
        previous = value
    pointer = folder / 'latest.json'
    if attempts:
        if not pointer.exists():
            raise LegalMathError('E_JOB_STATE', details='Finished recovery needs explicit receipt selection')
        if checked(read(pointer)['receipt']) != paths[-1]:
            raise LegalMathError('E_INTEGRITY', details='Selection omits or substitutes a role attempt')
    elif pointer.exists():
        raise LegalMathError('E_INTEGRITY', details='Role pointer has no recovery attempt')
    return previous, paths[-1]


def validate_recovery(spec, inputs, pairs):
    """Verify the exact reviewed failure; never infer retry authority from a budget."""
    timeout = spec.get('kind') == 'local-deadline-no-output'
    if (spec.get('kind') not in ('returned-http-502-no-output', 'local-deadline-no-output') or
            type(spec.get('attempt')) is not int or
            spec['attempt'] < 1 or spec.get('maximum_calls') != 1):
        raise LegalMathError('E_JOB_STATE', details='No reviewed bounded service recovery')
    if spec.get('timeout_seconds', 300) != (450 if timeout else 300):
        raise LegalMathError('E_JOB_STATE', details='Recovery timeout differs from the reviewed bounded remedy')
    previous = checked(spec['previous']); checked(spec['note'])
    folder = role_directory(spec['batch'], spec['role'])
    expected = folder if spec['attempt'] == 1 else folder / f"attempt-{spec['attempt'] - 1:02}"
    if previous != expected / 'receipt.json':
        raise LegalMathError('E_INTEGRITY', details='Recovery predecessor is not the preceding role attempt')
    receipt = verify_role(previous, inputs, pairs)
    failure = receipt.get('stopped') or {}
    details = failure.get('details', '')
    if (receipt['complete'] or receipt.get('proposal') is not None or receipt['calls'] != 1 or
            (receipt['batch'], receipt['role']) != (spec['batch'], spec['role'])):
        raise LegalMathError('E_JOB_STATE', details='Failure is not an empty-output charged role')
    journal_value = read(previous.parent / 'model/journal.json')['value']
    if timeout:
        checked(spec['termination_source'])
        if (spec['termination_source'] != ref(ROOT / 'src/legalmath/interpretation/search/providers.py') or
                failure.get('error') != 'E_RESOURCE_LIMIT' or details != 'Codex call deadline' or
                receipt.get('wall_seconds', 0) < 300 or
                journal_value['binding']['inputs']['settings']['timeout_seconds'] != 300):
            raise LegalMathError('E_JOB_STATE', details='Failure is not a reviewed terminated 300-second timeout')
    elif (failure.get('error') != 'E_DEPENDENCY' or not isinstance(details, str) or
            not details.startswith('unexpected status 502 Bad Gateway:')):
        raise LegalMathError('E_JOB_STATE', details='Failure is not the reviewed returned HTTP 502')
    journal = journal_value['actions']
    if (len(journal) != 1 or journal[0]['status'] != 'FAILED' or
            journal[0].get('error') != failure['error'] or journal[0].get('details') != details):
        raise LegalMathError('E_INTEGRITY', details='Failure differs from the completed journal')
    transport = checked(spec['transport'])
    manifest = read(transport)
    if (manifest.get('complete_output_present') is not False or 'result.json' in manifest['files'] or
            (transport.parent / 'result.json').exists() or manifest['request_hash'] != spec['dispatch']['request_hash'] or
            manifest['files']['schema.json']['original_sha256'] != spec['dispatch']['schema_hash']):
        raise LegalMathError('E_JOB_STATE', details='Transport is not the reviewed empty-output failure')
    for name, hashes in manifest['files'].items():
        if raw_digest((transport.parent / name).read_bytes()) != hashes['retained_sha256']:
            raise LegalMathError('E_INTEGRITY', details='Changed failed transport evidence')
    events = [json.loads(line) for line in (transport.parent / 'events.jsonl').read_text().splitlines() if line.strip()]
    if timeout:
        if (not any(e.get('type') == 'turn.started' for e in events) or
                any(e.get('type') not in ('thread.started', 'turn.started') for e in events)):
            raise LegalMathError('E_JOB_STATE', details='Timeout transport includes output or another failure')
    elif (not any(e.get('type') == 'turn.failed' and e.get('error', {}).get('message') == details for e in events) or
            any(e.get('type') == 'turn.completed' for e in events)):
        raise LegalMathError('E_JOB_STATE', details='Transport has no matching returned failed turn')
    calls = read(OUT / 'allowance.json')['calls']; slot = manifest['allowance_slot']
    if (not 1 <= slot <= len(calls) or (calls[slot - 1]['batch'], calls[slot - 1]['role'],
            calls[slot - 1]['request_hash']) != (spec['batch'], spec['role'], spec['dispatch']['request_hash'])):
        raise LegalMathError('E_INTEGRITY', details='Recovery transport differs from its charged reservation')
    starts = list((previous.parent / 'candidate-responses').glob('*/started.json'))
    if len(starts) != 1 or read(starts[0])['wire_hash'] != spec['dispatch']['request_hash']:
        raise LegalMathError('E_INTEGRITY', details='Recovery transport is not this failed role request')
    return spec


def run_role(batch, role, inputs, pairs, *, recovery=None):
    check_review()
    target = role_directory(batch, role)
    if recovery is not None:
        spec = validate_recovery(read(checked(recovery)), inputs, pairs)
        if (spec['batch'], spec['role']) != (batch, role) or check_review().get('recovery') != recovery:
            raise LegalMathError('E_STALE_REVIEW', details='Recovery is not the current reviewed action')
        original, selected = latest_role(target, inputs, pairs)
        if ref(selected) != spec['previous'] or original['complete']:
            raise LegalMathError('E_JOB_STATE', details='Reviewed recovery has already been consumed')
        target = target / f"attempt-{spec['attempt']:02}"
    elif target.exists():
        return latest_role(target, inputs, pairs)[0]
    if (target / 'receipt.json').exists():
        return verify_role(target / 'receipt.json', inputs, pairs)
    if (target / 'started.json').exists():
        raise LegalMathError('E_JOB_STATE', details='Started role has no receipt; explicit recovery is required')
    purpose = 'repair' if recovery is not None or batch == 17 else 'combined'
    if recovery is not None:
        repair = record_repair('One request-bound replacement under the exact recovery review: ' + spec['kind'],
                               [recovery, spec['previous'], spec['transport']], kind='service-recovery')
    else:
        repair = record_repair('Replace only batch 17\'s rejected qualification-first perspective with candidate-bound choices.',
            [ref(BASE / 'batches/combined/17/attempt-02/receipt.json')]) if purpose == 'repair' else None
    immutable(target / 'started.json', {'batch': batch, 'role': role, 'review': ref(review_path()),
        'repair': repair, 'pairs': pairs, 'started_epoch': time.time(), 'recovery': recovery})
    candidate_ids = {p[1] for p in pairs}; claim_ids = {p[0] for p in pairs}
    candidates = {k: v for k, v in inputs['candidates'].items() if k in candidate_ids}
    questions = {k: v for k, v in inputs['questions'].items() if k in candidate_ids}
    request = fidelity.request(inputs['packet'], [c for c in inputs['claims'] if c['claim_id'] in claim_ids],
                               candidates, questions, pairs)
    request['investigation'] = {'batch': batch, 'round': 1, 'perspective': role,
        'prior_round_evidence': None,
        'instruction': 'Investigate source support and the exact candidate question separately. Retain conflicting '
                       'explanations; do not force agreement. No peer proposal or prior legal answer is supplied.'}
    timeout_limit = spec.get('timeout_seconds', 300) if recovery is not None else 300
    settings = Settings(timeout_seconds=timeout_limit, max_input_bytes=200000, max_output_bytes=200000)
    provider = CandidateProvider(target / 'candidate-responses', allowance=ResumeAllowance(batch, role, purpose),
                                 expected_dispatch=spec['dispatch'] if recovery is not None else None,
                                 timeout_limit=timeout_limit)
    tools = ToolSession(ProductToolBackend(), role_tools(target))
    journal = EvidenceJournal(target / 'model', {'request': digest(request), 'review': ref(review_path()),
        'settings': settings.model_dump(), 'grant': ref(OUT / 'authorization.json'), 'tools': tools.identity},
        maximum_actions=1, maximum_per_issue=1, deadline_seconds=600)
    began = time.monotonic(); before = provider.allowance.verify()['used']

    def dispatch(work):
        immutable(work / 'request.json', request)
        if recovery is None:
            tools.candidates(inputs['packet'], candidates)
            wire = compact_request(tools.augment(request), profile='v2')
        else:
            previous_work = checked(spec['previous']).parent / 'model/action-0000'
            if read(previous_work / 'request.json') != request:
                raise LegalMathError('E_INTEGRITY', details='Recovery original request changed')
            # Preserve exact, verified tool evidence, including its original paths.
            wire = read(previous_work / 'wire-request.json')
        immutable(work / 'wire-request.json', wire)
        answer = executable.complete(provider, wire, fidelity.FidelityV2.model_json_schema(), settings,
            work / 'source-references', readings=candidates, questions=questions, input_profile='readable-tables.v1')
        immutable(work / 'response.json', {'value': answer.value, 'provenance': answer.provenance})
        value = fidelity.validate(answer.value, inputs['packet'], inputs['claims'], inputs['candidates'],
                                  inputs['questions'], pairs)
        return {'proposal': value, 'provenance': answer.provenance}

    try:
        value, journal_receipt = journal.execute('scoped-fidelity', {'request': request}, dispatch,
                                                issue=f'batch.{batch}.{role}')
        complete = role_valid(value['proposal'], inputs, pairs)
        receipt = {'complete': complete, 'proposal': value['proposal'], 'journal_receipt': journal_receipt,
                   'stopped': None if complete else {'kind': 'UNASSESSED_DIMENSION'}}
    except Exception as exc:
        failure = {'kind': 'ROLE_REJECTED_OR_DISPATCH_FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
                   'details': getattr(exc, 'details', None) or str(exc)}
        immutable(target / 'failure.json', failure)
        receipt = {'complete': False, 'proposal': None, 'stopped': failure}
    immutable(target / 'tools-report.json', tools.report())
    receipt.update(batch=batch, role=role, purpose=purpose,
        calls=provider.allowance.verify()['used']-before, wall_seconds=time.monotonic()-began,
        tools=ref(target / 'tools-report.json'), evidence=[ref(p) for p in sorted(target.rglob('*'))
        if p.is_file() and p.name != '.lock' and not p.name.endswith(('.tmp', '-wal', '-shm'))])
    immutable(target / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('batch', 'role', 'complete', 'calls', 'wall_seconds')}), flush=True)
    return receipt


def aggregate(*, verify_transport=False):
    inputs, spec, old = historical()
    selected = selected_roles(old); failed = []
    for folder in sorted((OUT / 'roles').glob('*/*')):
        if not folder.is_dir():
            continue
        number = int(folder.parent.name); role = folder.name
        receipt, p = latest_role(folder, inputs, spec['batches'][number])
        if (number, role) in selected:
            raise LegalMathError('E_INTEGRITY', details='Historical valid perspective was overwritten')
        if receipt['proposal'] is not None:
            selected[(number, role)] = {'proposal': receipt['proposal'], 'receipt': ref(p), 'origin': 'new-grant'}
        if not receipt['complete']:
            failed.append({'batch': number, 'role': role, 'receipt': ref(p), 'stopped': receipt['stopped']})
    batches = []
    for i, pairs in enumerate(spec['batches']):
        batch = {'required_pairs': pairs, 'attempts': [], 'proposals': []}
        for role in scoped.PERSPECTIVES:
            selected_row = selected.get((i, role))
            if selected_row:
                fidelity.validate(selected_row['proposal'], inputs['packet'], inputs['claims'],
                                  inputs['candidates'], inputs['questions'], pairs)
                batch['attempts'].append({'role': role, 'status': 'VALIDATED_PROPOSAL',
                                         'origin': selected_row['origin'], 'receipt': selected_row['receipt']})
                batch['proposals'].append(selected_row['proposal'])
        batches.append(batch)
    coverage = scoped.assessment_coverage(batches)
    calls = read(OUT / 'allowance.json')['calls'] if (OUT / 'allowance.json').exists() else []
    if verify_transport:
        for slot, row in enumerate(calls, 1):
            folder = OUT / 'provider-evidence' / f"{slot:04}-{row['request_hash'][:16]}"
            manifest = read(folder / 'manifest.json')
            if manifest['allowance_slot'] != slot or manifest['request_hash'] != row['request_hash']:
                raise LegalMathError('E_INTEGRITY', details='Transport slot differs from reservation')
            for name, hashes in manifest['files'].items():
                if raw_digest((folder / name).read_bytes()) != hashes['retained_sha256']:
                    raise LegalMathError('E_INTEGRITY', details='Transport evidence changed')
    pending = [{'batch': i, 'role': role} for i in range(41) for role in scoped.PERSPECTIVES
               if (i, role) not in selected or not role_valid(selected[(i, role)]['proposal'], inputs, spec['batches'][i])]
    return {'coverage': coverage, 'batches': batches, 'pending_roles': pending, 'failed_roles': failed,
        'new_calls': len(calls), 'calls_by_purpose': dict(Counter(c['purpose'] for c in calls)),
        'new_repairs': len(read(OUT / 'repairs.json')['repairs']),
        'execution_complete': coverage['assessed_pairs'] == 492 and not pending and not failed,
        'old_calls': 54, 'old_repairs': 20, 'legal_obligations_open': 46,
        'legal_accuracy_established': False, 'release_eligible': False}


def refresh():
    value = aggregate()
    plan = {k: v for k, v in value.items() if k != 'batches'}
    plan.update(remaining_calls=200-value['new_calls'], remaining_repairs=100-value['new_repairs'],
                remaining_seconds=max(0, int(DEADLINE-time.time())),
                next_action='REPORT' if value['execution_complete'] else 'REPAIR_REVIEW' if value['failed_roles'] else 'EXECUTE_NEXT_ROLE')
    history = OUT / 'plan-history' / f'{digest(plan)}.json'
    immutable(history, plan)
    save(OUT / 'next-phase-plan.json', {**plan, 'history': ref(history)})
    return plan


def test_directory():
    return OUT / 'tests' / digest({'files': [ref(ROOT / p) for p in FILES], 'product': implementation_identity()})


def tested():
    result = read(test_directory() / 'result.json')
    checked(result['execution']['log']); checked(result['junit'])
    if result['status'] != 'PASS' or result['counts']['failures'] or result['counts']['errors']:
        raise LegalMathError('E_STALE_REVIEW', details='Current method needs passing tests')
    return result


def tests():
    check_review()
    target = test_directory()
    if (target / 'result.json').exists():
        return tested()
    receipt = prior.command([ROOT / '.venv/bin/python', '-m', 'pytest', *TESTS, '-q', '--disable-warnings',
        '--junitxml', target / 'tests.xml'], target, 'tests', timeout=600)
    import xml.etree.ElementTree as ET
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in ET.parse(target / 'tests.xml').getroot().iter('testsuite'))
              for k in ('tests', 'errors', 'failures', 'skipped')}
    return immutable(target / 'result.json', {'status': 'PASS', 'counts': counts, 'execution': receipt,
                                             'junit': ref(target / 'tests.xml')})


def verify():
    check_review(); tested()
    result = aggregate(verify_transport=True)
    return {k: v for k, v in result.items() if k != 'batches'}


def repair():
    review = check_review(); tested()
    if not review.get('recovery'):
        raise LegalMathError('E_JOB_STATE', details='No specifically reviewed recovery')
    spec = read(checked(review['recovery']))
    inputs, partition, _ = historical(); pairs = partition['batches'][spec['batch']]
    validate_recovery(spec, inputs, pairs)
    folder = role_directory(spec['batch'], spec['role'])
    target = folder / f"attempt-{spec['attempt']:02}"
    if any(p.name > target.name for p in folder.glob('attempt-*')):
        raise LegalMathError('E_JOB_STATE', details='A later attempt exists; do not rewind recovery selection')
    if (target / 'receipt.json').exists():
        # A crash after writing the receipt may leave only pointer publication unfinished.
        receipt = verify_role(target / 'receipt.json', inputs, pairs)
        if read(target / 'started.json')['recovery'] != review['recovery']:
            raise LegalMathError('E_INTEGRITY', details='Attempt belongs to another recovery review')
    else:
        receipt = run_role(spec['batch'], spec['role'], inputs, pairs, recovery=review['recovery'])
    save(folder / 'latest.json', {'receipt': ref(target / 'receipt.json')})
    latest_role(folder, inputs, pairs)
    return {'status': 'RECOVERY_VALIDATED' if receipt['complete'] else 'REPAIR_REVIEW_REQUIRED', **refresh()}


def execute():
    check_review(); tested()
    current = aggregate()
    if current['execution_complete']:
        return verify()
    if current['failed_roles']:
        return {'status': 'REPAIR_REVIEW_REQUIRED', **refresh()}
    inputs, spec, _ = historical()
    for task in current['pending_roles']:
        receipt = run_role(task['batch'], task['role'], inputs, spec['batches'][task['batch']])
        refresh()
        if not receipt['complete']:
            return {'status': 'REPAIR_REVIEW_REQUIRED', **refresh()}
    result = verify()
    result.update(status='EXECUTED_WITH_OPEN_LEGAL_GAPS', finished_epoch=time.time())
    immutable(OUT / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    action = parser.parse_args().action
    with (OUT / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action == 'resume-check':
            value = {'status': 'REVIEW_VERIFIED', 'review': ref(review_path())}
            check_review(); historical()
        else:
            value = {'resume-test': tests, 'resume-execute': execute,
                     'resume-status': refresh, 'resume-verify': verify, 'resume-repair': repair}[action]()
        print(json.dumps(value, indent=2))
