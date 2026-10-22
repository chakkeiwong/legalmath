"""Prepare and review the bounded explicit-holder continuation; no live calls."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, digest as adigest
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/default-holder-362'
HERE = AUTH / 'attempts/basf-meanings/attempt-023'
PLAN = 'docs/plans/prospectus-default-holder-2026-10-20.md'
BASE = AUTH / 'attempts/basf-references/attempt-093'
FILES = (PLAN, 'scripts/prospectus_default_holder.py', 'scripts/prospectus_default_holder_run.py',
         'scripts/prospectus_default_holder_worker.py', 'tests/prospectus_successor/test_default_holder.py',
         'src/legalmath/prospectus/successor/default_holder.py',
         'src/legalmath/prospectus/successor/default_holder_verify.py',
         'src/legalmath/prospectus/successor/service.py',
         'src/legalmath/prospectus/successor/conditional_profiles.py')


def read(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def save(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    with p.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if p.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def cases():
    # Expected states are authored independently of the candidate formula/evaluator.
    events = dict.fromkeys(('cessation', 'disposal', 'value_cessation', 'risk_cessation',
                          'value_disposal', 'risk_disposal', 'value_joint', 'risk_joint'), True)
    common = {**events, 'holder': True, 'notice_form_delivery': True, 'cured': False}
    values = (False, True, None, 'conflict')
    table = (('YES', 'YES', 'YES', 'CONFLICT'), ('NO', 'YES', 'UNKNOWN', 'CONFLICT'),
             ('UNKNOWN', 'YES', 'UNKNOWN', 'CONFLICT'), ('CONFLICT',) * 4)
    rows, expected = [], {}
    def add(name, facts, statuses):
        rows.append({'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': facts})
        expected[name] = list(statuses)
    add('all-open', {}, ['UNKNOWN'] * 3)
    for i, entrusted in enumerate(values):
        for j, permission in enumerate(values):
            add('authority-' + str(i) + str(j), {**common, 'entrusted': entrusted,
                'express_permission': permission}, [table[i][j]] * 3)
    permitted = {**common, 'entrusted': True, 'express_permission': True}
    for key in ('holder', 'notice_form_delivery', 'cured'):
        for name, value, status in [('false-condition', key == 'cured', 'NO'),
                                    ('unknown', None, 'UNKNOWN'), ('conflict', 'conflict', 'CONFLICT')]:
            add(key + '-' + name, {**permitted, key: value}, [status] * 3)
    add('cessation-alone', {**permitted, **dict.fromkeys(events, False), 'cessation': True}, ['NO', 'NO', 'YES'])
    add('qualified-disposal', {**permitted, 'cessation': False}, ['NO', 'YES', 'YES'])
    add('no-conduct', {**permitted, 'cessation': False, 'disposal': False}, ['NO'] * 3)
    add('blocked-cessation-alone', {**permitted, **dict.fromkeys(events, False),
        'cessation': True, 'express_permission': False}, ['NO'] * 3)
    add('unknown-holder-blocked-authority', {**permitted, 'holder': None, 'express_permission': False}, ['NO'] * 3)
    return rows, expected


def prepare():
    started = time.monotonic()
    from legalmath.prospectus.successor import default_holder as model
    from legalmath.prospectus.successor.default_holder_verify import consequence, EVENT_NAMES
    old = read(PREP / 'reproduction.json')
    assert old['status'] == 'CAPABILITY_GAP_REPRODUCED' and not old['optional_argument_exists']
    for name, checksum in read(BASE / 'outputs.json').items():
        assert sha(BASE / name) == checksum, name
    manifest = read(ROOT / old['products'])['products']
    products = {k: read(ROOT / row['path']) for k, row in manifest.items()}
    for row in manifest.values():
        assert sha(ROOT / row['path']) == row['sha256']
    ordinary = read(BASE / 'ordinary-answer.json.gz')
    groups = model.source_groups(products)
    assert {k: v for k, v in groups.items() if k != 'representative'} == ordinary['default_f_review']['groups']
    sources = deepcopy(ordinary['default_f_review']['sources'])
    sources[0]['images'].append({'page': 130, 'path': old['source_image'], 'sha256': old['source_image_sha256']})
    for source in sources:
        for item in [source, *source['images']]:
            assert sha(ROOT / item['path']) == item['sha256']
    scenarios, expected = cases()
    for row in scenarios:
        assert [consequence(k, row['facts'])['status'] for k in EVENT_NAMES] == expected[row['id']]
    profile = {'version': model.VERSION, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'groups': groups, 'sources': sources,
        'premises': model.premises(), 'expressions': model.expressions(), 'scenarios': scenarios}
    save(PREP / 'profile.json', profile)
    save(PREP / 'expected.json', {'basis': 'Manually authored source-specific conditional expectations',
         'candidate_derived': False, 'statuses': expected})
    options = read(ROOT / old['profiles'])
    options['profiles'].append({'name': 'holder_authority', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', options)
    source_paths = [ROOT / old['products'], ROOT / old['profiles'], BASE / 'outputs.json',
                    BASE / 'ordinary-answer.json.gz']
    source_paths += [ROOT / r['path'] for r in manifest.values()]
    source_paths += [ROOT / r['path'] for r in options['profiles']]
    source_paths += [ROOT / item['path'] for s in sources for item in [s, *s['images']]]
    save(PREP / 'source-bindings.json', {rel(p): sha(p) for p in source_paths})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'role': 'PREPARATION_ONLY',
         'source_groups_equal': True, 'original_role_preserved': True, 'scenarios': len(scenarios),
         'original_image_inspected': old['source_image'], 'wall_seconds': time.monotonic() - started})
    return {'status': 'PASS', 'scenarios': len(scenarios), 'source_bound': True}


def proposal():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 361 and not HERE.exists()
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
    assert len(attempts) == 22
    bindings = {n: sha(ROOT / n) for n in FILES}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts})
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings.update(production)
    bindings.update(read(PREP / 'source-bindings.json'))
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production,
        'frozen_at': datetime.now(timezone.utc).isoformat()})
    candidate = deepcopy(program)
    candidate['revision'] = 362
    task = next(t for t in candidate['tasks'] if t['id'] == 'basf-meanings')
    task.update(dossier=PLAN, reason='Expose explicit individual-holder authority under existing unselected default(f) readings; preserve complete current answer',
        pre_admission_review=rel(PREP / 'METHOD-REVIEW.md'), timeout_seconds=380,
        holder_authority_continuation={'review': rel(PREP), 'original_task_complete': False,
            'prior_known015plus_seconds': 1520.0904145943932, 'prior_known015plus_bytes': 519849397,
            'cumulative_seconds': 2700, 'cumulative_bytes': 768 * 1024**2,
            'new_seconds': 1000, 'new_bytes': 128 * 1024**2, 'historical_unmeasured_time': 'UNKNOWN'},
        build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    candidate['budgets']['basf-meanings']['maximum_new_attempts'] = 23
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 362
    for row in routes['tasks']:
        if row['task'] == 'basf-meanings':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Complete explicit holder-authority trial then reconcile original source meanings; no external-opinion prerequisite',
                stop_condition='23 cumulative admissions;2700s/768MiB cumulative;1000s/128MiB increment;380s consumers;120s other children;no unchanged retry')
    save(PREP / 'routes.json', routes)
    candidate['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    candidate['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Same task exposes explicit authority rather than interpreting historical bundled eligibility',
                    'Retain all attempts; reviewed23rd admission and cumulative2700s/768MiB extension'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'METHOD-REVIEW.md'),
            'runtime_baseline': '093 293s per consumer;097 258–265s;380s child bounds',
            'historical_formula_declared_wrong': False, 'independent_expectations': True},
        'evidence_contract': {'primary': 'Complete093 preservation and separate source-bound authority consequences in ordinary and isolated installed CLI',
            'promotion_veto': ['Wrong consequence', 'Lost source or scope', 'Changed historical answer', 'Permissive tamper control'],
            'continuation_veto': ['Corrupt shared inputs', 'Invalid authority', 'Exhausted cumulative limit'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Exhaustive legal reading', 'Actual holder/default', 'Whole task/build completion']},
        'budget_revision': {'budget_key': 'basf-meanings', 'previous_maximum': 22, 'new_maximum': 23,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced explicit-authority capability; existing full-answer source evidence reused',
            'next_discriminating_check': 'Entrusted right blocks individual exercise unless expressly permitted; unknown/conflict remain',
            'stop_condition': '2700s/768MiB cumulative;1000s/128MiB incremental;one attempt;4MiB seal reserve',
            'same_scope_authorization': 'User requested master continuation and internally proved general build; no live calls or new external cost'}}
    save(PREP / 'proposal.json', candidate)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 362, 'attempt': 23, 'frozen_files': len(bindings)}


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('prepare', 'proposal'):
        raise SystemExit('Use prepare or proposal')
    print(json.dumps(globals()[sys.argv[1]]()))
