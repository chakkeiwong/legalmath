"""Recover the retained pension preparation using its reviewed exact plan append."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from scripts import prospectus_component_revalidation as c

PLAN='docs/plans/prospectus-post-repair-installed-batch-2026-10-17.md'


def main():
    tick=time.monotonic();a=Authority(ROOT);old,tasks,_=a.spec();assert old['revision']==238
    failed=REL+'/reviews/component-239';prior=read(ROOT/failed/'frozen.json')
    failure=read(ROOT/failed/'failure.json')
    c.require(failure['error']=='ValueError: Unexpected changed original source/document','Different failure')
    c.require(prior['methods']==c.methods() and prior['runtime_files']==c.runtime_files(), 'Prepared methods/runtime changed')
    c.require(prior['inputs']=={n:file_hash(ROOT/n) for n in prior['inputs']},'Prepared inputs changed')
    original=c.baseline(ROOT,'pension');proof=read(ROOT/REL/'reviews/component-217-r2/append-proof.json')
    raw=(ROOT/proof['path']).read_bytes()
    c.require(file_hash(ROOT/proof['path'])==proof['current_hash'] and hashlib.sha256(raw[:proof['original_bytes']]).hexdigest()==proof['original_hash']
        and len(raw)-proof['original_bytes']==proof['appended_bytes'],'Reviewed plan append changed')
    ad=read(original/'admission.json');c.require(ad['binding'][proof['path']]==proof['original_hash'],'Wrong original plan')
    delta={n:{'old':h,'current':file_hash(ROOT/n)} for n,h in ad['binding'].items() if file_hash(ROOT/n)!=h}
    c.require(all(n==proof['path'] or n=='pyproject.toml' or n.startswith(('src/','scripts/','tests/')) for n in delta),'Unreviewed source mutation')
    history=c.historic('pension');c.require(history==prior['history'],'Changed original pension evidence')
    donor=REL+'/attempts/source-bes-dep-06/attempt-013'
    c.require(read(ROOT/donor/'source-package.json')==prior['package']==c.package_files(ROOT/donor/'installed/legalmath'),'Wrong wheel')
    e=next(e for e in reversed(a.events()) if e.get('attempt')==donor and e['kind'] in {'RECORD','ACCEPT'})
    c.require(a.retained_evidence_valid(e),'Changed installed donor')
    review_name=REL+'/reviews/pension-post-repair-239';folder=ROOT/review_name;folder.mkdir(exist_ok=False)
    for name in ('tests.xml','tests.log'):
        with (folder/name).open('xb') as out:out.write((ROOT/failed/name).read_bytes())
    prep=read(ROOT/failed/'preparation.json');count=c.checked_tests(folder/'tests.xml',prep['tests'])
    write(folder/'append-proof.json',proof,exclusive=True)
    write(folder/'history.json',history,exclusive=True)
    write(folder/'review.json',{'verdict':'PASS','failed_preparation':failed,'failed_hash':file_hash(ROOT/failed/'failure.json'),
        'diagnosis':'Known exact master-plan append was incorrectly classified as changed financial source by generic preparation. Existing pension-specific review already records this append. No financial source changed.',
        'repair':'Reuse unchanged successful test evidence, bound exact append proof and full source identity; no rerun or shared-method mutation.',
        'plan':PLAN,'package_files':len(prior['package'])},exclusive=True)
    elapsed=failure['seconds']+time.monotonic()-tick
    c.require(elapsed<90,'Combined failed/repaired preparation bound')
    write(folder/'preparation.json',{**prep,'seconds':elapsed,'command':['.venv/bin/python',str(Path(__file__).relative_to(ROOT))],
        'test_evidence_origin':failed,'failed_preparation_charged':failure['seconds'],'no_duplicate_test_start':True},exclusive=True)
    inputs=set(prior['inputs'])|{PLAN,str(Path(__file__).relative_to(ROOT))}
    inputs|={str(p.relative_to(ROOT)) for parent in (folder,ROOT/failed) for p in parent.iterdir() if p.is_file()}
    frozen={**prior,'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)}}
    write(folder/'frozen.json',frozen,exclusive=True)
    task=tasks['basf-references'];events=a.events()
    admissions=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')==task['budget_key']]
    maximum=old['budgets'][task['budget_key']]['maximum_new_attempts'];c.require(len(admissions)==maximum==11,'Wrong pension allowance')
    new=deepcopy(old);new['revision']=239;t=next(t for t in new['tasks'] if t['id']==task['id'])
    t.update(dossier=c.PLAN,reason='Validate current452-file installed pension with exact reviewed plan append and retained preparation tests',
        current_component_validation={'version':'current-installed-component.v1','kind':'pension','review':review_name,
            'baseline':str(original.relative_to(ROOT)),'wheel_attempt':donor,'bounds':c.BOUNDS},timeout_seconds=210)
    t['inputs']=sorted(set(t['inputs'])|set(frozen['methods'])|inputs|{review_name+'/frozen.json',review_name+'/preflight.json'})
    new['budgets'][task['budget_key']]['maximum_new_attempts']=12
    attempt=REL+'/attempts/basf-references/attempt-012'
    write(folder/'preflight.json',{'revision':239,'expected_attempt':attempt,'changed_original_methods':delta,
        'exact_append_review':review_name+'/append-proof.json','prior_task_attempt_bytes':sum(p.stat().st_size for p in original.parent.rglob('*') if p.is_file()),
        'new_ceiling':c.BOUNDS['new_bytes'],'reserve':c.BOUNDS['reserve_bytes'],'forecast_new_bytes':40*1024**2},exclusive=True)
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=239
    row=next(r for r in routes['tasks'] if r['task']==task['id'])
    row.update(phase=0,mode='local',task_sha256=digest(t),remaining=t['reason'],next_action='Execute current and isolated pension consumers; preserve all original22 refusals; record and refresh.')
    next(r for r in routes['tasks'] if r['task']=='source-bes-dep-06').update(phase=5,remaining='Current452-file comparative component verified in013.',next_action='Reuse identical installed wheel; no repeated comparative validation absent method change.')
    route=REL+'/closure-routes-2026-10-17-pension-239.json';write(ROOT/route,routes,exclusive=True)
    new['continuation_review'].update(plan=PLAN,routes=route)
    for n in (PLAN,route,str(Path(__file__).relative_to(ROOT))):new['continuation_review']['bindings'][n]=file_hash(ROOT/n)
    audit={'baseline':digest(old),'changes':t['reason'],'scope_unchanged':True,'budget_unchanged':False,
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'repair':review_name+'/review.json','append_proof':review_name+'/append-proof.json'},
        'evidence_contract':'Complete original pension current/installed outputs, integer oracle and22 actual refusals; exact package/imports; no legal/whole-task promotion',
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':11,'new_maximum':12,'retained_attempts':admissions,
            'reason':t['reason'],'next_discriminating_check':'Exact current and installed pension whole results under original criterion',
            'stop_condition':c.BOUNDS,'same_scope_authorization':'User-directed continuous general build with reviewed repairs'}}
    a.validate_program(new)
    write(ROOT/REL/'proposals/post-repair-239.json',new,exclusive=True)
    write(ROOT/REL/'proposals/post-repair-239-review.json',audit,exclusive=True)
    print(json.dumps({'revision_prepared':239,'tests_retained':count,'failed_preparation_preserved':True,'combined_preparation_seconds':elapsed}))


if __name__=='__main__':main()
