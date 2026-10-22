"""Run with installed Python -I; never inject the checkout into sys.path."""
from copy import deepcopy
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

from legalmath.prospectus import geometry_transfer,relation_review,relation_boundaries,region_coverage,native_text_choice
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE=Path(sys.argv[1]).resolve();ROOT=Path(sys.argv[2]).resolve();STAGE=sys.argv[3]
ATTEMPTS=ROOT/'docs/implementation/prospectus-execution-authority/attempts'
TARGET=HERE/'installed-results'/STAGE;TARGET.mkdir(parents=True,exist_ok=False)
ENV=Path(sys.executable).parent.parent.resolve()
MODULES=[geometry_transfer,relation_review,relation_boundaries,region_coverage,native_text_choice,service]


def read(path):
    return json.loads(gzip.decompress(Path(path).read_bytes())) if str(path).endswith('.gz') else json.loads(Path(path).read_text())
def save(name,value):
    with (TARGET/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def gzsave(name,value):
    with (TARGET/name).open('xb') as f:f.write(gzip.compress(json.dumps(value,ensure_ascii=False).encode(),mtime=0))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


proof={'python':sys.executable,'prefix':sys.prefix,'isolated':sys.flags.isolated,'sys_path':sys.path,
       'modules':{m.__name__:{'path':m.__file__,'sha256':sha(m.__file__)} for m in MODULES},
       'dependencies':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
assert sys.flags.isolated and Path(sys.prefix).resolve()==ENV
assert all(Path(m.__file__).resolve().is_relative_to(ENV) for m in MODULES)
assert all(not Path(p).resolve().is_relative_to(ROOT/'src') for p in sys.path if p)
save('import-proof.json',proof)
def no_native(*args,**kwargs):raise AssertionError('Native/subprocess start forbidden in installed frozen consumers')
subprocess.Popen=no_native


def refuses(name,fn):
    try:fn()
    except ValueError as error:return {'case':name,'refused':True,'reason':str(error)}
    raise AssertionError('Expected refusal: '+name)


def geometry():
    old=ATTEMPTS/'native-candidates/attempt-002';ref=ATTEMPTS/'native-candidates/attempt-006'
    a=old/'workers/unpatched-enabled.json';b=old/'workers/patched.json'
    result=geometry_transfer.transfer_files(a,b,TARGET/'transferred-worker.json',
        original_sha256=sha(a),candidate_sha256=sha(b),policy=geometry_transfer.POLICY)
    actual=read(TARGET/'transferred-worker.json');assert actual==read(ref/'workers/patched.json')
    assert result['words']==1311 and result['changed_rectangles']==8
    answers=[]
    for arm in ('unpatched-enabled','patched'):
        folder=ref/'consumers'/arm;products={p:read(folder/(p+'.json.gz')) for p in ('P1','P2','P3','P4','P5')}
        out=service.consume(products,ROOT,include_artifacts=True);expected=read(folder/'answer.json.gz')
        normalized=deepcopy(out);normalized['assessment_mode']=expected['assessment_mode']
        normalized['report_sha256']=digest({k:v for k,v in normalized.items() if k!='report_sha256'})
        assert normalized==expected
        gzsave(arm+'-answer.json.gz',out)
        answers.append({'arm':arm,'full_equal_after_mode_normalization':True,'actual_mode':out['assessment_mode'],
                        'expected_mode':expected['assessment_mode']})
    base=read(a);candidate=read(b);controls=[]
    for case in ('word','source'):
        bad=deepcopy(candidate)
        if case=='word':bad['pages'][0]['words'][0][4]+='x'
        else:bad['source_sha256']='0'*64
        controls.append(refuses(case,lambda:geometry_transfer.transfer(base,bad,original_sha256=digest(base),
            candidate_sha256=digest(bad),policy=geometry_transfer.POLICY)))
    save('controls.json',controls)
    return {'worker_exact':True,'words':1311,'changed_rectangles':8,'answers':answers,'controls':2}


def review():
    base=ATTEMPTS/'relation-discovery';products=read(base/'attempt-002/v2-products.json.gz')
    discovery=read(base/'attempt-002/v2-answer.json.gz')['relation_candidates']
    targets=read(base/'attempt-001/protected-targets.json')['bes'];packet=read(base/'attempt-003/review-ledger.json')
    graph=products['P1']['payload']['graph']
    out=relation_review.validate_review_packet(graph,discovery,targets,packet,ROOT)
    assert out==read(base/'attempt-003/validated-packet.json')
    answer=service.consume(products,ROOT,include_artifacts=True)
    assert answer==read(base/'attempt-003/reconsumed-answer.json.gz')
    save('validated-packet.json',out);gzsave('answer.json.gz',answer)
    bad=deepcopy(packet);bad['reviews'].pop()
    controls=[refuses('missing_review',lambda:relation_review.validate_review_packet(graph,discovery,targets,bad,ROOT))]
    badgraph=deepcopy(graph);badgraph['units'][0]['raw']+='x'
    controls.append(refuses('changed_source',lambda:relation_review.validate_review_packet(badgraph,discovery,targets,packet,ROOT)))
    save('controls.json',controls)
    return {'candidate_count':out['candidate_count'],'full_packet_and_answer_equal':True,'controls':2}


def boundaries():
    base=ATTEMPTS/'relation-discovery';products=read(base/'attempt-002/v2-products.json.gz')
    out=relation_boundaries.consume_with_suggestions(products,ROOT)
    assert out==read(base/'attempt-004/consumer.json.gz')
    gzsave('consumer.json.gz',out)
    bad=deepcopy(products);bad['P1']['payload']['graph']['units'][0]['bbox']=None
    controls=[refuses('changed_source_product',lambda:relation_boundaries.consume_with_suggestions(bad,ROOT))]
    assert out['suggestions']['accepted_relations']==[] and not out['relation_admission_performed']
    save('controls.json',controls)
    return {'full_consumer_equal':True,'lineages':len(out['suggestions']['lineage']),
            'bounded':sum(r['status']=='BOUNDED' for r in out['suggestions']['lineage']),
            'abstained':sum(r['status']=='ABSTAINED' for r in out['suggestions']['lineage']),'controls':1}


def regions():
    base=ATTEMPTS/'page-coverage';ref=base/'attempt-003';pins=read(ref/'inventory-pins.json');counts={}
    for name,path in (('hypo',ref/'hypo-products.json.gz'),('heta',base/'attempt-002/source-017-products.json.gz')):
        products=read(path);inv=read(ref/(name+'-inventory.json'))
        out=region_coverage.consume_with_region_coverage(products,inv,ROOT,expected_inventory_sha256=pins[name])
        assert out==read(ref/(name+'-consumer.json.gz'));gzsave(name+'-consumer.json.gz',out)
        counts[name]=[r['status'] for r in out['region_coverage']['regions']]
    bad=deepcopy(inv);bad['pages'][0]['render_sha256']='0'*64
    controls=[refuses('changed_render',lambda:region_coverage.evaluate_regions(products['P1']['payload']['graph'],bad,ROOT,expected_inventory_sha256=digest(bad)))]
    omitted=deepcopy(inv);omitted['pages'][0]['regions'][0]['reading']=omitted['pages'][0]['regions'][0]['reading'].replace('not become due','become due')
    verdict=region_coverage.evaluate_regions(products['P1']['payload']['graph'],omitted,ROOT,expected_inventory_sha256=digest(omitted))
    assert not verdict['declared_readings_matched'] and not verdict['may_claim_coverage']
    controls.append({'case':'omitted_negation','safely_unresolved':True});save('controls.json',controls)
    return {'full_consumers_equal':True,'regions':counts,'controls':2}


def native_text():
    base=ATTEMPTS/'native-layout-cases';ref=base/'attempt-004'
    baseline=read(base/'attempt-003/source-product.json.gz');selection=read(ref/'selection.json')
    selected=native_text_choice.select_pages(baseline,selection,ROOT,expected_selection_sha256=digest(selection))
    assert selected==read(ref/'selected-source.json.gz')
    p2=service.construction_product(selected,ROOT);p3=service.interpretation_product(selected,p2)
    products={'P1':selected,'P2':p2,'P3':p3,'P4':service.law_product(selected,p3),
              'P5':service.financial_product(selected,p2,p3)}
    assert products==read(ref/'selected-products.json.gz')
    out=native_text_choice.consume_selected(products,baseline,selection,ROOT,expected_selection_sha256=digest(selection))
    assert out==read(ref/'selected-consumer.json.gz')
    gzsave('products.json.gz',products);gzsave('consumer.json.gz',out)
    bad=deepcopy(selection);bad['pages'].append(deepcopy(bad['pages'][0]))
    controls=[refuses('duplicate_page',lambda:native_text_choice.select_pages(baseline,bad,ROOT,expected_selection_sha256=digest(bad)))]
    changed=deepcopy(products);changed['P1']['payload']['graph']['units'][0]['raw']+='tamper'
    controls.append(refuses('changed_product',lambda:native_text_choice.consume_selected(changed,baseline,selection,ROOT,expected_selection_sha256=digest(selection))))
    save('controls.json',controls)
    return {'full_source_products_consumer_equal':True,'controls':2}


def inventory():
    package=Path(service.__file__).resolve().parents[2]
    installed={str(p.relative_to(package)):sha(p) for p in package.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    expected=read(HERE/'source-package.json')
    assert installed==expected
    save('installed-package.json',installed)
    return {'installed_files':len(installed),'all_package_bytes_equal':True}


result=globals()[STAGE.replace('-','_')]()
save('result.json',{'status':'PASS','details':result,'native_calls':0})
print(json.dumps({'stage':STAGE,'status':'PASS','details':result}))
