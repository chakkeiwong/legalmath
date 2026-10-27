"""Exercise isolated quotation successor modules; keep deployment bytes fixed."""
from pathlib import Path
import importlib.util
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import legal_optional_quote_validation as repair
repair.verify_preparation()
name='legalmath.interpretation.assurance.phased.context_disposition'
from legalmath.interpretation.assurance import phased
spec=importlib.util.spec_from_file_location(name,ROOT/repair.HERE/'candidate'/repair.PRODUCT)
module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
phased.context_disposition=module
import pytest
original='artifacts/legal-mission-control/2026-10-23/p14-corrected-context/'
code=pytest.main([original+'test_optional_answer_quotes.py',original+'test_optional_quote_checkpoint.py',
    'tests/tooling/test_optional_quote_validation.py',
    'tests/assurance/test_context_need_disposition.py',
    'tests/assurance/test_corrected_context_disposition.py',
    'tests/assurance/test_context_pointer_warrant_targets.py',
    '-q','--tb=short','--junitxml='+str(ROOT/repair.HERE/'tests.xml')])
repair.verify_preparation()
raise SystemExit(code)
