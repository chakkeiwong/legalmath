"""Build and test an isolated candidate; never edit the bound deployment."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT/'src/legalmath/interpretation/assurance/phased/context_disposition.py'
FOLDER = HERE/'optional-quote-candidate'
MODE = sys.argv[1]
assert MODE in ('baseline', 'candidate')
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
original = SOURCE.read_text()
before = digest(SOURCE)
FOLDER.mkdir(exist_ok=True)
if MODE == 'candidate':
    old = "        need, disposition = row['original_need'], result['disposition']\n"
    new = old + ("        evidence = result['answer_evidence']\n"
        "        if evidence['path'] or evidence['quote']:\n"
        "            answer_quote(answer, evidence['path'], evidence['quote'])\n")
    assert original.count(old) == 1
    candidate = FOLDER/'context_disposition.py'
    body = original.replace(old, new)
    if candidate.exists():
        assert candidate.read_text() == body
    else:
        candidate.write_text(body)
    from legalmath.interpretation.assurance import phased
    name = 'legalmath.interpretation.assurance.phased.context_disposition'
    spec = importlib.util.spec_from_file_location(name, candidate)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    phased.context_disposition = module
import pytest
tests = [str(HERE/'test_optional_answer_quotes.py')]
if MODE == 'candidate':
    tests += ['tests/assurance/test_context_need_disposition.py',
        'tests/assurance/test_corrected_context_disposition.py',
        'tests/assurance/test_context_pointer_warrant_targets.py']
code = pytest.main([*tests, '-q', '--tb=short', '--junitxml='+str(FOLDER/(MODE+'.xml'))])
assert digest(SOURCE) == before
installed = json.loads((HERE/'installation-manifest.json').read_text())['installed']
assert all(digest(ROOT/r['path']) == r['sha256'] for r in installed)
record = dict(at_utc=datetime.now(timezone.utc).isoformat(), mode=MODE,
    tests_exit_code=int(code), production_sha256=before,
    candidate_sha256=digest(FOLDER/'context_disposition.py') if MODE=='candidate' else None,
    installed_files_unchanged=True, provider_calls=0, deployed=False, legal_acceptance=False,
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    command=' '.join(sys.argv), environment=sys.executable,
    cpu_only='CUDA_VISIBLE_DEVICES=-1', random_seeds='N/A deterministic validation',
    plan='docs/implementation/legal-mission-control/results/p14-deployment-continuation-2026-10-23.md')
target = FOLDER/(MODE+'.json')
with target.open('x') as output:
    json.dump(record, output, indent=2)
raise SystemExit(code)
