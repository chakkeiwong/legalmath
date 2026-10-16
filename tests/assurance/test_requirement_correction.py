from copy import deepcopy
from dataclasses import replace

from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import envelope, limits, Scripted


class AccountDefect(Scripted):
    """The answer is correct, but its separate account omits the remote exception."""
    def __init__(self, *, omit_repair=False, fail_repair=False):
        super().__init__()
        self.omit_repair, self.fail_repair = omit_repair, fail_repair

    def complete(self, request, schema, settings):
        completion = super().complete(request, schema, settings)
        value = completion.value
        sources = [r for r in request['records'] if r['kind'] == 'source']
        quotes = [{'record_id': r['id'], 'quote': r['text'], 'locator': ''} for r in sources]
        task = request['task']
        if task == 'CORRECT_REVIEWED_REQUIREMENT':
            if self.fail_repair:
                raise RuntimeError('Terminal account repair failure')
            value.update(conclusion='Exception accounted for.' if not self.omit_repair else 'Duty applies.',
                         support=quotes, unresolved=[])
        elif task == 'CORRECT_REVIEWED_ANSWER':
            value.update(conclusion='The duty is conditional on consent.', support=quotes, unresolved=[])
        elif task.startswith('AUDIT_'):
            reject = task == 'AUDIT_ANSWER_AND_DETAILED_ACCOUNT' and (
                request['payload']['detailed_account']['conclusion'] != 'Exception accounted for.')
            value.update(verdict='REJECT' if reject else 'ACCEPT', support=quotes,
                         issues=['Account omits the exception.'] if reject else [],
                         reason='The final answer is conditional; its account must also cover the exception.')
        return Completion(value, completion.provenance)


def setup_product(tmp_path, **settings):
    provider = AccountDefect(**settings)
    product = BoundedProduct(tmp_path, tmp_path/'product', provider, envelope(), list,
        limits=replace(limits(), input_tokens=80000), maximum_corrections=1)
    a, b = [r for r in product.route.records.values() if r['kind'] == 'source']
    def quote(r):
        return {'record_id': r['id'], 'quote': r['text'], 'locator': ''}
    def note(conclusion, support, considered):
        return {'status': 'VALIDATED', 'value': {'conclusion': conclusion, 'support': support,
            'contrary': [], 'assumptions': [], 'unresolved': [], 'alternatives': [],
            'considered': considered, 'source_gaps': [], 'assertion_bindings': []}}
    answer = note('The duty is conditional on consent.', [quote(a), quote(b)], ['reduction'])
    details = [{'id': 'obligation:o1', 'requirement_hash': digest(product.route.records['obligation:o1']),
                'result': note('Duty applies.', [quote(a)], ['obligation:o1'])}]
    review = {'status': 'VALIDATED', 'value': {'verdict': 'REJECT', 'considered': ['obligation:o1'],
        'reason': 'Account incomplete; answer already correct.', 'issues': ['Account omits exception.'],
        'support': [quote(b)], 'source_gaps': [], 'assertion_bindings': []}}
    return provider, product, answer, details, review


def test_supported_account_defect_repairs_account_and_reaches_fresh_review(tmp_path):
    provider, product, answer, details, review = setup_product(tmp_path)
    before = deepcopy(details)
    candidate, fresh, retained = product.correct_answer('p14', 'When does duty apply?', answer,
        [review], details, [])
    assert details == before
    assert retained['original_requirement_details'] == before
    assert retained['original_answer'] == answer and retained['original_reviews'] == [review]
    changes = retained['requirement_corrections']
    assert len(changes) == 1 and changes[0]['id'] == 'obligation:o1'
    assert changes[0]['result']['value']['conclusion'] == 'Exception accounted for.'
    assert all(r['status'] == 'VALIDATED' and r['value']['verdict'] == 'ACCEPT' for r in fresh)
    audits = [r for r in provider.requests if r['task'] == 'AUDIT_ANSWER_AND_DETAILED_ACCOUNT']
    assert len(audits) == 1 and audits[0]['payload']['detailed_account']['conclusion'] == 'Exception accounted for.'
    correction = next(r for r in provider.requests if r['task'] == 'CORRECT_REVIEWED_REQUIREMENT')
    assert {r['unit_id'] for r in correction['records']} == {'source.a', 'source.b'}
    assert correction['required_considered'] == ['obligation:o1']
    count = len(provider.requests)
    # Identical resume consumes no new requests or correction iterations.
    assert product.correct_answer('p14', 'When does duty apply?', answer, [review], details, []) == (candidate, fresh, retained)
    assert len(provider.requests) == count


def test_account_omission_still_rejects_corrected_package(tmp_path):
    _, product, answer, details, review = setup_product(tmp_path, omit_repair=True)
    _, fresh, retained = product.correct_answer('p14', 'When does duty apply?', answer,
        [review], details, [])
    assert retained['status'] == 'REVIEWED'
    assert any(r['value']['verdict'] == 'REJECT' for r in fresh)


def test_failed_account_repair_does_not_promote_answer_or_erase_rejection(tmp_path):
    provider, product, answer, details, review = setup_product(tmp_path, fail_repair=True)
    candidate, fresh, retained = product.correct_answer('p14', 'When does duty apply?', answer,
        [review], details, [])
    assert candidate == answer and fresh == [review] and retained['status'] == 'FAILED'
    assert retained['requirement_corrections'][0]['result']['status'] == 'FAILED'
    assert not any(r['task'] == 'CORRECT_REVIEWED_ANSWER' for r in provider.requests)


def test_only_adverse_reviews_are_delivered_but_all_reviews_are_retained(tmp_path):
    provider, product, answer, details, adverse = setup_product(tmp_path)
    accepted = deepcopy(adverse)
    accepted['value'].update(verdict='ACCEPT', issues=[], reason='No supported defect.')
    reviews = [accepted, adverse, deepcopy(accepted)]
    _, fresh, retained = product.correct_answer('p14', 'When does duty apply?', answer,
        reviews, details, [])
    request = next(r for r in provider.requests if r['task'] == 'CORRECT_REVIEWED_ANSWER')
    assert request['payload']['adverse_reviews'] == [adverse['value']]
    assert request['payload']['retained_review_population']['count'] == 3
    assert request['payload']['retained_review_population']['sha256'] == digest(reviews)
    assert retained['original_reviews'] == reviews
    assert fresh and all(r['value']['verdict'] == 'ACCEPT' for r in fresh)
