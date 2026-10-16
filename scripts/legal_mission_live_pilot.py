#!/usr/bin/env python3
"""Fixed P10/evidence paired pilot. Only execute can make authorized model calls."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import Field
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.interpretation.assurance.engine import AssuranceSettings
from legalmath.interpretation.search.providers import CodexProvider

OUT = ROOT / 'artifacts/legal-mission-control/2026-10-10/live-pilot-400'
PLAN = ROOT / 'docs/plans/legal-mission-live-pilot-400.md'
SPEC = ROOT / 'artifacts/legal-mission-control/2026-10-10/tool-integration/live-preflight/pilot-specification.json'
SOURCE = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
AUTHORIZATION = 'you have 400 calls and 48 hours.  continue'
START = '2026-10-10T04:28:01+00:00'
END = '2026-10-12T04:28:01+00:00'
STAGES = {'core': 36, 'question_assignment': 3, 'scoped': 82,
          'dossier_reviews': 64, 'interaction': 1, 'synthesis': 1}
ARMS = ('baseline', 'candidate')
PROTECTED = {
    'path': 'artifacts/assurance-new-grant/2026-09-29/live-allowance.json',
    'sha256': 'd2d8d59338f65453fadf9b6b18c90e4d9158841e48975a06f046b254b48c9eaa'}


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    # Operational history includes fractional historical timestamps. It is not
    # a RuleIR value and must not be forced through that exact-number codec.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def require(ok, message, code='E_INTEGRITY'):
    if not ok:
        raise LegalMathError(code, details=message)


def ref(path, root=ROOT):
    path = Path(path).absolute()
    return {'path': str(path.relative_to(root.resolve())), 'sha256': raw_digest(path.read_bytes())}


def checked(item, root=ROOT):
    relative = Path(item['path'])
    require(not relative.is_absolute() and '..' not in relative.parts, 'Invalid evidence path')
    # Tool executables may be approved read-only symlinks to an existing conda
    # environment. Retain their worktree locator and check the target bytes.
    path = root / relative
    require(raw_digest(path.read_bytes()) == item['sha256'], 'Changed evidence: ' + item['path'])
    return path


def immutable(path, value):
    if path.exists():
        require(read(path) == value, 'Existing evidence differs: ' + str(path))
    else:
        save(path, value)
    return value


class PilotSettings(AssuranceSettings):
    """Reviewed clock for 36 calls; no change to the product's ordinary default."""
    deadline_seconds: int = Field(default=10800, ge=30, le=10800)


