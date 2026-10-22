"""Prepare one bounded original-task continuation; never edit the authority."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from legalmath.prospectus.successor import service

PLAN = 'docs/plans/prospectus-calendar-premises-2026-10-17.md'
REVIEW = REL + '/reviews/calendar-premises-234'
OLD = REL + '/attempts/law-applicability/attempt-006'
ALLOWED = ['src/legalmath/prospectus/successor/' + n + '.py'
           for n in ('calendar_facts', 'law_facts', 'service', 'contracts')]
BOUNDS = {'preparation_seconds': 60, 'stage_seconds': 110,
          'cumulative_seconds': 600, 'new_bytes': 64 * 1024**2,
          'failure_reserve_bytes': 2 * 1024**2, 'test_starts': 1,
          'new_native_calls': 0, 'network': False, 'gpu': False}


def load(name):
    return json.loads(gzip.decompress((ROOT / name).read_bytes()))


def main():
    tick = time.monotonic()
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
          'command': ['.venv/bin/python', 'scripts/prospectus_calendar_prepare.py'],
          'plan': PLAN}, exclusive=True)
    signal.alarm(60)
    try:
        a = Authority(ROOT)
        old, tasks, _ = a.spec()
        assert old['revision'] == 233
        events = a.events()
        selected = []
        for name in (OLD, REL + '/attempts/law-applicability/attempt-007',
                     REL + '/attempts/source-authority/attempt-005'):
            e = next(e for e in reversed(events) if e.get('attempt') == name
                     and e['kind'] in {'RECORD', 'ACCEPT', 'REJECT'})
            assert a.retained_evidence_valid(e), name
            selected.append({'attempt': name, 'kind': e['kind'], 'event': e['sha256'],
                             'outputs_sha256': file_hash(ROOT / name / 'outputs.json')})
        for name, hashed in read(ROOT / OLD / 'source-bindings.json').items():
            assert file_hash(ROOT / name) == hashed, name
        products = load(OLD + '/common-products.json.gz')
        law = load(OLD + '/favorable-deposit-input.json.gz')
        cases = load(OLD + '/favorable-deposit-P4.json.gz')['payload']['cases']
        p4 = service.law_product(products['P1'], products['P3'], cases=cases, law_input=law)
        answer = service.consume({**products, 'P4': p4}, ROOT, mode='current')
        assert p4 == load(OLD + '/favorable-deposit-P4.json.gz')
        assert answer == load(OLD + '/favorable-deposit-answer.json.gz')
        try:
            service.law_product(products['P1'], products['P3'], cases=cases,
                                law_input={**law, 'calendar_facts': []})
        except ValueError as exc:
            assert str(exc) == 'Unexpected or missing fields'
            unsupported = str(exc)
        else:
            raise ValueError('Calendar input already supported; proposed gap not reproduced')
        before = {str(p.relative_to(ROOT)): file_hash(p)
                  for p in sorted((ROOT / 'src/legalmath').rglob('*'))
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        assert len(before) == 450
        write(folder / 'before-methods.json', before, exclusive=True)
        for name in ALLOWED[1:]:
            dest = folder / 'before' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                stream.write((ROOT / name).read_bytes())
        provenance = read(ROOT / OLD / 'source-provenance.json')
        write(folder / 'review.json', {
            'status': 'PASS', 'sources': read(ROOT / OLD / 'source-bindings.json'),
            'original_excerpt_sha256': file_hash(ROOT / OLD / 'selected-meeting-reading.txt'),
            'original_image_sha256': provenance['original_image_sha256'],
            'source_read': 'Original page130 image and exact four retained German excerpts',
            'baseline_complete_equal': True, 'baseline_q4': answer['questions']['Q4']['status'],
            'unsupported_calendar_input': unsupported, 'history': selected,
            'diagnosis': 'Explicit uncomputed timing premises; no external-package defect shown',
            'production_before': len(before), 'allowed_production_changes': ALLOWED,
            'known_preparation_seconds': time.monotonic() - tick,
            'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
        admissions = [e['attempt'] for e in events
                      if e['kind'] == 'ADMIT' and e.get('budget_key') == 'law-applicability']
        assert len(admissions) == old['budgets']['law-applicability']['maximum_new_attempts'] == 7
        new = deepcopy(old)
        new['revision'] = 234
        t = next(t for t in new['tasks'] if t['id'] == 'law-applicability')
        t.update(dossier=PLAN,
                 reason='Compute four original BASF timing premises from source-bound dates under explicit alternative conventions; preserve actual and historical uncertainty',
                 calendar_premises={'version': 'calendar-premises.v1', 'review': REVIEW,
                     'bounds': BOUNDS, 'allowed_production_changes': ALLOWED,
                     'whole_task_complete': False})
        support = [PLAN, str(Path(__file__).relative_to(ROOT))]
        support += [str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file()]
        t['inputs'] = sorted(set(t['inputs']) | set(support))
        new['budgets']['law-applicability']['maximum_new_attempts'] = 8
        routes = read(ROOT / old['continuation_review']['routes'])
        routes['baseline_revision'] = 234
        for row in routes['tasks']:
            if row['task'] == t['id']:
                row.update(phase=0, mode='local', dossier=PLAN, task_sha256=digest(t),
                    remaining=t['reason'],
                    next_action='Implement admitted dated calculations, verify actual source-bound consumers and old complete answers, seal/record/refresh; continue remaining substantive work.',
                    stop_condition=BOUNDS)
            elif row['task'] == 'source-authority':
                row.update(phase=5,
                    remaining='005 recorded current and isolated installed interval, conversion and document-date repairs:352 malformed refusals per environment with complete valid outputs preserved; source authenticity remains unresolved.',
                    next_action='Preserve completed005; continue distinct source-authority questions without repeating its input-validation matrix.')
            elif row['task'] in {'native-binding', 'native-confinement', 'recovery', 'authority-acceptance'}:
                row.update(phase=6,
                    remaining='Historical finite evidence retained; current acceptance is stale after substantive build changes.',
                    next_action='After substantive batch, review exact current production delta and validate original routes/states. Do not rerun annual-profile-only compatibility against later changes or re-pin historical execution.')
        route = REL + '/closure-routes-2026-10-17-calendar-234.json'
        write(ROOT / route, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=route)
        for name in [PLAN, route, str(Path(__file__).relative_to(ROOT))]:
            new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        audit = {'baseline': digest(old), 'changes': [
            'Continue conditional source-to-answer build with computed timing premises',
            'Record completed installed repairs and postpone final current native validation until substantive edits stabilize'],
            'scope_unchanged': True, 'budget_unchanged': False,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'evidence': REVIEW + '/review.json'},
            'evidence_contract': PLAN,
            'budget_revision': {'budget_key': 'law-applicability', 'previous_maximum': 7, 'new_maximum': 8,
                'retained_attempts': admissions, 'reason': t['reason'],
                'next_discriminating_check': 'Actual P4/final consumer distinguishes source-bound early/boundary/late dates, shifted reference day and alternative conventions; original complete answers preserved',
                'stop_condition': BOUNDS,
                'same_scope_authorization': 'User-directed general build before actual holdings, no external-adviser prerequisite, reviewed continuous execution'}}
        a.validate_program(new)
        write(ROOT / REL / 'proposals/calendar-234.json', new, exclusive=True)
        write(ROOT / REL / 'proposals/calendar-234-review.json', audit, exclusive=True)
        # This final clock is retained outside the admission inputs; no input is
        # changed after the proposal computes its frozen bindings.
        write(folder / 'preparation-time.json', {'seconds': time.monotonic() - tick}, exclusive=True)
        print(json.dumps({'revision_prepared': 234, 'baseline_complete_equal': True,
                          'gap': unsupported, 'production_files': len(before),
                          'retained_admissions': len(admissions), 'seconds': time.monotonic() - tick}))
    except BaseException as exc:
        write(folder / 'failure.json', {'error': type(exc).__name__ + ': ' + str(exc),
              'seconds': time.monotonic() - tick}, exclusive=True)
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
