from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_successor_regression as regression
from run_assurance_successor import read,save,sha


@pytest.fixture
def receipt(tmp_path,monkeypatch):
    out=tmp_path/'out';directory=out/'regression-preflight';directory.mkdir(parents=True)
    source=tmp_path/'source.py';source.write_text('version = 1\n')
    xml=directory/'full.xml';xml.write_text('<testsuite tests="1029" failures="0" errors="0" skipped="0"/>')
    value={'status':'FULL_CURRENT_REGRESSION_PASSED','material_inputs':{'source.py':sha(source)},
        'counts':{'tests':1029,'failures':0,'errors':0,'skipped':0},
        'files':{'xml':{'path':str(xml.relative_to(tmp_path)),'sha256':sha(xml)}}}
    save(directory/'result.json',value)
    monkeypatch.setattr(regression,'ROOT',tmp_path);monkeypatch.setattr(regression,'OUT',out)
    monkeypatch.setattr(regression,'rel',lambda p:str(Path(p).relative_to(tmp_path)))
    monkeypatch.setattr(regression,'material_hashes',lambda:{'source.py':sha(source)})
    return directory,source,xml,value


def test_full_receipt_reuse_requires_current_material_identity(receipt):
    directory,source,xml,value=receipt
    assert regression.current_receipt()['counts']==value['counts']
    source.write_text('version = 2\n');assert regression.current_receipt() is None


@pytest.mark.parametrize('change',['tamper','skip','too_few','failed'])
def test_invalid_regression_cannot_replace_final_execution(receipt,change):
    directory,source,xml,value=receipt
    if change=='tamper':xml.write_text('<testsuite tests="1029"/>')
    elif change=='failed':value['status']='FAILED'
    else:
        value['counts']['skipped']=1 if change=='skip' else 0
        value['counts']['tests']=1028 if change=='too_few' else 1029
        xml.write_text('<testsuite '+' '.join(f'{k}="{v}"' for k,v in value['counts'].items())+'/>')
        value['files']['xml']['sha256']=sha(xml)
    save(directory/'result.json',value)
    assert regression.current_receipt() is None
