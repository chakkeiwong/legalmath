"""Finite source-bound coverage, with a separate recorded continuation grant."""
import argparse
from collections import Counter
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2, scoped_investigation as scoped
from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.interpretation.assurance.integrated import implementation_identity
from legalmath.interpretation.assurance.optional_tools import ToolSession
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.providers import Completion
from scripts.legal_gap_program import ROOT, OUT as OLD, read, save, ref, check_ref, command
from scripts.legal_gap_recovery import retained_inputs
from scripts.legal_integration_tools import ProductToolBackend

OUT = ROOT / 'artifacts/legal-integration-coverage/2026-10-08'
DOC = ROOT / 'docs/implementation/legal-integration-coverage'
PLAN = ROOT / 'docs/plans/legal-integration-coverage-program.md'
PRIOR = ROOT / 'artifacts/legal-integration-assessment/2026-10-08'
DEADLINE = 1791519402.34676
AUTHORIZATION = 'you have 100 calls more and 20 more repairs. continue the execution'
LIMITS = {'combined': 82, 'baseline': 4, 'repair': 14}
ACTIONS = ('check', 'test', 'pilot', 'execute', 'repair', 'diagnose', 'status', 'verify')
TESTS = ['tests/assurance/test_integration_coverage.py',
         'tests/assurance/test_coverage_aliases.py',
         'tests/assurance/test_integration_assessment.py',
         'tests/assurance/test_successor_batch_capacity.py',
         'tests/assurance/test_executable_references_v2.py',
         'tests/assurance/test_successor_grants.py']
FILES = ['scripts/run_legal_integration_coverage.py', 'scripts/legal_integration_coverage.py',
         'scripts/legal_coverage_aliases.py',
         'scripts/legal_gap_program.py', 'scripts/legal_gap_recovery.py',
         'scripts/legal_integration_tools.py', *TESTS]


def immutable(path, value):
    if path.exists():
        if read(path) != json.loads(json.dumps(value)):
            raise ValueError('Immutable evidence differs: ' + str(path))
    else:
        save(path, value)
    return value


def partition(inputs, size=12):
    pairs = [[c['claim_id'], cid] for cid in sorted(inputs['candidates'])
             for c in sorted(inputs['claims'], key=lambda c: c['claim_id'])]
    if len(pairs) != len(set(map(tuple, pairs))):
        raise ValueError('Duplicate source/candidate identity')
    return [pairs[i:i+size] for i in range(0, len(pairs), size)]


def pilots(inputs, batches):
    def available(pair):
        from legalmath.interpretation.assurance.semantics import representation
        return not representation(inputs['candidates'][pair[1]]).startswith('UNAVAILABLE_EXECUTABLE_MEANING:')
    return [next(i for i, b in enumerate(batches) if all(not available(p) for p in b)),
            next(i for i, b in enumerate(batches) if all(available(p) for p in b))]


