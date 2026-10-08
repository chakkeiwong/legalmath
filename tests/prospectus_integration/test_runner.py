"""Recovery tests use isolated receipts; historical evidence is never mutated."""
import pytest
from scripts import prospectus_integration_repair as runner


def test_entrypoint_imports_preserve_environment_binding(monkeypatch):
    """Late imports must not make completed checks stale without changed bytes."""
    import importlib
    import runpy
    import sys
    from legalmath.prospectus.successor.adoption_jobs import bindings
    monkeypatch.setattr(sys, 'path', list(sys.path))
    # The CLI is loaded under __main__; jobs also imports it by module name.
    runpy.run_path(runner.__file__, run_name='integration_bootstrap')
    before = bindings(runner.ROOT, 'A0')
    importlib.reload(runner)
    from scripts import prospectus_inception
    importlib.reload(prospectus_inception)
    assert bindings(runner.ROOT, 'A0') == before


def receipt(tmp_path,monkeypatch,status='PASS'):
    monkeypatch.setattr(runner,'OUT',tmp_path)
    monkeypatch.setattr(runner,'methods',lambda phase:{'code':'original'})
    monkeypatch.setattr(runner,'inputs',lambda phase:{'input':'original'})
    folder=tmp_path/'layout-001';folder.mkdir()
    runner.save(folder/'result.json',{'status':status})
    row={'status':status,'method':runner.methods('layout'),'inputs':runner.inputs('layout'),
         'outputs':{'result.json':runner.sha(folder/'result.json')}}
    runner.save(folder/'manifest.json',row)
    return folder


def test_identical_receipt_reused(tmp_path,monkeypatch):
    folder=receipt(tmp_path,monkeypatch)
    assert runner.current('layout')==folder/'manifest.json'


def test_changed_inputs_require_fresh_attempt(tmp_path,monkeypatch):
    receipt(tmp_path,monkeypatch)
    monkeypatch.setattr(runner,'inputs',lambda phase:{'input':'new'})
    assert runner.current('layout') is None


def test_changed_method_requires_fresh_attempt(tmp_path,monkeypatch):
    receipt(tmp_path,monkeypatch)
    monkeypatch.setattr(runner,'methods',lambda phase:{'code':'new'})
    assert runner.current('layout') is None


@pytest.mark.parametrize('mutation',['changed','missing','added'])
def test_corrupted_receipt_vetoes_reuse(tmp_path,monkeypatch,mutation):
    folder=receipt(tmp_path,monkeypatch)
    if mutation=='changed':(folder/'result.json').write_text('{}')
    if mutation=='missing':(folder/'result.json').unlink()
    if mutation=='added':(folder/'unexpected').write_text('new evidence')
    with pytest.raises(ValueError,match='evidence'):runner.current('layout')


def test_interrupted_attempt_without_outputs_is_never_reused(tmp_path,monkeypatch):
    folder=receipt(tmp_path,monkeypatch,'RUNNING')
    runner.save(folder/'manifest.json',{'status':'RUNNING'})
    assert runner.current('layout') is None
