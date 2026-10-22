"""Bounded actual pending-body consumer, controls and installed integration."""
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
from scripts import prospectus_basf_body_source as source
from scripts import prospectus_basf_equity as install_base
from legalmath.prospectus import basf_body_coverage as body, basf_body_spec as spec, basf_hedge_note
from legalmath.prospectus.execution_authority import read,file_hash
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest

ROOT,HERE,PRIOR,BASE,PLAN=source.ROOT,source.HERE,source.PRIOR,source.BASE,source.PLAN
RUNNER=ROOT/'scripts/prospectus_installed_body_runner.py'
save,load=source.save,source.load
install_base.HERE=HERE
PREDECESSORS={'profile':('prepare',),'baseline':('profile',),'compare':('baseline',),
    'controls':('compare',),'tests':('controls',),'install-prepare':('tests',),
    'build':('install-prepare',),'install':('build',),'replay':('install',),'verify':('replay',)}


def methods():
    names=[Path(__file__),Path(source.__file__),Path(source.base.__file__),Path(install_base.__file__),RUNNER,
           ROOT/PLAN,ROOT/'pyproject.toml',HERE/'IMAGE-REVIEW.md',HERE/'EXECUTION-AUDIT.md',
           ROOT/'tests/prospectus/test_basf_body_coverage.py']
    names+=sorted((ROOT/'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)):file_hash(p) for p in names}


def bindings():
    ad=source.bindings()
    if (HERE/'methods.json').exists(): assert methods()==read(HERE/'methods.json')
    return ad


def profile():
    products=load(HERE/'products.json.gz');prior=load(PRIOR/'hedge-consumer.json.gz')
    coverage,rows=body.inventory(products)
    assert coverage==prior['answer']['meaning_coverage']
    for row in rows: row['roles']=body.reviewed_roles(row)
    assert len(rows)==77
    value={'version':body.VERSION,'products_sha256':digest(products),'prior_sha256':digest(prior),
        'reviewer':{'identity':'Codex supplied original-image review2026-10-15',
                    'basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
        'source':read(HERE/'original-source.json'),'rows':rows,'meeting_heading':body.meeting_heading(rows),
        'legal_scope_resolved':False,'independent_legal_acceptance':False,'unknowns_resolved':0}
    save('profile.json',value);save('profile-pin.json',{'sha256':digest(value)})
    save('prior-profiles.json',{'preceding':read(PRIOR/'prior-profiles.json'),'hedge':read(PRIOR/'profile.json')})
    save('methods.json',methods())
    for p in methods():
        target=HERE/'methods'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    save('pre-run-audit.json',{'status':'PASS','plan':PLAN,'exact_baseline':str(PRIOR.relative_to(ROOT)),
        'pending_units':77,'unknown_spans':78,'unknown_characters':1872,
        'image_review':'IMAGE-REVIEW.md','counts_role':'EXPLANATORY_ONLY','unknowns_resolved':0,
        'native_allowance':0,'http_allowance':0,'outer_command_limit':4,'local_repair_limit':1,
        'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9})
    return {'pending_units':len(rows),'unknown_spans':sum(len(r['spans']) for r in rows),'unknowns_resolved':0}


def baseline():
    old=read(HERE/'prior-profiles.json');p,h=old['preceding'],old['hedge']
    result=basf_hedge_note.consume(load(HERE/'products.json.gz'),p,h,ROOT,
        expected_prior_profiles_sha256=digest(p),expected_profile_sha256=digest(h))
    save('baseline-consumer.json.gz',result)
    assert result==load(PRIOR/'hedge-consumer.json.gz')
    return {'complete_prior_consumer_equal':True}


def compare():
    old=read(HERE/'prior-profiles.json');profile=read(HERE/'profile.json')
    result=body.consume(load(HERE/'products.json.gz'),old,profile,ROOT,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(profile))
    save('body-consumer.json.gz',result)
    prior=load(HERE/'baseline-consumer.json.gz')
    assert {k:result[k] for k in prior}==prior
    review=result['body_coverage_review'];counts=review['counts']
    assert (counts['pending_units'],counts['unknown_spans'],counts['unknown_characters'])==(77,78,1872)
    assert counts['units_by_kind']=={'structural_only':67,'mixed':1,'substantive_only':9}
    assert [len(q['evidence']) for q in review['remaining_questions']]==[3,2,5]
    assert review['original_meaning_coverage']==prior['answer']['meaning_coverage']
    assert review['unknowns_resolved']==0 and not review['legal_scope_resolved']
    report={'status':'PASS','all_earlier_outputs_unchanged':True,'ordinary_answer_unchanged':True,
        'counts':counts,'remaining_question_groups':3,'substantive_pending_units':10,
        'unknowns_resolved':0,'original_unknown_coverage_preserved':True,
        'selected_raw_offsets_distinguished':True,'supplied_meeting_heading_order':spec.MEETING_ORDER,
        'automatic_classification':False,'independent_legal_acceptance':False,'legal_scope_resolved':False}
    save('comparison.json',report);return report


def controls():
    original=read(HERE/'profile.json');products=load(HERE/'products.json.gz');prior=load(HERE/'baseline-consumer.json.gz')
    names=['omitted-unit','duplicate-unit','reordered-unit','omitted-span','changed-selected-quote','changed-source-quote',
        'selected-offset-as-raw','lost-mapping-fragment','invented-bbox','default-as-heading','intro-as-heading',
        'placeholder-as-caption','field-label-as-caption','changed-original-coverage','omitted-image','changed-image',
        'changed-pdf','meeting-extraction-as-reading','claimed-scope','claimed-independent','claimed-resolved',
        'stale-products','stale-prior','stale-pin']
    observed=[]
    for name in names:
        value=deepcopy(original);rows=value['rows']
        def at(page,line):return next(r for r in rows if (r['page'],r['line'])==(page,line))
        if name=='omitted-unit':rows.pop()
        elif name=='duplicate-unit':rows.append(deepcopy(rows[-1]))
        elif name=='reordered-unit':rows[0],rows[1]=rows[1],rows[0]
        elif name=='omitted-span':at(123,82)['spans'].pop()
        elif name=='changed-selected-quote':at(127,12)['spans'][0]['quote']+=' or'
        elif name=='changed-source-quote':at(127,12)['spans'][0]['sources'][0]['source']['quote']+=' or'
        elif name=='selected-offset-as-raw':at(124,43)['spans'][0]['sources'][0]['source']['start']=0
        elif name=='lost-mapping-fragment':at(123,82)['spans'][1]['sources'].pop()
        elif name=='invented-bbox':at(123,82)['bbox']=[0,0,1,1]
        elif name=='default-as-heading':at(127,12)['roles']=['SECTION_HEADING']
        elif name=='intro-as-heading':at(123,82)['roles'][1]='SUBSECTION_CAPTION'
        elif name=='placeholder-as-caption':at(124,44)['roles']=['SUBSECTION_CAPTION']
        elif name=='field-label-as-caption':at(124,43)['roles']=['SUBSECTION_CAPTION']
        elif name=='changed-original-coverage':at(127,12)['coverage']['unknown_characters']=0
        elif name=='omitted-image':value['source']['images'].pop()
        elif name=='changed-image':value['source']['images'][0]['sha256']='0'*64
        elif name=='changed-pdf':value['source']['sha256']='0'*64
        elif name=='meeting-extraction-as-reading':value['meeting_heading']['reviewed_reading_order']=value['meeting_heading']['original_occurrence_order']
        elif name=='claimed-scope':value['legal_scope_resolved']=True
        elif name=='claimed-independent':value['reviewer']['independent']=True
        elif name=='claimed-resolved':value['unknowns_resolved']=77
        elif name=='stale-products':value['products_sha256']='0'*64
        elif name=='stale-prior':value['prior_sha256']='0'*64
        else:value['reviewer']['identity']+=' altered'
        pin=digest(original) if name=='stale-pin' else digest(value)
        save('adverse-inputs/'+name+'.json.gz',{'profile':value,'expected_profile_sha256':pin})
        try:body.evaluate(products,prior,value,ROOT,expected_profile_sha256=pin)
        except ValueError as error:observed.append({'case':name,'refused':True,'repinned':name!='stale-pin','reason':str(error)})
        else:raise AssertionError('Altered pending-body review accepted: '+name)
    save('actual-controls.json',observed)
    return {'controls_refused':len(observed),'repinned':len(observed)-1}


def tests():
    import pytest
    code=pytest.main(['-q','tests/prospectus/test_basf_body_coverage.py',
        'tests/prospectus_successor/test_meaning_coverage.py','--junitxml='+str(HERE/'tests.xml')])
    assert code==0;return {'pytest_exit':int(code)}


def workspace():return Path(read(HERE/'workspace.json')['directory'])


def install_prepare():
    old=Path(read(PRIOR/'workspace.json')['directory'])/'environment';old_package=read(PRIOR/'source-package.json')
    assert install_base.package_files(old/'lib/python3.11/site-packages/legalmath')==old_package
    temp=Path(tempfile.mkdtemp(prefix='installed-basf-body-',dir=ROOT/'.localresources/prospectus'))
    save('workspace.json',{'directory':str(temp),'environment_cloned_from':str(old)})
    shutil.copytree(old,temp/'environment',symlinks=True);(temp/'source').mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',temp/'source/pyproject.toml')
    shutil.copytree(ROOT/'src',temp/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    shutil.copyfile(RUNNER,temp/'runner.py')
    package=install_base.package_files(temp/'source/src/legalmath')
    assert all(package.get(p)==h for p,h in old_package.items())
    added=sorted(set(package)-set(old_package))
    assert added==['prospectus/basf_body_coverage.py','prospectus/basf_body_spec.py']
    save('source-package.json',package)
    save('prior-package-identity.json',{'status':'PASS','all_prior_files_unchanged':len(old_package),
        'prior_evidence':str(PRIOR.relative_to(ROOT)),'new_modules':added})
    save('environment-metadata.json',{str(p.relative_to(temp/'environment')):file_hash(p)
        for p in (temp/'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'prior_files_unchanged':len(old_package),'exact_package_files':len(package)}


def build():return install_base.build()
def install():return install_base.install()
def replay():
    install_base.run('replay',[str(workspace()/'environment/bin/python'),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT)])
    return read(HERE/'installed-results/result.json')


def verify():
    r=read(HERE/'installed-results/result.json')
    assert r['status']=='PASS' and r['full_output_equal'] and r['earlier_outputs_unchanged']
    assert r['controls']==24 and r['native_calls']==0
    package=workspace()/'environment/lib/python3.11/site-packages/legalmath';expected=read(HERE/'source-package.json')
    assert install_base.package_files(package)==expected==read(HERE/'installed-results/package-files.json')
    proof=read(HERE/'installed-results/import-proof.json');assert proof['isolated']==1
    for m in proof['modules'].values():
        p=Path(m['path']).resolve()
        assert p.is_relative_to(package) and file_hash(p)==m['sha256']==expected[str(p.relative_to(package))]
    assert load(HERE/'installed-results/body-consumer.json.gz')==load(HERE/'body-consumer.json.gz')
    assert read(HERE/'installed-results/controls.json')==read(HERE/'actual-controls.json')
    assert len(process_ledger.checked(HERE/'command-ledger.json')['reservations'])==3
    result={**read(HERE/'comparison.json'),'installed_full_output_equal':True,'actual_controls_refused':24,
        'exact_package_files':len(expected),'prior_package_files_unchanged':425,'outer_commands':3,
        'local_repairs_used':0,'different_host_portability':False,
        'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9}
    save('verified-result.json',result);return result


def main():
    stage=sys.argv[1];assert stage in PREDECESSORS
    ad=bindings()
    for previous in PREDECESSORS[stage]:
        assert read(HERE/'invocations'/previous/'result.json')['status']=='PASS','Failed prerequisite: '+previous
    folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False)
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_body_coverage',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic',
        'cpu_gpu':'CPU only;no framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors':list(PREDECESSORS[stage])})
    tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError('120-second body-review stage limit;no automatic retry')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        details=globals()[stage.replace('-','_')]();bindings()
        size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        if (HERE/'workspace.json').exists():size+=sum(p.stat().st_size for p in workspace().rglob('*') if p.is_file())
        assert size<500*1024*1024
        result={'status':'PASS','stage':stage,'details':details,'wall_seconds':time.monotonic()-tick,'evidence_and_workspace_bytes':size}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/'+stage+'/result.json',result);print(result)


if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