class CoverageGrant(GrantedAllowance):
    """Explicit independent user grant; never pretend an old grant was exhausted."""
    def __init__(self, purpose, batch, grant_path=None):
        self.grant_path = Path(grant_path or OUT / 'authorization.json')
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = read(self.grant_path)
        self.path = self.grant_path.parent / 'allowance.json'
        self.maximum = self.reservation_ceiling = 100
        self.purpose, self.batch = purpose, batch
        self.verify()

    def verify(self):
        g = self.grant
        if (self.grant_path.read_bytes() != self.grant_bytes or
                g.get('schema') != 'legalmath.integration-coverage-grant.v1' or
                g.get('authorization') != AUTHORIZATION or g.get('maximum') != 100 or
                g.get('repair_maximum') != 20 or g.get('purpose_limits') != LIMITS or
                g.get('deadline_epoch') != DEADLINE or self.purpose not in LIMITS or
                type(self.batch) is not int or not 0 <= self.batch < 41 or
                not g.get('predecessor')):
            raise LegalMathError('E_AUTHORITY', details='Changed continuation authorization')
        for item in g['predecessor']:
            if raw_digest((ROOT / item['path']).read_bytes()) != item['sha256']:
                raise LegalMathError('E_INTEGRITY', details='Prior ledger or evidence changed')
        value = read(self.path) if self.path.exists() else {'maximum': 100, 'calls': []}
        if set(value) != {'maximum', 'calls'} or value['maximum'] != 100 or not isinstance(value['calls'], list):
            raise LegalMathError('E_INTEGRITY')
        counts = Counter()
        for row in value['calls']:
            if (set(row) != {'purpose', 'batch', 'request_hash', 'issued_at_ns'} or
                    row['purpose'] not in LIMITS or type(row['batch']) is not int or not 0 <= row['batch'] < 41 or
                    not isinstance(row['request_hash'], str) or not re.fullmatch('[0-9a-f]{64}', row['request_hash']) or
                    not isinstance(row['issued_at_ns'], str) or not row['issued_at_ns'].isdigit()):
                raise LegalMathError('E_INTEGRITY', details='Invalid continuation reservation')
            counts[row['purpose']] += 1
        if len(value['calls']) > 100 or any(counts[k] > v for k, v in LIMITS.items()):
            raise LegalMathError('E_INTEGRITY', details='Allowance cap exceeded')
        return {'grant_id': g['schema'], 'grant_hash': raw_digest(self.grant_bytes),
                'maximum': 100, 'used': len(value['calls']), 'purpose': self.purpose,
                'purpose_maximum': LIMITS[self.purpose], 'batch': self.batch,
                'deadline_epoch': DEADLINE}

    def reserve(self, request_hash):
        if not isinstance(request_hash, str) or not re.fullmatch('[0-9a-f]{64}', request_hash):
            raise LegalMathError('E_SCHEMA')
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.verify()
            value = read(self.path) if self.path.exists() else {'maximum': 100, 'calls': []}
            if (time.time() + 5 >= DEADLINE or len(value['calls']) >= 100 or
                    sum(r['purpose'] == self.purpose for r in value['calls']) >= LIMITS[self.purpose]):
                raise LegalMathError('E_RESOURCE_LIMIT', details='Continuation cap or original deadline exhausted')
            value['calls'].append({'purpose': self.purpose, 'batch': self.batch,
                'request_hash': request_hash, 'issued_at_ns': str(time.time_ns())})
            tmp = self.path.with_suffix('.tmp')
            tmp.write_bytes(canonical(value)); tmp.replace(self.path)
            return len(value['calls'])


class CoverageProvider(CodexProvider):
    def complete(self, request, schema, settings):
        seconds = min(180, settings.timeout_seconds, int(DEADLINE - time.time()))
        if seconds < 5:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Original deadline exhausted')
        print(json.dumps({'dispatch': self.allowance.purpose, 'batch': self.allowance.batch,
                          'prior_calls': self.allowance.verify()['used']}), flush=True)
        return super().complete(request, schema, settings.model_copy(update={'timeout_seconds': seconds}))


class AliasProvider(CoverageProvider):
    provider_id = 'coverage.response-aliases.v1'

    def __init__(self, directory, **kwargs):
        super().__init__(**kwargs)
        self.directory = Path(directory)

    def complete(self, request, schema, settings):
        from scripts import legal_coverage_aliases as aliases
        wire, output_schema, references = aliases.prepare(request, schema)
        target = self.directory / digest(request)
        if (target / 'started.json').exists():
            raise LegalMathError('E_JOB_STATE', details='Alias dispatch already started; no automatic retry')
        immutable(target / 'original-request.json', request)
        immutable(target / 'original-schema.json', schema)
        immutable(target / 'references.json', references)
        immutable(target / 'started.json', {'request_hash': digest(request), 'wire_hash': digest(wire)})
        answer = super().complete(wire, output_schema, settings)
        immutable(target / 'raw-response.json', {'value': answer.value, 'provenance': answer.provenance})
        value = aliases.resolve(answer.value, request, schema, references)
        immutable(target / 'expanded-response.json', value)
        return Completion(value, {**answer.provenance, 'response_hash': digest(value),
            'alias_wire_response_hash': answer.provenance['response_hash'],
            'alias_original_request_hash': digest(request), 'response_alias_profile': aliases.PROFILE,
            'alias_references': ref(target / 'references.json')})


