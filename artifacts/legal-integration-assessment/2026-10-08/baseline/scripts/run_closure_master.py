"""Round-12 fixed-command phases, immutable attempts, repairs and plan refresh."""
from argparse import ArgumentParser
from pathlib import Path
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

from run_assurance_master import invoke, now, sha, write, read

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/implementation/interpretation-round12'
OUT = ROOT / 'artifacts/interpretation/round12'
PY = ROOT / '.venv/bin/python'
TOOLPY = ROOT / '.localresources/assurance-tools/venv/bin/python'
DOCPY = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
PHASES = tuple('P'+str(i) for i in range(6))
LIVE_INCOMPLETE = 'INCOMPLETE_LIVE_EVIDENCE'


def state():
    return read(OUT/'state.json', {'phases': {p: {'status': 'PLANNED', 'attempts': [], 'repairs': []} for p in PHASES}})


def material(phase):
    paths = [Path(__file__), ROOT/'scripts/run_assurance_master.py',
             DOC/'master-plan.json', DOC/'allowlist.json', DOC/'design-review.json']
    if phase == 'P0':
        paths += [p for p in (ROOT/'docs/monograph').rglob('*') if p.is_file() and
                  p.suffix in ('.tex', '.bib') and 'review' not in p.parts]
        paths += [ROOT/'docs/plans/assurance-round12-execution.md', ROOT/'scripts/assurance_routes.py']
    else:
        paths += [p for b in ('src', 'tests') for p in (ROOT/b).rglob('*') if p.is_file() and
                  p.suffix in ('.py', '.java', '.json') and '__pycache__' not in p.parts]
        paths += [ROOT/'scripts/closure_routes.py', ROOT/'scripts/closure_live.py', ROOT/'scripts/closure_corpus.py', ROOT/'scripts/closure_pit.py', ROOT/'scripts/closure_evaluation.py',
                  DOC/'case-contract.json', DOC/'authorization.json', DOC/'transfer-reference-packets.json']
        paths += list((ROOT/'examples/multi-circular-2026').rglob('*.json'))
        paths += list((ROOT/'examples/java-dry-run').rglob('*.json'))
        paths += list((ROOT/'docs/specs/v0.1/fixtures').rglob('*'))
        paths += [ROOT/'.localresources/assurance-tools'/name for name in
                  ('tool-lock.json', 'model-lock.json', 'requirements.lock')]
        paths += list((ROOT/'.localresources/sfc').glob('*'))
    if phase == 'P5':
        paths += [ROOT/'scripts/closure_references.py']
        paths += list((DOC/'transfer-bindings').glob('*.json'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths)) if p.is_file()}


def commands(phase, out):
    def route(name, tool=False):
        return [str(TOOLPY if tool else PY), str(ROOT/'scripts/closure_routes.py'), name, '--out', str(out/name)]
    def tests(*targets):
        return [str(PY), '-m', 'pytest', *targets, '-q', '--junitxml='+str(out/'tests.xml'), '-o', 'faulthandler_timeout=60']
    if phase == 'P0':
        return [('document', [str(DOCPY), str(ROOT/'scripts/assurance_routes.py'), 'document', '--out', str(out/'document')])]
    if phase == 'P1':
        return [('tests', tests('tests/assurance/test_investigation.py', 'tests/assurance/test_closure_master.py')),
                ('sources', route('sources', True))]
    if phase == 'P2':
        return [('tests', tests('tests/assurance/test_investigation.py', 'tests/assurance/test_integrated_workflow.py',
                                'tests/assurance/test_authorities.py', 'tests/assurance/test_repair.py'))]
    if phase == 'P3':
        return [('formal', route('formal', True)), ('mutations', route('mutations')),
                ('catala', tests('tests/catala'))]
    if phase == 'P4': return [('live', [str(PY), str(ROOT/'scripts/closure_live.py'), '--out', str(out/'live')])]
    return [('tests', tests('tests')), ('evaluation', route('evaluation'))]


