import sys
from pathlib import Path
from legalmath.canonical import canonical,loads
from legalmath.cli import main
from legalmath.translation import cli
from legalmath.translation.frontend import SharedGeneration,GenerationV2
from tests.catala.backend_support import JDK,TOOLCHAIN
from tests.catala.native.reference import task,f
from legalmath.catala.native.boundary import make_snapshot
from .test_frontend import provider
from .support import AT,fixture


def invoke(monkeypatch,capsys,*args):
    monkeypatch.setattr(sys,'argv',['legalmath',*map(str,args)]);main()
    return loads(capsys.readouterr().out.encode())


def test_generation_schema_has_no_untyped_objects():
    def visit(value):
        if isinstance(value,dict):
            if value.get('type')=='object': assert value.get('additionalProperties') is False
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(SharedGeneration.model_json_schema())
    visit(GenerationV2.model_json_schema())


def test_modular_cli_interpret_translate_build_execute(monkeypatch,capsys,tmp_path):
    t,g=fixture();p=provider(g);monkeypatch.setattr(cli,'provider',lambda _:p)
    file=tmp_path/'task.json';file.write_bytes(canonical(t));front=tmp_path/'front'
    state=invoke(monkeypatch,capsys,'rules','interpret','--task',file,'--out',front,'--allowance','fixture-only')
    model=front/state['models'][0]['path']
    for target in ('ruleir','catala'):
        translated=invoke(monkeypatch,capsys,'rules','translate','--model',model,'--target',target,'--out',tmp_path/(target+'.json'))
        assert translated['status']=='TRANSLATED'
    built=tmp_path/'build'
    invoke(monkeypatch,capsys,'rules','build','--model',model,'--target','ruleir','--out',built,'--jdk',JDK)
    from .support import snapshot
    sf=tmp_path/'snapshot.json';sf.write_bytes(canonical(snapshot(loads(model.read_bytes()),{'months':'6'})))
    result=invoke(monkeypatch,capsys,'rules','execute','--build',built,'--snapshot',sf,'--rule','selected.control','--valid-at',AT,'--known-at',AT,'--jdk',JDK)
    assert result['status']=='TRUE' and len(p.requests)==2
    batch=invoke(monkeypatch,capsys,'rules','execute','--build',built,'--snapshot',sf,'--all','--valid-at',AT,'--known-at',AT,'--jdk',JDK)
    assert batch['results']['selected.control']==result
    resources=invoke(monkeypatch,capsys,'rules','resources','--model',model,'--out',tmp_path/'resources.json')
    assert resources['supported'] and resources['route']=='scalar-compatibility'


def test_native_cli_defaults_to_shared_frontend(monkeypatch,capsys,tmp_path):
    t=task('cli','Control','At least six months.',[f('months','integer')],[f('result','boolean')])
    from legalmath.translation.native_compat import task as shared_task
    shared=shared_task(t);_,g=fixture();r=g['readings'][0]
    r['formalization'].update(facts=shared['facts'],types=shared['types'])
    r['citations']=[{'unit_id':'clause.one','quote':'At least six months.'}]
    g['coverage']=[{'unit_id':'clause.one','status':'INTERPRETED','reason':'Compiler fixture'}]
    for d in g['dimensions']:d['source_unit_ids']=['clause.one']
    p=provider(g);monkeypatch.setattr(cli,'provider',lambda _:p)
    file=tmp_path/'task.json';file.write_bytes(canonical(t));out=tmp_path/'converted'
    args=['catala-convert','generate','--task',file,'--out',out,'--allowance','fixture-only','--jdk',JDK]
    for key,value in TOOLCHAIN.items():args.extend(['--'+key,value])
    converted=invoke(monkeypatch,capsys,*args)
    assert converted['status']=='READY_FOR_BEHAVIOR_CHECK' and len(p.requests)==2
    built=out/converted['build_directory'];sf=tmp_path/'snapshot.json';s=make_snapshot(t,{'months':'6'});sf.write_bytes(canonical(s))
    result=invoke(monkeypatch,capsys,'catala-convert','execute','--build',built,'--snapshot',sf,'--jdk',JDK)
    assert result['status']=='TRUE'
    cf=tmp_path/'cases.json';cf.write_bytes(canonical([{'id':'threshold','snapshot':s,'expected':{'status':'VALUE','value':{'result':True}}}]))
    checked=invoke(monkeypatch,capsys,'catala-convert','verify','--build',built,'--cases',cf,'--out',tmp_path/'checked.json','--jdk',JDK,'--compiler',TOOLCHAIN['compiler'])
    assert checked['records'][0]['checks']['original_ruleir_trace_match']