def check():
    path = review_path()
    if path.exists():
        checked_review()
        return {'status': 'REVIEW_VERIFIED', 'review': ref(path)}
    # The predecessor was sealed and verified before this successor was
    # authored. Its verifier intentionally rejects the later dirty source
    # identity (including unrelated prospectus work and subsequent legal
    # integration modules), so never rewrite or weaken that historical review.
    # Check its immutable receipt and frozen evidence instead.
    predecessor_receipt = PRIOR / 'completion-check.json'
    predecessor_state = PRIOR / 'state.json'
    predecessor_review = ROOT / 'docs/implementation/legal-integration-assessment/review-final.json'
    for source in (predecessor_receipt, predecessor_state, predecessor_review):
        check_ref(ref(source))
    verified = read(predecessor_receipt)
    if verified.get('status') != 'PASS' or verified.get('scoped_pairs') != 492:
        raise ValueError('Sealed predecessor receipt is not the expected verified assessment')
    immutable(OUT / 'predecessor-verification.json', {
        'receipt': ref(predecessor_receipt), 'state': ref(predecessor_state),
        'review': ref(predecessor_review), 'receipt_value': verified,
        'status': 'SEALED_PREDECESSOR_RECEIPT_ACCEPTED',
        'current_live_source_verification': 'NOT_RESEALED; old verifier identity is stale after later dirty source changes'})
    checkpoint = []
    for p in [OLD / 'provider-allowance.json', OLD / 'repairs.json', PRIOR / 'state.json',
              PRIOR / 'completion-check.json', PRIOR / 'input-inventory.json',
              ROOT / 'docs/implementation/legal-integration-assessment/review-final.json']:
        target = OUT / 'predecessor' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != p.read_bytes():
                raise ValueError('Predecessor checkpoint changed')
        else:
            shutil.copyfile(p, target)
        checkpoint += [ref(p), ref(target)]
    g = {'schema': 'legalmath.integration-coverage-grant.v1', 'authorization': AUTHORIZATION,
         'maximum': 100, 'repair_maximum': 20, 'purpose_limits': LIMITS,
         'deadline_epoch': DEADLINE, 'predecessor': checkpoint,
         'old_consumption': {'calls': 73, 'repairs': 10},
         'meaning': 'Additional explicit user authorization; old ledgers remain unchanged. No renewed time window.'}
    immutable(OUT / 'authorization.json', g)
    inputs = retained_inputs('baseline')
    batches = partition(inputs)
    if len(batches) != 41 or sum(map(len, batches)) != 492:
        raise ValueError('Retained denominator changed')
    selected = pilots(inputs, batches)
    # Validate every request's exact source and question before a reservation.
    for batch in batches:
        ids = {p[1] for p in batch}; claims = {p[0] for p in batch}
        fidelity_v2.request(inputs['packet'], [c for c in inputs['claims'] if c['claim_id'] in claims],
            {k: v for k, v in inputs['candidates'].items() if k in ids},
            {k: v for k, v in inputs['questions'].items() if k in ids}, batch)
    immutable(OUT / 'inputs.json', inputs)
    immutable(OUT / 'partition.json', {'batches': batches, 'pilots': selected,
        'pair_count': 492, 'unavailable_pairs': 246, 'broad_pairs': 420, 'context_pairs': 72,
        'minimum_combined_calls': 82, 'baseline_calls': 4})
    # Preserve actual reviewed source, including uncommitted files.
    snapshots = []
    sources = [p for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file() and
               p.suffix in ('.py', '.json', '.java', '.lean', '.sql')]
    sources += [ROOT / p for p in FILES]
    for p in sorted(set(sources)):
        dest = OUT / 'source' / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != p.read_bytes():
            raise ValueError('Sealed source snapshot changed')
        if not dest.exists(): shutil.copyfile(p, dest)
        snapshots.append({'live': ref(p), 'copy': ref(dest)})
    immutable(OUT / 'source-manifest.json', snapshots)
    reviewed = {'status': 'PASS_BOUNDED_FULL_RETAINED_COVERAGE', 'plan': ref(PLAN),
        'authorization': ref(OUT / 'authorization.json'), 'inputs': ref(OUT / 'inputs.json'),
        'partition': ref(OUT / 'partition.json'), 'source_manifest': ref(OUT / 'source-manifest.json'),
        'predecessor_verification': ref(OUT / 'predecessor-verification.json'),
        'implementation': implementation_identity(), 'route': CodexProvider().routing,
        'backend': ProductToolBackend().identity(), 'files': [ref(ROOT / p) for p in FILES]}
    immutable(path, reviewed)
    immutable(OUT / 'run-manifest.json', {'git_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'dirty_source': reviewed['source_manifest'],
        'environment': str(ROOT / '.venv/bin/python'), 'CPU_GPU': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'data_version': reviewed['inputs'], 'seeds': 'N/A; external provider seed unavailable',
        'commands': ['.venv/bin/python scripts/run_legal_integration_coverage.py ' + a for a in ACTIONS],
        'plan': reviewed['plan'], 'result_path': str((OUT / 'result.json').relative_to(ROOT)),
        'started_epoch': time.time(), 'deadline_epoch': DEADLINE})
    immutable(OUT / 'repairs.json', {'maximum': 20, 'repairs': [{'id': 1,
        'reason': 'Fund and durably execute full retained coverage plus unavailable-state applicability pilots.',
        'review': ref(path), 'new_provider_calls': 0, 'kind': 'implementation'}]})
    return {'status': 'REVIEW_SEALED', 'pilots': selected, 'pairs': 492, 'initial_call_allocation': 86}