class PilotAllowance(GrantedAllowance):
    """New grant with immutable expired predecessor and disjoint arm/stage caps."""
    def __init__(self, arm, *, root=ROOT, directory=OUT):
        self.root, self.directory = Path(root).resolve(), Path(directory).resolve()
        require(self.directory.is_relative_to(self.root), 'Grant outside worktree')
        self.grant_path = self.directory / 'authorization.json'
        self.grant_bytes = self.grant_path.read_bytes()
        self.grant = read(self.grant_path)
        self.path = self.directory / 'allowance.json'
        self.maximum, self.reservation_ceiling = 400, 374
        self.arm, self.arm_maximum = arm, sum(STAGES.values())
        self.stage = 'core'
        self.verify()

    def verify(self):
        g = self.grant
        require(self.grant_path.read_bytes() == self.grant_bytes, 'Grant changed during execution')
        require(g['schema'] == 'legalmath.mission-pilot-grant.v1'
                and g['authorization'] == AUTHORIZATION and g['maximum'] == 400
                and g['started_utc'] == START and g['deadline_utc'] == END
                and g['allocations'] == {a: STAGES for a in ARMS}
                and g['optional_assessment_calls'] == 1 and g['unallocated_calls'] == 25
                and g['historical_unused_transfer'] is False and self.arm in ARMS,
                'Unreviewed pilot grant', 'E_AUTHORITY')
        old = read(checked(g['historical_ledger'], self.root))
        prior = read(checked(g['historical_authorization'], self.root))
        require(old['maximum'] == 200 and len(old['calls']) == 49,
                'Unexpected historical spending')
        require(prior['schema'] == 'legalmath.coverage-resumption-grant.v1'
                and prior['maximum'] == 200
                and prior['deadline_epoch'] < datetime.fromisoformat(START).timestamp(),
                'Predecessor was not expired before fresh grant')
        for item in prior['predecessor']:
            checked(item, self.root)
        for key in ('plan', 'specification', 'protected_allowance'):
            checked(g[key], self.root)
        value = read(self.path)
        require(set(value) == {'maximum', 'calls'} and value['maximum'] == 400
                and isinstance(value['calls'], list), 'Invalid pilot allowance')
        counts = Counter()
        start_ns = int(datetime.fromisoformat(START).timestamp()) * 10**9
        end_ns = int(datetime.fromisoformat(END).timestamp()) * 10**9
        for row in value['calls']:
            require(set(row) == {'arm', 'stage', 'request_hash', 'issued_at_ns'}
                    and row['arm'] in ARMS and row['stage'] in STAGES
                    and isinstance(row['request_hash'], str)
                    and re.fullmatch('[0-9a-f]{64}', row['request_hash'])
                    and isinstance(row['issued_at_ns'], str) and row['issued_at_ns'].isdigit()
                    and start_ns <= int(row['issued_at_ns']) < end_ns,
                    'Invalid pilot reservation')
            counts[row['arm'], row['stage']] += 1
        require(len(value['calls']) <= 374
                and all(counts[a, s] <= limit for a in ARMS for s, limit in STAGES.items()),
                'Pilot allocation exceeded')
        return {'maximum': 400, 'used': len(value['calls']), 'arm': self.arm,
                'arm_used': sum(counts[self.arm, s] for s in STAGES),
                'stage_used': {s: counts[self.arm, s] for s in STAGES},
                'deadline_utc': END, 'historical_used': 49, 'expired_unused': 151,
                'grant_hash': raw_digest(self.grant_bytes)}

    def remaining_seconds(self):
        now = time.time()
        require(now >= datetime.fromisoformat(START).timestamp(), 'Grant not started', 'E_AUTHORITY')
        return int(datetime.fromisoformat(END).timestamp() - now)

    def stage_limit(self, stage):
        return STAGES[stage]

    def reserve(self, request_hash):
        require(isinstance(request_hash, str) and re.fullmatch('[0-9a-f]{64}', request_hash),
                'Invalid request hash', 'E_SCHEMA')
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = self.verify()
            require(self.stage in STAGES, 'Unknown pilot stage', 'E_AUTHORITY')
            require(self.remaining_seconds() >= 5 and state['used'] < 374
                    and state['stage_used'][self.stage] < self.stage_limit(self.stage),
                    'Pilot stage envelope or global deadline exhausted', 'E_RESOURCE_LIMIT')
            value = read(self.path)
            value['calls'].append({'arm': self.arm, 'stage': self.stage,
                'request_hash': request_hash, 'issued_at_ns': str(time.time_ns())})
            save(self.path, value)
            return len(value['calls'])


def stage_for(request):
    task = request.get('original_task', request.get('task'))
    return {'DEFINE_EXACT_QUESTIONS': 'question_assignment',
            'SCOPED_SOURCE_FIDELITY': 'scoped',
            'REVIEW_DOSSIER_EVIDENCE': 'dossier_reviews',
            'REVIEW_DOSSIER_INTERACTIONS': 'interaction',
            'SYNTHESIZE_WHOLE_DOSSIER_ANSWER': 'synthesis'}.get(task, 'core')


class PilotProvider(CodexProvider):
    def __init__(self, *, protocol_directory=None, **kwargs):
        super().__init__(**kwargs)
        self.protocol_directory = protocol_directory or self.allowance.directory
        self.expected_route = deepcopy(self.routing)
        self.stopped = None

    def complete(self, request, schema, settings):
        require(self.stopped is None, {'pilot_provider_stopped': self.stopped}, 'E_DEPENDENCY')
        require(self.routing == self.expected_route, 'Pilot provider route changed', 'E_STALE_REVIEW')
        check_frozen(self.protocol_directory, self.allowance.root)
        self.allowance.stage = stage_for(request)
        seconds = min(settings.timeout_seconds, self.allowance.remaining_seconds())
        require(seconds >= 5, 'Pilot global deadline exhausted', 'E_RESOURCE_LIMIT')
        print(json.dumps({'event': 'dispatch', 'arm': self.allowance.arm,
                          'stage': self.allowance.stage, 'task': request.get('task'),
                          'used_before': self.allowance.verify()['used'],
                          'request_bytes': len(canonical(request)), 'timeout_seconds': seconds}), flush=True)
        try:
            answer = super().complete(request, schema, settings.model_copy(update={'timeout_seconds': seconds}))
        except Exception as exc:
            # No further calls through this instance after failed transport. This
            # also catches core paths that convert provider exceptions to reports.
            self.stopped = {'error': getattr(exc, 'code', type(exc).__name__),
                            'details': getattr(exc, 'details', str(exc))}
            save(self.protocol_directory / (self.allowance.arm + '-provider-stop.json'), self.stopped)
            raise
        print(json.dumps({'event': 'response', 'arm': self.allowance.arm,
                          'slot': answer.provenance['allowance_slot'],
                          'wall_milliseconds': answer.provenance['wall_milliseconds']}), flush=True)
        return answer


