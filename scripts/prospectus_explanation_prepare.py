"""Prepare the reviewed optional explanation repair; preserve old evidence."""
from copy import deepcopy
from pathlib import Path
import json
import os
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from legalmath.prospectus.successor import service
from scripts.prospectus_calendar_evidence import load, require

PLAN = 'docs/plans/prospectus-minimal-explanations-2026-10-17.md'
REVIEW = REL + '/reviews/minimal-explanations-236'
LITERATURE = '.localresources/prospectus-explanations-2019'
CHANGED = ['src/legalmath/prospectus/successor/' + n + '.py'
           for n in ('law_facts', 'service', 'contracts')]
ADDED = 'src/legalmath/prospectus/successor/explanations.py'
BOUNDS = {'preparation_seconds': 60, 'stage_seconds': 110, 'incremental_seconds': 600,
          'new_bytes': 64 * 1024**2, 'reserve_bytes': 2 * 1024**2,
          'test_starts': 1, 'native_calls': 0, 'gpu_calls': 0}


def main():
    start = time.monotonic()
    signal.alarm(60)
    a = Authority(ROOT)
    old, tasks, _ = a.spec()
    require(old['revision'] == 235, 'Wrong active baseline')
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'command': ['.venv/bin/python', 'scripts/prospectus_explanation_prepare.py']}, exclusive=True)
    events = a.events()
    checked = []
    for name in ('reasoning-corpus/attempt-007', 'law-applicability/attempt-006',
                 'law-applicability/attempt-008', 'law-applicability/attempt-009'):
        path = REL + '/attempts/' + name
        e = next(e for e in reversed(events) if e.get('attempt') == path and e['kind'] in {'RECORD','ACCEPT','REJECT'})
        require(a.retained_evidence_valid(e), 'Historical evidence changed')
        checked.append({'attempt': path, 'kind': e['kind'], 'outputs': file_hash(ROOT / path / 'outputs.json')})
    baseline = REL + '/attempts/law-applicability/attempt-008'
    ps = load(ROOT / baseline / 'common-products.json.gz')
    record = load(ROOT / baseline / 'cases/boundary-no-registration.json.gz')
    old_answer = load(ROOT / REL / 'attempts/law-applicability/attempt-009/calendar/boundary-no-registration.json.gz')
    p4 = service.law_product(ps['P1'], ps['P3'], law_input=record['input'])
    require(p4 == old_answer['P4'] and service.consume({**ps,'P4':p4},ROOT,mode='current') == old_answer['answer'],
            'Wrong complete-answer baseline')
    try:
        service.law_product(ps['P1'], ps['P3'], law_input={**record['input'], 'law_explanation':'subset-minimal.v1'})
    except ValueError as error:
        require(str(error) == 'Unexpected or missing fields', 'Unexpected reproduction error')
    else:
        raise ValueError('Proposed explanation gap not reproduced')
    before = {str(p.relative_to(ROOT)):file_hash(p) for p in (ROOT/'src/legalmath').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    require(len(before) == 451 and not (ROOT/ADDED).exists(), 'Unexpected production baseline')
    write(folder/'before-methods.json',before,exclusive=True)
    mapping = {}
    for name in CHANGED:
        dest = folder/'before'/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream: stream.write((ROOT/name).read_bytes())
        mapping[name] = {'snapshot':str(dest.relative_to(ROOT)), 'sha256':file_hash(dest)}
    write(folder/'input-snapshots.json',mapping,exclusive=True)
    write(folder/'review.json',{'verdict':'PASS','baseline_full_answer_equal':True,
        'gap':'Optional source-linked minimal explanation is unsupported', 'history':checked,
        'production_before':len(before), 'allowed_changed':CHANGED,'allowed_added':ADDED,
        'historical_unmeasured_seconds':'UNKNOWN','explanation_claim':'ONE_SUBSET_MINIMAL_NOT_MINIMUM_CARDINALITY'},exclusive=True)
    admissions = [e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='reasoning-corpus']
    require(len(admissions) == old['budgets']['reasoning-corpus']['maximum_new_attempts'] == 7,'Wrong cumulative admissions')
    new = deepcopy(old)
    new['revision'] = 236
    task = next(t for t in new['tasks'] if t['id']=='reasoning-corpus')
    require(all(n in task['inputs'] for n in CHANGED),'Snapshot mapping does not match task inputs')
    task['inputs'] = [mapping[n]['snapshot'] if n in mapping else n for n in task['inputs']]
    task.update(dossier=PLAN,reason='Add optional per-basis source-linked subset-minimal explanations through actual Q4/final consumers',
        explanation_repair={'version':'subset-minimal.v1','review':REVIEW,'bounds':BOUNDS,
            'allowed_changed':CHANGED,'allowed_added':ADDED,'whole_task_complete':False})
    support = [PLAN,str(Path(__file__).relative_to(ROOT))]
    support += [str(p.relative_to(ROOT)) for parent in (folder,ROOT/LITERATURE) for p in parent.rglob('*') if p.is_file()]
    task['inputs'] = sorted(set(task['inputs'])|set(support))
    new['budgets']['reasoning-corpus']['maximum_new_attempts']=8
    routes=read(ROOT/old['continuation_review']['routes'])
    routes['baseline_revision']=236
    for row in routes['tasks']:
        if row['task']=='reasoning-corpus':
            row.update(phase=0,mode='local',task_sha256=digest(task),dossier=PLAN,remaining=task['reason'],
                next_action='Implement admitted optional explanation, independently verify exact original consumers, retain result and refresh.',stop_condition=BOUNDS)
        elif row['task']=='law-applicability':
            row.update(phase=2,remaining='008 temporal arithmetic and009 assistance attribution recorded; broad legal scope remains incomplete.',
                next_action='Preserve sealed008/009; extend distinct conditional source-law questions without rerunning completed repairs.')
    route=REL+'/closure-routes-2026-10-17-explanations-236.json'
    write(ROOT/route,routes,exclusive=True)
    new['continuation_review'].update(plan=PLAN,routes=route)
    for name in (PLAN,route,str(Path(__file__).relative_to(ROOT))):
        new['continuation_review']['bindings'][name]=file_hash(ROOT/name)
    audit={'baseline':digest(old),'changes':task['reason'],'scope_unchanged':True,'budget_unchanged':False,
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'snapshot_mapping':REVIEW+'/input-snapshots.json'},
        'evidence_contract':PLAN,'budget_revision':{'budget_key':'reasoning-corpus',
            'previous_maximum':7,'new_maximum':8,'retained_attempts':admissions,'reason':task['reason'],
            'next_discriminating_check':'Independent sufficiency/minimality and actual source-bound Q4 consumers; complete legacy answers unchanged',
            'stop_condition':BOUNDS,'same_scope_authorization':'User-directed continuous general build, reviewed original reasoning obligations'}}
    a.validate_program(new)
    write(ROOT/REL/'proposals/explanations-236.json',new,exclusive=True)
    write(ROOT/REL/'proposals/explanations-236-review.json',audit,exclusive=True)
    write(folder/'preparation-time.json',{'seconds':time.monotonic()-start},exclusive=True)
    print(json.dumps({'prepared_revision':236,'retained_admissions':7,'seconds':time.monotonic()-start}))
    signal.alarm(0)


if __name__ == '__main__':
    main()