def checked_review():
    value = read(review_path())
    for key in ('plan', 'authorization', 'inputs', 'partition', 'source_manifest', 'predecessor_verification'):
        check_ref(value[key])
    for row in value['files']:
        check_ref(row)
    for row in read(check_ref(value['source_manifest'])):
        check_ref(row['live'])
        check_ref(row['copy'])
    for key in ('previous_review', 'revision_review'):
        if key in value: check_ref(value[key])
    if (value['implementation'] != implementation_identity() or value['route'] != CodexProvider().routing or
            value['backend'] != ProductToolBackend().identity()):
        raise ValueError('Reviewed source, route or backend changed')
    CoverageGrant('combined', 0).verify()
    repairs = read(OUT / 'repairs.json')
    if repairs['maximum'] != 20 or len(repairs['repairs']) > 20:
        raise ValueError('Repair batch limit changed or exhausted')
    return value


def review_path():
    for name in ('review-v5.json', 'review-v4.json', 'review-v3.json', 'review-v2.json', 'review.json'):
        if (OUT / name).exists(): return OUT / name
    return OUT / 'review.json'


def test_directory():
    # Cache only the exact reviewed source and tests, never a directory name.
    return OUT / 'C0' / digest({'files': [ref(ROOT / p) for p in FILES],
                               'product': implementation_identity()})


def tested():
    row = read(test_directory() / 'result.json')
    check_ref(row['junit']); check_ref(row['execution']['log'])
    if row['status'] != 'PASS' or row['counts']['errors'] or row['counts']['failures']:
        raise ValueError('Current method has no passing test receipt')
    return row


def tests():
    checked_review()
    target = test_directory()
    if (target / 'result.json').exists():
        return tested()
    receipt = command([ROOT / '.venv/bin/python', '-m', 'pytest', *TESTS, '-q', '--disable-warnings',
                       '--junitxml', target / 'tests.xml'], target, 'tests', timeout=600)
    import xml.etree.ElementTree as ET
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in ET.parse(target / 'tests.xml').getroot().iter('testsuite'))
              for k in ('tests', 'errors', 'failures', 'skipped')}
    return immutable(target / 'result.json', {'status': 'PASS', 'counts': counts,
        'execution': receipt, 'junit': ref(target / 'tests.xml')})


def verify_journal(directory):
    binding = read(directory / 'journal.json')['value']['binding']
    return EvidenceJournal(directory, binding['inputs'], **{k: binding[k] for k in
        ('maximum_actions', 'maximum_per_issue', 'deadline_seconds')}).report()


def validate_result(value, inputs, pairs):
    if set(map(tuple, value['required_pairs'])) != set(map(tuple, pairs)):
        raise ValueError('Batch scope changed')
    for batch in value['batches']:
        for proposal in batch['proposals']:
            fidelity_v2.validate(proposal, inputs['packet'], inputs['claims'], inputs['candidates'],
                                inputs['questions'], batch['required_pairs'])
    if value['assessment_coverage'] != scoped.assessment_coverage(value['batches']):
        raise ValueError('Forged assessment summary')
    return scoped.execution_complete(value, expected_pairs=pairs)