def audit():
    plan = read(DOC/'master-plan.json'); allow = read(DOC/'allowlist.json')
    review = read(DOC/'design-review.json')
    if tuple(p['id'] for p in plan['phases']) != PHASES or len(review['findings']) < 12:
        raise ValueError('Incomplete phase plan or skeptical review')
    if review['verdict'] != 'PASS_WITH_EXPLICIT_EVIDENCE_LIMITS' or plan['release_eligible']:
        raise ValueError('Unreviewed plan')
    for specification in plan['phases']:
        bound = specification.get('max_failed_attempts', plan['max_failed_attempts_per_phase'])
        if type(bound) is not int or not 1 <= bound <= 4:
            raise ValueError('Invalid declared phase-attempt bound')
    for phase in PHASES:
        for _, argv in commands(phase, OUT/phase/'audit'):
            if argv[0] not in allow['interpreters']: raise ValueError('Interpreter denied')
            if argv[1] == '-m':
                if argv[2] != 'pytest': raise ValueError('Module denied')
                targets = argv[3:argv.index('-q')]
                if any(t not in allow['pytest_targets'] for t in targets): raise ValueError('Test target denied')
            elif str(Path(argv[1]).relative_to(ROOT)) not in allow['scripts']:
                raise ValueError('Script denied')
    authority = read(DOC/'authorization.json')
    ledger = read(ROOT/authority['allowance_path'])
    if ledger['maximum'] != 500 or authority['ceiling'] > 500:
        raise ValueError('Allowance ceiling changed')
    prefix = ledger['calls'][:authority['used_at_preparation']]
    if hashlib.sha256(json.dumps(prefix, sort_keys=True).encode()).hexdigest() != authority['prefix_sha256']:
        raise ValueError('Historical allowance changed')
    return {'verdict': review['verdict'], 'review_sha256': sha(DOC/'design-review.json'),
            'independent_review': False, 'ledger_consumed': len(ledger['calls']),
            'remaining_this_round': max(0, authority['ceiling']-len(ledger['calls']))}


def refresh(phase, s):
    spec = next(p for p in read(DOC/'master-plan.json')['phases'] if p['id'] == phase)
    value = {'phase': phase, 'at': now(), 'spec': spec, 'inputs': material(phase), 'audit': audit(),
             'predecessors': {p: s['phases'][p] for p in PHASES[:PHASES.index(phase)]},
             'repairs': s['phases'][phase]['repairs'], 'release_eligible': False}
    write(OUT/phase/'next-plan.json', value)
    return value


def verify_attempt(entry):
    path = ROOT/entry['path']
    if sha(path) != entry['sha256']: raise ValueError('Attempt manifest changed')
    record = read(path)
    for name, expected in record['artifacts'].items():
        target = (path.parent/name).resolve()
        if not target.is_relative_to(path.parent.resolve()) or sha(target) != expected:
            raise ValueError('Attempt artifact changed: '+name)
    return record


def invalidate(s):
    stale = None
    for phase in PHASES:
        ps = s['phases'][phase]
        for entry in ps['attempts']: verify_attempt(entry)
        if ps['status'] in ('PASSED', LIVE_INCOMPLETE) and verify_attempt(ps['attempts'][-1])['inputs'] != material(phase):
            stale = phase; break
    if stale:
        for phase in PHASES[PHASES.index(stale):]:
            if s['phases'][phase]['status'] in ('PASSED', LIVE_INCOMPLETE): s['phases'][phase]['status'] = 'STALE'
        write(OUT/'state.json', s)
        if (OUT/'final-report.json').exists():
            report = read(OUT/'final-report.json'); report['engineering_status'] = 'STALE'
            write(OUT/'final-report.json', report)


