"""Executed Lean rules, separate from source meaning and Python correspondence."""
from pathlib import Path
import subprocess
from ...canonical import loads,raw_digest
from ...errors import LegalMathError
from .diversity import save
from .proof_certificate import LEAN

PRELUDE=Path(__file__).with_name('ChallengeRules.lean')
THEOREMS=('conditional_rejection','joined_partition_obligations','partitioned_disagreement')


def execute(path):
    result=subprocess.run([str(LEAN),str(path)],capture_output=True,text=True,timeout=60,cwd=path.parent)
    log=result.stdout+result.stderr
    if (result.returncode or 'sorry' in log or 'depends on axioms' in log or
        any('LegalMathChallenges.'+name not in log for name in THEOREMS)):
        raise LegalMathError('E_INTEGRITY',details='Lean rejected challenge rules or reported additional axioms')
    return log


def kernel(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'certificate.json').exists():return verify(directory)
    path=directory/'ChallengeRules.lean';path.write_bytes(PRELUDE.read_bytes())
    log=execute(path);(directory/'lean.log').write_text(log)
    value={'profile':'legalmath.challenge-rules.lean.v1','status':'KERNEL_CHECKED',
        'theorems':list(THEOREMS),'source_sha256':raw_digest(path.read_bytes()),
        'tool_sha256':raw_digest(LEAN.read_bytes()),'log_sha256':raw_digest(log.encode()),
        'assumptions':['The supplied Boolean functions and obligations express the declared formal question.',
            'Partition membership is the declared complete index family.'],
        'scope':'Universal conditional rejection and partition propositions over the declared functions and index sets.',
        'excludes':['English entailment','all possible legal obligations','Python-to-Lean implementation equivalence',
            'whole Java compiler correctness','independence of model readers']}
    save(directory/'certificate.json',value);return value


def verify(directory):
    directory=Path(directory);value=loads((directory/'certificate.json').read_bytes())
    source=directory/'ChallengeRules.lean';log=directory/'lean.log'
    if (source.read_bytes()!=PRELUDE.read_bytes() or value['source_sha256']!=raw_digest(source.read_bytes()) or
        value['tool_sha256']!=raw_digest(LEAN.read_bytes()) or value['log_sha256']!=raw_digest(log.read_bytes()) or
        value['theorems']!=list(THEOREMS) or value['status']!='KERNEL_CHECKED'):
        raise LegalMathError('E_INTEGRITY',details='Challenge kernel receipt changed')
    if execute(source)!=log.read_text():raise LegalMathError('E_INTEGRITY')
    return value
