"""Exact substantive refusals, reviewed against the unchanged consumer order."""
from copy import deepcopy
import inspect
import traceback

from scripts.prospectus_internal_reference_preparation import IDS, reseal
from legalmath.prospectus.successor import service, reviewed_references, basf_internal_references
from legalmath.prospectus.successor.contracts import digest


GENERIC = 'legalmath.prospectus.successor.service'
REVIEWED = 'legalmath.prospectus.successor.reviewed_references'
INTERNAL = 'legalmath.prospectus.successor.basf_internal_references'
RULES = {
    'closure-drop': ('Consumed reviewed reference lacks unresolved closure', REVIEWED, 'verify_consumed'),
    'closure-duplicate': ('Consumed reviewed reference lacks unresolved closure', REVIEWED, 'verify_consumed'),
    'closure-invent': ('Consumed reference closure differs from source reconstruction', GENERIC, '_verify_consumed_dependencies'),
    'dependency-drop': ('Consumed dependencies differ from source reconstruction', GENERIC, '_verify_consumed_dependencies'),
    'dependency-status': ('Consumed dependencies differ from source reconstruction', GENERIC, '_verify_consumed_dependencies'),
    'question-closure': ('Consumed reviewed reference hides unresolved closure in question', REVIEWED, 'verify_consumed'),
    'question-status': ('Consumed question resolves source dependency uncertainty', GENERIC, '_verify_consumed_dependencies'),
    'subquestion-status': ('Consumed question resolves source dependency uncertainty', GENERIC, '_verify_consumed_dependencies'),
    'subquestion-missing': ('Consumed BASF question hides or invents a missing internal link', INTERNAL, 'verify_consumed'),
    'q3-status': ('Consumed semantic completeness differs from question uncertainty', GENERIC, '_verify_consumed_dependencies'),
    'q3-value': ('Consumed semantic completeness differs from question uncertainty', GENERIC, '_verify_consumed_dependencies'),
    'target': ('BASF internal reference requires its exact complete selected target', INTERNAL, 'check'),
}


def mutation(p, case):
    assert case in RULES
    original = p['P3']['payload']
    semantic = deepcopy(original)
    deps = semantic['dependencies']
    closure = next(d for d in deps if d['id'] == 'reference-closure:Q1')
    changed = 'dependencies'
    if case == 'closure-drop':
        deps.remove(closure)
        assert len(deps) == len(original['dependencies']) - 1
    elif case == 'closure-duplicate':
        deps.append(deepcopy(closure))
        assert sum(d['id'] == closure['id'] for d in deps) == 2
    elif case == 'closure-invent':
        deps.append({**deepcopy(closure), 'id': 'reference-closure:invented'})
        assert len(deps) == len(original['dependencies']) + 1
    elif case.startswith('dependency-'):
        dep = next(d for d in deps if d.get('source_use') and '@' in d['id'])
        assert dep['status'] == 'UNRESOLVED', 'Inherited mutation must change status'
        assert not dep['id'].startswith(('reviewed-reference:', 'legacy-reference:'))
        from legalmath.prospectus.successor import (
            basf_call_references, basf_payment_references, basf_governance_references,
            basf_default_references, basf_substitution_references, basf_financial_references)
        for module in (basf_call_references, basf_payment_references, basf_governance_references,
                       basf_default_references, basf_substitution_references,
                       basf_financial_references, basf_internal_references):
            assert not module._owned(dep['id']), 'Raw dependency belongs to earlier verifier'
        if case == 'dependency-drop':
            deps.remove(dep)
        else:
            dep['status'] = 'RESOLVED'
    elif case in ('question-closure', 'question-status', 'subquestion-status', 'subquestion-missing'):
        changed = 'questions'
        q = semantic['questions']['Q2']
        if case == 'question-closure':
            q['unresolved'].remove('reference-closure:Q2')
        elif case == 'subquestion-missing':
            q['subquestions']['possible_common']['unresolved'].remove('internal-reference:' + IDS[9])
        else:
            if case == 'subquestion-status':
                q = q['subquestions']['possible_common']
            assert q['status'] in ('UNKNOWN', 'CONFLICT') and q['unresolved']
            q['status'] = 'YES'
    elif case.startswith('q3-'):
        changed = 'questions'
        q = semantic['questions']['Q3']
        if case == 'q3-status':
            assert q['status'] == 'PARTIAL'
            q['status'] = 'COMPLETE'
        else:
            assert q['value']['Q1']['complete'] is False
            q['value']['Q1']['complete'] = True
    else:
        changed = 'interpretation_input'
        row = next(r for r in semantic[changed]['reference_admission']['references'] if r['id'] == IDS[0])
        assert len(row['targets']) > 1
        row['targets'] = row['targets'][-1:]
    assert digest(semantic[changed]) != digest(original[changed]), 'No-op adverse mutation'
    assert {k: v for k, v in semantic.items() if k != changed} == {
        k: v for k, v in original.items() if k != changed}, 'Unintended semantic field changed'
    forged = reseal(p, semantic)
    bundle = p['P1']['payload']['request']['bundle']
    for stage in ('P3', 'P4', 'P5'):
        expected = p[stage]['inputs'] if stage == 'P3' else {**p[stage]['inputs'], 'P3': forged['P3']['sha256']}
        service.verify(forged[stage], stage, bundle, expected)
    return forged, {'case': case, 'original_products_sha256': digest(p),
        'forged_products_sha256': digest(forged), 'mutated_semantic_sha256': digest(semantic),
        'validly_resealed': True, 'changed_semantic_member': changed,
        'expected_refusal': RULES[case][0], 'expected_origin': list(RULES[case][1:])}


