"""No-native-call repair of retained mixed-script source selection."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus import native_text_choice as choice
from legalmath.prospectus.execution_authority import file_hash,read,write
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

BASE=ROOT/'docs/implementation/prospectus-execution-authority/attempts/native-layout-cases'
HERE=BASE/'attempt-004';PRIOR=BASE/'attempt-003';SOURCE=BASE/'attempt-002'
PLAN='docs/plans/prospectus-native-text-choice-2026-10-15.md'
PAGES=(5,6,14)
URLS=('https://www.riyadbank.com/','www.cma.org.sa','www.saudiexchange.sa','https://www.riyadcapital.com/')


def save(name,value):write(HERE/name,value,exclusive=True)
def loadgz(path):return json.loads(gzip.decompress(Path(path).read_bytes()))
def gzsave(name,value):
    with (HERE/name).open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value,ensure_ascii=False,allow_nan=False).encode(),mtime=0))


def methods():
    paths=[ROOT/'src/legalmath/prospectus/native_text_choice.py',
           ROOT/'tests/prospectus/test_native_text_choice.py',
           *(ROOT/'src/legalmath/prospectus/successor').glob('*.py')]
    return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted(paths)}


def bindings():
    ad=read(HERE/'admission.json')
    assert all(file_hash(ROOT/p)==h for p,h in ad['binding'].items())
    assert not (HERE/'outputs.json').exists()
    return ad


def prepare():
    for directory in (PRIOR,SOURCE):
        assert all(file_hash(directory/p)==h for p,h in read(directory/'outputs.json').items())
    baseline=loadgz(PRIOR/'source-product.json.gz')
    inspection=read(SOURCE/'source-inspection.json')
    selection={'version':choice.VERSION,'source_product_sha256':baseline['sha256'],'document':'riyad-ar',
        'inspection_path':str((SOURCE/'source-inspection.json').relative_to(ROOT)),
        'inspection_sha256':file_hash(SOURCE/'source-inspection.json'),
        'pages':[{'page':page,'path':str((SOURCE/f'riyad-page-{page}-native-reviewed.json.gz').relative_to(ROOT)),
                  'sha256':file_hash(SOURCE/f'riyad-page-{page}-native-reviewed.json.gz'),
                  'render_path':str((SOURCE/f'riyad-page-{page}.png').relative_to(ROOT)),
                  'render_sha256':next(r['sha256'] for r in inspection['renders'] if r['page']==page)} for page in PAGES],
        'reason':'Explicit exposed native observation alternative for reproduced URL-space and script-order differences; no independent Arabic reading.',
        'independent_legal_acceptance':False}
    save('selection.json',selection)
    save('method-identities.json',methods())
    for p in methods():
        target=HERE/'method'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    return {'selected_pages':list(PAGES),'native_calls':0}


def tests():
    command=[sys.executable,'-m','pytest','-q','tests/prospectus/test_native_text_choice.py',
             'tests/prospectus/test_region_coverage.py','--junitxml='+str(HERE/'tests.xml')]
    with (HERE/'tests.log').open('x') as out:
        result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},
                              stdout=out,stderr=subprocess.STDOUT,timeout=110)
    assert result.returncode==0,'See retained tests.log and tests.xml'
    suites=list(ET.parse(HERE/'tests.xml').getroot().iter('testsuite'))
    return {'tests':sum(int(s.get('tests',0)) for s in suites),'command':command}


def select():
    baseline=loadgz(PRIOR/'source-product.json.gz');selection=read(HERE/'selection.json')
    selected=choice.select_pages(baseline,selection,ROOT,expected_selection_sha256=digest(selection))
    gzsave('selected-source.json.gz',selected)
    graph=selected['payload']['graph']
    return {'units':len(graph['units']),'selected_units':sum(u['page'] in PAGES for u in graph['units']),
            'selected_words':sum(len(u['words']) for u in graph['units'] if u['page'] in PAGES)}


def consume():
    p1=loadgz(HERE/'selected-source.json.gz');selection=read(HERE/'selection.json')
    baseline=loadgz(PRIOR/'source-product.json.gz')
    p2=service.construction_product(p1,ROOT);p3=service.interpretation_product(p1,p2)
    products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
    result=choice.consume_selected(products,baseline,selection,ROOT,expected_selection_sha256=digest(selection))
    gzsave('selected-products.json.gz',products);gzsave('selected-consumer.json.gz',result)
    original=service.consume(loadgz(PRIOR/'products.json.gz'),ROOT,include_artifacts=True)
    assert original==loadgz(PRIOR/'baseline-answer.json.gz')
    gzsave('baseline-reconsumed.json.gz',original)
    return {'questions':{q:r['status'] for q,r in result['answer']['questions'].items()},
            'baseline_full_answer_unchanged':True,'native_calls':0}


def controls():
    selection=read(HERE/'selection.json');base=loadgz(PRIOR/'source-product.json.gz');out=[]
    for case in ('changed_selection_pin','wrong_product','missing_page_file','wrong_render','duplicate_page','false_independence'):
        bad=deepcopy(selection);pin=digest(bad)
        if case=='changed_selection_pin':bad['reason']+='changed'
        elif case=='wrong_product':bad['source_product_sha256']='0'*64;pin=digest(bad)
        elif case=='missing_page_file':bad['pages'][0]['path']='missing-native.json.gz';pin=digest(bad)
        elif case=='wrong_render':bad['pages'][0]['render_sha256']='0'*64;pin=digest(bad)
        elif case=='duplicate_page':bad['pages'].append(deepcopy(bad['pages'][0]));pin=digest(bad)
        else:bad['independent_legal_acceptance']=True;pin=digest(bad)
        try:choice.select_pages(base,bad,ROOT,expected_selection_sha256=pin)
        except ValueError as error:out.append({'case':case,'refused':True,'reason':str(error)})
        else:raise AssertionError('Invalid selection accepted: '+case)
    document=base['payload']['graph']['documents'][0]
    original=loadgz(SOURCE/'riyad-page-5-native-reviewed.json.gz')
    for case in ('removed_word','duplicate_word','bad_block','wrong_text','omitted_line','wrong_page','bad_geometry'):
        bad=deepcopy(original)
        if case=='removed_word':bad['words'].pop()
        elif case=='duplicate_word':bad['words'].append(deepcopy(bad['words'][-1]))
        elif case=='bad_block':bad['words'][-1][5]=14
        elif case=='wrong_text':bad['words'][0][4]='wrong'
        elif case=='omitted_line':bad['native_dict']['blocks'][0]['lines'].pop()
        elif case=='wrong_page':bad['page']=True
        else:bad['words'][0][0]=-1
        try:choice.page_units(bad,document,evidence_sha256=digest(bad),image_sha256='0'*64)
        except ValueError as error:out.append({'case':case,'refused':True,'reason':str(error)})
        else:raise AssertionError('Invalid observation accepted: '+case)
    products=loadgz(HERE/'selected-products.json.gz');products['P1']['payload']['graph']['units'][0]['raw']+='tamper'
    try:choice.consume_selected(products,base,selection,ROOT,expected_selection_sha256=digest(selection))
    except ValueError as error:out.append({'case':'changed_selected_product','refused':True,'reason':str(error)})
    else:raise AssertionError('Changed selected product accepted')
    save('actual-controls.json',out)
    return {'controls':len(out),'refused':len(out)}


def compare():
    base=loadgz(PRIOR/'source-product.json.gz');selected=loadgz(HERE/'selected-source.json.gz')
    old=base['payload']['graph'];new=selected['payload']['graph']
    assert [u for u in old['units'] if u['page'] not in PAGES]==[u for u in new['units'] if u['page'] not in PAGES]
    accounting=[]
    for page in PAGES:
        observed=loadgz(SOURCE/f'riyad-page-{page}-native-reviewed.json.gz')
        units=[u for u in new['units'] if u['page']==page]
        assert '\n'.join(u['raw'] for u in units)+'\n'==observed['text']
        assert sum(len(u['words']) for u in units)==len(observed['words'])
        assert all(u['raw'][w['start']:w['end']]==w['text'] for u in units for w in u['words'])
        accounting.append({'page':page,'lines':len(units),'words':len(observed['words']),
                           'complete_observed_text_preserved':True})
    result=loadgz(HERE/'selected-consumer.json.gz');answer=result['answer']
    baseline=loadgz(HERE/'baseline-reconsumed.json.gz')
    assert answer['source_map']==new
    urls=[]
    for literal in URLS:
        selected_hits=[{'unit':u['id'],'start':u['raw'].index(literal),'end':u['raw'].index(literal)+len(literal)}
                       for u in answer['source_map']['units'] if u['page']==6 and literal in u['raw']]
        old_hits=[u['id'] for u in old['units'] if u['page']==6 and literal in u['raw']]
        assert len(selected_hits)==1 and not old_hits
        urls.append({'literal':literal,'baseline_exact':0,'selected_exact':selected_hits})
    assert {q:r['status'] for q,r in answer['questions'].items()}=={q:r['status'] for q,r in baseline['questions'].items()}
    assert all(not r['witnesses'] for r in answer['questions'].values())
    assert not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
    for q in ('Q4','Q5','Q6'):assert answer['questions'][q]==baseline['questions'][q]
    unresolved_changes=[]
    def compare_questions(left,right,path):
        assert type(left) is type(right),path
        if isinstance(left,dict):
            assert left.keys()==right.keys(),path
            for key in left:
                if key=='unresolved':
                    assert isinstance(left[key],list) and isinstance(right[key],list),path
                    assert all(isinstance(v,str) for v in left[key]+right[key]),path
                    unresolved_changes.append({'path':path+'/'+key,'selected':left[key],'baseline':right[key]})
                else:compare_questions(left[key],right[key],path+'/'+key)
        elif isinstance(left,list):
            assert len(left)==len(right),path
            for i,(a,b) in enumerate(zip(left,right)):compare_questions(a,b,path+'/'+str(i))
        else:assert left==right,path
    for q in ('Q1','Q2','Q3'):
        compare_questions(answer['questions'][q],baseline['questions'][q],q)
    references=choice._references(new['units']);assert references==new['references']
    assert all(r['unit'] in {u['id'] for u in new['units']} for r in references)
    changed=[k for k in set(answer)|set(baseline) if answer.get(k)!=baseline.get(k)]
    allowed={'source_graph_sha256','questions','consumed_products','source_map','assembly',
             'clause_graph','dependencies','report_sha256','native_text_gaps'}
    assert set(changed)<=allowed
    save('complete-answer-differences.json',{'changed_top_level_fields':changed,
         'unresolved_ids':unresolved_changes,
         'full_comparators':['baseline-reconsumed.json.gz','selected-consumer.json.gz'],
         'interpretation':'Source,assembly,parent hashes and unresolved source occurrence IDs change; legal outcomes remain unknown.'})
    save('page-accounting.json',accounting);save('literal-repair.json',urls)
    comparison={'status':'PASS','native_lines_preserved':sum(r['lines'] for r in accounting),
        'native_words_accounted':sum(r['words'] for r in accounting),'exact_urls_repaired':4,
        'unselected_pages_unchanged':195,'baseline_full_answer_unchanged':True,
        'selected_full_answer_retained':True,'no_supported_legal_conclusion_added':True,
        'changed_top_level_fields':changed,'actual_controls':len(read(HERE/'actual-controls.json')),
        'native_calls':0,'independent_legal_acceptance':False,'installed_optional_route_evaluated':False}
    save('comparison.json',comparison);return comparison


def main():
    stage=sys.argv[1];assert stage in {'prepare','tests','select','consume','controls','compare','compare-reviewed'}
    ad=bindings();folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,folder/'method.py');tick=time.monotonic()
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_native_text_choice',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds':'N/A deterministic','methods':methods()})
    def expire(s,f):raise TimeoutError('120-second native-text-choice stage bound')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        if stage!='prepare':assert methods()==read(HERE/'method-identities.json')
        details=compare() if stage=='compare-reviewed' else globals()[stage]();bindings()
        assert sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())<80*1024*1024
        result={'status':'PASS','details':details,'wall_seconds':time.monotonic()-tick}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':type(error).__name__+': '+str(error),
              'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/'+stage+'/result.json',result);print(json.dumps(result))


if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