def run_batch(arm, index):
    checked_review()
    inputs = read(OUT / 'inputs.json'); pairs = read(OUT / 'partition.json')['batches'][index]
    folder = OUT / 'batches' / arm / f'{index:02}'
    result_path = folder / 'receipt.json'
    if result_path.exists():
        receipt, retained_folder = latest_receipt(folder)
        for item in receipt['evidence']: check_ref(item)
        if receipt.get('result'):
            result = read(check_ref(receipt['result']))
            if validate_result(result, inputs, pairs) != receipt['complete']:
                raise ValueError('Completion receipt changed')
            verify_journal(retained_folder / 'scoped/model')
        return receipt
    if (folder / 'started.json').exists():
        raise LegalMathError('E_JOB_STATE', details='Interrupted batch needs reviewed recovery; no redispatch')
    immutable(folder / 'started.json', {'arm': arm, 'batch': index, 'pairs': pairs, 'epoch': time.time()})
    provider = AliasProvider(folder / 'response-aliases', allowance=CoverageGrant(arm, index))
    tools = ToolSession(ProductToolBackend(), folder / 'tools') if arm == 'combined' else None
    began = time.monotonic(); before = provider.allowance.verify()['used']
    try:
        result = scoped.investigate(inputs['packet'], inputs['claims'], inputs['candidates'], inputs['questions'],
            provider, folder / 'scoped', required_pairs=pairs, batch_size=12,
            maximum_rounds=1, maximum_actions=2, deadline_seconds=600, pair_order='candidate-first',
            settings=Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000),
            reference_protocol=PROTOCOL, input_profile='readable-tables.v1', optional_tools=tools,
            stop_on_rejection=True)
        complete = validate_result(result, inputs, pairs)
        receipt = {'complete': complete, 'result': ref(folder / 'scoped/result.json'),
            'assessment_coverage': result['assessment_coverage'], 'stopped': result['stopped']}
        if tools:
            immutable(folder / 'tools-report.json', tools.report())
            receipt['tools'] = ref(folder / 'tools-report.json')
    except Exception as exc:
        immutable(folder / 'failure.json', {'type': type(exc).__name__, 'code': getattr(exc, 'code', None),
                  'details': str(getattr(exc, 'details', '') or exc)[:5000]})
        receipt = {'complete': False, 'failure': ref(folder / 'failure.json')}
    evidence = [ref(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name != '.lock'
                and not p.name.endswith(('.tmp', '-wal', '-shm'))]
    receipt.update(arm=arm, batch=index, calls=provider.allowance.verify()['used'] - before,
                   wall_seconds=time.monotonic() - began, evidence=evidence)
    immutable(result_path, receipt)
    print(json.dumps({k: receipt[k] for k in ('arm', 'batch', 'complete', 'calls', 'wall_seconds')}), flush=True)
    refresh()
    return receipt


def record_repair(arm, index, reason, evidence):
    path = OUT / 'repairs.json'
    value = read(path)
    if value.get('maximum') != 20 or len(value.get('repairs', [])) >= 20:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Repair batch cap exhausted')
    row = {'id': len(value['repairs']) + 1, 'kind': 'provider-recovery', 'arm': arm,
           'batch': index, 'reason': reason, 'evidence': evidence, 'recorded': time.time()}
    value['repairs'].append(row)
    save(path, value)
    return row


def repair():
    """Run one explicit successor attempt for the earliest failed batch."""
    checked_review()
    tested()
    failed = [r for r in collected() if not r.get('complete')]
    if not failed:
        return {'status': 'NO_REPAIR_REQUIRED', **refresh()}
    failed.sort(key=lambda r: (r['arm'], r['batch']))
    original = failed[0]
    reason = repair_reason(original)
    arm, index = original['arm'], original['batch']
    base = OUT / 'batches' / arm / f'{index:02}'
    attempts = sorted(base.glob('attempt-*'))
    for attempt in attempts:
        if not (attempt / 'receipt.json').exists():
            raise LegalMathError('E_JOB_STATE', details='Interrupted repair requires investigation; no redispatch')
    number = len(attempts) + 1
    target = base / f'attempt-{number:02}'
    repair_row = record_repair(arm, index, reason, original.get('evidence', []))
    inputs = read(OUT / 'inputs.json'); pairs = read(OUT / 'partition.json')['batches'][index]
    target.mkdir(parents=True, exist_ok=False)
    save(target / 'started.json', {'arm': arm, 'batch': index, 'attempt': number,
                                   'pairs': pairs, 'repair_id': repair_row['id'], 'epoch': time.time()})
    provider = AliasProvider(target / 'response-aliases', allowance=CoverageGrant('repair', index))
    tools = ToolSession(ProductToolBackend(), target / 'tools') if arm == 'combined' else None
    began = time.monotonic(); before = provider.allowance.verify()['used']
    try:
        result = scoped.investigate(inputs['packet'], inputs['claims'], inputs['candidates'], inputs['questions'],
            provider, target / 'scoped', required_pairs=pairs, batch_size=12,
            maximum_rounds=1, maximum_actions=2, deadline_seconds=600, pair_order='candidate-first',
            settings=Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000),
            reference_protocol=PROTOCOL, input_profile='readable-tables.v1', optional_tools=tools,
            stop_on_rejection=True)
        complete = validate_result(result, inputs, pairs)
        receipt = {'complete': complete, 'result': ref(target / 'scoped/result.json'),
            'assessment_coverage': result['assessment_coverage'], 'stopped': result['stopped']}
        if tools:
            immutable(target / 'tools-report.json', tools.report())
            receipt['tools'] = ref(target / 'tools-report.json')
    except Exception as exc:
        immutable(target / 'failure.json', {'type': type(exc).__name__, 'code': getattr(exc, 'code', None),
                  'details': str(getattr(exc, 'details', '') or exc)[:5000]})
        receipt = {'complete': False, 'failure': ref(target / 'failure.json')}
    evidence = [ref(p) for p in sorted(target.rglob('*')) if p.is_file() and p.name != '.lock'
                and not p.name.endswith(('.tmp', '-wal', '-shm'))]
    receipt.update(arm=arm, batch=index, attempt=number,
                   calls=provider.allowance.verify()['used'] - before,
                   wall_seconds=time.monotonic() - began, evidence=evidence)
    attempt_receipt = target / 'receipt.json'
    immutable(attempt_receipt, receipt)
    save(base / 'latest.json', {'receipt': ref(attempt_receipt), 'attempt': number})
    refresh()
    print(json.dumps({k: receipt[k] for k in ('arm', 'batch', 'attempt', 'complete', 'calls')}), flush=True)
    return {'status': 'REPAIR_EXECUTED', 'receipt': ref(attempt_receipt), **receipt}


