"""Review the narrow report attribution repair using actual old answers."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import sys
import time
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from legalmath.prospectus.successor import service
from scripts.prospectus_calendar_evidence import load, require

PLAN = 'docs/plans/prospectus-law-assistance-label-2026-10-17.md'
REVIEW = REL + '/reviews/law-mode-235'
PRIOR = REL + '/attempts/law-applicability/attempt-008'
ORIGINAL = REL + '/attempts/law-applicability/attempt-006'
NATIVE = REL + '/attempts/native-binding/attempt-017'
SERVICE = 'src/legalmath/prospectus/successor/service.py'
BOUNDS = {'preparation_seconds': 60, 'stage_seconds': 110, 'cumulative_seconds_with_008': 600,
          'new_bytes_with_008': 64 * 1024**2, 'reserve_bytes': 2 * 1024**2,
          'test_starts': 1, 'new_native_calls': 0}


def main():
    tick = time.monotonic()
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
          'command': ['.venv/bin/python', 'scripts/prospectus_law_mode_prepare.py']}, exclusive=True)
    signal.alarm(60)
    try:
        a = Authority(ROOT)
        old, tasks, _ = a.spec()
        require(old['revision'] == 234, 'Unexpected authority baseline')
        events = a.events()
        history = []
        for name in (PRIOR, ORIGINAL, NATIVE):
            e = next(e for e in reversed(events) if e.get('attempt') == name and e['kind'] in {'RECORD', 'ACCEPT', 'REJECT'})
            require(a.retained_evidence_valid(e), 'Retained evidence changed')
            history.append({'attempt': name, 'disposition': e['kind'], 'event': e['sha256'],
                            'outputs_sha256': file_hash(ROOT / name / 'outputs.json')})
        before = {str(p.relative_to(ROOT)): file_hash(p) for p in (ROOT / 'src/legalmath').rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        require(before == {k: v for k, v in read(ROOT / PRIOR / 'methods.json').items() if k.startswith('src/')},
                'Current calendar implementation changed')
        ps = load(ROOT / PRIOR / 'common-products.json.gz')
        record = load(ROOT / PRIOR / 'cases/boundary-no-registration.json.gz')
        current = service.consume({**ps, 'P4': record['P4']}, ROOT, mode='current')
        require(service.digest(current) == service.digest(record['answer'])
                and current['mode'] == 'AUTOMATIC_BOUNDED' and record['input']['law_bases']
                and record['input']['calendar_facts'], 'Attribution defect not reproduced')
        write(folder / 'before-methods.json', before, exclusive=True)
        with (folder / 'before-service.py').open('xb') as stream:
            stream.write((ROOT / SERVICE).read_bytes())
        write(folder / 'reproduction.json', {'status': 'REPRODUCED', 'observed': current['mode'],
              'expected': 'ASSISTED', 'complete_calendar_record_equal': True, 'history': history,
              'prior_seconds': read(ROOT / PRIOR / 'run-manifest.json')['cumulative_seconds'],
              'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
        admissions = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'law-applicability']
        require(len(admissions) == old['budgets']['law-applicability']['maximum_new_attempts'] == 8, 'Wrong cumulative admission count')
        new = deepcopy(old)
        new['revision'] = 235
        t = next(t for t in new['tasks'] if t['id'] == 'law-applicability')
        t.update(dossier=PLAN, reason='Correct automatic label for supplied P4 legal models without changing any legal or financial result',
                 law_mode_repair={'version': 'law-assistance-mode.v1', 'review': REVIEW,
                                  'production_change': SERVICE, 'bounds': BOUNDS})
        support = [PLAN, str(Path(__file__).relative_to(ROOT))]
        support += [str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()]
        t['inputs'] = sorted(set(t['inputs']) | set(support))
        new['budgets']['law-applicability']['maximum_new_attempts'] = 9
        routes = read(ROOT / old['continuation_review']['routes'])
        routes['baseline_revision'] = 235
        row = next(r for r in routes['tasks'] if r['task'] == 'law-applicability')
        row.update(task_sha256=digest(t), dossier=PLAN,
            remaining='008 recorded19 conditional date cases/68 independent comparisons/8 refusals and unchanged21 prior records; its post-run review reproduced misleading automatic label.',
            next_action='Execute admitted narrow mode repair; compare complete original and temporal answers, preserve questions/proofs, record and refresh.',
            stop_condition=BOUNDS)
        route = REL + '/closure-routes-2026-10-17-law-mode-235.json'
        write(ROOT / route, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=route)
        for n in [PLAN, route, str(Path(__file__).relative_to(ROOT))]:
            new['continuation_review']['bindings'][n] = file_hash(ROOT / n)
        audit = {'baseline': digest(old), 'changes': t['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
                 'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'reproduction': REVIEW + '/reproduction.json'},
                 'evidence_contract': PLAN,
                 'budget_revision': {'budget_key': 'law-applicability', 'previous_maximum': 8, 'new_maximum': 9,
                     'retained_attempts': admissions, 'reason': t['reason'],
                     'next_discriminating_check': 'Complete original answers change only corrected mode and derived digest; empty/overridden/legal-input routes classified consistently',
                     'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed reviewed general build and continuous repair; no new external action'}}
        a.validate_program(new)
        write(ROOT / REL / 'proposals/law-mode-235.json', new, exclusive=True)
        write(ROOT / REL / 'proposals/law-mode-235-review.json', audit, exclusive=True)
        write(folder / 'preparation-time.json', {'seconds': time.monotonic() - tick}, exclusive=True)
        print(json.dumps({'revision_prepared': 235, 'defect': 'supplied legal model labelled automatic',
                          'retained_admissions': 8, 'seconds': time.monotonic() - tick}))
    except BaseException as exc:
        write(folder / 'failure.json', {'error': type(exc).__name__ + ': ' + str(exc),
              'seconds': time.monotonic() - tick}, exclusive=True)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
