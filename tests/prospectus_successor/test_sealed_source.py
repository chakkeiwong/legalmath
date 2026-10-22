import hashlib
import subprocess

import pytest
from legalmath.prospectus.successor import sealed_source as route, sealed_runtime as runtime
from legalmath.prospectus.successor import source_graph


def make_runtime(tmp_path):
    source = tmp_path / 'executable'
    source.write_bytes(b'explicit executable'); source.chmod(0o755)
    folder = tmp_path / 'snapshot'
    manifest = runtime.snapshot(folder, {'/case/program': source})
    return route.SourceRuntime(folder, runtime.digest(manifest)), manifest


def test_context_restores_and_rejects_nested_selection(tmp_path):
    value, _ = make_runtime(tmp_path)
    assert route.current() is None
    with pytest.raises(RuntimeError):
        with route.selected(value):
            assert route.current() is value
            with pytest.raises(ValueError, match='Nested'):
                with route.selected(value): pass
            raise RuntimeError('deliberate consumer failure')
    assert route.current() is None


@pytest.mark.parametrize('case', ['missing-input', 'wrong-source-hash', 'unbound-executable', 'changed-manifest', 'missing-blob'])
def test_incomplete_native_inputs_refuse_before_any_launch(tmp_path, monkeypatch, case):
    value, manifest = make_runtime(tmp_path)
    required = {'/case/program': manifest['files'][0]['sha256']}
    if case == 'missing-input': required['/case/missing.pdf'] = '0'*64
    if case == 'wrong-source-hash': required['/case/program'] = '0'*64
    if case == 'unbound-executable': required = {'/case/missing.pdf': '0'*64}
    if case == 'changed-manifest': value.manifest['directories'].append('/changed')
    if case == 'missing-blob': (value.folder/'blobs'/manifest['files'][0]['sha256']).unlink()
    def no_launch(*args, **kwargs): pytest.fail('A native command launched before validation')
    monkeypatch.setattr(subprocess, 'Popen', no_launch)
    with pytest.raises((ValueError, FileNotFoundError)):
        value.execute(['/case/program'], b'', required)


def test_unselected_native_text_keeps_original_command_and_metadata(tmp_path, monkeypatch):
    executable=tmp_path/'pdftotext';executable.write_bytes(b'known executable')
    source=tmp_path/'document.pdf';source.write_bytes(b'known source')
    xml=b'<html xmlns="http://www.w3.org/1999/xhtml"><page width="1" height="1"/></html>'
    commands=[]
    def run(argv, **kwargs):
        commands.append((argv,kwargs));return subprocess.CompletedProcess(argv,0,xml,b'')
    monkeypatch.setattr(source_graph.subprocess, 'run', run)
    monkeypatch.setattr(source_graph.shutil, 'which', lambda name:str(executable))
    units,count,metadata=source_graph.pdf_units(source, {'id':'source','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'language':'en'})
    assert commands==[(['pdftotext','-bbox-layout','-enc','UTF-8',str(source),'-'],{'capture_output':True,'timeout':90,'check':True})]
    assert count==1 and len(units)==1 and 'sealed_execution' not in metadata


def test_selection_refuses_unbound_executable_without_default_fallback(tmp_path, monkeypatch):
    from pathlib import Path
    value,_=make_runtime(tmp_path)
    source=tmp_path/'document.pdf';source.write_bytes(b'known source')
    executable=Path('/usr/bin/true')
    monkeypatch.setattr(source_graph.shutil,'which',lambda name:str(executable))
    def fallback(*args,**kwargs):pytest.fail('Selected runtime fell back to host subprocess')
    monkeypatch.setattr(source_graph.subprocess,'run',fallback)
    with route.selected(value),pytest.raises(ValueError,match='Required native input'):
        source_graph.pdf_units(source,{'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})


def test_reserved_input_path_refuses_before_launch(tmp_path, monkeypatch):
    value,_=make_runtime(tmp_path)
    def no_launch(*args,**kwargs):pytest.fail('Reserved input launched a native process')
    monkeypatch.setattr(subprocess,'Popen',no_launch)
    with pytest.raises(ValueError,match='reserved snapshot'):
        value.execute(['/case/program'],b'',{'/tmp/reserved.pdf':'0'*64})


@pytest.mark.parametrize('cap',[0,-1,True,64*1024*1024+1,'large'])
def test_explicit_native_text_capacity_refuses_invalid_bounds(tmp_path,cap):
    value,manifest=make_runtime(tmp_path)
    with pytest.raises(ValueError,match='stream bound'):
        route.SourceRuntime(value.folder,runtime.digest(manifest),native_text_max_stream=cap)
