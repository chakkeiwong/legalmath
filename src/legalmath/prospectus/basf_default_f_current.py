"""Optional default(f) alternatives on the complete ordinary consumer answer.

The caller first verifies P1–P5 through service.consume. The profile binds that
actual answer, rather than requiring the historical body/financial supplement.
Boolean certificates prove consequences of the disclosed hypotheses only.
"""
from copy import deepcopy
from pathlib import Path

from . import basf_default_f as hypotheses
from . import default_f_certificates as independent
from .successor.anchors import fields
from .successor.contracts import bound_path, digest

VERSION = 'basf-current-default-f.v1'
ADDITIONS = frozenset({'default_f_review', 'default_f_reasoning_certificate',
                       'default_f_reasoning_verification'})
SCENARIO_TEXT = {
    'interpretation': 'Comparison is conditional on the enumerated formulas; agreement does not adjudicate the governing clause.',
    'bc_result_scope': 'Only the quorum condition; all other requirements for grounds(b)/(c) remain separate.',
}


def _subject(ordinary, review):
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body['default_f_review'] = review
    return {**body, 'report_sha256': digest(body)}


def _context(subject, profile):
    return {'products_sha256': profile['products_sha256'],
            'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
            'profile_sha256': digest(profile), 'sources': profile['sources'],
            'complete_consumer_sha256': digest(subject)}


