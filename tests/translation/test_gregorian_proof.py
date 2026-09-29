from copy import deepcopy
from datetime import date

import pytest

from legalmath.errors import LegalMathError
from legalmath.qualification import proof, gregorian
from legalmath.prospectus.models import make_model


def model():
    return make_model('calendar', {'facts': [('left', 'date'), ('right', 'date')],
        'outputs': [('after', 'bool', '(> left right)'), ('same', 'bool', '(= left right)'),
                    ('cutoff', 'bool', '(>= left (date 2000-02-29))')],
        'meaning': 'Declared Gregorian calendar comparison, independent of any legal selection of a date.'})


@pytest.mark.parametrize('value', ['0001-01-01', '9999-12-31', '1900-02-28', '2000-02-29', '2024-02-29', '2023-03-01'])
def test_independent_codec(value):
    assert gregorian.ordinal(value) == date.fromisoformat(value).toordinal() - 1


@pytest.mark.parametrize('value', ['0000-01-01', '10000-01-01', '1900-02-29', '2100-02-29', '2023-02-29', '2024-04-31', '2024-1-01', '２０２４-01-01'])
def test_invalid_dates_rejected(value):
    with pytest.raises(ValueError): gregorian.parse(value)
    with pytest.raises(LegalMathError): proof.source_tree(proof.parse('(date ' + value + ')'), [])


def test_date_lowering_and_gregorian_order_theorems(tmp_path):
    certificate = proof.produce(model(), tmp_path/'original')
    assert certificate['date_semantics']['status'] == 'KERNEL_CHECKED'
    assert set(certificate['date_semantics']['theorems']) == gregorian.THEOREMS
    assert proof.verify(certificate, model(), tmp_path/'verified') == certificate


@pytest.mark.parametrize('mutation', ['reverse', 'equality', 'fact', 'literal', 'source'])
def test_old_certificate_cannot_accept_changed_date_proposition(tmp_path, mutation):
    m = model()
    certificate = proof.produce(m, tmp_path/'original')
    formal = deepcopy(m['review']['reading']['formalization'])
    if mutation == 'source':
        m['review']['packet']['units'][0]['text'] += ' changed legal edition'
    else:
        m['review'].update(origin='manual', reading=None)
        if mutation == 'reverse':
            body = m['rules'][0]['body']
            body['left'], body['right'] = body['right'], body['left']
        elif mutation == 'equality': m['rules'][2]['body']['cmp'] = 'gt'
        elif mutation == 'fact': m['rules'][0]['body']['left']['name'] = 'right'
        else: m['rules'][2]['body']['right']['value'] = '2000-03-01'
    with pytest.raises(LegalMathError):
        proof.verify(certificate, m, tmp_path/'changed', formalization=formal)
