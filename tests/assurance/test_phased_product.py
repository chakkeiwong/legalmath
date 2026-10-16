from copy import deepcopy
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import Scripted, envelope, limits


class PhasedScripted(Scripted):
    def complete(self, request, schema, settings):
        if request['task'] == 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
            self.requests.append(deepcopy(request))
            source = request['records'][0]
            return Completion({'analyses': [{'analysis_id': 'uncertain', 'decision': {
                'verdict': 'UNRESOLVED', 'reason': 'Actual consent remains unknown.',
                'support': [{'record_id': source['id'], 'quote': source['text'], 'locator': ''}],
                'issues': ['Actual facts needed.'], 'source_gaps': [], 'assertion_bindings': [],
                'context_needs': [{'kind': 'CLIENT_FACT', 'reason': 'Consent fact needed.',
                    'record_ids': [], 'locators': [], 'query': ''}]}}],
                'assignments': {i: {'analysis_id': 'uncertain'} for i in request['required_considered']}},
                {'provider': 'scripted-phased'})
        return super().complete(request, schema, settings)


def test_actual_product_answer_uses_exact_synthesis_and_grouped_reviews(tmp_path):
    provider = PhasedScripted()
    original = BoundedProduct(tmp_path, tmp_path / 'acquisition', provider, envelope(), list, limits=limits())
    investigation = original.investigate()
    admissions = []
    def admit(name, count):
        admissions.append((name, count))
        return {'name': name, 'count': count}
    product = PhasedProduct(tmp_path, tmp_path / 'answer', provider, envelope(), list, limits=limits(),
        phase_admit=admit, phase_identity='fixture')
    product.install_dispatch_admission()
    result = product.answer(investigation)
    assert result['answers']['p14']['answer']['status'] == 'VALIDATED'
    assert not result['all_question_reviews_accepted']
    rows = result['answers']['p14']['reviews']
    expected = {r['id'] for r in product.route.records.values() if r['kind'] == 'source'}
    expected |= {r['id'] for r in investigation['discovered_dependencies']}
    reviewed = {i for r in rows if r['status'] == 'VALIDATED' for i in r['value']['considered']}
    assert expected <= reviewed
    assert any(name.startswith('reduction-') for name, count in admissions)
    assert (product.directory / 'synthesis-representation-p14.json').exists()
    count = len(provider.requests)
    second = product.answer(investigation)
    assert second['answers'] == result['answers']
    assert len(provider.requests) == count


def test_opt_in_product_cannot_silently_reacquire_sources(tmp_path):
    product = PhasedProduct(tmp_path, tmp_path / 'answer', PhasedScripted(), envelope(), list,
        limits=limits(), phase_admit=lambda *a: {}, phase_identity='fixture')
    with pytest.raises(LegalMathError):
        product.investigate()
