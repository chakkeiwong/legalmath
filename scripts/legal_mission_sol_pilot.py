#!/usr/bin/env python3
"""One matched Sol continuation using the original product, grant and clock."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import legal_mission_live_pilot as pilot
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import CodexProvider

OUT = pilot.OUT / 'sol'
PARENT = pilot.OUT / 'decomposed'
CANARY = pilot.OUT / 'sol-canary'
PLAN = ROOT / 'docs/plans/legal-mission-live-pilot-sol.md'
MODEL = 'gpt-6.1-sol'
PRIOR_CALLS = 8
CORE_CALLS = 28


def now():
    return datetime.now(timezone.utc).isoformat()


class SolAllowance(pilot.PilotAllowance):
    def stage_limit(self, stage):
        # Eight historical baseline/core reservations remain charged. Candidate
        # cannot use its eight otherwise unspent slots to gain unequal effort.
        if self.arm == 'candidate' and stage == 'core':
            return CORE_CALLS
        return super().stage_limit(stage)


class SolProvider(CodexProvider):
    def __init__(self, *, protocol_directory=OUT, **kwargs):
        super().__init__(**kwargs)
        self.routing['model'] = MODEL
        self.expected_route = deepcopy(self.routing)
        self.protocol_directory = Path(protocol_directory)
        self.stopped = None

    def command(self, directory, schema, output):
        command = super().command(directory, schema, output)
        pilot.require(command[command.index('--model') + 1] == MODEL,
                      'Sol model selection lost', 'E_STALE_REVIEW')
        slot = self.allowance.verify()['used']
        pilot.save(self.protocol_directory / 'provider-commands' / f'{slot:04}.json',
                   {'argv': command, 'model': MODEL, 'route_hash': digest(self.routing)})
        return command

    def complete(self, request, schema, settings):
        pilot.require(self.stopped is None, {'provider_stopped': self.stopped}, 'E_DEPENDENCY')
        frozen = check_frozen(self.protocol_directory)
        pilot.require(self.routing == self.expected_route == frozen['route'],
                      'Provider differs from the explicit Sol method', 'E_STALE_REVIEW')
        self.allowance.stage = pilot.stage_for(request)
        seconds = min(settings.timeout_seconds, self.allowance.remaining_seconds())
        pilot.require(seconds >= 5, 'Original grant deadline exhausted', 'E_RESOURCE_LIMIT')
        print(json.dumps({'event': 'dispatch', 'arm': self.allowance.arm,
            'stage': self.allowance.stage, 'task': request.get('task'), 'model': MODEL,
            'used_before': self.allowance.verify()['used'], 'timeout_seconds': seconds}), flush=True)
        try:
            answer = super().complete(request, schema, settings.model_copy(update={'timeout_seconds': seconds}))
        except Exception as exc:
            self.stopped = {'error': getattr(exc, 'code', type(exc).__name__),
                            'details': getattr(exc, 'details', str(exc))}
            pilot.save(self.protocol_directory / (self.allowance.arm + '-provider-stop.json'), self.stopped)
            raise
        print(json.dumps({'event': 'response', 'arm': self.allowance.arm,
            'slot': answer.provenance['allowance_slot'],
            'wall_milliseconds': answer.provenance['wall_milliseconds']}), flush=True)
        return answer


def runner_for(arm, provider, directory=OUT):
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from legalmath.interpretation.assurance.source_references import PROTOCOL
    from scripts.legal_integration_tools import ProductToolBackend
    spec = pilot.read(pilot.SPEC)
    settings = pilot.PilotSettings.model_validate({**spec['arms'][arm]['settings'],
        'deadline_seconds': 10800, 'total_model_calls': CORE_CALLS,
        'inventory_piece_characters': 20000, 'inventory_piece_units': 32})
    return CompleteInvestigation(ROOT, Path(directory) / arm / 'product', provider,
        ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', '2026-10-10T00:00:00Z',
        settings=settings, maximum_scoped_actions=82, scoped_rounds=1, scoped_batch_size=12,
        reference_protocol=PROTOCOL, input_profile='readable-tables.v1',
        optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)) if arm == 'candidate' else None)


def check_frozen(directory=OUT):
    from legalmath.interpretation.assurance.integrated import implementation_identity
    frozen = pilot.read(Path(directory) / 'protocol.json')
    for item in frozen['files']:
        pilot.checked(item)
    for row in frozen['source_snapshot']:
        pilot.checked(row['current'])
        pilot.checked(row['retained'])
    pilot.require(implementation_identity() == frozen['implementation'], 'Product source changed', 'E_STALE_REVIEW')
    route = CodexProvider().routing
    route['model'] = MODEL
    pilot.require(route == frozen['route'], 'Configured service route changed', 'E_STALE_REVIEW')
    before = pilot.read(pilot.checked(frozen['grant_prefix']))
    current = pilot.read(ROOT / frozen['shared_ledger'])
    pilot.require(before['maximum'] == current['maximum'] == 400
        and len(before['calls']) == PRIOR_CALLS and current['calls'][:PRIOR_CALLS] == before['calls'],
        'The eight spent calls changed', 'E_AUTHORITY')
    return frozen


def admission():
    from scripts.legal_mission_control import admit, BASE
    value = admit(pilot.read(ROOT / BASE / 'mission.json'), pilot.read(ROOT / BASE / 'tools.json'))
    pilot.require(value['task']['id'] == 'product-contribution', 'Wrong admitted task', 'E_AUTHORITY')
    return value


def prepare():
    from legalmath.interpretation.assurance.investigation_observations import method
    from legalmath.interpretation.assurance.integrated import implementation_identity
    pilot.require(not (OUT / 'protocol.json').exists() and not (OUT / 'execution-started.json').exists(),
                  'Sol continuation already prepared or started', 'E_JOB_STATE')
    admitted = admission()
    allowance = SolAllowance('baseline')
    pilot.require(allowance.verify()['used'] == PRIOR_CALLS and allowance.remaining_seconds() >= 10800,
                  'Sol continuation requires its eight-call predecessor and original remaining clock', 'E_AUTHORITY')
    prefix = pilot.read(allowance.path)
    pilot.require(all(r['arm'] == 'baseline' and r['stage'] == 'core' for r in prefix['calls']),
                  'Unexpected earlier allocation')
    parent = pilot.check_frozen(PARENT)
    canary = pilot.read(CANARY / 'result.json')
    pilot.require(canary['status'] == 'PASS' and canary['calls_used'] == PRIOR_CALLS
                  and canary['model'] == MODEL, 'Sol canary did not pass')
    _, qualified, spec = pilot.roots_and_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    pilot.immutable(OUT / 'calls-before.json', prefix)
    pilot.save(OUT / 'admission-before.json', admitted)
    pilot.save(OUT / 'qualified-source-context.json', qualified)
    qualification = pilot.read(PARENT / 'qualification.json')
    pilot.require(qualification['minimum_inventory_calls'] == 12
                  and qualification['all_55_units_preserved_in_order']
                  and all(p['round_trip_exact'] and p['wire_bytes'] <= 200000 for p in qualification['pieces']),
                  'Retained full-source decomposition qualification failed')
    arms = {arm: method(runner_for(arm, SolProvider(allowance=SolAllowance(arm)))) for arm in pilot.ARMS}
    baseline, candidate = deepcopy(arms['baseline']), deepcopy(arms['candidate'])
    baseline.pop('optional_tools'); candidate.pop('optional_tools')
    pilot.require(baseline == candidate, 'Sol methods are unmatched')
    # Require only the requested provider change and remaining call reduction
    # relative to the already-qualified product method.
    for arm in pilot.ARMS:
        current, prior = deepcopy(arms[arm]), deepcopy(parent['arms'][arm])
        current.pop('provider'); prior.pop('provider')
        current['settings']['total_model_calls'] = prior['settings']['total_model_calls']
        pilot.require(current == prior, 'An unreviewed product setting changed')
    paths = [ROOT / row['current']['path'] for row in parent['source_snapshot']]
    paths += [PLAN, Path(__file__).resolve(), ROOT / 'tests/assurance/test_mission_sol_pilot.py']
    snapshots = []
    for path in sorted(set(paths)):
        target = OUT / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots.append({'current': pilot.ref(path), 'retained': pilot.ref(target)})
    evidence = [PARENT / 'protocol.json', PARENT / 'result.json', PARENT / 'qualification.json',
        CANARY / 'protocol.json', CANARY / 'result.json', CANARY / 'run-manifest.json',
        OUT / 'calls-before.json', OUT / 'qualified-source-context.json',
        ROOT / 'docs/implementation/legal-mission-control/results/sol-canary.md']
    frozen = {'profile': 'legalmath.mission-sol-pilot.v1', 'arms': arms,
        'implementation': implementation_identity(), 'route': arms['baseline']['provider']['route'],
        'configured_route': CodexProvider().routing, 'source_inputs': spec['source_inputs'],
        'questions': spec['questions'], 'source_snapshot': snapshots,
        'files': parent['files'] + [pilot.ref(p) for p in evidence],
        'grant_prefix': pilot.ref(OUT / 'calls-before.json'),
        'shared_ledger': str(allowance.path.relative_to(ROOT)), 'prior_calls': PRIOR_CALLS,
        'new_core_calls_per_arm': CORE_CALLS, 'maximum_additional_calls': 358,
        'random_seeds': parent['random_seeds'], 'arm_order': list(pilot.ARMS),
        'legal_question_reduced': False, 'prior_attempts_erased': False,
        'authorization': 'continue the execution; following explicit user selection of GPT-6.1 Sol'}
    pilot.immutable(OUT / 'protocol.json', frozen)
    pilot.save(OUT / 'run-manifest.json', {'status': 'PREPARED', 'prepared_utc': now(),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': '.venv/bin/python scripts/legal_mission_sol_pilot.py execute',
        'environment': {'python': sys.version, 'executable': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU only; GPU devices intentionally hidden.', 'plan': pilot.ref(PLAN),
        'protocol': pilot.ref(OUT / 'protocol.json'), 'authorization': pilot.ref(pilot.OUT / 'authorization.json'),
        'data_version': spec['source_inputs'], 'random_seeds': frozen['random_seeds'],
        'deadline_utc': pilot.END, 'calls_before': PRIOR_CALLS, 'wall_seconds': 'Pending execution',
        'result_file': str((OUT / 'result.json').relative_to(ROOT)),
        'result_note': 'docs/implementation/legal-mission-control/results/live-pilot-sol.md'})
    check_frozen()
    result = {'status': 'PREPARED', 'model': MODEL, 'methods_match_except_tools': True,
        'used_calls': PRIOR_CALLS, 'maximum_additional_calls': 358, 'maximum_all_attempt_calls': 366,
        'deadline_utc': pilot.END, 'core_calls_per_arm': CORE_CALLS,
        'minimum_inventory_calls': 12, 'complete_workflow_capacity': 'NOT_ESTABLISHED'}
    pilot.save(OUT / 'preparation-result.json', result)
    return result


def check():
    from legalmath.interpretation.assurance.investigation_observations import method
    admitted = admission()
    pilot.require(admitted['task'].get('live_method_revision') == {
        'id': 'sol', 'protocol': pilot.ref(OUT / 'protocol.json'), 'plan': pilot.ref(PLAN)},
        'Sol continuation is not registered', 'E_AUTHORITY')
    frozen = check_frozen()
    pilot.roots_and_inputs()
    for arm in pilot.ARMS:
        provider = SolProvider(allowance=SolAllowance(arm))
        pilot.require(method(runner_for(arm, provider)) == frozen['arms'][arm],
                      'Actual method differs from reviewed Sol arm', 'E_STALE_REVIEW')
    return {'check': 'PASS', 'model': MODEL, 'allowance': SolAllowance('baseline').verify()}


def execute():
    from legalmath.interpretation.assurance import dossier_answer as consumer
    from legalmath.interpretation.assurance.investigation_answer import question_text
    from legalmath.interpretation.assurance.investigation_observations import method
    with (OUT / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (OUT / 'result.json').exists():
            return pilot.read(OUT / 'result.json')
        pilot.require(not (OUT / 'execution-started.json').exists(),
                      'Uncertain prior Sol execution cannot restart', 'E_JOB_STATE')
        check()
        pilot.immutable(OUT / 'execution-started.json', {'epoch_seconds': int(time.time()),
                                                      'protocol': pilot.ref(OUT / 'protocol.json')})
        began = time.monotonic()
        manifest = pilot.read(OUT / 'run-manifest.json')
        manifest.update({'status': 'RUNNING', 'started_utc': now()})
        pilot.save(OUT / 'run-manifest.json', manifest)
        results = {}
        try:
            roots, qualified, spec = pilot.roots_and_inputs()
            frozen = check_frozen()
            for arm in pilot.ARMS:
                arm_directory = OUT / arm
                arm_directory.mkdir(exist_ok=True)
                allowance = SolAllowance(arm)
                provider = SolProvider(allowance=allowance)
                runner = runner_for(arm, provider)
                pilot.require(method(runner) == frozen['arms'][arm], 'Actual method changed', 'E_STALE_REVIEW')
                try:
                    dossier = runner.run(roots, question_text(spec['questions']), source_context=qualified)
                    dref = pilot.ref(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json')
                    pilot.save(arm_directory / 'investigation-result.json', {'dossier': dref,
                        'execution_complete': dossier['execution_complete'], 'allowance': allowance.verify()})
                    pilot.require(dossier['execution_complete'], {'stage': 'INVESTIGATION', 'dossier': dref,
                        'reason': 'Incomplete investigation cannot establish a complete-answer comparator'}, 'E_REFERENCE')
                    def guard():
                        check_frozen()
                        allowance.verify()
                        pilot.require(allowance.remaining_seconds() >= 5,
                                      'Original grant deadline exhausted', 'E_RESOURCE_LIMIT')
                    answer = consumer.propose(ROOT, dref, provider, arm_directory / 'answer',
                        investigation_directory=runner.directory, expected_revision=dossier['revision'],
                        questions=spec['questions'], qualification_ref=spec['source_qualification'], dispatch_guard=guard)
                    results[arm] = {'dossier': dref, 'answer_result': answer, 'allowance': allowance.verify()}
                    pilot.save(arm_directory / 'result.json', results[arm])
                    if answer['status'] != 'STRUCTURALLY_VALID_PROPOSAL':
                        break
                except Exception as exc:
                    results[arm] = {'status': 'STOPPED', 'error': getattr(exc, 'code', type(exc).__name__),
                        'details': getattr(exc, 'details', str(exc)), 'allowance': allowance.verify()}
                    pilot.save(arm_directory / 'result.json', results[arm])
                    break
            complete = len(results) == 2 and all(r.get('answer_result', {}).get('status') ==
                'STRUCTURALLY_VALID_PROPOSAL' for r in results.values())
            result = {'status': 'PAIR_READY_FOR_SOURCE_REVIEW' if complete else 'PAIR_UNAVAILABLE',
                'model': MODEL, 'arms': results, 'used_calls': SolAllowance('baseline').verify()['used'],
                'wall_seconds': round(time.monotonic() - began, 3), 'deadline_utc': pilot.END,
                'legal_quality_evaluated': False, 'release_eligible': False,
                'next_action': 'Review source arguments and actual tool contribution' if complete else
                               'Retain and classify the precise failed prerequisite; no automatic rerun'}
            pilot.save(OUT / 'result.json', result)
        finally:
            manifest.update({'finished_utc': now(), 'wall_seconds': round(time.monotonic() - began, 3),
                'calls_after': SolAllowance('baseline').verify()['used'],
                'status': pilot.read(OUT / 'result.json')['status'] if (OUT / 'result.json').exists()
                          else 'INTERRUPTED_OR_ERROR'})
            pilot.save(OUT / 'run-manifest.json', manifest)
        return result


def status():
    return {'model': MODEL, 'allowance': SolAllowance('baseline').verify(),
        'started': (OUT / 'execution-started.json').exists(),
        'result': pilot.read(OUT / 'result.json')['status'] if (OUT / 'result.json').exists() else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'execute', 'status'])
    args = parser.parse_args()
    try:
        result = globals()[args.action]()
        display = {k: v for k, v in result.items() if k != 'arms'}
        if 'arms' in result:
            display['arms'] = {a: {'status': r.get('status', r.get('answer_result', {}).get('status')),
                                  'error': r.get('error')} for a, r in result['arms'].items()}
        print(json.dumps(display, indent=2), flush=True)
        return 1 if result.get('status') == 'PAIR_UNAVAILABLE' else 0
    except (LegalMathError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'REFUSED', 'error': getattr(exc, 'code', type(exc).__name__),
                          'details': getattr(exc, 'details', str(exc))}), flush=True)
        return 2


if __name__ == '__main__':
    # Keep method provenance identical between script and imported execution.
    from scripts.legal_mission_sol_pilot import main as entrypoint
    sys.exit(entrypoint())
