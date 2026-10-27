"""Every claimed answer quotation must be exact, even when optional."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import context_disposition as context
from tests.assurance.test_context_need_disposition import setup, checked

@pytest.mark.parametrize('disposition', ['SUPPLIED_SOURCE', 'STILL_REQUIRED',
    'MAPPING_CLARIFIED', 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER'])
@pytest.mark.parametrize('damage', ['false_quote', 'empty_path', 'empty_quote'])
def test_each_nonempty_answer_evidence_pair_is_checked(tmp_path, disposition, damage):
    args = list(setup(tmp_path, ('SOURCE_TEXT',)))
    value = deepcopy(args[-1])
    row = value['need_dispositions'][0]
    row['disposition'] = disposition
    if disposition == 'STILL_REQUIRED':
        value.update(verdict='UNRESOLVED', context_needs=deepcopy(args[3]['value']['context_needs']))
    if disposition == 'MAPPING_CLARIFIED':
        args[6][0]['route'] = 'ASSIGNMENT_MAPPING'
    if damage == 'false_quote':
        row['answer_evidence']['quote'] = 'This sentence does not occur in the unchanged answer.'
    elif damage == 'empty_path':
        row['answer_evidence']['path'] = ''
    else:
        row['answer_evidence']['quote'] = ''
    with pytest.raises(LegalMathError):
        checked(args, value)

@pytest.mark.parametrize('disposition', ['SUPPLIED_SOURCE', 'STILL_REQUIRED', 'MAPPING_CLARIFIED'])
@pytest.mark.parametrize('empty', [False, True])
def test_optional_exact_or_absent_evidence_remains_valid(tmp_path, disposition, empty):
    args = list(setup(tmp_path, ('SOURCE_TEXT',)))
    value = deepcopy(args[-1])
    row = value['need_dispositions'][0]
    row['disposition'] = disposition
    if disposition == 'STILL_REQUIRED':
        value.update(verdict='UNRESOLVED', context_needs=deepcopy(args[3]['value']['context_needs']))
    if disposition == 'MAPPING_CLARIFIED':
        args[6][0]['route'] = 'ASSIGNMENT_MAPPING'
    if empty:
        row['answer_evidence'] = dict(path='', quote='')
    checked(args, value)

def test_actual_saved_false_optional_quote_is_rejected_without_changing_receipt():
    root = Path(__file__).resolve().parents[4]
    runtime = root/'artifacts/legal-mission-control/2026-10-23/p14-deployment/context-isolated-live/arms/p14/baseline'
    target = 'dependency-4712f423197e017ddf84010e'
    found = []
    for path in runtime.glob('context-review-*.json'):
        value = json.loads(path.read_text())
        if value['item']['id'] == target:
            found.append((path, value))
    assert len(found) == 1
    path, retained = found[0]
    before = path.read_bytes()
    request_path = next(runtime.glob('capacity/audit-context-disposition-*/request.json'))
    answer = json.loads(request_path.read_text())['payload']['answer']
    # Only isolate the newly checked answer field here. The product fixtures
    # above exercise source checking; this is not a legal revalidation.
    product = SimpleNamespace(citations=lambda *args: None,
        route=SimpleNamespace(envelope={}, records={}))
    assert retained['result']['status'] == 'VALIDATED'
    with pytest.raises(LegalMathError):
        context.validate(product, 'p14', retained['result']['value'], answer,
            retained['item'], retained['prior_needs'], [], retained['source_delivery_failures'])
    assert path.read_bytes() == before
