from copy import deepcopy
import zipfile
from pathlib import Path

import pytest

from legalmath.errors import LegalMathError
from legalmath.translation.expressions import expression
from legalmath.translation.model import from_reading
from legalmath.qualification import assurance, proof
from legalmath.interpretation.assurance import proof_certificate
from tests.catala.backend_support import JDK, TOOLCHAIN
from tests.translation.support import AT, fixture, snapshot


def nary_model(arity=4):
    t, g = fixture(); reading = g['readings'][0]
    reading['formalization'].update(result_type='integer', result='(+ '+' '.join(['months']*(arity-1)+['(integer 7)'])+')')
    model = from_reading(reading, t['packet'], AT, coverage=g['coverage'], dimensions=g['dimensions'])
    return model


def test_binary_expression_bytes_unchanged_from_archived_implementation():
    root = Path(__file__).resolve().parents[2]
    with zipfile.ZipFile(root/'artifacts/assurance-continuation/2026-09-29/baseline.zip') as z:
        text = z.read('src/legalmath/translation/expressions.py').decode()
    # Execute only the locally preserved reviewed source; never model code.
    env = {'__package__': 'legalmath.translation'}; exec(compile(text, 'archived-expressions.py', 'exec'), env)
    for code in ('(+ months (integer 7))', '(and true (> (+ months months) (integer 4)))',
                 '(if true (+ months (integer -7)) (integer 0))'):
        assert expression(code, 'same') == env['expression'](code, 'same')


@pytest.mark.parametrize('code', ['(+)', '(+ x)', '(- x x x)', '(* x x x)', '(+ '+' '.join(['x']*80)+')'])
def test_unsupported_arity_and_expanded_depth_reject(code):
    with pytest.raises(LegalMathError): expression(code, 'bounded')


def test_duplicate_operands_have_unique_nodes_and_preserved_multiplicity():
    m = nary_model(); nodes = []
    def collect(n):
        nodes.append(n)
        for key in ('left', 'right'):
            if key in n: collect(n[key])
    collect(m['rules'][0]['body'])
    assert len({n['node_id'] for n in nodes}) == len(nodes)
    assert sum(n.get('name') == 'months' for n in nodes) == 3
    bad = deepcopy(m); bad['review'].update(origin='manual', reading=None)
    bad['rules'][0]['body']['right'] = expression('true', 'wrong.type')
    from legalmath.translation.model import validate
    with pytest.raises(LegalMathError): validate(bad)


@pytest.mark.parametrize('arity', [3, 4, 20])
def test_nary_addition_executes_actual_java_catala_and_independent_exact_oracle(tmp_path, arity):
    m = nary_model(arity)
    values = [0, 1, -7, 10**45, -(10**45)]
    cases = [{'id': 'integer.'+str(n), 'snapshot': snapshot(m, {'months': str(n)}),
              'valid_at': AT, 'known_at': AT} for n in values]
    for status in ('unknown', 'conflict'):
        s = snapshot(m, {'months': '1'}); s['evidence'] = {}
        s['facts']['months'] = {'status': status, 'type': 'integer', **(
            {'reason': 'MISSING'} if status == 'unknown' else {'evidence_ids': ['a', 'b']})}
        cases.append({'id': status, 'snapshot': s, 'valid_at': AT, 'known_at': AT})
    report = assurance.run(m, cases, tmp_path/'run', JDK, toolchain=TOOLCHAIN)
    assert report['summary']['status'] == 'QUALIFIED'
    assert report['summary']['executed_target_cases'] == 2*len(cases)
    assert report['summary']['independent_formal_matches'] == 2*len(values)
    assert report['proof']['exact_addition']['status'] == 'KERNEL_CHECKED'
    assert assurance.verify(tmp_path/'run', m, JDK, compiler=TOOLCHAIN['compiler']) == report
    assert report['summary']['legal_correctness'] == 'NOT_ESTABLISHED'


def test_dropped_operand_fails_constructor_proof_and_old_boolean_profile_stays_narrow(tmp_path):
    m = nary_model(); formal = deepcopy(m['review']['reading']['formalization'])
    bad = deepcopy(m); bad['review'].update(origin='manual', reading=None)
    bad['rules'][0]['body'] = deepcopy(bad['rules'][0]['body']['left'])
    with pytest.raises(LegalMathError): proof.produce(bad, tmp_path/'mutated', formalization=formal)
    assert 'error' in (tmp_path/'mutated/lean.log').read_text()
    with pytest.raises(LegalMathError): proof_certificate.parse_source('(+ x x x)', ['x'])
