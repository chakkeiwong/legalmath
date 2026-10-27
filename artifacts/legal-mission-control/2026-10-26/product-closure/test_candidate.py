"""Run isolated candidate checks with CPU-only imports and retained results."""
from pathlib import Path
import os, sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
TREE=Path('/tmp/legalmath-product-closure-20261026')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.chdir(TREE)
sys.path[:0]=[str(TREE/'src'),str(TREE)]
import importlib
for name in ('legal_mission_execution','legal_integration_master','legal_mission_control',
        'legal_integration_campaign','legal_integration_qualification_continuation'):
    importlib.import_module('scripts.'+name).ROOT=ROOT
import pytest
label=sys.argv[1]
output=WORK/(label+'-tests.xml')
assert not output.exists(), 'Do not replace test evidence'
raise SystemExit(pytest.main([*sys.argv[2:], '-q', '--junitxml='+str(output)]))