def repair_reason(original):
    failure = original.get('stopped', {}) or {}
    if (failure.get('error') == 'E_DEPENDENCY' and
            'Read-only file system' in str(failure.get('details', '')) and not original.get('attempt')):
        return 'Provider state database was read-only in the sandbox; retry with the same reviewed request under trusted execution.'
    if (original['arm'] == 'baseline' and original['batch'] == 0 and original.get('attempt') == 1 and
            failure == {'kind': 'DISPATCH_STOPPED', 'error': 'E_RESOURCE_LIMIT', 'details': 'Codex call deadline'} and
            (OUT / 'diagnostic/result.json').exists() and verify_diagnostic()['status'] == 'SMALL_APPLICABILITY_PASSED'):
        return ('One reviewed 12-pair retry after the sentinel and all four small assessments responded. '
                'Tests current 12-pair feasibility, not timeout causation; any repeated failure blocks this repair.')
    if (original['arm'] == 'baseline' and original['batch'] == 0 and original.get('attempt') == 2 and
            failure == {'kind': 'DISPATCH_STOPPED', 'error': 'E_RESOURCE_LIMIT', 'details': 'Codex call deadline'} and
            (OUT / 'review-v5.json').exists()):
        return ('Reviewed response-alias transport repair of the failed 12-pair pilot. '
                'Original sources, questions, judgments and 180-second limit are unchanged; full identities are restored before validation.')
    raise LegalMathError('E_JOB_STATE', details='No reviewed remedy for this failure; no automatic retry')


def verify_diagnostic():
    folder = OUT / 'diagnostic'
    value = read(folder / 'result.json')
    for row in value['evidence']: check_ref(row)
    inputs = read(OUT / 'inputs.json')
    scoped_stages = [s for s in value['stages'] if 'result' in s]
    if scoped_stages:
        pairs = read(folder / 'selected-pairs.json')['pairs']
        for stage in scoped_stages:
            result = read(check_ref(stage['result']))
            if validate_result(result, inputs, pairs) != stage['passed']:
                raise ValueError('False diagnostic completion')
            verify_journal(folder / stage['stage'] / 'scoped/model')
        if any(s['stage'] == 'combined' for s in scoped_stages):
            report = ToolSession(ProductToolBackend(), folder / 'combined/tools').report()
            if report != read(folder / 'combined/tools-report.json'):
                raise ValueError('Changed diagnostic tools')
    success = (len(value['stages']) == 3 and [s['stage'] for s in value['stages']] ==
               ['sentinel', 'baseline', 'combined'] and all(s['passed'] for s in value['stages']))
    if success and read(folder / 'sentinel-response.json')['value'] != {'status': 'ready'}:
        raise ValueError('Invalid sentinel')
    if (value['status'] == 'SMALL_APPLICABILITY_PASSED') != success:
        raise ValueError('False diagnostic status')
    return {'status': value['status'], 'calls': value['calls'], 'scoped_pairs_per_arm':
            len(read(folder / 'selected-pairs.json')['pairs']) if scoped_stages else 0}


def latest_receipt(folder):
    original = folder / 'receipt.json'
    paths = [original, *sorted(folder.glob('attempt-*/receipt.json'))]
    for path in paths:
        for evidence in read(path)['evidence']: check_ref(evidence)
    pointer = folder / 'latest.json'
    if pointer.exists():
        selected = check_ref(read(pointer)['receipt'])
        if selected not in paths[1:]:
            raise ValueError('Foreign repair attempt')
    else:
        selected = original
    return read(selected), selected.parent


def collected():
    rows = []
    for p in sorted((OUT / 'batches').glob('*/*/receipt.json')):
        rows.append(latest_receipt(p.parent)[0])
    return rows