def check_exception(case, exc):
    rule = RULES[case]
    tb = exc.__traceback__
    frames = []
    while tb is not None:
        frames.append({'module': tb.tb_frame.f_globals.get('__name__'),
                       'function': tb.tb_frame.f_code.co_name, 'line': tb.tb_lineno})
        tb = tb.tb_next
    actual = frames[-1]
    if type(exc) is not ValueError or str(exc) != rule[0] or (
            actual['module'], actual['function']) != rule[1:]:
        raise ValueError('Unexpected adverse outcome: ' + case + ': ' + str(exc)) from exc
    return {'actual_consumer_refusal': str(exc), 'origin': actual, 'traceback': frames}


def order_preflight(candidate, omitted):
    source = inspect.getsource(service.consume)
    sequence = ['call_references = verify_call_references(', 'payment_references = verify_payment_references(',
        'legacy_references = verify_legacy_references(', 'governance_references = verify_governance_references(',
        'default_references = verify_default_references(', 'substitution_references = verify_substitution_references(',
        'financial_references = verify_financial_references(', 'verify_reviewed_references(',
        'internal_references = verify_internal_references(', '_verify_consumed_dependencies(']
    offsets = [source.index(text) for text in sequence]
    assert offsets == sorted(offsets)
    for case, (message, module, name) in RULES.items():
        owner = {GENERIC: service, REVIEWED: reviewed_references, INTERNAL: basf_internal_references}[module]
        assert repr(message) in inspect.getsource(getattr(owner, name)), 'Unbound expected error: ' + case
    p = candidate['P3']['payload']
    assert p['interpretation_input']['reference_admission']['version'] == 'reviewed-references.v3'
    for q in ('Q1', 'Q2'):
        required = {d['id'] for d in p['dependencies'] if d['id'].startswith('reviewed-reference:')
                    and d['status'] == 'UNRESOLVED' and q in d['questions']}
        assert required, 'Missing premise for earlier v3 refusal'
        closure = [d for d in p['dependencies'] if d['id'] == 'reference-closure:' + q]
        assert len(closure) == 1 and {'Unresolved reference: ' + key for key in required} <= set(closure[0]['unresolved'])
    matrix = []
    for case in RULES:
        _, receipt = mutation(omitted if case == 'subquestion-missing' else candidate, case)
        matrix.append(receipt)
    return {'status': 'PASS', 'matrix': matrix, 'verification_order': sequence,
        'role': 'EXPLANATORY_HARNESS_DIAGNOSTIC', 'actual_consumers_run': 0}
