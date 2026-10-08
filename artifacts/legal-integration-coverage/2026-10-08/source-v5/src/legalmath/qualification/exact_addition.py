"""Checked ordered addition identities, with an explicit narrow status domain."""
from pathlib import Path
import re
import subprocess

from ..canonical import raw_digest
from ..errors import LegalMathError

PRELUDE = Path(__file__).with_name('NaryAddition.lean')
THEOREMS = ('ordered_lowering', 'missing_operand', 'exact_sum')
STANDARD_AXIOMS = {'propext', 'Quot.sound'}


def contains_nary(tree):
    return isinstance(tree, list) and ((len(tree) > 3 and tree[0] == '+') or any(contains_nary(t) for t in tree))


def produce(directory, lean):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    path = directory/'NaryAddition.lean'; path.write_bytes(PRELUDE.read_bytes())
    result = subprocess.run([str(lean), str(path.resolve())], cwd=directory,
                            capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr; (directory/'lean.log').write_text(log)
    dependencies = re.findall(r"'LegalMathExactAddition\.([a-z_]+)' depends on axioms: \[([^\]]*)\]", log)
    axioms = {n.strip() for _, names in dependencies for n in names.split(',') if n.strip()}
    if (result.returncode or 'sorry' in log or {name for name, _ in dependencies} != set(THEOREMS)
            or not axioms <= STANDARD_AXIOMS):
        raise LegalMathError('E_INTEGRITY', details='Exact-addition theorem or axiom audit failed')
    return {'profile': 'lean.exact-optional-integer-addition.v1', 'status': 'KERNEL_CHECKED',
        'theorems': list(THEOREMS), 'standard_axioms': sorted(axioms),
        'domain': 'Every finite ordered list of unbounded exact integers or missing (Option Int) inputs.',
        'proposition': 'Ordered binary lowering equals n-ary fold; complete inputs yield their integer sum; any missing operand yields missing.',
        'excludes': ['English meaning', 'financial admissibility', 'conflict/scope/time selection',
                     'other arithmetic operators', 'Java/Catala implementation correctness'],
        'prelude_sha256': raw_digest(PRELUDE.read_bytes()), 'log_sha256': raw_digest(log.encode()),
        'tool_sha256': raw_digest(Path(lean).read_bytes())}