def refresh():
    rows = collected(); spec = read(OUT / 'partition.json')
    done = {r['batch'] for r in rows if r['arm'] == 'combined' and r['complete']}
    calls = read(OUT / 'allowance.json')['calls'] if (OUT / 'allowance.json').exists() else []
    result = {'phase': 'C3' if len(done) == 41 else 'C1' if any(i not in done for i in spec['pilots']) else 'C2',
        'combined_batches_complete': len(done), 'combined_pairs_complete': sum(len(spec['batches'][i]) for i in done),
        'full_pairs': 492, 'pending_batches': [i for i in range(41) if i not in done],
        'failed_batches': [{'arm': r['arm'], 'batch': r['batch']} for r in rows if not r['complete']],
        'calls': len(calls), 'remaining_calls': 100 - len(calls), 'calls_by_purpose': dict(Counter(c['purpose'] for c in calls)),
        'remaining_seconds': max(0, int(DEADLINE-time.time())), 'release_eligible': False,
        'review_reason': 'Proceed only after exact batch validation; limitations/disputes stay open. Failed batches require reviewed repair.'}
    key = digest({'receipts': [ref(p) for p in sorted((OUT / 'batches').glob('*/*/receipt.json'))], 'calls': calls})
    history = OUT / 'plan-history' / (key + '.json')
    if not history.exists(): immutable(history, result)
    save(OUT / 'next-phase-plan.json', {'history': ref(history), **result})
    return result


def execute(pilot_only=False):
    checked_review()
    tested()
    if (OUT / 'result.json').exists(): return verify()
    spec = read(OUT / 'partition.json'); a, b = spec['pilots']
    order = [('baseline', a), ('combined', a), ('combined', b), ('baseline', b)]
    if not pilot_only:
        order += [('combined', i) for i in range(41) if i not in (a, b)]
    for arm, index in order:
        row = run_batch(arm, index)
        if not row['complete']:
            return {'status': 'REPAIR_REVIEW_REQUIRED', 'failed': {'arm': arm, 'batch': index}, **refresh()}
    if pilot_only: return {'status': 'PILOTS_COMPLETE', **refresh()}
    result = verify()
    result.update(status='EXECUTED_WITH_OPEN_LEGAL_GAPS', finished_epoch=time.time(),
                  wall_seconds=time.time()-read(OUT / 'run-manifest.json')['started_epoch'])
    immutable(OUT / 'result.json', result)
    return result


def verify():
    checked_review(); tested()
    inputs = read(OUT / 'inputs.json'); spec = read(OUT / 'partition.json')
    rows = collected(); combined = []; baseline = []
    for row in rows:
        for item in row['evidence']: check_ref(item)
        folder = OUT / 'batches' / row['arm'] / f"{row['batch']:02}"
        _, folder = latest_receipt(folder)
        if row.get('result'):
            result = read(check_ref(row['result']))
            if validate_result(result, inputs, spec['batches'][row['batch']]) != row['complete']:
                raise ValueError('Invalid completion claim')
            verify_journal(folder / 'scoped/model')
            (combined if row['arm'] == 'combined' else baseline).extend(result['batches'])
        if row.get('tools'):
            report_folder = ROOT / Path(row['tools']['path']).parent / 'tools'
            report = ToolSession(ProductToolBackend(), report_folder).report()
            if report != read(check_ref(row['tools'])): raise ValueError('Changed tool report')
    covered = [tuple(p) for b in combined for p in b['required_pairs']]
    expected = {tuple(p) for b in spec['batches'] for p in b}
    if len(covered) != len(set(covered)) or not set(covered) <= expected:
        raise ValueError('Duplicate or foreign pair in aggregation')
    calls = read(OUT / 'allowance.json')['calls'] if (OUT / 'allowance.json').exists() else []
    for slot, row in enumerate(calls, 1):
        folder = OUT / 'provider-evidence' / f"{slot:04}-{row['request_hash'][:16]}"
        manifest = read(folder / 'manifest.json')
        if manifest['allowance_slot'] != slot or manifest['request_hash'] != row['request_hash']:
            raise ValueError('Wrong dispatch evidence')
        for name, hashes in manifest['files'].items():
            if raw_digest((folder / name).read_bytes()) != hashes['retained_sha256']:
                raise ValueError('Transport evidence changed')
    coverage = scoped.assessment_coverage(combined)
    coverage['required_pairs'] = 492
    coverage['unassessed_pairs'] = 492-coverage['assessed_pairs']
    complete = (set(covered) == expected and coverage['assessed_pairs'] == 492 and
                len([r for r in rows if r['arm'] == 'baseline' and r['complete']]) == 2 and
                all(r['complete'] for r in rows))
    diagnostic = verify_diagnostic() if (OUT / 'diagnostic/result.json').exists() else None
    return {'status': 'EVIDENCE_VERIFIED', 'execution_complete': complete, 'diagnostic': diagnostic,
        'coverage': coverage, 'baseline_pilot_coverage': scoped.assessment_coverage(baseline),
        'calls': len(calls), 'calls_by_purpose': dict(Counter(c['purpose'] for c in calls)),
        'repairs': len(read(OUT / 'repairs.json')['repairs']), 'legal_gaps_closed': 0,
        'full_product_regenerated': False, 'legal_accuracy_established': False, 'release_eligible': False,
        'meaning': 'Complete retained scoped stage only; previous generation and controlled product evidence are separate.'}


