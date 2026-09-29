"""Installed sidecar failure contracts; full tool runs belong to the master."""
from pathlib import Path
import os
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[2]
PY=ROOT/'.localresources/assurance-tools/venv/bin/python'


def test_solver_unknown_unsupported_and_argument_limits_remain_explicit():
    if not (PY.parent.parent.parent/'tool-lock.json').exists():
        pytest.skip('Optional sidecar absent; round-11 M1 requires installation before its own acceptance')
    script='''
from unittest.mock import patch,MagicMock
import cvc5
from legalmath.interpretation.assurance.diversity import cvc5_compare,clingo_extensions,conclusion_support
from legalmath.interpretation.search.formal import expression
a=expression('(and a (not b))','a')
with patch.object(cvc5,'Solver') as cls:
    cls.return_value.assertFormula=MagicMock()
    cls.return_value.checkSat.return_value.isUnsat.return_value=False
    cls.return_value.checkSat.return_value.isSat.return_value=False
    r=cvc5_compare(a,a,['a','b'])
    assert r['status']=='UNKNOWN' and not r['equivalence_established']
r=cvc5_compare(expression('(>= x (integer 6))','n'),a,['a','b'])
assert r['status']=='UNSUPPORTED' and not r['equivalence_established']
r=clingo_extensions(['a'],[['a','a']])
assert r['complete'] and r['extensions']==[]
assert conclusion_support(r['extensions'],{'a':'p'},True)['status']=='NO_STABLE_EXTENSION'
r=clingo_extensions(['a','b'],[['a','b'],['b','a']],1)
assert not r['complete']
assert conclusion_support(r['extensions'],{'a':'p','b':'p'},False)['status']=='INCOMPLETE_ENUMERATION'
print('PASS: unknown, unsupported, empty and truncated formal results stay explicit')
'''
    r=subprocess.run([str(PY),'-c',script],cwd=ROOT,capture_output=True,text=True,timeout=30,
                     env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':str(ROOT/'src'),'HF_HUB_OFFLINE':'1'})
    assert r.returncode==0,r.stdout+r.stderr
