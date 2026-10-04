from pathlib import Path
import subprocess
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.engine import Assurance

from legalmath.interpretation.assurance.integrated import IntegratedInvestigation
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import responder, source, settings


def test_clean_source_to_actual_java_and_independent_routes_resume(root, tmp_path):
    provider = FunctionProvider(responder())
    workflow = IntegratedInvestigation(tmp_path/'case', provider,
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings())
    result = workflow.run([source()], 'Selected gift control')
    assert result['execution_complete'], result
    assert result['independent']['binaries']
    assert result['independent']['formal']['result']['status'] == 'PASS'
    assert result['independent']['arguments']['result']['status'] == 'PASS'
    count = len(provider.requests)
    resumed = workflow.run([source()], 'Selected gift control')
    assert all(r['reused'] for r in resumed['receipts']) and len(provider.requests) == count
    assert not resumed['legal_correctness_established'] and not resumed['release_eligible']


def test_new_cli_is_available(root):
    proc = subprocess.run([str(root/'.venv/bin/python'), '-m', 'legalmath.cli', 'assurance-investigate', '--help'],
                          text=True, capture_output=True, timeout=20)
    assert proc.returncode == 0 and '--ceiling' in proc.stdout


def test_nested_integrity_failure_cannot_become_ordinary_incomplete_evidence(root, tmp_path, monkeypatch):
    monkeypatch.setattr(Assurance, 'drive', lambda *args, **kwargs:
        {'status': 'FAILED_INTEGRITY', 'execution_complete': False,
         'failures': [{'error': 'E_DUPLICATE_ID'}]})
    workflow = IntegratedInvestigation(tmp_path/'case', FunctionProvider(responder()),
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings())
    with pytest.raises(LegalMathError) as error:
        workflow.run([source()], 'Selected gift control')
    assert error.value.code == 'E_INTEGRITY'
    actions = workflow.journal.report()['actions']
    assert [a['spec']['stage'] for a in actions] == ['source', 'interpretation']
    assert actions[-1]['status'] == 'FAILED'


def test_interpretation_only_settings_change_reuses_source_processing(root, tmp_path):
    provider = FunctionProvider(responder())
    workflow = IntegratedInvestigation(tmp_path/'case', provider,
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings())
    first = workflow.run([source()], 'Selected gift control')
    adjusted = settings().model_copy(update={'max_fidelity_pairs_per_call': 8})
    resumed = IntegratedInvestigation(tmp_path/'case', provider,
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=adjusted)
    second = resumed.run([source()], 'Selected gift control')
    assert first['execution_complete'] and second['execution_complete']
    assert second['receipts'][0]['reused'] and not second['receipts'][1]['reused']