def diagnose():
    """One service sentinel; only if ready, a separately bounded two-pair ladder."""
    checked_review(); tested()
    folder = OUT / 'diagnostic'
    if (folder / 'result.json').exists():
        value = read(folder / 'result.json')
        for row in value['evidence']: check_ref(row)
        return value
    if (folder / 'started.json').exists():
        raise LegalMathError('E_JOB_STATE', details='Interrupted diagnostic requires review, not automatic resend')
    row = record_repair('diagnostic', 0,
        'Trusted 12-pair request reached turn.started but exceeded 180 seconds. A tiny sentinel distinguishes present route availability; two original unformalized pairs test task-size applicability if it passes.',
        [ref(OUT / 'batches/baseline/00/attempt-01/receipt.json')])
    immutable(folder / 'started.json', {'repair_id': row['id'], 'epoch': time.time(), 'maximum_calls': 5})
    provider = CoverageProvider(allowance=CoverageGrant('repair', 0))
    schema = {'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['ready']}},
              'required': ['status'], 'additionalProperties': False}
    request = {'task': 'Return status ready in the requested JSON. No tools.'}
    before = provider.allowance.verify()['used']; began = time.monotonic()
    stages = []
    try:
        answer = provider.complete(request, schema,
            Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000))
        immutable(folder / 'sentinel-response.json', {'value': answer.value, 'provenance': answer.provenance})
        if answer.value != {'status': 'ready'}: raise ValueError('Sentinel response did not match schema')
        stages.append({'stage': 'sentinel', 'passed': True})
        inputs = read(OUT / 'inputs.json')
        from scripts.legal_gap_recovery import select_pairs
        cid = sorted(cid for cid, r in inputs['candidates'].items() if r['formalization'] is None)[0]
        pairs = [[claim, cid] for claim, _ in select_pairs(inputs)]
        immutable(folder / 'selected-pairs.json', {'pairs': pairs, 'question': inputs['questions'][cid],
            'full_matrix': 492, 'limit': 'Small applicability diagnostic; not a replacement for the full matrix.'})
        for arm in ('baseline', 'combined'):
            target = folder / arm
            tools = ToolSession(ProductToolBackend(), target / 'tools') if arm == 'combined' else None
            result = scoped.investigate(inputs['packet'], inputs['claims'], inputs['candidates'], inputs['questions'],
                provider, target / 'scoped', required_pairs=pairs, batch_size=2, maximum_rounds=1,
                maximum_actions=2, deadline_seconds=600, settings=Settings(timeout_seconds=180,
                    max_input_bytes=200000, max_output_bytes=200000), reference_protocol=PROTOCOL,
                input_profile='readable-tables.v1', optional_tools=tools, stop_on_rejection=True)
            passed = validate_result(result, inputs, pairs)
            stages.append({'stage': arm, 'passed': passed, 'result': ref(target / 'scoped/result.json'),
                           'coverage': result['assessment_coverage'], 'stopped': result['stopped']})
            if tools: immutable(target / 'tools-report.json', tools.report())
            if not passed: break
    except Exception as exc:
        immutable(folder / 'failure.json', {'type': type(exc).__name__, 'code': getattr(exc, 'code', None),
                  'details': str(getattr(exc, 'details', '') or exc)[:5000]})
        stages.append({'stage': 'failure', 'passed': False, 'failure': ref(folder / 'failure.json')})
    evidence = [ref(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name != '.lock']
    result = {'status': 'SMALL_APPLICABILITY_PASSED' if len(stages) == 3 and all(s['passed'] for s in stages)
              else 'LIVE_DIAGNOSTIC_FAILED', 'stages': stages, 'calls': provider.allowance.verify()['used']-before,
              'wall_seconds': time.monotonic()-began, 'evidence': evidence, 'full_pairs': 492,
              'legal_accuracy_established': False, 'release_eligible': False}
    immutable(folder / 'result.json', result)
    refresh()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    action = parser.parse_args().action
    OUT.mkdir(parents=True, exist_ok=True)
    if action == 'status':
        print(json.dumps(refresh(), indent=2)); return
    with (OUT / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        value = {'check': check, 'test': tests, 'pilot': lambda: execute(True),
                 'execute': execute, 'repair': repair, 'diagnose': diagnose, 'verify': verify}[action]()
        print(json.dumps(value, indent=2))