def execute_phase(phase, s):
    ps = s['phases'][phase]
    if ps['status'] in ('RUNNING', 'REPAIR_REQUIRED'): raise ValueError('Repair or recovery required')
    plan = read(DOC/'master-plan.json')
    specification = next(p for p in plan['phases'] if p['id'] == phase)
    bound = specification.get('max_failed_attempts', plan['max_failed_attempts_per_phase'])
    if sum(a['status'] != 'PASSED' for a in ps['attempts']) >= bound: raise ValueError('Phase retry budget exhausted')
    if any(s['phases'][p]['status'] != 'PASSED' and
           not (phase == 'P5' and p == 'P4' and s['phases'][p]['status'] == LIVE_INCOMPLETE)
           for p in PHASES[:PHASES.index(phase)]):
        raise ValueError('Predecessor incomplete')
    reviewed = refresh(phase, s)
    out = OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    out.mkdir(parents=True, exist_ok=False)
    write(out/'reviewed-plan.json', reviewed)
    record = {'phase': phase, 'started': now(), 'inputs': reviewed['inputs'], 'commands': [],
              'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'plan': 'docs/plans/assurance-round12-execution.md', 'cpu_only': True,
              'gpu': 'intentionally hidden', 'seeds': 'N/A: deterministic challenges; live provider nondeterminism retained',
              'status': 'RUNNING', 'release_eligible': False}
    ps['status'] = 'RUNNING'; write(OUT/'state.json', s)
    write(out/'in-progress.json', record)
    began = time.monotonic()
    try:
        for name, argv in commands(phase, out):
            print(phase+' '+name, flush=True)
            exit_code = invoke(argv, out/(name+'.log'), reviewed['spec']['timeout_seconds'])
            record['commands'].append({'name': name, 'argv': argv, 'exit_code': exit_code})
            if phase == 'P4' and exit_code == 2:
                live = read(out/'live/result.json')
                expected = {c['case_id'] for c in read(DOC/'case-contract.json')['cases']}
                if (live.get('engineering_status') != 'INCOMPLETE' or live.get('harness_failures') or
                    live.get('continuation_status') != 'INDEPENDENT_CHECKS_MAY_CONTINUE' or
                    {c['case_id'] for c in live.get('cases', [])} != expected):
                    raise ValueError('Missing or invalid incomplete live evidence')
                record['live_evidence_incomplete'] = True
                continue
            if exit_code: raise RuntimeError(name+' failed; inspect '+str(out/(name+'.log')))
        if material(phase) != record['inputs']: raise ValueError('Inputs changed during phase')
        record['status'] = ps['status'] = LIVE_INCOMPLETE if record.get('live_evidence_incomplete') else 'PASSED'
    except BaseException as exc:
        record['status'] = 'FAILED'; record['error'] = str(exc) or type(exc).__name__
        ps['status'] = 'REPAIR_REQUIRED'
    record['wall_milliseconds'] = int((time.monotonic()-began)*1000)
    record['finished'] = now()
    record['artifacts'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                           if p.is_file() and p.name != 'run-manifest.json'}
    write(out/'run-manifest.json', record)
    ps['attempts'].append({'path': str((out/'run-manifest.json').relative_to(ROOT)),
                           'sha256': sha(out/'run-manifest.json'), 'status': record['status']})
    write(OUT/'state.json', s)
    next_phase = phase if ps['status'] not in ('PASSED', LIVE_INCOMPLETE) else PHASES[min(PHASES.index(phase)+1, len(PHASES)-1)]
    write(OUT/'next-phase-plan.json', refresh(next_phase, s))
    if ps['status'] not in ('PASSED', LIVE_INCOMPLETE): raise RuntimeError(record['error'])