def roots_and_inputs():
    from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
    from legalmath.interpretation.assurance import source_context
    from legalmath.interpretation.assurance.investigation_answer import question_text
    spec = read(SPEC)
    for key in ('source_packet', 'source_context', 'source_qualification'):
        checked(spec[key])
    context = read(SOURCE / 'context.json')
    roots = [{'url': d['url'], 'media_type': d['media_type'], 'data': d['text'].encode(),
              'selection': d['selection']} for d in context['documents']]
    def no_network(_):
        raise AssertionError('Frozen pilot attempted new source acquisition')
    acquired = acquire_context(roots, fetcher=no_network, max_documents=4, max_depth=0)
    packet = packet_from_context(acquired, question_text(spec['questions']))
    require(packet == read(checked(spec['source_packet'])), 'Frozen source packet differs')
    qualified = source_context.validate(ROOT, read(checked(spec['source_context'])), roots)
    require(source_context.input_identity(roots) == spec['source_inputs'], 'Frozen roots differ')
    return roots, qualified, spec


def runner_for(arm, provider, directory=OUT):
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from scripts.legal_integration_tools import ProductToolBackend
    spec = read(SPEC)
    settings = PilotSettings.model_validate({**spec['arms'][arm]['settings'], 'deadline_seconds': 10800})
    return CompleteInvestigation(ROOT, directory / arm / 'product', provider,
        ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', '2026-10-10T00:00:00Z',
        settings=settings, maximum_scoped_actions=82, scoped_rounds=1, scoped_batch_size=12,
        optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)) if arm == 'candidate' else None)


def check_frozen(directory=OUT, root=ROOT):
    freeze = read(directory / 'protocol.json')
    for item in freeze['files']:
        checked(item, root)
    for row in freeze['source_snapshot']:
        checked(row['current'], root)
        checked(row['retained'], root)
    from legalmath.interpretation.assurance.integrated import implementation_identity
    require(implementation_identity() == freeze['implementation'], 'Product implementation changed', 'E_STALE_REVIEW')
    require(CodexProvider().routing == freeze['route'], 'Configured provider route changed', 'E_STALE_REVIEW')
    if 'grant_prefix' in freeze:
        before = read(checked(freeze['grant_prefix'], root))
        current = read(root / freeze['shared_ledger'])
        prior_calls = freeze.get('prior_calls', 4)
        require(type(prior_calls) is int and prior_calls in (4, 5)
                and before['maximum'] == current['maximum'] == 400
                and len(before['calls']) == prior_calls
                and current['calls'][:prior_calls] == before['calls'],
                'Continuation rewrote its spent reservations', 'E_AUTHORITY')
        parent = read(checked(freeze['parent_protocol'], root))
        for row in parent['source_snapshot']:
            checked(row['retained'], root)
    return freeze


