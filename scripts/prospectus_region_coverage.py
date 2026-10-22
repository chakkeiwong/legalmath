"""Bounded source-region experiment with retained products and original renders."""
from copy import deepcopy
import argparse
import gzip
import json
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import read,write,file_hash
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.region_coverage import VERSION,evaluate_regions,consume_with_region_coverage

BASE=ROOT/'docs/implementation/prospectus-execution-authority/attempts/page-coverage'
OLD=BASE/'attempt-002';HERE=BASE/'attempt-003'
PLAN='docs/plans/prospectus-declared-region-coverage-2026-10-15.md'
METHODS=['src/legalmath/prospectus/region_coverage.py','tests/prospectus/test_region_coverage.py',
         'scripts/prospectus_region_coverage.py']


def load(path):
    return json.load(gzip.open(path)) if str(path).endswith('.gz') else read(path)


def save(name,value):
    if name.endswith('.gz'):
        with (HERE/name).open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream:
                stream.write(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())
    else:write(HERE/name,value,exclusive=True)


def bindings():
    changed=[p for p,h in read(HERE/'admission.json')['binding'].items() if file_hash(ROOT/p)!=h]
    if changed:raise ValueError('Admitted input changed: '+repr(changed))


def inventory(graph,identity,regions):
    image=next(p for p in read(OLD/'selected-images.json')['pages'] if p['source']['id']==identity)
    source=image['source']
    return {'version':VERSION,'source_graph_sha256':digest(graph),'scope':'DECLARED_REGIONS_ONLY',
        'reviewer':{'identity':'Codex exposed source review2026-10-15',
                    'basis':'AGENT_EXPOSED_DEVELOPMENT_REVIEW','independent':False},
        'pages':[{'document':identity,'source_path':source['path'],'source_sha256':source['sha256'],
            'page':image['page'],'display_rect':image['display_rect'],
            'render_path':str((OLD/image['image']).relative_to(ROOT)),
            'render_sha256':image['image_sha256'],'regions':regions}]}


def prepare():
    p1=load(OLD/'source-019-P1.json.gz')
    boxes=[[78,112,734,180],[78,200,734,268],[78,286,735,355],[78,372,735,442]]
    regions=[{'id':name,'bbox':box,'kind':'table','reason':reason,'reading':None}
        for name,box,reason in zip(['default-upper','default-lower','prepayment-upper','prepayment-lower'],boxes,
        ['First visible Time to Default cohort table; header,years,quarter columns and cells require transcription.',
         'Second visible Time to Default cohort table; separate category and table must not be omitted.',
         'First visible Prepayment Rates cohort table; values and unfilled cells are untranscribed.',
         'Second visible Prepayment Rates cohort table; grey cells are not interpreted as zero.'])]
    hypo=inventory(p1['payload']['graph'],'source-019',regions)
    heta=load(OLD/'source-017-products.json.gz')
    reading=read(OLD/'heta-corrected-reading.json')['reading']
    matched=inventory(heta['P1']['payload']['graph'],'source-017',[{'id':reading['id'],
         'bbox':reading['bbox'],'kind':'paragraph','reason':'Full English maturity paragraph including edict and not-due qualification.',
         'reading':reading['text']}])
    save('hypo-inventory.json',hypo);save('heta-inventory.json',matched)
    save('inventory-pins.json',{'hypo':digest(hypo),'heta':digest(matched)})
    save('method-identities.json',{p:file_hash(ROOT/p) for p in METHODS})
    for p in METHODS:
        target=HERE/'method'/p;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write((ROOT/p).read_bytes())
    return {'required_table_regions':4,'positive_paragraphs':1,'new_native_starts':0}


def tests():
    import pytest
    code=pytest.main(['-q','tests/prospectus/test_region_coverage.py','--junitxml='+str(HERE/'tests.xml')])
    if code:raise ValueError('Region tests failed: '+str(code))
    return {'pytest_exit':int(code)}


def construct():
    from legalmath.prospectus.successor import service
    p1=load(OLD/'source-019-P1.json.gz')
    p2=service.construction_product(p1,ROOT)
    save('hypo-P2.json.gz',p2)
    return {'P1':p1['sha256'],'P2':p2['sha256'],'fresh_extraction':False}


def finish():
    from legalmath.prospectus.successor import service
    p1=load(OLD/'source-019-P1.json.gz');p2=load(HERE/'hypo-P2.json.gz')
    p3=service.interpretation_product(p1,p2)
    products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),
              'P5':service.financial_product(p1,p2,p3)}
    answer=service.consume(products,ROOT,include_artifacts=True)
    save('hypo-products.json.gz',products);save('hypo-baseline-answer.json.gz',answer)
    return {'consumed_products':answer['consumed_products'],
            'questions':{k:v['status'] for k,v in answer['questions'].items()},'fresh_extraction':False}


