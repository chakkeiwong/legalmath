"""Installed profile API lifecycle refusals without native process launches."""
from copy import deepcopy
import os
from pathlib import Path

import pytest

from legalmath.prospectus import native_profile as profile
from legalmath.prospectus.successor import sealed_runtime, service
from legalmath.prospectus.successor.contracts import VERSION, digest


def captured(tmp_path):
    original = tmp_path / 'original'
    original.write_bytes(b'worker')
    original.chmod(0o755)
    out = tmp_path / 'profile'
    out.mkdir()
    result = profile.capture({'repository': str(tmp_path), 'sources': {'/worker': str(original)},
        'directories': [], 'ocr_python': '/worker', 'native_text_max_stream': 64*1024*1024}, out)
    return out, result['profile_sha256']


def test_profile_capture_and_currentness(tmp_path):
    folder, pin = captured(tmp_path)
    value, manifest = profile.load_profile(folder, pin)
    assert value['native_reuse_allowed'] is False
    assert manifest['files'][0]['sha256'] == digest(b'worker')


@pytest.mark.parametrize('mutation', ['pin', 'profile', 'manifest', 'blob', 'missing', 'method', 'runtime'])
def test_changed_profile_or_snapshot_refuses_before_launch(tmp_path, monkeypatch, mutation):
    folder, pin = captured(tmp_path)
    value = profile.read(folder / 'profile.json')
    if mutation == 'pin':
        pin = '0'*64
    elif mutation == 'profile':
        value['native_reuse_allowed'] = True
        (folder / 'profile.json').write_text(__import__('json').dumps(value))
    elif mutation == 'manifest':
        path = folder / 'snapshot/manifest.json'
        manifest = profile.read(path)
        manifest['directories'].append('/changed')
        path.write_text(__import__('json').dumps(manifest))
    elif mutation in ('blob','missing'):
        blob = folder / 'snapshot/blobs' / digest(b'worker')
        if mutation == 'missing':
            blob.unlink()
        else:
            blob.write_bytes(b'change')
    elif mutation == 'method':
        monkeypatch.setattr(profile, 'methods', lambda: {'changed': '0'*64})
    else:
        monkeypatch.setattr(sealed_runtime, 'trusted_runtime', lambda: {'changed': True})
    with pytest.raises((ValueError, FileNotFoundError)):
        profile.load_profile(folder, pin)


def test_capture_rejects_implicit_interpreter(tmp_path):
    with pytest.raises(ValueError, match='explicitly captured'):
        profile.capture({'repository': str(tmp_path), 'sources': {}, 'directories': [],
            'ocr_python': '/unknown', 'native_text_max_stream': 4096}, tmp_path / 'capture')


def test_cpu_environment_restores_after_error(monkeypatch):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', 'old')
    monkeypatch.delenv('LEGALMATH_OCR_PYTHON', raising=False)
    with pytest.raises(RuntimeError):
        with profile.cpu_environment('/worker'):
            assert os.environ['CUDA_VISIBLE_DEVICES'] == '-1'
            assert os.environ['LEGALMATH_OCR_PYTHON'] == '/worker'
            raise RuntimeError('controlled')
    assert os.environ['CUDA_VISIBLE_DEVICES'] == 'old'
    assert 'LEGALMATH_OCR_PYTHON' not in os.environ


def test_stage_does_not_repeat_failed_work(tmp_path):
    job = tmp_path / 'job'
    calls = []
    def fail():
        calls.append(1)
        raise ValueError('Controlled stage failure')
    with pytest.raises(ValueError, match='Controlled'):
        profile.stage(job, 'source', fail, new=True)
    assert profile.read(job / 'stages/source/result.json')['status'] == 'FAIL'
    with pytest.raises(FileExistsError):
        profile.stage(job, 'source', fail, new=True)
    assert calls == [1]
    with pytest.raises(ValueError, match='did not pass'):
        profile.checked_stage(job, 'source')


def test_stage_predecessor_hashes_are_checked(tmp_path):
    job = tmp_path / 'job'
    def produce():
        (job / 'output').write_bytes(b'original')
        return ['output']
    profile.stage(job, 'source', produce, new=True)
    profile.checked_stage(job, 'source')
    (job / 'output').write_bytes(b'changed')
    with pytest.raises(ValueError, match='Predecessor file changed'):
        profile.checked_stage(job, 'source')


