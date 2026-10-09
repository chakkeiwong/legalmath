"""Runtime trust and exhaustion boundaries through actual consumers."""
import sys
import json
import pytest
from legalmath.prospectus.successor import predicates, read_context, extraction
from scripts.prospectus_closure_fixtures import request, PREFIX
from legalmath.prospectus.successor.contracts import digest


def test_installed_runtime_uses_verified_latest_success_without_corruption_fallback(tmp_path):
    from scripts.prospectus_closure_install import successful_attempt, sha
    for number, status in [(1, 'PASS'), (2, 'PASS'), (3, 'FAIL')]:
        folder = tmp_path/f'attempt-{number:03d}'
        folder.mkdir()
        (folder/'result.json').write_text(json.dumps({'status':status}))
        (folder/'request.json').write_text(json.dumps({'case':number}))
        (folder/'manifest.json').write_text(json.dumps({'files':{
            name:sha(folder/name) for name in ('result.json','request.json')}}))
    assert successful_attempt(tmp_path, {'request.json'}) == tmp_path/'attempt-002'
    (tmp_path/'attempt-002/request.json').write_text('changed')
    with pytest.raises(ValueError, match='evidence changed'):
        successful_attempt(tmp_path, {'request.json'})


def test_installed_runtime_requires_complete_consumer_manifest(tmp_path):
    from scripts.prospectus_closure_install import successful_attempt, sha
    folder = tmp_path/'attempt-001'
    folder.mkdir()
    (folder/'result.json').write_text(json.dumps({'status':'PASS'}))
    (folder/'manifest.json').write_text(json.dumps({'files':{'result.json':sha(folder/'result.json')}}))
    with pytest.raises(ValueError, match='manifest is incomplete'):
        successful_attempt(tmp_path, {'request.json'})


def test_installed_runtime_question_comparison_detects_nested_evidence_change():
    from scripts.prospectus_closure_installed_check import question_summary
    questions = {'Q1':{'status':'UNKNOWN','evidence':[{'quote':'source', 'dependency':'unresolved'}]}}
    before = question_summary(questions)
    questions['Q1']['evidence'][0]['quote'] = 'different source'
    after = question_summary(questions)
    assert before['Q1']['status'] == after['Q1']['status']
    assert before != after
    assert 'evidence' not in after['Q1']


def test_installed_runtime_evidence_budget_reserves_metadata(tmp_path):
    from scripts.prospectus_closure_install import check_evidence_budget
    (tmp_path/'output').write_bytes(b'0123456789')
    assert check_evidence_budget(tmp_path, limit=12, metadata_reserve=2) == 10
    with pytest.raises(ValueError, match='Evidence budget exceeded'):
        check_evidence_budget(tmp_path, limit=11, metadata_reserve=2)


def test_native_unrecorded_read_prohibits_reuse(tmp_path):
    secret_input = tmp_path / 'undeclared.txt'
    secret_input.write_text('version one')
    worker = tmp_path / 'worker.py'
    worker.write_text("from pathlib import Path\nprint(Path('undeclared.txt').read_text())\n")
    ctx = read_context.ReadContext(tmp_path, tmp_path / 'snapshots')
    run = ctx.tool([sys.executable, str(worker)], inputs=['worker.py'])
    assert run.stdout.strip() == b'version one'
    assert read_context.current(tmp_path, ctx.manifest())
    assert not read_context.reusable(tmp_path, ctx.manifest())
    secret_input.write_text('version two')
    assert not read_context.reusable(tmp_path, ctx.manifest())


def test_z3_exhaustion_is_typed_without_launching_solver():
    def forbidden():
        raise AssertionError('Out-of-domain input must not start solver')
    expr = {'all': [{'all': ['f' + str(i) for i in range(start, min(start + 100, 257))]}
                    for start in (0, 100, 200)]}
    result = predicates.solve(expr, {}, solver_factory=forbidden)
    assert result['status'] == 'UNKNOWN' and result['reason'] == 'DOMAIN_LIMIT'
    assert result['limits']['max_facts'] == 256


def test_scan_missing_runtime_and_language_are_typed(tmp_path, monkeypatch):
    req = request(tmp_path, [PREFIX])
    document = req['bundle']['documents'][0]
    model = tmp_path / 'eng.traineddata'
    model.write_bytes(b'synthetic profile path check; never executed')
    document['scan_profile'] = {'version': 'pymupdf-scan.v1', 'dpi': 300, 'language': 'eng', 'max_pages': 2,
        'tessdata': '.', 'models': {'eng': digest(model.read_bytes())}}
    monkeypatch.setenv('LEGALMATH_OCR_PYTHON', str(tmp_path / 'missing-runtime'))
    with pytest.raises(extraction.ExtractionUnavailable, match='Configure LEGALMATH_OCR_PYTHON'):
        extraction.scan(document, tmp_path)
    model.unlink()
    with pytest.raises(extraction.ExtractionUnavailable, match='language model missing'):
        extraction.scan(document, tmp_path)
