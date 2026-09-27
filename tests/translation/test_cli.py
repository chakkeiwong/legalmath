import sys
from pathlib import Path
from legalmath.canonical import canonical,loads
from legalmath.cli import main
from legalmath.translation import cli
from legalmath.translation.frontend import SharedGeneration
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