def test_native_multi_output_cli_uses_v2_and_checks_every_output(monkeypatch,capsys,tmp_path):
    from legalmath.translation.native_compat import task as shared_task
    from tests.catala.native.reference import q
    text='When active, halve cash exactly; independently round the ratio in minor units with ties away from zero.'
    native=task('multiple','Control',text,[f('cash','money'),f('ratio','decimal'),f('active','boolean')],
                [f('halfCash','money'),f('roundedCash','money')])
    shared=shared_task(native);assert shared['version']=='2'
    _,g=fixture();r=g['readings'][0]
    r.update(local_id='multiple',family='scope',subject='Synthetic cash calculation',
             distinction='Separate scoped exact and unscoped rounded outputs',
             statement=text,citations=[{'unit_id':'clause.one','quote':text}])
    r['formalization']={'version':'2','facts':shared['facts'],'types':shared['types'],'helpers':[],
        'outputs':[{'id':'halfCash','result_type':'money_hkd','scope':'active','result':'(scale cash 1 2)'},
                   {'id':'roundedCash','result_type':'money_hkd','scope':'true','result':'(round money_hkd nearest_away ratio)'}]}
    g['coverage']=[{'unit_id':'clause.one','status':'INTERPRETED','reason':'Synthetic compiler control'}]
    for d in g['dimensions']:d['source_unit_ids']=['clause.one']
    p=provider(g);monkeypatch.setattr(cli,'provider',lambda _:p)
    file=tmp_path/'task.json';file.write_bytes(canonical(native));out=tmp_path/'converted'
    args=['catala-convert','generate','--task',file,'--out',out,'--allowance','fixture-only','--jdk',JDK]
    for key,value in TOOLCHAIN.items():args.extend(['--'+key,value])
    converted=invoke(monkeypatch,capsys,*args)
    assert converted['status']=='READY_FOR_BEHAVIOR_CHECK' and len(p.requests)==2
    built=out/converted['build_directory'];sf=tmp_path/'snapshot.json'
    s=make_snapshot(native,{'cash':'100','ratio':q(3,2),'active':True});sf.write_bytes(canonical(s))
    result=invoke(monkeypatch,capsys,'catala-convert','execute','--build',built,'--snapshot',sf,'--jdk',JDK)
    assert result['value']=={'halfCash':'50','roundedCash':'2'}
    cases=[{'id':'values','snapshot':s,'expected':{'status':'VALUE','value':{'halfCash':'50','roundedCash':'2'}}}]
    s2=make_snapshot(native,{'cash':'101','ratio':q(3,2),'active':False});sf.write_bytes(canonical(s2))
    result=invoke(monkeypatch,capsys,'catala-convert','execute','--build',built,'--snapshot',sf,'--jdk',JDK,'--rule','halfCash')
    assert result['status']=='OUT_OF_SCOPE'
    cases.append({'id':'scoped','snapshot':s2,'expected':{'status':'PARTIAL_RESULTS','value':None,'results':{
        'halfCash':{'status':'OUT_OF_SCOPE','value':None},'roundedCash':{'status':'VALUE','value':'2'}}}})
    s3=make_snapshot(native,{'cash':'100','ratio':q(3,2),'active':True})
    s3['facts']['cash']={'status':'unknown','reason':'MISSING'}
    cases.append({'id':'missing','snapshot':s3,'expected':{'status':'ABSTAIN','reason':'INCOMPLETE_INPUTS','value':None,
        'results':{name:{'status':'ABSTAIN','reason':'INCOMPLETE_INPUTS','value':None} for name in ('halfCash','roundedCash')}}})
    cf=tmp_path/'cases.json';cf.write_bytes(canonical(cases))
    checked=invoke(monkeypatch,capsys,'catala-convert','verify','--build',built,'--cases',cf,'--out',tmp_path/'checks.json',
                   '--jdk',JDK,'--compiler',TOOLCHAIN['compiler'])
    assert checked['passed']==3
    assert all(c['interpreter']['exact_match'] for row in checked['records'][:2] for c in row['checks'].values())
