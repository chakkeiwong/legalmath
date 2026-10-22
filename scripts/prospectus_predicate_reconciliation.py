"""Current source-bound predicates versus retained finite evidence."""
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
import os, signal, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from scripts import prospectus_conditional_rebind as previous
from legalmath.prospectus.execution_authority import Authority, CODE, digest as adigest
from legalmath.prospectus.successor import clause_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.predicates import names
read, save, sha, rel = previous.read, previous.save, previous.sha, previous.rel
AUTH = previous.AUTH
PREP = AUTH/'reviews/predicate-reconciliation-297'
HERE = AUTH/'attempts/basf-references/attempt-038'
OLD = AUTH/'attempts/basf-meanings'
PLAN = 'docs/plans/prospectus-predicate-evidence-reconciliation-2026-10-19.md'
METHOD = 'scripts/prospectus_predicate_reconciliation.py'
STAGES = ('reconcile', 'evaluate', 'seal')

def costs(extra=0):
    start=read(PREP/'accounting-start.json')
    seconds=start['prior']['cumulative026_037_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file()}
    paths.update(ROOT/n for n in (PLAN,METHOD))
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH/'revisions/0297.json')
    size=start['prior']['cumulative026_037_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    assert seconds<5400 and size<508*1024**2,'Cumulative026 bound exhausted'
    return {'cumulative026_038_measured_seconds':seconds,'cumulative026_038_bytes':size,
        'prior_costs_reset':False,'manual_controller_seconds':'UNKNOWN',
        'prior_unmeasured_preparation':start['prior']['prior_unmeasured_preparation'],
        'seconds_bound':5400,'bytes_bound_including_4MiB_reserve':512*1024**2}

def prepare():
    program=read(AUTH/'program.json');assert program['revision']==296
    events=Authority(ROOT).events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==37 and any(e['kind']=='RECORD' and e.get('attempt')==rel(previous.HERE) for e in events)
    save(PREP/'accounting-start.json',{'prior':previous.costs(),'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    for name,value in read(previous.HERE/'outputs.json').items():assert sha(previous.HERE/name)==value,name
    bindings={n:sha(ROOT/n) for n in (*CODE,PLAN,METHOD,'scripts/prospectus_conditional_rebind.py',
        'scripts/prospectus_structural_integration.py','scripts/prospectus_structural_oracle.py','scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'})
    old_files={}
    for num in (2,3,4,5,6):
        directory=OLD/('attempt-'+str(num).zfill(3));manifest=read(directory/'outputs.json')
        bindings[rel(directory/'outputs.json')]=sha(directory/'outputs.json')
        keep=[n for n in manifest if '/' not in n and (n.endswith('.py') or n.endswith('answer.json.gz') or 'comparison' in n or n in ('SOURCE-REVIEW.md',
            'RESULT.md','result.json','controls.json','logic-controls.json.gz','source-readings.json','open-clauses.json.gz'))]
        for name in keep:
            assert sha(directory/name)==manifest[name],rel(directory/name)
            bindings[rel(directory/name)]=manifest[name]
        old_files[str(num)]=keep
    for p in (previous.HERE/'outputs.json',previous.HERE/'answer-delta.json.gz',
              previous.HERE/'open-condition-source-packet.json.gz',previous.BASE/'answer.json.gz',
              previous.prior.BASE/'complete-products.json.gz',previous.prior.BASE/'complete-expected-answer.json.gz'):
        bindings[rel(p)]=sha(p)
    save(PREP/'old-evidence.json',old_files)
    (PREP/'METHOD-REVIEW.md').write_text('''# Corrected predicate continuation audit

PASS for bounded reconciliation and current finite evaluation. Verify all twelve
complete036 source predicates against retained006. The former next plan mistook
open facts for absent implementations. Exact node/source equality and separately
transcribed formulas are primary; counts are explanatory. Current037 complete
and installed replay is separate evidence, not a new consumer scenario. Generic
ratio/calendar helpers do not establish source-specific clause integration.
No external adviser, client facts, network or installation is needed. Preserve
all unknowns and003 failure. Source corruption, unexplained drift or exhausted
existing limits veto execution. Historical statutory application remains next.
''')
    bindings.update({rel(PREP/n):sha(PREP/n) for n in ('METHOD-REVIEW.md','old-evidence.json')})
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=297
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Reconcile existing predicate evidence; distinguish open facts from missing arithmetic and historical statutory application',
        predicate_reconciliation={'review':rel(PREP),'original_task_complete':False,'production_changes':False,
            'cumulative026_seconds':5400,'cumulative026_bytes_with_reserve':512*1024**2})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=38
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=297
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Reconcile conditional predicates then historical section11 statutory applications',
            stop_condition='38 admissions;90s stages;5400s cumulative026;512MiB including4MiB reserve;no unchanged retry')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    resource=costs();forecast={'seconds':resource['cumulative026_038_measured_seconds']+120,
        'bytes':resource['cumulative026_038_bytes']+3*(AUTH/'program.json').stat().st_size+4*1024**2,'estimate_only':True}
    assert forecast['seconds']<5400 and forecast['bytes']<508*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Correct next-work baseline using retained predicate evidence','Admission37 to38; cumulative ceilings unchanged'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Current source/node equality and independent complete Boolean worlds with unknown/conflict controls',
            'promotion_veto':['Source drift','Wrong outcomes','Lost uncertainty','Unsupported integration claim'],
            'continuation_veto':['Corrupt evidence','Frozen-method drift','Exhausted limits'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Actual events','Exhaustive legal interpretation','Whole task completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':37,'new_maximum':38,'retained_attempts':attempts,
            'reason':'Correct duplicate-work premise and identify actual gaps','next_discriminating_check':'Current predicates versus retained source formulas',
            'stop_condition':'90s stages;120s additional forecast;5400s cumulative026;512MiB with4MiB reserve',
            'same_scope_authorization':'User requested refreshed master and continued internally supported general build'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':297,'forecast':forecast}

def frozen():
    admission=read(HERE/'admission.json')
    assert adigest(read(AUTH/'program.json'))==admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec'])==admission['binding']
    for name,value in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/name)==value,name

def expected(identifier,f):
    # Direct source formulas, independently of the expression tree.
    key=identifier.split(':')[1]
    if identifier.startswith('basf-default:'):
        if key=='a':event=f['default.a.payment30']
        elif key=='b':event=f['default.b.other30']
        elif key=='c':event=f['default.c.accelerated'] or (f['default.c.overdue'] and not f['default.c.disputed']) or f['default.c.security']
        elif key=='d':event=f['default.d.announced'] or f['default.d.suspended']
        elif key=='e':event=f['default.e.court_opened'] or f['default.e.proceeding60'] or f['default.e.issuer_applied']
        elif key=='g':event=f['default.g.liquidation'] and not(f['default.g.reorganization'] and f['default.g.assumption_all'])
        else:raise ValueError(identifier)
        return bool(f['default.notice'] and event and not f['default.'+key+'.cured']
            and (key not in ('b','c') or f['default.quorum'] or f['default.other_at_receipt'])
            and (not f['representative.'+key+'.entrusted'] or f['representative.'+key+'.express_permission']))
    if key=='maturity':return f['maturity.due'] and not f['maturity.already_discharged']
    if key=='tax':return all(f['tax.'+k] for k in ('election','whole_series','notice_30_60','qualifying_change','next_coupon','unavoidable','within_90','continues','notice_form'))
    if key=='control_put':
        return (all(f['control_put.'+k] for k in ('control','rating','event_notice','timely_exercise','valid_declaration','delivery','payment_day'))
            and not f['control_put.earlier_tax_notice'] and (not f['representative.put.entrusted'] or f['representative.put.express_permission']))
    if key=='early_call':return f['early_call.election'] and f['early_call.notice'] and (not f['early_call.partial'] or f['early_call.selection'])
    if key=='par_call':return f['par_call.election'] and f['par_call.window'] and f['par_call.notice'] and (not f['par_call.partial'] or f['par_call.selection'])
    if key=='minimum_call':return all(f['minimum_call.'+k] for k in ('election','acquired_75','global_reduced','whole_remaining','notice'))
    raise ValueError(identifier)

def reconcile():
    products,ordinary=previous.prior.retained('answer')
    packet=read(previous.HERE/'open-condition-source-packet.json.gz')
    current={n['id']:n for n in products['P3']['payload']['clauses']['nodes']}
    old={n['id']:n for n in read(OLD/'attempt-006/open-clauses.json.gz')['nodes']}
    rows=[]
    for row in packet['clauses']:
        node=row['node'];identifier=node['id']
        assert node==current[identifier]==old[identifier],identifier
        domain=sorted(node['scenario_premises'])
        assert set(domain)==names(clause_graph.activation_expression(node,{})) and len(domain)<=12
        key=identifier.split(':')[1]
        prior_cases=['005','006'] if identifier.startswith('basf-default:') else (['003','004'] if key in ('early_call','minimum_call') else ['002'])
        if key=='control_put':prior_cases.append('006')
        rows.append({'id':identifier,'node_sha256':digest(node),'node':node,'sources':row['sources'],
            'prior_attempts':prior_cases,'complete_node_equal':True,'domain':domain,
            'missing_facts':domain,'quantitative_derivation':'NOT_ESTABLISHED_BY_PREDICATE_TESTS','actual_activation':False})
    assert len(rows)==12
    save(HERE/'reconciliation.json.gz',{'rows':rows,'products_sha256':digest(products),'ordinary_sha256':digest(ordinary),'all_complete_nodes_equal':True})
    return {'status':'PASS','complete_node_equal':12,'new_meanings':0}

def evaluate():
    rows=read(HERE/'reconciliation.json.gz')['rows']
    outputs=[];totals={'worlds':0,'withheld':0,'conflicts':0,'omissions':0}
    for row in rows:
        identifier,node,domain=row['id'],row['node'],row['domain']
        worlds=[];favorable=None
        for values in product((False,True),repeat=len(domain)):
            facts=dict(zip(domain,values));want='YES' if expected(identifier,facts) else 'NO'
            got=clause_graph.active(node,{},facts)['status'];assert got==want,(identifier,facts,want,got)
            worlds.append({'facts':facts,'expected':want,'actual':got})
            if want=='YES' and favorable is None:favorable=facts
        assert favorable is not None and clause_graph.active(node,{}, {})['status']=='UNKNOWN'
        missing=[];conflicts=[]
        for name in domain:
            facts={k:v for k,v in favorable.items() if k!=name}
            outcomes={expected(identifier,{**facts,name:v}) for v in (False,True)}
            want='UNKNOWN' if len(outcomes)==2 else ('YES' if True in outcomes else 'NO')
            got=clause_graph.active(node,{},facts)['status'];assert want==got
            missing.append({'withheld':name,'expected':want,'actual':got})
            got=clause_graph.active(node,{}, {**favorable,name:'conflict'})['status'];assert got=='CONFLICT'
            conflicts.append({'fact':name,'actual':got})
        omissions=[]
        for name in domain:
            witness=next(w for w in worlds if expected(identifier,{**w['facts'],name:not w['facts'][name]})!=(w['expected']=='YES'))
            bad=deepcopy(node)
            def replace(expr):
                if expr==name:return not witness['facts'][name]
                if isinstance(expr,dict):return {k:([replace(a) for a in v] if isinstance(v,list) else replace(v)) for k,v in expr.items()}
                return expr
            for field in ('conditions','exceptions'):bad[field]=replace(bad[field])
            got=clause_graph.active(bad,{},witness['facts'])['status'];assert got!=witness['expected']
            omissions.append({'premise':name,'facts':witness['facts'],'source_required':witness['expected'],'mutated_actual':got})
        outputs.append({'id':identifier,'worlds':worlds,'withheld':missing,'conflicts':conflicts,'omissions':omissions})
        for key,values in (('worlds',worlds),('withheld',missing),('conflicts',conflicts),('omissions',omissions)):totals[key]+=len(values)
    save(HERE/'finite-controls.json.gz',{'clauses':outputs,'totals':totals,'declared_boolean_premises_only':True})
    return {'status':'PASS',**totals,'new_legal_meanings':0}

def seal():
    totals=read(HERE/'finite-controls.json.gz')['totals']
    gaps={'implemented':'All12 source-bound conditional activation expressions;per-right representative restriction on7 routes',
        'current_compatibility':'Complete current nodes equal retained006;current evaluator matches independent formulas',
        'open_facts':'Events,notice,cure,eligible amounts,mandate and causation remain unknown by design',
        'quantitative_gaps':'These nodes consume Boolean observations;ratio/calendar calculations are in separate law_facts path,not adapters for these contract premises',
        'generic_helpers':'ratio_facts provides GT/GE ratios;calendar_facts provides GE/LE under an explicit convention',
        'not_established':['Strict30-day source adapter','EUR200m amount/FX qualification','Frankfurt17:00 cutoff and45-day rule',
            'Causal rating rule','Historical statutory application','Actual events'],
        'next_action':'Historical SchVG section11 conditional applications and edition evidence;retain numeric/time adapters as subsequent work',
        'external_adviser_required':False,'client_facts_required_for_conditional_analysis':False}
    save(HERE/'gap-map.json',gaps)
    result={'status':'PASS','task':'basf-references','original_task_complete':False,
        'result_kind':'CURRENT_PREDICATE_EVIDENCE_RECONCILIATION','equal_complete_predicate_nodes':12,
        'finite_controls':totals,'production_changes':False,'prior_failures_preserved':True,
        'resources':costs(),'next_action':gaps['next_action']}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU; GPU intentionally hidden',
        'data_version':sha(previous.BASE/'answer.json.gz'),'random_seeds':'N/A deterministic',
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Existing conditional meanings verified on current data

All twelve complete current predicate nodes equal retained006. The current
finite evaluator matches separately transcribed source formulas over every
declared Boolean world, with explicit withheld-premise, conflict and omission
controls. Historical actual-consumer evidence applies to those identical
source-bound readings; the earlier003 timeout remains retained.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain conditional implementation | Exact node/source equality and independent finite outcomes | No mismatch or lost uncertainty | Legal completeness and event/quantity derivation | Historical statutory application,then source-specific arithmetic | Actual events,exhaustive law or finished build |

The mistaken next-work assumption was ours: open factual predicates were treated
as absent implementations. Boolean tests do not close source-specific quantity
derivation or historical law. The strongest alternative explanation is an
omitted legal distinction. A source-supported counterexample overturns the
reading even if every Boolean test passes. Open facts establish no package defect.
''')
    return result

def main():
    import json
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_predicate_reconciliation',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':90})
    started=time.monotonic()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Reconciliation stage bound')));signal.alarm(90)
    try:
        if stage!='prepare':frozen()
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-started);result['wall_seconds']=time.monotonic()-started
        save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder/'failure.json',{'type':type(exc).__name__,'message':str(exc),'wall_seconds':time.monotonic()-started});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