def test_stage_refuses_absent_predecessor(tmp_path):
    job = tmp_path / 'job'
    job.mkdir()
    with pytest.raises(FileNotFoundError):
        profile.construct(job)


def test_invalid_stage_is_rejected_before_output(tmp_path):
    out = tmp_path / 'must-not-exist'
    with pytest.raises(SystemExit):
        profile.main(['invented', '--output', str(out)])
    assert not out.exists()


def test_check_cli_validates_without_native_launch(tmp_path, capsys):
    folder, pin = captured(tmp_path)
    out = tmp_path / 'check'
    assert profile.main(['check','--profile',str(folder),'--profile-sha256',pin,'--output',str(out)]) == 0
    assert profile.read(out / 'stages/check/result.json')['status'] == 'PASS'
    assert profile.read(out / 'check.json')['native_reuse_allowed'] is False


def preflight_fixture(tmp_path, monkeypatch):
    source = tmp_path / 'source.pdf'
    source.write_bytes(b'not launched')
    executable = tmp_path / 'pdftotext'
    executable.write_bytes(b'not launched')
    executable.chmod(0o755)
    interpreter = tmp_path / 'python'
    interpreter.write_bytes(b'not launched')
    interpreter.chmod(0o755)
    model = tmp_path / 'por.traineddata'
    model.write_bytes(b'pinned model')
    monkeypatch.setattr(profile.shutil, 'which', lambda name: str(executable))
    date = '2026-01-01T00:00:00Z'
    request = {'version': VERSION, 'bundle': {'instrument_id': 'synthetic', 'purpose': 'review',
        'issue_date': date, 'effective_at': date, 'known_at': date, 'documents': [{
            'id': 'd', 'path': str(source), 'sha256': digest(source.read_bytes()), 'format':'pdf',
            'language':'pt', 'authority':'Synthetic no-launch control', 'hybrid_profile': {'version':'pymupdf-hybrid.v1','dpi':300,
                'language':'por','max_pages':1,'page_count':1,'pages':[1],
                'tessdata':str(tmp_path),'models':{'por':digest(model.read_bytes())}}}]}}
    worker = Path(profile.extraction.__file__).with_name('ocr_worker.py').resolve()
    files = [source, executable, interpreter, model, worker, worker.with_name('native_inputs.py')]
    manifest = {'files':[{'path':str(p),'sha256':profile.file_hash(p),'mode':0o555} for p in files]}
    config = {'repository':str(tmp_path),'ocr_python':str(interpreter)}
    return request, config, manifest, str(worker)


@pytest.mark.parametrize('mutation', ['source', 'model', 'worker', 'executable-mode', 'retained'])
def test_required_inputs_refuse_before_native_launch(tmp_path, monkeypatch, mutation):
    request, config, manifest, worker = preflight_fixture(tmp_path, monkeypatch)
    assert profile.preflight(request, config, manifest)
    if mutation == 'source':
        request['bundle']['documents'][0]['sha256'] = '0'*64
    elif mutation == 'model':
        (tmp_path / 'por.traineddata').write_bytes(b'changed')
    elif mutation == 'worker':
        manifest['files'] = [r for r in manifest['files'] if r['path'] != worker]
    elif mutation == 'executable-mode':
        next(r for r in manifest['files'] if r['path']==str(tmp_path/'pdftotext'))['mode'] = 0o444
    else:
        request['bundle']['documents'][0]['hybrid_ocr'] = {'path':'missing.json','sha256':'0'*64}
    with pytest.raises((ValueError, FileNotFoundError, profile.extraction.ExtractionUnavailable)):
        profile.preflight(request, config, manifest)


def test_hybrid_preflight_matches_original_implicit_pdf_convention(tmp_path, monkeypatch):
    request, config, manifest, _ = preflight_fixture(tmp_path, monkeypatch)
    request['bundle']['documents'][0].pop('format')
    assert profile.preflight(request, config, manifest)
    request['bundle']['documents'][0]['format'] = 'text'
    with pytest.raises(ValueError, match='hybrid PDF'):
        profile.preflight(request, config, manifest)
