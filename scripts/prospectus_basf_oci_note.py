"""Bounded source-scope comparisons with exact prior and installed output checks."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

from scripts import prospectus_basf_oci_source as source
from scripts import prospectus_basf_equity as install_base
from legalmath.prospectus import basf_oci_notes as note, basf_equity
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT,HERE,PRIOR,BASE,PLAN=source.ROOT,source.HERE,source.PRIOR,source.BASE,source.PLAN
STATEMENT=BASE/'basf-incorporation/attempt-002/repair'
RUNNER=ROOT/'scripts/prospectus_installed_oci_runner.py'
save,load=source.save,source.load
install_base.HERE=HERE
PREDECESSORS={'profile':('prepare','render'),'baseline':('profile',),'compare':('baseline',),
    'controls':('compare',),'tests':('controls',),'install-prepare':('tests',),
    'build':('install-prepare',),'install':('build',),'replay':('install',),'verify':('replay',)}


def methods():
    names=[Path(__file__),Path(source.__file__),Path(install_base.__file__),RUNNER,ROOT/PLAN,
           ROOT/'pyproject.toml',HERE/'IMAGE-REVIEW.md',HERE/'EXECUTION-AUDIT.md',
           ROOT/'tests/prospectus/test_basf_oci_notes.py',ROOT/'tests/prospectus/test_basf_equity.py',
           ROOT/'tests/prospectus/test_basf_statement.py']
    names+=sorted((ROOT/'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)):file_hash(p) for p in names}


def bindings():
    ad=source.bindings()
    if (HERE/'methods.json').exists():
        assert methods()==read(HERE/'methods.json')
    return ad


def profile():
    assert (HERE/'IMAGE-REVIEW.md').is_file()
    save('methods.json',methods())
    for p in methods():
        target=HERE/'methods'/p
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/p,target)
    products=load(HERE/'products.json.gz')
    graph=products['P1']['payload']['graph']
    units={u['id']:u for u in graph['units']}
    def unit(n):
        return units[note.DOCUMENT+':p256:l'+str(n)]
    def numbered(n):
        return anchor(unit(n))
    groups={k:{'column':col,'meaning':meaning,'anchors':[numbered(n) for n in ids]}
            for k,(ids,col,meaning) in note.GROUPS.items()}
    amounts={}
    for key,(group,n,token,year,direction,scope) in note.AMOUNTS.items():
        u=unit(n);start=u['raw'].index(token)
        src=anchor(u)
        src.update(start=start,end=start+len(token),quote=token)
        amounts[key]={'group':group,'year':year,'direction':direction,'scope':scope,'source':src}
    rendered=read(HERE/'rendered-source.json')
    value={'version':note.VERSION,'graph_sha256':digest(graph),
           'prior_sha256':digest(load(PRIOR/'equity-consumer.json.gz')),
           'reviewer':{'identity':'Codex supplied original-image review2026-10-15',
                       'basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
           'source':{k:rendered[k] for k in ('document','page','path','sha256','image_path','image_sha256')},
           'metadata':[numbered(n) for n in (0,1,2)],'heading':numbered(3),'groups':groups,
           'typographic_occurrences':[numbered(43)],'amounts':amounts,
           'selected_reading':None,'financial_values_validated':False}
    save('profile.json',value)
    save('profile-pin.json',{'sha256':digest(value)})
    save('pre-run-audit.json',{'status':'PASS','plan':PLAN,'baseline':str(PRIOR.relative_to(ROOT)),
        'original_image_review':'IMAGE-REVIEW.md','scope_associations':'SUPPLIED_EXPOSED_REVIEW',
        'arithmetic_role':'EXPLANATORY_ONLY','native_render_allowance':1,'http_allowance':0,
        'outer_command_limit':5,'local_repair_limit':1,'historical_native_lower_bound':77,
        'new_render_reservations':1,'historical_source_http_lower_bound':9})
    return {'original_occurrences':59,'paragraph_groups':len(groups),'monetary_associations':len(amounts)}


def baseline():
    sp,ep=read(STATEMENT/'profile.json'),read(PRIOR/'profile.json')
    result=basf_equity.consume(load(HERE/'products.json.gz'),sp,ep,ROOT,
        expected_statement_profile_sha256=digest(sp),expected_profile_sha256=digest(ep))
    save('baseline-consumer.json.gz',result)
    assert result==load(PRIOR/'equity-consumer.json.gz')
    assert result['answer']==load(PRIOR/'baseline-answer.json.gz')
    return {'full_prior_consumer_equal':True,'ordinary_answer_unchanged':True}


def compare():
    sp,ep,np=read(STATEMENT/'profile.json'),read(PRIOR/'profile.json'),read(HERE/'profile.json')
    result=note.consume(load(HERE/'products.json.gz'),sp,ep,np,ROOT,
        expected_statement_profile_sha256=digest(sp),expected_equity_profile_sha256=digest(ep),
        expected_profile_sha256=digest(np))
    save('note-consumer.json.gz',result)
    assert {k:result[k] for k in ('answer','statement_review','equity_review')}==load(HERE/'baseline-consumer.json.gz')
    review=result['oci_note_review']
    assert (review['source_occurrences_accounted'],review['monetary_associations'])==(59,23)
    comparisons=review['comparisons']
    assert len(comparisons)==20
    equal=[c['name'] for c in comparisons if c['status']=='EQUAL_PRINTED_VALUES']
    different=[(c['name'],c['left_minus_right']) for c in comparisons if c['status']=='PRINTED_DIFFERENCE']
    unmatched=[c['name'] for c in comparisons if c['status']=='SCOPE_EQUIVALENCE_NOT_ESTABLISHED']
    assert len(equal)==10 and different==[('2022:hedge-net',-1)] and len(unmatched)==9
    assert review['amounts']['wintershall_recycling']['year'] is None
    assert not review['rounding_warning_is_proven_cause']
    report={'status':'PASS','ordinary_answer_unchanged':True,'all_earlier_reviews_unchanged':True,
        'source_occurrences':59,'monetary_associations':23,'direct_equalities':10,
        'printed_differences':different,'scope_equivalence_not_established':9,
        'diagnostic_role':'EXPLANATORY_ONLY','incorporation_scope_selected':False,
        'both_candidate_scopes_include_note':True,'financial_values_validated':False,
        'independent_legal_acceptance':False,'new_native_render_reservations':1,'new_native_extractions':0,
        'http_calls':0,'rounding_cause_established':False}
    save('comparison.json',report)
    return report


def controls():
    original=read(HERE/'profile.json')
    products,prior=load(HERE/'products.json.gz'),load(HERE/'baseline-consumer.json.gz')
    names=('swapped-years','sign-loss','wrong-decrease-direction','boolean-direction','component-as-total',
        'invented-wintershall-year','swapped-paragraphs','changed-column','changed-paragraph-meaning',
        'omitted-qualification','omitted-onward-reference','duplicate-occurrence','omitted-typographic-occurrence',
        'changed-source','changed-image','changed-unit','omitted-amount','wrong-amount-context','truncated-paragraph',
        'claimed-legal-selection','claimed-financial-validation','claimed-independent-review','stale-prior','stale-pin')
    results=[]
    for name in names:
        value=deepcopy(original)
        if name=='swapped-years': value['amounts']['pension_net_2022']['year']='2021'
        elif name=='sign-loss': value['amounts']['pension_tax_2022']['source']['quote']='€1,256'
        elif name=='wrong-decrease-direction': value['amounts']['hedge_net_2022']['direction']=1
        elif name=='boolean-direction': value['amounts']['pension_net_2022']['direction']=True
        elif name=='component-as-total': value['amounts']['pension_equity_2022']['scope']='pension OCI after taxes'
        elif name=='invented-wintershall-year': value['amounts']['wintershall_recycling']['year']='2022'
        elif name=='swapped-paragraphs':
            a,b=value['groups']['pension_amounts'],value['groups']['currency_amounts'];a['anchors'],b['anchors']=b['anchors'],a['anchors']
        elif name=='changed-column': value['groups']['currency_amounts']['column']='left'
        elif name=='changed-paragraph-meaning': value['groups']['policy']['meaning']='All items recycle into income.'
        elif name=='omitted-qualification': value['groups']['pension_amounts']['anchors'].pop(2)
        elif name=='omitted-onward-reference': del value['groups']['hedge_onward']
        elif name=='duplicate-occurrence': value['groups']['policy']['anchors'].append(deepcopy(value['groups']['policy']['anchors'][0]))
        elif name=='omitted-typographic-occurrence': value['typographic_occurrences']=[]
        elif name=='changed-source': value['source']['sha256']='0'*64
        elif name=='changed-image': value['source']['image_sha256']='0'*64
        elif name=='changed-unit': value['amounts']['hedge_net_2022']['source']['quote']='33'
        elif name=='omitted-amount': del value['amounts']['hedge_tax_2021']
        elif name=='wrong-amount-context': value['amounts']['hedge_net_2022']['group']='pension_amounts'
        elif name=='truncated-paragraph':
            a=value['groups']['currency_amounts']['anchors'][-1];a['quote']=a['quote'][:-1];a['end']-=1
        elif name=='claimed-legal-selection': value['selected_reading']='full-financial-statements'
        elif name=='claimed-financial-validation': value['financial_values_validated']=True
        elif name=='claimed-independent-review': value['reviewer']['independent']=True
        elif name=='stale-prior': value['prior_sha256']='0'*64
        else: value['reviewer']['identity']+='changed'
        pin=digest(original) if name=='stale-pin' else digest(value)
        save('adverse-inputs/'+name+'.json.gz',{'profile':value,'expected_profile_sha256':pin})
        try:
            note.evaluate(products['P1']['payload']['graph'],prior,value,ROOT,expected_profile_sha256=pin)
        except ValueError as error:
            results.append({'case':name,'refused':True,'repinned':name!='stale-pin','reason':str(error)})
        else:
            raise AssertionError('Altered Note20 accepted: '+name)
    save('actual-controls.json',results)
    return {'actual_controls_refused':len(results),'repinned':len(results)-1}


def tests():
    import pytest
    code=pytest.main(['-q','tests/prospectus/test_basf_oci_notes.py','tests/prospectus/test_basf_equity.py',
                     'tests/prospectus/test_basf_statement.py','--junitxml='+str(HERE/'tests.xml')])
    assert code==0
    return {'pytest_exit':int(code)}


def workspace():
    return Path(read(HERE/'workspace.json')['directory'])


def install_prepare():
    old=Path(read(PRIOR/'workspace.json')['directory'])/'environment'
    old_package=read(PRIOR/'source-package.json')
    assert install_base.package_files(old/'lib/python3.11/site-packages/legalmath')==old_package
    temp=Path(tempfile.mkdtemp(prefix='installed-basf-oci-',dir=ROOT/'.localresources/prospectus'))
    save('workspace.json',{'directory':str(temp),'environment_cloned_from':str(old)})
    shutil.copytree(old,temp/'environment',symlinks=True)
    (temp/'source').mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',temp/'source/pyproject.toml')
    shutil.copytree(ROOT/'src',temp/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    shutil.copyfile(RUNNER,temp/'runner.py')
    package=install_base.package_files(temp/'source/src/legalmath')
    assert all(package.get(p)==h for p,h in old_package.items())
    assert sorted(set(package)-set(old_package))==['prospectus/basf_oci_notes.py']
    save('source-package.json',package)
    save('prior-package-identity.json',{'status':'PASS','all_prior_files_unchanged':len(old_package),
        'earlier_evidence':str(PRIOR.relative_to(ROOT)),'new_modules':['prospectus/basf_oci_notes.py']})
    save('environment-metadata.json',{str(p.relative_to(temp/'environment')):file_hash(p)
        for p in (temp/'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'new_files':1,'prior_files_unchanged':len(old_package),'exact_package_files':len(package)}


def build():
    return install_base.build()


def install():
    return install_base.install()


def replay():
    install_base.run('replay',[str(workspace()/'environment/bin/python'),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT)])
    return read(HERE/'installed-results/result.json')


def verify():
    r=read(HERE/'installed-results/result.json')
    assert r['status']=='PASS' and r['full_output_equal'] and r['earlier_outputs_unchanged']
    assert r['controls']==24 and r['native_calls']==0
    package=workspace()/'environment/lib/python3.11/site-packages/legalmath'
    expected=read(HERE/'source-package.json')
    assert install_base.package_files(package)==expected==read(HERE/'installed-results/package-files.json')
    proof=read(HERE/'installed-results/import-proof.json')
    assert proof['isolated']==1
    for m in proof['modules'].values():
        p=Path(m['path']).resolve()
        assert p.is_relative_to(package) and file_hash(p)==m['sha256']==expected[str(p.relative_to(package))]
    assert load(HERE/'installed-results/note-consumer.json.gz')==load(HERE/'note-consumer.json.gz')
    assert read(HERE/'installed-results/controls.json')==read(HERE/'actual-controls.json')
    assert len(process_ledger.checked(HERE/'command-ledger.json')['reservations'])==4
    assert len(process_ledger.checked(HERE/'native-ledger.json')['reservations'])==1
    result={**read(HERE/'comparison.json'),'installed_full_output_equal':True,
        'actual_controls_refused':24,'exact_package_files':len(expected),'prior_package_files_unchanged':422,
        'outer_commands':4,'local_repairs_used':0,'different_host_portability':False,
        'historical_visible_native_reservation_lower_bound':78,'historical_visible_source_http_lower_bound':9}
    save('verified-result.json',result)
    return result


def main():
    stage=sys.argv[1]
    assert stage in PREDECESSORS
    ad=bindings()
    for prior in PREDECESSORS[stage]:
        assert read(HERE/'invocations'/prior/'result.json')['status']=='PASS','Failed prerequisite: '+prior
    folder=HERE/'invocations'/stage
    folder.mkdir(parents=True,exist_ok=False)
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_oci_note',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic',
        'cpu_gpu':'CPU only;no GPU/framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors':list(PREDECESSORS[stage])})
    tick=time.monotonic()
    def expire(signum,frame):
        raise TimeoutError('120-second Note20 stage limit;no automatic retry')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        details=globals()[stage.replace('-','_')]()
        bindings()
        size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        if (HERE/'workspace.json').exists():
            size+=sum(p.stat().st_size for p in workspace().rglob('*') if p.is_file())
        assert size<500*1024*1024
        result={'status':'PASS','stage':stage,'details':details,'wall_seconds':time.monotonic()-tick,
                'evidence_and_workspace_bytes':size}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/'+stage+'/result.json',result)
    print(result)


if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        main()
