"""Adverse inputs for the actual optional ordinary default(f) consumer."""
from copy import deepcopy

from legalmath.prospectus import basf_default_f_current as current
from legalmath.prospectus.successor.contracts import digest


def profile_controls(profile):
    """Repin mutations so controls test meaning checks as well as hash checks."""
    mutations = {
        'old-version': lambda p: p.update(version='basf-default-f-alternatives.v1'),
        'extra-actual-default': lambda p: p.update(actual_default_established=True),
        'english-governs': lambda p: p.update(governing_language='English'),
        'selected-reading': lambda p: p.update(selected_reading='both_conducts'),
        'exhaustive-reading-set': lambda p: p.update(candidate_set_exhaustive=True),
        'independent-legal-acceptance': lambda p: p.update(independent_legal_acceptance=True),
        'reviewer-independence': lambda p: p['reviewer'].update(independent=True),
        'reviewer-authority': lambda p: p['reviewer'].update(basis='LEGAL_ACCEPTANCE'),
        'empty-reviewer': lambda p: p['reviewer'].update(identity=''),
        'missing-reading': lambda p: p['candidates'].pop(),
        'causal-qualification': lambda p: p['candidates'][0]['event']['all'].pop(),
        'exercise-notice': lambda p: p['candidates'][0]['expressions']['modeled_f_exercise']['all'].pop(1),
        'receipt-quorum': lambda p: p['candidates'][0]['expressions']['bc_quorum_condition_at_receipt']['any'].pop(),
        'premise-time': lambda p: p['premises']['notice'].update(time='receipt'),
        'premise-causality': lambda p: p['premises']['exercise.value_cessation'].update(meaning='Any fall in value'),
        'missing-open-baseline': lambda p: p['scenarios'].pop(0),
        'duplicate-scenario': lambda p: p['scenarios'].append(deepcopy(p['scenarios'][1])),
        'actual-scenario': lambda p: p['scenarios'][1].update(kind='ACTUAL_TRANSACTION'),
        'misspelled-time': lambda p: p['scenarios'][1]['facts'].update({'reciept.cessation': True}),
        'numeric-boolean': lambda p: p['scenarios'][1]['facts'].update({'exercise.cessation': 1}),
        'stale-products': lambda p: p.update(products_sha256='0' * 64),
        'stale-whole-answer': lambda p: p.update(ordinary_answer_sha256='0' * 64),
        'missing-source-line': lambda p: p['groups']['german_f'].pop(),
        'translated-connector': lambda p: p['groups']['german_f'][0]['source'].update(quote='or'),
        'selected-source-interval': lambda p: p['groups']['german_f'][0]['selected_sources'].clear(),
        'missing-original-document': lambda p: p['sources'].pop(),
        'wrong-original-edition': lambda p: p['sources'][0].update(sha256='0' * 64),
        'missing-qualification-image': lambda p: p['sources'][0]['images'].pop(),
        'wrong-image-page': lambda p: p['sources'][0]['images'][0].update(page=127),
        'wrong-image-bytes': lambda p: p['sources'][0]['images'][0].update(sha256='0' * 64),
        'absolute-image-path': lambda p: p['sources'][0]['images'][0].update(path='/tmp/not-a-default-source.png'),
        'escaping-image-path': lambda p: p['sources'][0]['images'][0].update(path='../../not-a-default-source.png'),
    }
    for name, mutate in mutations.items():
        changed = deepcopy(profile)
        mutate(changed)
        yield name, changed, digest(changed)
    yield 'missing-profile-pin', deepcopy(profile), None
    yield 'wrong-profile-pin', deepcopy(profile), '0' * 64


def adverse_controls(products, ordinary, profile, root):
    outcomes = []
    for name, changed, pin in profile_controls(profile):
        try:
            current.evaluate(products, ordinary, changed, root, expected_profile_sha256=pin)
        except ValueError as error:
            outcomes.append({'case': name, 'status': 'REFUSED', 'error': str(error)})
        else:
            raise AssertionError('Adverse current default(f) profile accepted: ' + name)
    changed_products = {**products, 'P5': {**products['P5'], 'sha256': '0' * 64}}
    changed_ordinary = {**ordinary, 'may_execute_transaction': True}
    for name, p, answer in [('changed-financial-product', changed_products, ordinary),
                             ('changed-ordinary-answer', products, changed_ordinary)]:
        try:
            current.evaluate(p, answer, profile, root, expected_profile_sha256=digest(profile))
        except ValueError as error:
            outcomes.append({'case': name, 'status': 'REFUSED', 'error': str(error)})
        else:
            raise AssertionError('Adverse current default(f) comparator accepted: ' + name)
    return outcomes