def _profile_policy(profile, expected_profile_sha256):
    """Validate admissible premises at both public boundaries, without inference."""
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'reviewer',
            'sources', 'groups', 'premises', 'candidates', 'scenarios',
            'governing_language', 'selected_reading', 'candidate_set_exhaustive',
            'independent_legal_acceptance'}
    fields(profile, keys, keys)
    if profile['version'] != VERSION or digest(profile) != expected_profile_sha256:
        raise ValueError('Pinned current default(f) profile changed')
    if (profile['governing_language'] != 'German' or profile['selected_reading'] is not None
            or profile['candidate_set_exhaustive'] is not False
            or profile['independent_legal_acceptance'] is not False):
        raise ValueError('Unresolved German construction and hypothetical scope must remain')
    reviewer = profile['reviewer']
    fields(reviewer, {'identity', 'basis', 'independent'}, {'identity', 'basis', 'independent'})
    if (not isinstance(reviewer['identity'], str) or not reviewer['identity'].strip()
            or reviewer['basis'] != 'AGENT_EXPOSED_DEVELOPMENT_REVIEW'
            or reviewer['independent'] is not False):
        raise ValueError('Unsupported current default(f) review authority')
    candidates = [{'id': k, 'meaning': hypotheses.READINGS[k], 'event': v,
                   'expressions': hypotheses.expressions(k)} for k, v in hypotheses.FORMULAS.items()]
    if (digest(profile['premises']) != digest(hypotheses.premises())
            or digest(profile['candidates']) != digest(candidates)):
        raise ValueError('Causal, temporal, notice, cure or eligibility hypothesis changed')
    if any(r['assembly_role'] != 'UNKNOWN' for r in profile['groups']['german_f']):
        raise ValueError('Conditional alternatives cannot promote original default(f) roles')
    scenarios = profile['scenarios']
    if (not isinstance(scenarios, list) or not scenarios
            or any(not isinstance(s, dict) for s in scenarios)
            or digest(scenarios[0]) != digest({'id': 'all-open', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': {}})):
        raise ValueError('Distinct hypothetical scenarios and all-open baseline required')
    identifiers = set()
    allowed = {prefix + '.' + name for prefix in ('exercise', 'receipt')
               for name in hypotheses.FACTS} | set(hypotheses.EXTRA)
    for scenario in scenarios:
        fields(scenario, {'id', 'kind', 'facts'}, {'id', 'kind', 'facts'})
        if (not isinstance(scenario['id'], str) or not scenario['id']
                or scenario['id'] in identifiers or scenario['kind'] != 'HYPOTHETICAL_DEVELOPMENT'):
            raise ValueError('Distinct hypothetical scenario identities required')
        identifiers.add(scenario['id'])
        fields(scenario['facts'], allowed)
        if any(v is not None and v != 'conflict' and type(v) is not bool
               for v in scenario['facts'].values()):
            raise ValueError('Scenario facts are Boolean, unknown or conflict')
    sources = profile['sources']
    if (not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources)
            or [s.get('document') for s in sources] != [hypotheses.DOC, hypotheses.FINAL]):
        raise ValueError('Both original default(f) source documents required')
    for source in sources:
        fields(source, {'document', 'path', 'sha256', 'images'}, {'document', 'path', 'sha256', 'images'})
        pages = [82, 126, 127, 133] if source['document'] == hypotheses.DOC else [7]
        if (not isinstance(source['images'], list) or any(not isinstance(i, dict) for i in source['images'])
                or digest([i.get('page') for i in source['images']]) != digest(pages)):
            raise ValueError('Complete original comparison and qualification images required')
        for image in source['images']:
            fields(image, {'page', 'path', 'sha256'}, {'page', 'path', 'sha256'})
    return candidates


def _ordinary_policy(ordinary, profile):
    if (profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            or ADDITIONS.intersection(ordinary)):
        raise ValueError('Complete pre-option ordinary answer changed')


def _review_metadata(profile):
    """The fixed explanation contract; deliberately contains no computed decision."""
    return {
        'version': VERSION, 'profile_sha256': digest(profile), 'reviewer': deepcopy(profile['reviewer']),
        'sources': deepcopy(profile['sources']), 'groups': deepcopy(profile['groups']),
        'premises': deepcopy(profile['premises']), 'candidates': deepcopy(profile['candidates']),
        'products_sha256': profile['products_sha256'],
        'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'selected_reading': None, 'candidate_set_exhaustive': False, 'governing_language': 'German',
        'source_meaning_promoted': False, 'actual_default_established': False,
        'independent_legal_acceptance': False,
        'unresolved_default_f': {'status': 'UNRESOLVED', 'evidence': [r['source'] for r in profile['groups']['german_f']]},
        'temporal_rule': 'Receipt facts determine only the quorum condition; exercise facts, notice and cure determine modeled direct(f) exercise.',
        'causal_rule': 'Distinct consequences belong to cessation, disposal or combined conduct; no cross-candidate causal equivalence is assumed.',
        'next_evidence': 'Further governing-source and authority analysis distinguishing the German constructions; dated event, causation, notice and appointment evidence for actual application.',
    }


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    """Build additions after ordinary phase verification; never select a reading."""
    _profile_policy(profile, expected_profile_sha256)
    _ordinary_policy(ordinary, profile)
    if profile['products_sha256'] != digest(products):
        raise ValueError('Current default(f) products changed')
    groups = hypotheses.source_groups(products)
    if digest(profile['groups']) != digest(groups):
        raise ValueError('Complete original/selected default(f) source groups changed')
    documents = products['P1']['payload']['request']['bundle']['documents']
    for source in profile['sources']:
        document = next(d for d in documents if d['id'] == source['document'])
        if (source['path'], source['sha256']) != (document['path'], document['sha256']):
            raise ValueError('Original default(f) source edition changed')
        for item in [source, *source['images']]:
            if Path(item['path']).is_absolute() or digest(bound_path(root, item['path']).read_bytes()) != item['sha256']:
                raise ValueError('Original default(f) PDF or inspected image changed')
    review = {**_review_metadata(profile),
              'scenarios': [hypotheses.analyze(s) for s in profile['scenarios']]}
    subject = _subject(ordinary, review)
    context = _context(subject, profile)
    certificate = independent.certificate(subject, profile, expected_context=context)
    verification = independent.verify_consumer({**subject, 'reasoning_certificate': certificate},
                                               profile, expected_context=context)
    return {'default_f_review': review, 'default_f_reasoning_certificate': certificate,
            'default_f_reasoning_verification': verification}


def verify_answer(answer, ordinary, profile, *, expected_profile_sha256):
    """Verify a retained complete answer, its unchanged baseline and certificates.

    The certificate subject is the complete ordinary answer plus the review,
    before adding the certificates themselves. The final report hash covers all
    three additions; this explicit ordering avoids a circular hash dependency.
    """
    _profile_policy(profile, expected_profile_sha256)
    _ordinary_policy(ordinary, profile)
    if (not ADDITIONS <= answer.keys()
            or answer.get('report_sha256') != digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            or digest({k: v for k, v in answer.items() if k not in ADDITIONS | {'report_sha256'}}) != digest({
                k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Complete current answer or ordinary fields changed')
    metadata = _review_metadata(profile)
    review = answer['default_f_review']
    fields(review, set(metadata) | {'scenarios'}, set(metadata) | {'scenarios'})
    if digest({k: v for k, v in review.items() if k != 'scenarios'}) != digest(metadata):
        raise ValueError('Current default(f) explanation or attribution changed')
    rows = review['scenarios']
    if not isinstance(rows, list) or len(rows) != len(profile['scenarios']):
        raise ValueError('Scenario coverage changed')
    for source, row in zip(profile['scenarios'], rows, strict=True):
        fixed = {**source, **SCENARIO_TEXT, 'selected_reading': None, 'actual_event_established': False}
        variable = {'readings', 'comparison', 'input_conflicts'}
        fields(row, set(fixed) | variable, set(fixed) | variable)
        if digest({k: row[k] for k in fixed}) != digest(fixed):
            raise ValueError('Scenario explanation, facts or scope changed')
        fields(row['comparison'], independent.QUESTIONS, independent.QUESTIONS)
    subject = _subject(ordinary, answer['default_f_review'])
    verification = independent.verify_consumer(
        {**subject, 'reasoning_certificate': answer['default_f_reasoning_certificate']},
        profile, expected_context=_context(subject, profile))
    if digest(answer['default_f_reasoning_verification']) != digest(verification):
        raise ValueError('Current default(f) verification result changed')
    return verification