def prepare():
    from scripts.legal_mission_control import admit, BASE
    from legalmath.interpretation.assurance.investigation_observations import method
    from legalmath.interpretation.assurance.integrated import implementation_identity
    require(not (OUT / 'protocol.json').exists() and not (OUT / 'execution-started.json').exists(),
            'Pilot already frozen or executed; use check/status, never reset it', 'E_JOB_STATE')
    if (OUT / 'allowance.json').exists():
        require(read(OUT / 'allowance.json') == {'maximum': 400, 'calls': []},
                'Cannot prepare over a spent allowance', 'E_AUTHORITY')
    admission = admit(read(ROOT / BASE / 'mission.json'), read(ROOT / BASE / 'tools.json'))
    require(admission['task']['id'] == 'product-contribution', 'Wrong mission task', 'E_AUTHORITY')
    roots, qualified, spec = roots_and_inputs()
    checked(PROTECTED)
    OUT.mkdir(parents=True, exist_ok=True)
    save(OUT / 'mission-before.json', read(ROOT / BASE / 'mission.json'))
    save(OUT / 'admission-before.json', admission)
    save(OUT / 'qualified-source-context.json', qualified)
    grant = {'schema': 'legalmath.mission-pilot-grant.v1', 'authorization': AUTHORIZATION,
        'maximum': 400, 'started_utc': START, 'deadline_utc': END,
        'allocations': {a: STAGES for a in ARMS}, 'optional_assessment_calls': 1, 'unallocated_calls': 25,
        'historical_unused_transfer': False,
        'historical_ledger': spec['historical_resources']['ledger'],
        'historical_authorization': spec['historical_resources']['authorization'],
        'protected_allowance': PROTECTED, 'plan': ref(PLAN), 'specification': ref(SPEC),
        'cost_basis': 'Explicit call/time authorization on existing route; service prices and token limits unknown; no monetary ceiling asserted.'}
    immutable(OUT / 'authorization.json', grant)
    immutable(OUT / 'allowance.json', {'maximum': 400, 'calls': []})
    arms = {a: method(runner_for(a, PilotProvider(allowance=PilotAllowance(a)))) for a in ARMS}
    baseline, candidate = deepcopy(arms['baseline']), deepcopy(arms['candidate'])
    baseline.pop('optional_tools'); candidate.pop('optional_tools')
    require(baseline == candidate, 'Unmatched methods before dispatch')
    paths = [PLAN, Path(__file__), ROOT / 'scripts/legal_mission_control.py',
             ROOT / 'tests/assurance/test_mission_live_pilot.py',
             *sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    for item in arms['candidate']['optional_tools']['files']:
        paths.append(ROOT / item['path'])
    for item in arms['candidate']['optional_tools']['logical_english']['files']:
        paths.append(ROOT / item['path'])
    snapshots = []
    for path in sorted(set(paths)):
        target = OUT / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots.append({'current': ref(path), 'retained': ref(target)})
    freeze = {'profile': 'legalmath.mission-pilot-protocol.v1', 'arms': arms,
        'arm_order': list(ARMS), 'implementation': implementation_identity(), 'route': CodexProvider().routing,
        'source_inputs': spec['source_inputs'], 'questions': spec['questions'],
        'source_snapshot': snapshots,
        'files': [ref(OUT / 'authorization.json'), ref(SPEC), spec['source_packet'],
                  spec['source_qualification'], ref(OUT / 'qualified-source-context.json')],
        'random_seeds': 'Not configurable by this service route; same-model correlation unmeasured.',
        'legal_question_reduced': False, 'both_arm_envelopes_reserved_upfront': True}
    save(OUT / 'protocol.json', freeze)
    save(OUT / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': '.venv/bin/python scripts/legal_mission_live_pilot.py execute',
        'environment': {'python': sys.version, 'executable': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU only; GPU devices intentionally hidden.',
        'plan': ref(PLAN), 'protocol': ref(OUT / 'protocol.json'), 'authorization': ref(OUT / 'authorization.json'),
        'data_version': spec['source_inputs'], 'random_seeds': freeze['random_seeds'],
        'started_utc': START, 'deadline_utc': END, 'wall_seconds': 'Pending execution',
        'result_file': str((OUT / 'result.json').relative_to(ROOT))})
    result = {'status': 'PREPARED', 'new_calls': 0, 'maximum': 400, 'allocated_pair': 374,
              'optional_assessment': 1, 'unallocated': 25, 'deadline_utc': END,
              'core_deadline_seconds': 10800, 'methods_match_except_tools': True}
    save(OUT / 'preparation-result.json', result)
    check_frozen()
    return result


def check():
    from scripts.legal_mission_control import admit, BASE
    admission = admit(read(ROOT / BASE / 'mission.json'), read(ROOT / BASE / 'tools.json'))
    require(admission['task']['id'] == 'product-contribution', 'Wrong admitted task', 'E_AUTHORITY')
    registered = admission.get('recorded_live_pilot')
    require(registered is not None and registered['authorization'] == ref(OUT / 'authorization.json')
            and registered['protocol'] == ref(OUT / 'protocol.json'),
            'Fresh live protocol must be registered with mission control', 'E_AUTHORITY')
    freeze = check_frozen()
    roots_and_inputs()
    return {'check': 'PASS', 'protocol_hash': digest(freeze),
            'allowance': PilotAllowance('baseline').verify(), 'new_calls': 0}


def execute(directory=None, *, checker=None, runner_factory=None, allowance_factory=None):
    from legalmath.interpretation.assurance import dossier_answer as consumer
    from legalmath.interpretation.assurance.investigation_answer import question_text
    from legalmath.interpretation.assurance.investigation_observations import method
    directory = OUT if directory is None else Path(directory)
    checker = checker or check
    runner_factory = runner_factory or runner_for
    allowance_factory = allowance_factory or PilotAllowance
    with (directory / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (directory / 'result.json').exists():
            return read(directory / 'result.json')
        require(not (directory / 'execution-started.json').exists(),
                'Prior execution was interrupted; inspect receipts before a reviewed continuation', 'E_JOB_STATE')
        checker()
        immutable(directory / 'execution-started.json', {'epoch_seconds': int(time.time()), 'protocol': ref(directory / 'protocol.json')})
        began = time.monotonic()
        results = {}
        roots, qualified, spec = roots_and_inputs()
        freeze = check_frozen(directory)
        for arm in ARMS:
            arm_directory = directory / arm
            arm_directory.mkdir(exist_ok=True)
            allowance = allowance_factory(arm)
            provider = PilotProvider(allowance=allowance, protocol_directory=directory)
            runner = runner_factory(arm, provider, directory)
            require(method(runner) == freeze['arms'][arm], 'Method differs from frozen arm', 'E_STALE_REVIEW')
            try:
                dossier = runner.run(roots, question_text(spec['questions']), source_context=qualified)
                dref = ref(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json')
                save(arm_directory / 'investigation-result.json', {'dossier': dref,
                    'execution_complete': dossier['execution_complete'], 'allowance': allowance.verify()})
                require(dossier['execution_complete'], {'stage': 'INVESTIGATION', 'dossier': dref,
                    'reason': 'Incomplete investigation cannot establish the complete-answer comparator'}, 'E_REFERENCE')
                def guard():
                    check_frozen(directory)
                    allowance.verify()
                    require(allowance.remaining_seconds() >= 5, 'Pilot deadline exhausted', 'E_RESOURCE_LIMIT')
                result = consumer.propose(ROOT, dref, provider, arm_directory / 'answer',
                    investigation_directory=runner.directory, expected_revision=dossier['revision'],
                    questions=spec['questions'], qualification_ref=spec['source_qualification'], dispatch_guard=guard)
                results[arm] = {'dossier': dref, 'answer_result': result, 'allowance': allowance.verify()}
                save(arm_directory / 'result.json', results[arm])
                if result['status'] != 'STRUCTURALLY_VALID_PROPOSAL':
                    break
            except Exception as exc:
                results[arm] = {'status': 'STOPPED', 'error': getattr(exc, 'code', type(exc).__name__),
                    'details': getattr(exc, 'details', str(exc)), 'allowance': allowance.verify()}
                save(arm_directory / 'result.json', results[arm])
                break
        complete = len(results) == 2 and all(r.get('answer_result', {}).get('status') == 'STRUCTURALLY_VALID_PROPOSAL' for r in results.values())
        result = {'status': 'PAIR_READY_FOR_SOURCE_REVIEW' if complete else 'PAIR_UNAVAILABLE',
            'arms': results, 'used_calls': allowance_factory('baseline').verify()['used'],
            'wall_seconds': int(time.monotonic() - began), 'legal_quality_evaluated': False,
            'release_eligible': False, 'deadline_utc': END,
            'next_action': 'Review complete source arguments and reduction fidelity' if complete else 'Inspect the exact retained failure and review a bounded remedy; no automatic retry'}
        save(directory / 'result.json', result)
        return result


def status():
    return {'grant': PilotAllowance('baseline').verify(), 'candidate': PilotAllowance('candidate').verify(),
            'result': read(OUT / 'result.json') if (OUT / 'result.json').exists() else None,
            'started': (OUT / 'execution-started.json').exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'execute', 'status'))
    parser.add_argument('--revision', choices=('source-spans', 'decomposed'))
    args = parser.parse_args()
    try:
        if args.revision:
            from scripts import legal_mission_pilot_source_spans as revision
            revision.select(args.revision)
            result = getattr(revision, args.action)()
        else:
            result = globals()[args.action]()
        # Full failures are retained on disk; avoid flooding the editor stream.
        display = {k: v for k, v in result.items() if k not in ('arms', 'result')}
        if 'result' in result:
            display['result_status'] = result['result'].get('status') if result['result'] else None
        if 'arms' in result:
            display['arms'] = {a: {'status': r.get('status', r.get('answer_result', {}).get('status')),
                                  'error': r.get('error')} for a, r in result['arms'].items()}
        print(json.dumps(display, indent=2), flush=True)
        return 1 if result.get('status') == 'PAIR_UNAVAILABLE' else 0
    except (LegalMathError, ValueError, OSError) as exc:
        print(json.dumps({'status': 'REFUSED', 'error': getattr(exc, 'code', type(exc).__name__),
                          'details': getattr(exc, 'details', str(exc))}), flush=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