def compare():
    from legalmath.prospectus.successor import service
    pins=read(HERE/'inventory-pins.json');checks={}
    for name,products in [('hypo',load(HERE/'hypo-products.json.gz')),('heta',load(OLD/'source-017-products.json.gz'))]:
        before=digest(products);inv=read(HERE/(name+'-inventory.json'))
        baseline=(load(HERE/'hypo-baseline-answer.json.gz') if name=='hypo' else service.consume(products,ROOT,include_artifacts=True))
        if name=='heta':save('heta-baseline-answer.json.gz',baseline)
        output=consume_with_region_coverage(products,inv,ROOT,expected_inventory_sha256=pins[name])
        save(name+'-consumer.json.gz',output)
        coverage=output['region_coverage'];rows=coverage['regions']
        save(name+'-coverage.json',coverage)
        checks[name+'_full_answer_unchanged']=output['answer']==baseline
        checks[name+'_products_unchanged']=digest(products)==before
        checks[name+'_no_completeness_claim']=not any(coverage[k] for k in ('page_complete','document_complete','may_claim_coverage','independent_legal_acceptance','legal_scope_inferred','raw_replaced'))
        if name=='hypo':
            checks['four_missing_tables']=len(rows)==4 and all(r['status']=='REQUIRED_CONTENT_UNAVAILABLE' and not r['retained_word_anchors'] for r in rows)
            checks['positive_text_does_not_hide_regions']=all(r['native_page_nonspace_characters']==3 for r in rows)
        else:
            checks['whole_heta_paragraph_matched']=len(rows)==1 and rows[0]['status']=='MATCHED_DECLARED_TEXT'
            actual=rows[0]['projection']['mappings'][0]['text'] if rows[0]['projection']['mappings'] else ''
            checks['heta_qualifications_preserved']=''.join(actual.split())==''.join(inv['pages'][0]['regions'][0]['reading'].split())
    report={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'native_starts':0,'fresh_extraction':False}
    save('comparison.json',report)
    if not all(checks.values()):raise ValueError('Source-region comparison failed')
    return report


def controls():
    products=load(OLD/'source-017-products.json.gz');graph=products['P1']['payload']['graph']
    original=read(HERE/'heta-inventory.json');pin=read(HERE/'inventory-pins.json')['heta'];results=[]
    for name in ('missing','duplicate','foreign_page','changed_render','independence','omitted_negation','omitted_qualifier','partial_word'):
        inv=deepcopy(original);region=inv['pages'][0]['regions'][0];usepin=pin
        if name=='missing':inv['pages'][0]['regions']=[]
        elif name=='duplicate':inv['pages'][0]['regions'].append(deepcopy(region))
        elif name=='foreign_page':inv['pages'][0]['page']=2;usepin=digest(inv)
        elif name=='changed_render':inv['pages'][0]['render_sha256']='0'*64;usepin=digest(inv)
        elif name=='independence':inv['reviewer']['independent']=True;usepin=digest(inv)
        elif name=='omitted_negation':region['reading']=region['reading'].replace('not become due','become due');usepin=digest(inv)
        elif name=='omitted_qualifier':region['reading']=region['reading'].replace('The published edict includes details on the affected debt instruments and other eligi- ble liabilities. ','');usepin=digest(inv)
        else:region['bbox'][0]=418;usepin=digest(inv)
        try:
            result=evaluate_regions(graph,inv,ROOT,expected_inventory_sha256=usepin)
            statuses=[r['status'] for r in result['regions']]
            safe=not result['declared_readings_matched'] and not result['may_claim_coverage']
            results.append({'case':name,'safely_unresolved_or_refused':safe,'statuses':statuses})
        except ValueError as error:results.append({'case':name,'safely_unresolved_or_refused':True,'refusal':str(error)})
    save('actual-controls.json',results)
    assert all(r['safely_unresolved_or_refused'] for r in results)
    return {'controls':len(results),'all_safely_unresolved_or_refused':True}


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','tests','construct','finish','compare','controls']);args=p.parse_args()
    def expired(signum,frame):raise TimeoutError('120-second stage bound;no automatic retry')
    signal.signal(signal.SIGALRM,expired);signal.alarm(120)
    if (HERE/'outputs.json').exists():raise ValueError('Attempt sealed')
    bindings();folder=HERE/'invocations'/args.stage;folder.mkdir(parents=True,exist_ok=False)
    write(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_region_coverage',args.stage],
        'environment':sys.executable,'plan':PLAN,'cpu_gpu':'CPU-only;no GPU framework imported',
        'git_commit':read(HERE/'admission.json')['git_commit']},exclusive=True)
    start=time.monotonic()
    try:result={'status':'PASS','stage':args.stage,'result':globals()[args.stage]()}
    except BaseException as error:
        result={'status':'FAIL','stage':args.stage,'error':repr(error)};raise
    finally:
        result['wall_seconds']=time.monotonic()-start
        write(folder/'result.json',result,exclusive=True);signal.alarm(0)
    print(json.dumps(result))


if __name__=='__main__':main()
