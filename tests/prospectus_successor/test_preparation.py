from argparse import ArgumentParser
from copy import deepcopy
import json
import pytest
from scripts.prospectus_preparation_fixture import create
from legalmath.prospectus.successor import preparation as module, service
from legalmath.prospectus.successor.contracts import digest, read, write


def run(root,stage,pin,parents=None,out=None):
    return module.prepare(root,stage=stage,recipe_path='recipe.json',recipe_sha256=pin,
        output=out or stage,parents_path=None if parents is None else parents['manifest'],
        parents_sha256=None if parents is None else parents['manifest_sha256'])


def test_all_phases_equal_direct_functions_and_forward_later_inputs(tmp_path):
    _,pin,expected=create(tmp_path);parent=None;products={}
    for stage in module.STAGES:
        receipt=run(tmp_path,stage,pin,parent)
        products[stage]=read(tmp_path/stage/(stage+'.json'))
        assert products[stage]==expected[stage]
        assert receipt['source_reextracted'] == (stage=='P1')
        assert receipt['legal_acceptance'] is False
        parent=receipt
    assert products['P3']['payload']['interpretation_input']['scope']['Q1']['complete'] is False
    assert products['P4']['payload']['cases']==[{'id':'forwarded-law-case'}]
    assert products['P5']['payload']['cases']==[{'id':'forwarded-financial-case'}]
    assert service.consume(products,tmp_path)==service.consume(expected,tmp_path)


@pytest.mark.parametrize('kind',['recipe-hash','input-hash','source','extra-input','duplicate-json','input-size',
    'output-exists','output-absolute','output-escape','output-symlink','unknown-stage','unexpected-parent'])
def test_invalid_preparation_inputs_are_refused(tmp_path,monkeypatch,kind):
    recipe,pin,_=create(tmp_path);stage='P1';out='output';parents=None
    if kind=='recipe-hash':pin='0'*64
    elif kind=='input-hash':(tmp_path/'interpretation.json').write_text('{}')
    elif kind=='source':(tmp_path/'source.txt').write_text('Changed')
    elif kind=='extra-input':
        recipe['inputs']['extra']=recipe['inputs']['law'];write(tmp_path/'recipe.json',recipe);pin=digest((tmp_path/'recipe.json').read_bytes())
    elif kind=='duplicate-json':
        raw=b'{"version":1,"version":2}';(tmp_path/'recipe.json').write_bytes(raw);pin=digest(raw)
    elif kind=='input-size':monkeypatch.setattr(module,'INPUT_LIMIT',10)
    elif kind=='output-exists':(tmp_path/out).mkdir()
    elif kind=='output-absolute':out=str(tmp_path/out)
    elif kind=='output-escape':out='../escape'
    elif kind=='output-symlink':
        (tmp_path/'outside').symlink_to(tmp_path.parent,target_is_directory=True);out='outside/new'
    elif kind=='unknown-stage':stage='P6'
    else:parents={'manifest':'recipe.json','manifest_sha256':pin}
    with pytest.raises(ValueError):run(tmp_path,stage,pin,parents,out)


@pytest.mark.parametrize('kind',['missing','pin','recipe','stages','product-bytes','relinked-request','relinked-parent'])
def test_parent_recipe_sequence_and_seals_are_checked(tmp_path,kind):
    _,pin,_=create(tmp_path);p1=run(tmp_path,'P1',pin);p2=run(tmp_path,'P2',pin,p1)
    parent=deepcopy(p2);manifest=read(tmp_path/parent['manifest'])
    if kind=='missing':parent=None
    elif kind=='pin':parent['manifest_sha256']='0'*64
    elif kind in ('recipe','stages'):
        if kind=='recipe':manifest['recipe_sha256']='0'*64
        else:manifest['products'].pop('P2')
        write(tmp_path/parent['manifest'],manifest);parent['manifest_sha256']=digest((tmp_path/parent['manifest']).read_bytes())
    else:
        path=tmp_path/manifest['products']['P2' if kind=='relinked-parent' else 'P1']['path'];product=read(path)
        if kind=='product-bytes':path.write_text('{}')
        else:
            if kind=='relinked-request':product['payload']['request']['scope']={}
            else:product['inputs']['P1']='0'*64
            product['sha256']=digest({k:v for k,v in product.items() if k!='sha256'});write(path,product)
            manifest['products'][product['stage']]['sha256']=digest(path.read_bytes())
            write(tmp_path/parent['manifest'],manifest);parent['manifest_sha256']=digest((tmp_path/parent['manifest']).read_bytes())
    with pytest.raises(ValueError):run(tmp_path,'P3',pin,parent,'bad')


def test_actual_source_extraction_and_failed_stage_evidence(tmp_path,monkeypatch):
    _,pin,_=create(tmp_path)
    def fail(*args,**kwargs):raise ValueError('deliberate extraction failure')
    monkeypatch.setattr(service,'source_product',fail)
    with pytest.raises(ValueError,match='extraction failure'):run(tmp_path,'P1',pin)
    assert read(tmp_path/'P1/failure.json')['stage']=='P1'
    assert not (tmp_path/'P1/products.json').exists()


def test_prepare_parser_dispatch_and_legacy_commands(tmp_path):
    _,pin,expected=create(tmp_path);parser=ArgumentParser();service.configure(parser)
    args=parser.parse_args(['prepare','--stage','P1','--recipe','recipe.json','--recipe-sha256',pin,
        '--repository',str(tmp_path),'--output','prepared'])
    result=service.dispatch(args)
    assert result['status']=='PREPARED' and read(tmp_path/'prepared/P1.json')==expected['P1']
    assert parser.parse_args(['consume','--products','x','--output','y']).prospectus_command=='consume'
    assert parser.parse_args(['assess','--request','x','--output','y']).prospectus_command=='assess'