def recover(phase, s):
    """Retain an interrupted supervisor attempt without refunding its budget."""
    ps = s['phases'][phase]
    if ps['status'] != 'RUNNING': raise ValueError('No interrupted phase')
    out = OUT/phase/f"attempt-{len(ps['attempts'])+1:02}"
    for receipt in out.glob('*.process.json'):
        process = read(receipt); stat = Path('/proc')/str(process['pid'])/'stat'
        if stat.exists() and stat.read_text().split()[21] == process['start']:
            # The original launcher creates a dedicated process group. Verify
            # its identity and start time before terminating only that group.
            if os.getpgid(process['pid']) != process['pid']:
                raise ValueError('Unexpected process group during recovery')
            os.killpg(process['pid'], signal.SIGKILL)
    record = read(out/'in-progress.json')
    record.update(status='FAILED', error='SUPERVISOR_INTERRUPTED', finished=now())
    record['artifacts'] = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob('*'))
                           if p.is_file() and p.name != 'run-manifest.json'}
    write(out/'run-manifest.json', record)
    ps['attempts'].append({'path': str((out/'run-manifest.json').relative_to(ROOT)),
                          'sha256': sha(out/'run-manifest.json'), 'status': 'FAILED'})
    ps['status'] = 'REPAIR_REQUIRED'; write(OUT/'state.json', s)
    refresh(phase, s)


def repair(phase, note, s):
    ps = s['phases'][phase]
    if ps['status'] != 'REPAIR_REQUIRED': raise ValueError('No recorded failure to repair')
    note = Path(note).resolve()
    if not note.is_relative_to(DOC.resolve()) or not note.is_file() or len(note.read_text()) < 100:
        raise ValueError('Substantive local repair note required')
    out = OUT/phase/f"repair-{len(ps['repairs'])+1:02}"
    out.mkdir(parents=True, exist_ok=False)
    argv = [str(PY), '-m', 'pytest', 'tests/assurance/test_investigation.py',
            'tests/assurance/test_closure_master.py', '-q']
    if invoke(argv, out/'checks.log', 180): raise ValueError('Focused repair check failed')
    ps['repairs'].append({'note': str(note.relative_to(ROOT)), 'sha256': sha(note),
                         'command': argv, 'log_sha256': sha(out/'checks.log')})
    ps['status'] = 'REPAIRED'; write(OUT/'state.json', s); refresh(phase, s)


def finalize(s):
    if any(s['phases'][p]['status'] != 'PASSED' and
           not (p == 'P4' and s['phases'][p]['status'] == LIVE_INCOMPLETE)
           for p in PHASES): raise ValueError('Incomplete phases')
    evidence = {}
    for phase in PHASES:
        entry = s['phases'][phase]['attempts'][-1]
        if verify_attempt(entry)['inputs'] != material(phase): raise ValueError('Stale accepted phase')
        evidence[phase] = entry
    incomplete = s['phases']['P4']['status'] == LIVE_INCOMPLETE
    result = {'engineering_status': 'ENGINEERING_CHECKS_PASSED_LIVE_EVIDENCE_INCOMPLETE' if incomplete else 'PASSED_DECLARED_CHECKS',
              'phases': evidence, 'live_execution_complete': not incomplete,
              'interpretation_status': 'READ_EVALUATION_AND_RESIDUAL_QUESTIONS',
              'legal_correctness_established': False, 'review_cost_saving_measured': False,
              'release_eligible': False, 'completed': now(), 'allowance': audit()}
    write(OUT/'final-report.json', result); return result


def main():
    parser = ArgumentParser(__doc__)
    parser.add_argument('command', choices=('audit', 'status', 'refresh', 'execute', 'repair', 'recover'))
    parser.add_argument('phase', choices=PHASES, nargs='?')
    parser.add_argument('--note')
    args = parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        s = state()
        if args.command == 'audit': print(json.dumps(audit())); return
        if args.command == 'status': print(json.dumps(s, indent=2)); return
        invalidate(s)
        if args.command == 'refresh': refresh(args.phase or PHASES[0], s)
        elif args.command == 'repair': repair(args.phase, args.note, s)
        elif args.command == 'recover': recover(args.phase, s)
        else:
            audit()
            for phase in PHASES:
                if s['phases'][phase]['status'] not in ('PASSED', LIVE_INCOMPLETE): execute_phase(phase, s)
            print(json.dumps(finalize(s)))


if __name__ == '__main__': main()
