"""Bounded original reference admission and final-consumer integrity trial."""
from copy import deepcopy
from datetime import datetime, timezone
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from scripts.prospectus_payment_references import retained as baseline
from scripts.prospectus_reference_integrity_preparation import PREP, SPEC
from scripts.prospectus_reference_integrity_oracle import MISSING
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE = AUTH / 'attempts/basf-references/attempt-015'
PLAN = 'docs/plans/prospectus-reference-consumer-integrity-2026-10-18.md'
TESTS = ['tests/prospectus_successor/' + n for n in ('test_reference_consumer_integrity.py',
    'test_basf_call_references.py', 'test_basf_payment_references.py',
    'test_closure_reference_replacement.py', 'test_closure_references.py')]
STAGES = ('tests', 'candidate-p3', 'candidate-answer', 'missing-p3', 'missing-answer',
    'upstream-controls', 'consumer-change', 'consumer-drop', 'consumer-invent',
    'consumer-duplicate', 'consumer-uncertainty', 'consumer-target', 'validate', 'seal')


def costs():
    seconds = read(PREP/'preparation-failure.json')['wall_seconds']
    seconds += read(PREP/'preparation-v2/preparation-result.json')['wall_seconds']
    seconds += read(PREP/'oracle-preflight.json')['wall_seconds']
    seconds += sum(float(s.attrib['time']) for f in PREP.glob('preflight*tests.xml')
                   for s in ET.parse(f).getroot().iter('testsuite'))
    seconds += sum(read(f)['wall_seconds'] for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                   for f in HERE.glob(pattern))
    size = sum(f.stat().st_size for folder in (PREP, HERE) if folder.exists()
               for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    extra = [ROOT/PLAN, SPEC, Path(__file__), AUTH/'program.json', AUTH/'revisions/0274.json',
        ROOT/'scripts/prospectus_reference_integrity_preparation.py',
        ROOT/'scripts/prospectus_reference_integrity_oracle.py',
        ROOT/'src/legalmath/prospectus/successor/basf_legacy_references.py', *(ROOT/t for t in TESTS)]
    size += sum(f.stat().st_size for f in extra if f.exists())
    if seconds >= 1200 or size >= 188*1024**2:
        raise ValueError('Reference integrity cumulative resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size, 'new_seconds_bound': 1200,
        'new_bytes_bound': 192*1024**2, 'reserve_bytes': 4*1024**2,
        'unmeasured_authoring_controller_time': 'UNKNOWN', 'prior_admissions_retained': 14}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH/'program.json')
    assert program['revision'] == 273
    inputs = {relative(f):sha(f) for f in sorted(PREP.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
    for s in read(PREP/'source-review.json')['sources']:
        inputs[s['path']] = s['sha256']
    for folder, names in ((DONOR, ('outputs.json','installed-construct/products.json.gz',
            'installed-interpret/semantic.json.gz','installed-complete/downstream-products.json.gz',
            'installed-answer/ordinary-answer.json.gz')),
        (AUTH/'attempts/basf-references/attempt-014', ('outputs.json','candidate-answer.json.gz','result.json')),
        (AUTH/'attempts/basf-references/attempt-001', ('outputs.json','reference-ledger.json'))):
        manifest = read(folder/'outputs.json')
        for name in names:
            f = folder/name
            if name != 'outputs.json': assert sha(f) == manifest[name]
            inputs[relative(f)] = sha(f)
    for f, checksum in inputs.items(): assert sha(ROOT/f) == checksum
    methods = {relative(f):sha(f) for f in sorted((ROOT/'src/legalmath/prospectus').rglob('*'))
               if f.suffix in ('.py','.json')}
    for name in (*CODE, PLAN, relative(Path(__file__)), 'scripts/prospectus_reference_integrity_preparation.py',
        'scripts/prospectus_reference_integrity_oracle.py','scripts/prospectus_payment_references.py',
        'scripts/prospectus_payment_reference_preparation.py','scripts/prospectus_relative_notices.py',
        'scripts/prospectus_margin_preparation.py','scripts/prospectus_typed_delta.py',*TESTS):
        methods[name] = sha(ROOT/name)
    save(PREP/'freeze.json', {'methods': methods, 'inputs': inputs})
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==14
    proposal = deepcopy(program)
    proposal['revision'] = 274
    task = next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN, timeout_seconds=180, build_criteria_scope=[],
        reason='Actual P3 and final consumer accept altered old reference targets; enforce original20mappings and every supplied reviewed dependency',
        reference_integrity_review={'version':'basf-legacy-references.v1','review':relative(PREP),
            'original_task_complete':False,'bounds':{'stage_seconds':180,'new_seconds':1200,'new_bytes':192*1024**2},
            'further_harness_retry_allowed':False}, pre_admission_review=relative(PREP/'PRE-ADMISSION-REVIEW.md'))
    task['inputs'] = list(dict.fromkeys(task['inputs']+list(methods)+list(inputs)+[relative(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=15
    routes = read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision']=274
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(dossier=PLAN,task_sha256=authority_digest(task),
                remaining='014 RECORD1823 adds three selected payment links and lossless original60record reconciliation. Older20links have a reproduced live-consumer enforcement gap.',
                next_action='Enforce original20source targets and recompute all supplied dependencies at the ordinary consumer; then continue unresolved source mappings.',
                acceptance='Original-source oracle and whole-answer equality, matched three undiscovered-link omission, actual upstream and resealed consumer refusals; partial evidence only.',
                stop_condition='Fifteen cumulative admissions;180s stages;1200s measured including failed preparation;192MiB/4MiB reserve;no unchanged/harness retry.')
        if row['task']=='basf-margins':
            row['remaining']='Historical006 ACCEPT1817 retained; shared references changed after acceptance, so current-build revalidation remains phase5.'
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=relative(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        relative(PREP/'routes.json'):sha(PREP/'routes.json'),relative(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':authority_digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'original_obligations_preserved':True,
        'changes':['Original20source links enforced during P3','Every supplied reviewed dependency recomputed by final consumer',
                   'Missing original links visible','All prior attempts and failures preserved'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'reproduced':relative(PREP/'preparation-v2/preparation-result.json'),
            'corrected_source_shape':True,'distinct_same_line_citations_preserved':True,
            'omission_scope':'Three older undiscovered relative links only','whole_task_acceptance_claimed':False},
        'evidence_contract':{'primary':'Original-ledger reconstruction and actual complete consumer behavior',
            'veto':['Wrong target','Hidden uncertainty','Resealed forgery accepted','Unrelated change','Drift','Resource/harness failure'],
            'not_concluded':['Whole graph','Unreviewed legal interpretation','Discovery recall','Actual compliance','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':14,'new_maximum':15,
            'retained_attempts':attempts,'reason':'Reproduced old-reference actual consumer integration failure',
            'next_discriminating_check':'Preserve complete original answers and refuse resealed changes independently of hashes',
            'stop_condition':'180s stages;1200s new measured;192MiB;no unchanged/harness retry',
            'same_scope_authorization':'User requests general build completion without external-opinion prerequisite'}}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':274,'prior_admissions':14,'resources':costs()}


def frozen():
    record=read(PREP/'freeze.json')
    for name,checksum in {**record['inputs'],**record['methods']}.items():
        if sha(ROOT/name)!=checksum: raise ValueError('Frozen reference integrity method/input changed: '+name)
    for name,checksum in read(HERE/'admission.json')['binding'].items():
        if sha(ROOT/name)!=checksum: raise ValueError('Admitted reference integrity binding changed: '+name)


def retain(label,p,a=None):
    from scripts.prospectus_typed_delta import changes,apply,equal
    original=products()
    delta=changes(original,p)
    equal(apply(original,delta),p,'Lossy products')
    out={'products_delta':delta,'products_sha256':digest(p)}
    if a is not None:
        old=read(DONOR/'installed-answer/ordinary-answer.json.gz')
        delta=changes(old,a)
        equal(apply(old,delta),a,'Lossy answer')
        out.update(answer_delta=delta,answer_sha256=digest(a))
    save(HERE/(label+'.json.gz'),out)


def retained(label):
    from scripts.prospectus_typed_delta import apply
    row=read(HERE/(label+'.json.gz'))
    p=apply(products(),row['products_delta'])
    assert digest(p)==row['products_sha256']
    a=None
    if 'answer_delta' in row:
        a=apply(read(DONOR/'installed-answer/ordinary-answer.json.gz'),row['answer_delta'])
        assert digest(a)==row['answer_sha256']
    return p,a


def interpretation(label):
    from scripts.prospectus_reference_integrity_oracle import verify
    p,_=baseline('candidate-answer')
    value=deepcopy(p['P3']['payload']['interpretation_input'])
    missing=MISSING if label.startswith('missing') else ()
    value['reference_admission']['references']=[r for r in value['reference_admission']['references'] if r['id'] not in missing]
    p['P3']=service.interpretation_product(p['P1'],p['P2'],value)
    result=verify(p,missing=missing)
    retain(label,p)
    return result


def answer(label):
    from scripts.prospectus_reference_integrity_oracle import verify
    p,_=retained(label.replace('-answer','-p3'))
    missing=MISSING if label.startswith('missing') else ()
    old4,old5=p['P4']['payload'],p['P5']['payload']
    p['P4']=service.law_product(p['P1'],p['P3'],old4['cases'],old4['law_input'])
    p['P5']=service.financial_product(p['P1'],p['P2'],p['P3'],old5['cases'],old5['scenario_input'])
    actual=service.consume(p,ROOT,mode='frozen')
    result=verify(p,actual,missing=missing)
    retain(label,p,actual)
    return result


def tests():
    import pytest
    with (HERE/'tests.log').open('x') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        code=pytest.main(['-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')])
    if code: raise ValueError('Reference integrity tests failed')
    return {'status':'PASS'}


def upstream_controls():
    p,_=baseline('candidate-answer')
    done=[]
    for index,row in enumerate(p['P3']['payload']['interpretation_input']['reference_admission']['references'][:20]):
        began=time.monotonic()
        value=deepcopy(p['P3']['payload']['interpretation_input'])
        value['reference_admission']['references'][index]['targets']=row['targets'][:1]
        try: service.interpretation_product(p['P1'],p['P2'],value)
        except ValueError as exc:
            if 'original complete reviewed target' not in str(exc): raise
            save(HERE/'controls'/(row['id']+'.json'),{'status':'PASS','case':row['id'],'refusal':str(exc),
                'wall_seconds':time.monotonic()-began})
            done.append(row['id'])
        else: raise ValueError('Truncated original reference accepted: '+row['id'])
    return {'status':'PASS','actual_P3_refusals':done}


def consumer(label):
    p,_=retained('missing-answer' if label=='consumer-uncertainty' else 'candidate-answer')
    semantic=deepcopy(p['P3']['payload'])
    identity='reviewed-reference:prose-notice-118-34'
    dep=next(d for d in semantic['dependencies'] if d['id']==identity)
    required='Consumed reviewed-reference dependencies differ'
    if label=='consumer-change': dep['targets']=dep['targets'][:1]
    elif label=='consumer-drop': semantic['dependencies'].remove(dep)
    elif label=='consumer-invent': semantic['dependencies'].append({**deepcopy(dep),'id':'reviewed-reference:invented'})
    elif label=='consumer-duplicate': semantic['dependencies'].append(deepcopy(dep))
    elif label=='consumer-uncertainty':
        semantic['questions']['Q2']['subquestions'][next(iter(semantic['questions']['Q2']['subquestions']))]['unresolved'].remove('legacy-reference:'+MISSING[0])
        required='hides or invents'
    else:
        row=next(r for r in semantic['interpretation_input']['reference_admission']['references'] if r['id']=='prose-notice-118-34')
        row['targets']=row['targets'][:1]
        required='original complete reviewed target'
    bundle=p['P1']['payload']['request']['bundle']
    p['P3']=service.seal('P3',bundle,p['P3']['inputs'],semantic)
    for stage in ('P4','P5'):
        p[stage]=service.seal(stage,bundle,{**p[stage]['inputs'],'P3':p['P3']['sha256']},p[stage]['payload'])
    try: service.consume(p,ROOT,mode='frozen')
    except ValueError as exc:
        if required not in str(exc): raise
        return {'status':'PASS','case':label,'actual_consumer_refusal':str(exc)}
    raise ValueError('Forged ordinary consumer accepted: '+label)


def validate():
    from scripts.prospectus_reference_integrity_oracle import verify
    checks=[]
    for label,missing in (('candidate-answer',()),('missing-answer',MISSING)):
        p,a=retained(label)
        checks.append(verify(p,a,missing=missing))
    return {'status':'PASS','independent_cases':checks,'whole_task_complete':False}


def seal():
    resources=costs()
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'actual_ordinary_answers':2,'actual_upstream_refusals':20,'actual_consumer_refusals':6,
        'original_mappings_checked':20,'resources':resources,
        'remaining':['Other original source targets','Statutory originals and editions','Self/cyclic scope',
            'Unqualified defined terms','Original complete reference acceptance'],
        'next_action':'Continue source mappings from014lossless inventory; preserve all25current reviewed links and the new generic final-consumer checks'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'commands':['.venv/bin/python -m scripts.prospectus_reference_integrity '+s for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU deliberately hidden',
        'data_version':sha(PREP/'source-review.json'),'seeds':'N/A deterministic',
        'wall_time':resources,'plan':PLAN,'result':relative(HERE/'result.json'),'artifacts':relative(HERE),
        'method_freeze':sha(PREP/'freeze.json'),'prior_admissions':read(PREP/'review.json')['budget_revision']['retained_attempts']})
    (HERE/'RESULT.md').write_text('''# Original reference consumer integrity

The pre-edit actual P3 accepted a shortened notice target and the actual final
consumer accepted a changed old dependency after its hashes were resealed.
Preparation-time source checks had not reached those live routes. The repair
enforces all20retained original source mappings and reconstructs every supplied
reviewed dependency at the final consumer, including on non-BASF inputs.

The complete current candidate and matched omission of three older undiscovered
relative links passed independent full-answer comparisons. The original ledger
independently reconstructs all20old dependencies. Twenty actual P3 truncations
and six individually receipted resealed consumer controls are refused. Existing
meanings, financial/legal payloads and other answer fields remain unchanged.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain consumer-integrity repair | Original-source and complete answer checks pass | Altered, missing, invented and duplicate dependencies refused; hidden uncertainty refused | Other original targets, sources and interpretations remain open | Continue original source remainder | Complete reference graph, legal completeness, discovery recall, actual compliance or whole build |

This is a local integration failure; no third-party package failure is shown.
The strongest alternative explanation is an incorrect original development
reading. Original source intervals and retained full records make that reading
reviewable, but this trial proves enforcement rather than every legal reading.
Generic occurrence replay alone does not validate an unreviewed target.

Historical failed preparation and preflight tests remain included in resource
accounting. Original14admissions are retained. Shared-code historical acceptances
require final current-build revalidation. No unchanged or harness retry follows.
''')
    return {'status':'PASS','original_task_complete':False,'resources':resources}


def main():
    label=sys.argv[1]
    if label=='propose':
        print(json.dumps(propose()))
        return
    if label not in STAGES: raise ValueError('Unknown reference integrity stage')
    frozen()
    i=STAGES.index(label)
    if i: assert read(HERE/'stages'/STAGES[i-1]/'result.json')['status']=='PASS'
    costs()
    began=time.monotonic()
    folder=HERE/'stages'/label
    save(folder/'started.json',{'command':sys.argv,'stage_seconds':180,'started_at':datetime.now(timezone.utc).isoformat()})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Reference integrity stage180s')))
    signal.alarm(180)
    try:
        if label.endswith('-p3'): result=interpretation(label)
        elif label.endswith('-answer'): result=answer(label)
        elif label.startswith('consumer-'): result=consumer(label)
        else: result=globals()[label.replace('-','_')]()
        frozen()
        assert result['status']=='PASS'
        result['wall_seconds']=time.monotonic()-began
        save(folder/'result.json',result)
        if label=='seal':
            save(HERE/'outputs.json',{str(f.relative_to(HERE)):sha(f) for f in sorted(HERE.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-began})
        raise
    finally: signal.alarm(0)


if __name__=='__main__':
    main()
