"""Complete Note26.5 source/cell comparisons and bounded installed use."""
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
from scripts import prospectus_basf_hedge_source as source
from scripts import prospectus_basf_equity as install_base
from legalmath.prospectus import basf_hedge_note as note,basf_hedge_spec as spec,basf_oci_notes
from legalmath.prospectus.execution_authority import read,file_hash
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT,HERE,PRIOR,BASE,PLAN=source.ROOT,source.HERE,source.PRIOR,source.BASE,source.PLAN
RUNNER=ROOT/'scripts/prospectus_installed_hedge_runner.py'
save,load=source.save,source.load
install_base.HERE=HERE
PREDECESSORS={'profile':('prepare','render'),'baseline':('profile',),'compare':('baseline',),
    'controls':('compare',),'tests':('controls',),'install-prepare':('tests',),
    'build':('install-prepare',),'install':('build',),'replay':('install',),'verify':('replay',)}


def methods():
    names=[Path(__file__),Path(source.__file__),Path(source.base.__file__),Path(install_base.__file__),RUNNER,
           ROOT/PLAN,ROOT/'pyproject.toml',HERE/'IMAGE-REVIEW.md',HERE/'EXECUTION-AUDIT.md',
           ROOT/'tests/prospectus/test_basf_hedge_note.py']
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
        target=HERE/'methods'/p;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/p,target)
    products=load(HERE/'products.json.gz');graph=products['P1']['payload']['graph']
    units={u['id']:u for u in graph['units']}
    def numbered(page,n):
        return anchor(units[note.DOCUMENT+':p'+str(page)+':l'+str(n)])
    def group(page,ids):
        return [numbered(page,n) for n in ids]
    def part(n,start,end):
        a=numbered(281,n);a.update(start=start,end=end,quote=a['quote'][start:end]);return a
    fair_rows=[]
    for (name,label,ids,parent),expected in zip(spec.FAIR_ROWS,spec.FAIR_VALUES):
        cells={y:group(279,i) for y,i in zip(('2022','2021'),ids)}
        assert [a[0]['quote'] for a in cells.values()]==expected
        fair_rows.append({'id':name,'parent':parent,'label':group(279,label),'cells':cells})
    fair={'title':numbered(279,31),'unit':numbered(279,32),
          'years':{'2022':numbered(279,33),'2021':numbered(279,34)},'rows':fair_rows,'footnote':numbered(279,65)}
    effects=[]
    for year,title_id,unit_id,footnote_id in [('2022',3,4,119),('2021',120,121,213)]:
        rows=[]
        for (name,label,ids),expected in zip(spec.EFFECT_ROWS[year],spec.EFFECT_VALUES[year]):
            cells={c:group(281,i) for c,i in zip(spec.COLUMNS,ids)}
            assert [' '.join(a['quote'] for a in cells[c]) for c in spec.COLUMNS]==expected
            rows.append({'id':name,'label':group(281,label),'cells':cells})
        shared=spec.SHARED[year]
        effects.append({'year':year,'title':numbered(281,title_id),'unit':numbered(281,unit_id),
            'group_headers':[{'members':members,'anchors':group(281,ids)}
                for ids,members in zip(spec.GROUP_HEADERS[year],spec.HEADER_MEMBERS)],
            'columns':[{'id':c,'kind':'text' if c in spec.TEXT_COLUMNS else 'integer_millions','headers':group(281,ids)}
                for c,ids in zip(spec.COLUMNS,spec.HEADERS[year])],
            'shared_header':{'original':numbered(281,shared),
                'associations':{'hedged_change':part(shared,0,11),'ineffectiveness':part(shared,12,23)},
                'separator':part(shared,11,12)},'rows':rows,'footnote':numbered(281,footnote_id)})
    rendered=read(HERE/'rendered-source.json')
    value={'version':note.VERSION,'graph_sha256':digest(graph),'prior_sha256':digest(load(PRIOR/'note-consumer.json.gz')),
        'reviewer':{'identity':'Codex supplied original-image review2026-10-15',
                    'basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
        'source':{k:rendered[k] for k in ('document','path','sha256','images')},
        'metadata':{str(p):group(p,ids) for p,ids in spec.METADATA.items()},
        'prose':{k:{'meaning':meaning,'anchors':group(p,ids)} for k,(p,ids,meaning) in spec.PROSE.items()},
        'typographic':{'279':group(279,[28,97])},'fair_table':fair,'effects_tables':effects,
        'excluded_note27':group(282,list(range(10,86))),'selected_reading':None,'financial_values_validated':False}
    save('profile.json',value);save('profile-pin.json',{'sha256':digest(value)})
    old={'statement':read(BASE/'basf-incorporation/attempt-002/repair/profile.json'),
         'equity':read(BASE/'basf-incorporation/attempt-003/profile.json'),'oci':read(PRIOR/'profile.json')}
    save('prior-profiles.json',old)
    save('pre-run-audit.json',{'status':'PASS','plan':PLAN,'baseline':str(PRIOR.relative_to(ROOT)),
        'image_review':'IMAGE-REVIEW.md','complete_page_occurrences':452,'note_occurrences':376,
        'excluded_occurrences':76,'grid_positions':128,'numeric_positions':101,'printed_text_positions':21,
        'blank_positions':6,'shared_header_occurrences':2,'comparison_role':'EXPLANATORY_ONLY',
        'native_render_allowance':1,'http_allowance':0,'outer_command_limit':5,'local_repair_limit':1,
        'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9})
    return {'occurrences':452,'grid_positions':128,'printed_cells':122,'blank_positions':6,'shared_headers':2}


def baseline():
    old=read(HERE/'prior-profiles.json');sp,ep,np=[old[k] for k in ('statement','equity','oci')]
    result=basf_oci_notes.consume(load(HERE/'products.json.gz'),sp,ep,np,ROOT,
        expected_statement_profile_sha256=digest(sp),expected_equity_profile_sha256=digest(ep),expected_profile_sha256=digest(np))
    save('baseline-consumer.json.gz',result)
    assert result==load(PRIOR/'note-consumer.json.gz')
    return {'complete_prior_consumer_equal':True,'ordinary_answer_unchanged':True}


def compare():
    old=read(HERE/'prior-profiles.json');profile=read(HERE/'profile.json')
    result=note.consume(load(HERE/'products.json.gz'),old,profile,ROOT,
        expected_prior_profiles_sha256=digest(old),expected_profile_sha256=digest(profile))
    save('hedge-consumer.json.gz',result)
    prior=load(HERE/'baseline-consumer.json.gz')
    assert {k:result[k] for k in prior}==prior
    review=result['hedge_note_review']
    assert (review['page_occurrences_accounted'],review['note_occurrences'],review['excluded_occurrences'])==(452,376,76)
    assert [[r['cells'][y]['literal'] for y in ('2022','2021')] for r in review['fair_table']['rows']]==spec.FAIR_VALUES
    blanks=0
    for table in review['effects_tables']:
        expected=spec.EFFECT_VALUES[table['year']]
        actual=[[r['cells'][c]['literal'] or '' for c in spec.COLUMNS] for r in table['rows']]
        assert actual==expected
        blanks+=sum(r['cells'][c]['status']=='BLANK_ORIGINAL_NO_PRINTED_VALUE' for r in table['rows'] for c in spec.COLUMNS)
    assert blanks==6
    comparisons=review['comparisons']
    equal=[c for c in comparisons if c['status']=='EQUAL_PRINTED_VALUES']
    unknown=[c for c in comparisons if c['status']=='UNKNOWN_COMPONENT']
    mismatched=[c for c in comparisons if c['status']=='SCOPE_EQUIVALENCE_NOT_ESTABLISHED']
    differences=[(c['name'],c['left_minus_right']) for c in comparisons if c['status']=='PRINTED_DIFFERENCE']
    assert (len(equal),len(unknown),len(mismatched))==(11,10,4)
    assert differences==[('fair:2021:total',-1)]
    assert review['earlier_hedge_net_difference']['left_minus_right']==-1
    assert not review['unique_bridge_to_prior_net_established'] and not review['rounding_cause_established']
    report={'status':'PASS','ordinary_answer_unchanged':True,'all_earlier_reviews_unchanged':True,
        'page_occurrences':452,'note_occurrences':376,'excluded_occurrences':76,
        'grid_positions':128,'numeric_positions':101,'printed_text_positions':21,'blank_positions':6,
        'shared_headers':2,'footnoted_unknown_preserved':True,'direct_equalities':11,'unknown_arithmetic':10,
        'scope_equivalence_not_established':4,'printed_differences':differences,
        'prior_hedge_net_difference':-1,'unique_bridge_to_prior_net_established':False,
        'rounding_cause_established':False,'diagnostic_role':'EXPLANATORY_ONLY',
        'financial_values_validated':False,'independent_legal_acceptance':False,'legal_scope_selected':False,
        'new_native_render_reservations':1,'new_native_extractions':0,'http_calls':0}
    save('comparison.json',report);return report


def controls():
    original=read(HERE/'profile.json');products=load(HERE/'products.json.gz');prior=load(HERE/'baseline-consumer.json.gz')
    names=('wrong-year','swapped-tables','cross-row','cross-column','omitted-cell','duplicate-cell','blank-as-dash',
        'dash-as-zero','omitted-footnote-marker','omitted-footnote','wrong-footnote','wrong-caption-kind',
        'missing-header','shared-header-as-one-column','swapped-shared-spans','omitted-separator','invented-substring-box',
        'wrong-parent-group','lost-of-which-scope','omitted-closing-qualification','changed-recognition-rule',
        'note27-leak','omitted-note27-context','omitted-typographic','changed-source','changed-image',
        'claimed-legal-selection','claimed-independent-review','claimed-financial-validation','stale-prior','stale-pin')
    results=[]
    for name in names:
        value=deepcopy(original);table=value['effects_tables'][0];other=value['effects_tables'][1]
        if name=='wrong-year':table['year']='2021'
        elif name=='swapped-tables':value['effects_tables'].reverse()
        elif name=='cross-row':table['rows'][0]['cells'],table['rows'][1]['cells']=table['rows'][1]['cells'],table['rows'][0]['cells']
        elif name=='cross-column':
            cells=table['rows'][0]['cells'];cells['assets'],cells['liabilities']=cells['liabilities'],cells['assets']
        elif name=='omitted-cell':table['rows'][0]['cells']['assets']=[]
        elif name=='duplicate-cell':table['rows'][0]['cells']['assets'].append(deepcopy(table['rows'][0]['cells']['assets'][0]))
        elif name=='blank-as-dash':table['rows'][-1]['cells']['income_item']=deepcopy(table['rows'][-1]['cells']['ineffectiveness'])
        elif name=='dash-as-zero':other['rows'][2]['cells']['reclassified'][0]['quote']='0 a'
        elif name=='omitted-footnote-marker':other['rows'][2]['cells']['reclassified'][0]['quote']='–'
        elif name=='omitted-footnote':del table['footnote']
        elif name=='wrong-footnote':table['footnote']=deepcopy(other['footnote'])
        elif name=='wrong-caption-kind':table['columns'][2]['kind']='integer_millions'
        elif name=='missing-header':table['columns'][4]['headers'].pop()
        elif name=='shared-header-as-one-column':table['shared_header']['associations']['hedged_change']=deepcopy(table['shared_header']['original'])
        elif name=='swapped-shared-spans':
            a=table['shared_header']['associations'];a['hedged_change'],a['ineffectiveness']=a['ineffectiveness'],a['hedged_change']
        elif name=='omitted-separator':del table['shared_header']['separator']
        elif name=='invented-substring-box':table['shared_header']['associations']['hedged_change']['bbox']=[0,0,1,1]
        elif name=='wrong-parent-group':table['group_headers'][0]['members']=['oci_change']
        elif name=='lost-of-which-scope':value['fair_table']['rows'][3]['parent']=None
        elif name=='omitted-closing-qualification':value['prose']['closing_rule']['anchors'].pop()
        elif name=='changed-recognition-rule':value['prose']['closing_rule']['meaning']='All derecognition immediately recycles through income.'
        elif name=='note27-leak':value['prose']['closing_rule']['anchors'].append(deepcopy(value['excluded_note27'][0]))
        elif name=='omitted-note27-context':value['excluded_note27'].pop()
        elif name=='omitted-typographic':value['typographic']['279'].pop()
        elif name=='changed-source':value['source']['sha256']='0'*64
        elif name=='changed-image':value['source']['images'][2]['sha256']='0'*64
        elif name=='claimed-legal-selection':value['selected_reading']='full-financial-statements'
        elif name=='claimed-independent-review':value['reviewer']['independent']=True
        elif name=='claimed-financial-validation':value['financial_values_validated']=True
        elif name=='stale-prior':value['prior_sha256']='0'*64
        else:value['reviewer']['identity']+='changed'
        pin=digest(original) if name=='stale-pin' else digest(value)
        save('adverse-inputs/'+name+'.json.gz',{'profile':value,'expected_profile_sha256':pin})
        try:note.evaluate(products['P1']['payload']['graph'],prior,value,ROOT,expected_profile_sha256=pin)
        except ValueError as error:
            results.append({'case':name,'refused':True,'repinned':name!='stale-pin','reason':str(error)})
        else:raise AssertionError('Altered hedge note accepted: '+name)
    save('actual-controls.json',results)
    return {'actual_controls_refused':len(results),'repinned':len(results)-1}


def tests():
    import pytest
    code=pytest.main(['-q','tests/prospectus/test_basf_hedge_note.py','--junitxml='+str(HERE/'tests.xml')])
    assert code==0;return {'pytest_exit':int(code)}


def workspace():return Path(read(HERE/'workspace.json')['directory'])


def install_prepare():
    old=Path(read(PRIOR/'workspace.json')['directory'])/'environment';old_package=read(PRIOR/'source-package.json')
    assert install_base.package_files(old/'lib/python3.11/site-packages/legalmath')==old_package
    temp=Path(tempfile.mkdtemp(prefix='installed-basf-hedge-',dir=ROOT/'.localresources/prospectus'))
    save('workspace.json',{'directory':str(temp),'environment_cloned_from':str(old)})
    shutil.copytree(old,temp/'environment',symlinks=True);(temp/'source').mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',temp/'source/pyproject.toml')
    shutil.copytree(ROOT/'src',temp/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    shutil.copyfile(RUNNER,temp/'runner.py')
    package=install_base.package_files(temp/'source/src/legalmath')
    assert all(package.get(p)==h for p,h in old_package.items())
    added=sorted(set(package)-set(old_package))
    assert added==['prospectus/basf_hedge_note.py','prospectus/basf_hedge_spec.py']
    save('source-package.json',package)
    save('prior-package-identity.json',{'status':'PASS','all_prior_files_unchanged':len(old_package),
        'prior_evidence':str(PRIOR.relative_to(ROOT)),'new_modules':added})
    save('environment-metadata.json',{str(p.relative_to(temp/'environment')):file_hash(p)
        for p in (temp/'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'new_modules':added,'prior_files_unchanged':len(old_package),'exact_package_files':len(package)}


def build():return install_base.build()
def install():return install_base.install()
def replay():
    install_base.run('replay',[str(workspace()/'environment/bin/python'),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT)])
    return read(HERE/'installed-results/result.json')


def verify():
    result=read(HERE/'installed-results/result.json')
    assert result['status']=='PASS' and result['full_output_equal'] and result['earlier_outputs_unchanged']
    assert result['controls']==31 and result['native_calls']==0
    package=workspace()/'environment/lib/python3.11/site-packages/legalmath';expected=read(HERE/'source-package.json')
    assert install_base.package_files(package)==expected==read(HERE/'installed-results/package-files.json')
    proof=read(HERE/'installed-results/import-proof.json');assert proof['isolated']==1
    for m in proof['modules'].values():
        p=Path(m['path']).resolve()
        assert p.is_relative_to(package) and file_hash(p)==m['sha256']==expected[str(p.relative_to(package))]
    assert load(HERE/'installed-results/hedge-consumer.json.gz')==load(HERE/'hedge-consumer.json.gz')
    assert read(HERE/'installed-results/controls.json')==read(HERE/'actual-controls.json')
    assert len(process_ledger.checked(HERE/'command-ledger.json')['reservations'])==4
    assert len(process_ledger.checked(HERE/'native-ledger.json')['reservations'])==1
    result={**read(HERE/'comparison.json'),'installed_full_output_equal':True,'actual_controls_refused':31,
        'exact_package_files':len(expected),'prior_package_files_unchanged':423,'outer_commands':4,
        'local_repairs_used':0,'different_host_portability':False,
        'historical_visible_native_reservation_lower_bound':79,'historical_visible_source_http_lower_bound':9}
    save('verified-result.json',result);return result


def main():
    stage=sys.argv[1];assert stage in PREDECESSORS
    ad=bindings()
    for prior in PREDECESSORS[stage]:
        assert read(HERE/'invocations'/prior/'result.json')['status']=='PASS','Failed prerequisite: '+prior
    folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False)
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_hedge_note',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic',
        'cpu_gpu':'CPU only;no GPU/framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors':list(PREDECESSORS[stage])})
    tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError('120-second hedge-note stage limit;no automatic retry')
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
