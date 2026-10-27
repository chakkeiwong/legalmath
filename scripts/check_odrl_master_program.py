"""Read-only validation of the proposed ODRL master. No task dispatch or network."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = Path('docs/implementation/odrl-master/program.json')
EXPECTED = {'S00','S01','N02','T03','E04','P05','F06','X07','V08','R08','C09',
            'C09C','Q10','D11','D12','Q13','G14','G15','G16','K17','A18','L19'}
TERMINAL = {'SUCCEEDED','FAILED','BLOCKED','SKIPPED'}
SUCCESS_DEPENDENCIES = {
    'S00': [], 'S01': ['S00'], 'N02': ['S01'], 'T03': ['S01'], 'E04': ['S00'],
    'P05': ['N02'], 'F06': ['N02','T03','E04','P05'],
    'X07': ['N02','P05','E04','T03'],
    'V08': ['X07','F06','T03','E04'], 'R08': ['X07','F06','T03','E04'],
    'C09': ['F06','T03'], 'C09C': ['C09','E04'],
    'Q10': ['X07','F06','T03','C09'], 'D11': ['N02','T03'],
    'D12': ['D11','F06','X07'], 'Q13': ['D12','Q10','T03'],
    'G14': ['Q10','D11','T03'], 'G15': ['G14','X07'],
    'G16': ['G15','Q13','G14'], 'K17': ['Q10','Q13','G15'],
    'A18': ['K17'], 'L19': [],
}


def safe_file(root: Path, name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('Unsafe relative path: ' + name)
    if any(x in {'.git','.aws','.ssh','.codex','.agents'} for x in p.parts):
        raise ValueError('Protected path: ' + name)
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('Path escapes root: ' + name)
    if not resolved.is_file():
        raise ValueError('Missing bound file: ' + name)
    return resolved


def validate(program: dict, root: Path = ROOT, *, check_bindings: bool = True) -> dict:
    errors = []
    def require(ok, label):
        if not ok: errors.append(label)
    if not isinstance(program,dict):
        return {'status':'FAIL','errors':['program must be an object']}
    for key in ['authority','resources','controller','requirements','completion',
                'state_contract','evidence_bindings','acceptance_inventory']:
        require(isinstance(program.get(key),dict),key+': object required')
    if errors:return {'status':'FAIL','errors':errors}
    require(program.get('schema') == 'legalmath.odrl-master-program.v1','schema')
    require(program.get('status') in {'DRAFT_NOT_EXECUTED','REVIEWED_NOT_EXECUTED'},'plan status')
    a = program.get('authority', {})
    require(a.get('current_scope') == 'create_and_review_program_only','planning authority')
    require(a.get('feature_execution_authorized') is False,'no feature execution grant')
    require(a.get('external_model_calls') == 0 and a.get('subagents_authorized') is False,'no external/subagent grant')
    require(a.get('active_legal_master_modified') is False,'active master untouched')
    r=program.get('resources', {})
    require(r.get('external_calls_authorized') == 0,'external allowance remains zero')
    require(program.get('controller',{}).get('status')=='NO_DISPATCHER_INSTALLED','checker is not dispatcher')
    rows=program.get('tasks',[])
    require(isinstance(rows,list),'task list')
    if not isinstance(rows,list):return {'status':'FAIL','errors':errors}
    require(all(isinstance(t,dict) and isinstance(t.get('id'),str) for t in rows),'task identity structure')
    if any(not isinstance(t,dict) or not isinstance(t.get('id'),str) for t in rows):
        return {'status':'FAIL','errors':errors}
    tasks={t['id']:t for t in rows};ids=set(tasks)
    require(len(tasks)==len(rows),'unique IDs')
    require(ids==EXPECTED,'complete task inventory')
    requirements=program.get('requirements',{})
    require(set(requirements)=={f'R{i:02}' for i in range(1,12)},'complete proposal requirements')
    graph={};coverage=set()
    for name,t in tasks.items():
        require(t.get('status')=='NOT_STARTED' and t.get('attempts_used')==0,name+': no fabricated execution')
        maximum=t.get('max_attempts')
        require(type(maximum) is int and 1 <= maximum <= 2,name+': finite attempts')
        require(t.get('execution_command') is None,name+': no fake executable handler')
        for field in ['outputs','acceptance','write_scope','requirements']:
            value=t.get(field)
            require(isinstance(value,list) and bool(value) and all(isinstance(x,str) and x for x in value),name+': '+field)
        for field in ['title','owner','recovery','evidence_directory']:
            require(isinstance(t.get(field),str) and bool(t[field]),name+': '+field)
        for field in ['requires_success','after_completion','on_failure']:
            value=t.get(field)
            require(isinstance(value,list) and all(isinstance(x,str) for x in value),name+': '+field+' structure')
        groups=t.get('any_success')
        require(isinstance(groups,list) and all(isinstance(g,list) and bool(g) and all(isinstance(x,str) for x in g) for g in groups),name+': alternative groups')
        if any(not isinstance(t.get(k),list) for k in ['requires_success','after_completion','on_failure','any_success']):continue
        if any(not isinstance(g,list) for g in groups):continue
        deps=set(t['requires_success']+t['after_completion']+t['on_failure'])
        for g in groups:deps.update(g)
        require(deps <= ids,name+': known dependencies')
        require(name not in deps,name+': no self dependency')
        graph[name]=deps
        coverage.update(t.get('requirements',[]))
        require(set(t.get('requirements',[])) <= set(requirements),name+': known requirements')
        require(t.get('authority_gate') in a.get('future_gates',{}),name+': known authority gate')
        require(not t['on_failure'] or t.get('kind')=='recovery',name+': failure trigger only on recovery')
    require(coverage==set(requirements),'every requirement assigned')
    done=set(); layers=[]
    while len(done)<len(graph):
        ready=sorted(k for k,v in graph.items() if k not in done and v <= done)
        if not ready:break
        layers.append(ready);done.update(ready)
    require(done==ids,'acyclic dependency graph')
    if EXPECTED <= ids:
        for name,required_success in SUCCESS_DEPENDENCIES.items():
            require(tasks[name]['requires_success']==required_success,
                    name+': reviewed success dependencies')
            expected_completion=(sorted(ids-{'L19'}) if name=='L19' else
                                 ['V08'] if name=='R08' else ['C09C'] if name=='A18' else [])
            require(sorted(tasks[name]['after_completion'])==expected_completion,
                    name+': reviewed completion dependencies')
            require(tasks[name]['on_failure']==(['V08'] if name=='R08' else []),
                    name+': reviewed failure dependency')
            require(tasks[name]['any_success']==([['V08','R08']] if name=='Q10' else []),
                    name+': reviewed alternatives')
            require(tasks[name]['authority_gate']==('bounded_generation' if name=='G16' else 'local_implementation'),
                    name+': scoped authority gate')
            require(tasks[name]['max_attempts']==(1 if name in {'R08','G16'} else 2),
                    name+': reviewed attempt bound')
        require(tasks['F06']['requires_success'] == ['N02','T03','E04','P05'],
                'fact binding waits for profile contract')
        require(tasks['X07']['requires_success'] == ['N02','P05','E04','T03'],
                'export waits for independent cases')
        require(tasks['Q10']['any_success']==[['V08','R08']],'qualified evaluator alternatives')
        require('V08' not in tasks['Q10']['requires_success'],'fallback not blocked by engine failure')
        require(tasks['R08']['on_failure']==['V08'] and tasks['R08']['max_attempts']==1,'bounded recovery trigger')
        require('Q10' not in tasks['D11']['requires_success'],'duty specification independent of evaluator')
        require(tasks['G16']['authority_gate']=='bounded_generation','generation external gate')
        require('Q13' in tasks['G16']['requires_success'] and 'G14' in tasks['G16']['requires_success'],'generation after manual semantic checks/protocol')
        require('G16' not in tasks['K17']['requires_success'] and 'G16' not in tasks['A18']['requires_success'],'manual release independent of model comparison')
        require(set(tasks['L19']['after_completion'])==ids-{'L19'},'completion review preserves all branches')
        require(not tasks['L19']['requires_success'],'completion assessment must survive branch failure')
        require(tasks['A18']['after_completion']==['C09C'],
                'manual release records optional Catala disposition')
        trigger=tasks['R08'].get('failure_trigger',{})
        require(trigger.get('task')=='V08','recovery names triggering evaluator')
        require(trigger.get('accepted_failure_classes')==['SUPPORTED_FRAGMENT_INCOMPATIBILITY'],
                'recovery has one qualified failure class')
        require(isinstance(trigger.get('classification_receipt'),str) and trigger['classification_receipt'],
                'recovery classification receipt')
    c=program.get('completion',{})
    required={t['id'] for t in rows if t.get('mandatory_for_full_program')}
    require(required==EXPECTED-{'V08','R08','C09C'},'all required proposal tasks retained')
    require(set(c.get('full_program_requires',[]))==required,'honest full-completion requirements')
    require({'A18','G16','L19'} <= required,'full program includes generation and final assessment')
    require(not {'V08','R08','C09C'} & required,'optional alternatives do not require both engines')
    require(c.get('manual_release_requires')==['A18'],'separate manual release criterion')
    require(c.get('manual_release_after_completion')==['C09C'],
            'manual release accounts for optional Catala outcome')
    require(c.get('qualification_alternatives')==[['V08','R08']],'full completion keeps evaluator alternative')
    require(c.get('report_is_not_release') is True,'assessment success is not product success')
    require(program.get('state_contract',{}).get('terminal_states')==['SUCCEEDED','FAILED','BLOCKED','SKIPPED'],'explicit terminal states')
    inventory=program['acceptance_inventory']
    require(inventory.get('families')==[f'F{i:02}' for i in range(1,21)],'complete case-family inventory')
    require(inventory.get('mutations')==[f'M{i:02}' for i in range(1,18)],'complete mutation inventory')
    require(inventory.get('specification_task')=='T03','independent specification owner')
    require(inventory.get('contract_file')==program.get('contracts'),'acceptance contract identity')
    bindings=program.get('evidence_bindings',{})
    require(isinstance(bindings,dict) and len(bindings)>=20,'retained baseline bindings')
    for name,expected in bindings.items():
        require(isinstance(expected,str) and len(expected)==64 and all(x in '0123456789abcdef' for x in expected),'hash format: '+name)
        if check_bindings:
            try:
                actual=hashlib.sha256(safe_file(root,name).read_bytes()).hexdigest()
                require(actual==expected,'changed evidence: '+name)
            except (OSError,ValueError) as exc:errors.append(str(exc))
    if check_bindings:
        for field in ['contracts','review','plan']:
            try:safe_file(root,program[field])
            except (OSError,ValueError,KeyError) as exc:errors.append(str(exc))
        try:
            contract=safe_file(root,program['contracts']).read_text()
            require(re.findall(r'^\| (F\d{2}) \|',contract,re.MULTILINE)==inventory['families'],
                    'contract case rows match machine inventory')
            require(set(re.findall(r'\bM\d{2}\b',contract))==set(inventory['mutations']),
                    'contract mutations match machine inventory')
        except (OSError,ValueError,KeyError) as exc:errors.append(str(exc))
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'task_count':len(tasks),
            'requirement_count':len(requirements),'binding_count':len(bindings),'topological_layers':layers,
            'execution_status':'NOT_STARTED','authority':'PLANNING_ONLY',
            'limit':'Graph, identities and planning invariants only; no legal validation or implementation evidence.'}


def frontier(program: dict, states: dict | None = None, gates: set | None = None,
             failure_classes: dict | None = None) -> dict:
    """Pure scenario helper, not an execution-state loader or dispatch command."""
    states=states or {};gates=gates or set();failure_classes=failure_classes or {}
    ready=[];blocked={};skip=[]
    for t in program['tasks']:
        name=t['id']
        if states.get(name,'NOT_STARTED') in TERMINAL or states.get(name)=='RUNNING':continue
        reasons=[]
        failed=t['on_failure']
        if failed and all(states.get(x)=='SUCCEEDED' for x in failed):
            skip.append(name);continue
        trigger=t.get('failure_trigger')
        if trigger and any(states.get(x)=='FAILED' for x in failed):
            failure_class=failure_classes.get(trigger.get('task'))
            if failure_class is not None and failure_class not in trigger.get('accepted_failure_classes',[]):
                skip.append(name);continue
            if failure_class is None:
                reasons.append('failure class not qualified')
        if failed and not any(states.get(x)=='FAILED' for x in failed):reasons.append('failure trigger not met')
        if any(states.get(x)!='SUCCEEDED' for x in t['requires_success']):reasons.append('success prerequisites')
        if any(states.get(x) not in TERMINAL for x in t['after_completion']):reasons.append('completion prerequisites')
        if any(not any(states.get(x)=='SUCCEEDED' for x in group) for group in t['any_success']):reasons.append('qualified alternative missing')
        if t['authority_gate'] not in gates:reasons.append('authority: '+t['authority_gate'])
        if reasons:blocked[name]=reasons
        else:ready.append(name)
    return {'ready':ready,'blocked':blocked,'recovery_not_needed':skip}


def completion(program: dict, states: dict) -> dict:
    """Check a hypothetical state closure, never execution receipts or authority."""
    c=program['completion']
    tasks={t['id']:t for t in program['tasks']}
    memo={}
    visiting=set()
    def succeeded(name):
        if name in memo:return memo[name]
        if name in visiting or name not in tasks:return False
        visiting.add(name)
        t=tasks[name]
        result=(states.get(name)=='SUCCEEDED'
                and all(succeeded(x) for x in t['requires_success'])
                and all(states.get(x) in TERMINAL for x in t['after_completion'])
                and all(any(succeeded(x) for x in g) for g in t['any_success'])
                and (not t['on_failure'] or any(states.get(x)=='FAILED' for x in t['on_failure'])))
        visiting.remove(name);memo[name]=result
        return result
    missing=[x for x in c['full_program_requires'] if not succeeded(x)]
    alternatives=all(any(succeeded(x) for x in g) for g in c['qualification_alternatives'])
    manual_after=[x for x in c['manual_release_after_completion']
                  if states.get(x) not in TERMINAL]
    full_after=[t['id'] for t in program['tasks'] if t['id']!='L19'
                and states.get(t['id']) not in TERMINAL]
    return {'manual_release':(all(succeeded(x) for x in c['manual_release_requires'])
                              and not manual_after),
            'full_program_complete':(not missing and alternatives and not full_after
                                     and states.get('L19')=='SUCCEEDED'),
            'missing_required':missing,'manual_release_pending_completion':manual_after,
            'nonterminal_before_completion':full_after,'qualified_evaluator':alternatives}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program',default=str(PROGRAM),help='worktree-relative plan, read only')
    args=parser.parse_args()
    try:
        program=json.loads(safe_file(ROOT,args.program).read_text())
        result=validate(program)
        result['program_sha256']=hashlib.sha256(safe_file(ROOT,args.program).read_bytes()).hexdigest()
        result['current_frontier']=frontier(program) if result['status']=='PASS' else None
        if result['current_frontier']:
            result['current_frontier']={'ready':result['current_frontier']['ready'],
                                       'gate':'No implementation instruction recorded; no task dispatched.'}
    except (OSError,ValueError,KeyError,TypeError) as exc:
        result={'status':'FAIL','errors':[str(exc)]}
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
