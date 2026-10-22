"""Explicit individual-holder premises for the supplied default(f) alternatives."""
from copy import deepcopy
from pathlib import Path

from .. import basf_default_f as hypotheses
from ..basf_body_coverage import selected_sources
from .anchors import fields
from .contracts import bound_path, digest
from .predicates import dispatch

VERSION = 'basf-default-holder-authority.v1'
KEY = 'default_holder_authority_review'
NODE = 'basf-representative:individual-exercise-restriction'
QUOTE = ('Soweit er zur Geltendmachung von Rechten der Gläubiger ermächtigt ist, '
         'sind die einzelnen Gläubiger zur selbständigen Geltendmachung dieser '
         'Rechte nicht befugt, es sei denn der Mehrheitsbeschluß sieht dies ausdrücklich vor.')
EXTRA = {
    'holder': 'The exercising person is a holder of this note at exercise; other exercise requirements are separate.',
    'notice_form_delivery': 'At exercise the holder elects by written German or English declaration delivered by hand or registered mail to the designated Fiscal Agent office. This does not establish holder authority.',
    'cured': 'The particular default(f) ground was cured before exercise.',
    'entrusted': 'At exercise the common representative is effectively empowered to assert this specific right. Appointment alone does not establish this proposition.',
    'express_permission': 'The majority resolution expressly permits individual holders to assert this specific right at exercise.',
}


def premises():
    return {**{k: {'meaning': v, 'source_group': 'german_f'} for k, v in hypotheses.FACTS.items()},
            **{k: {'meaning': v, 'source_group': 'representative' if k in ('entrusted', 'express_permission')
                    else 'entitlement' if k == 'holder' else 'notice' if k == 'notice_form_delivery' else 'cure'}
               for k, v in EXTRA.items()}}


def expressions():
    return {key: {'all': [deepcopy(event), 'holder', 'notice_form_delivery', {'not': 'cured'},
                         {'any': [{'not': 'entrusted'}, 'express_permission']}]}
            for key, event in hypotheses.FORMULAS.items()}


def validate_scenarios(scenarios):
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 64:
        raise ValueError('One to 64 explicit hypothetical scenarios required')
    ids = set()
    for row in scenarios:
        fields(row, {'id', 'kind', 'facts'}, {'id', 'kind', 'facts'})
        if (not isinstance(row['id'], str) or not row['id'] or row['id'] in ids
                or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT'):
            raise ValueError('Distinct hypothetical scenario identities required')
        ids.add(row['id'])
        fields(row['facts'], set(hypotheses.FACTS) | set(EXTRA))
        if any(v is not None and v != 'conflict' and type(v) is not bool for v in row['facts'].values()):
            raise ValueError('Holder premises are Boolean, unknown or conflict')


def analyze(scenario):
    validate_scenarios([scenario])
    from .predicates import names
    decisions = {}
    for reading, expression in expressions().items():
        required = sorted(names(expression))
        facts = scenario['facts']
        decisions[reading] = {'status': dispatch(expression, facts, engine='finite')['status'],
            'missing': [k for k in required if facts.get(k) is None],
            'conflicts': [k for k in required if facts.get(k) == 'conflict']}
    return {**deepcopy(scenario), 'readings': decisions,
            'comparison': hypotheses.comparison([r['status'] for r in decisions.values()])}


def source_groups(products):
    groups = hypotheses.source_groups(products)
    graph = products['P1']['payload']['graph']
    raw = {r['id']: r for r in graph['units']}
    assembly = products['P2']['payload']['assembly']['units']
    selected = {r['unit']: r for r in assembly}
    nodes = [n for n in products['P3']['payload']['clauses']['nodes'] if n['id'] == NODE]
    if len(nodes) != 1 or len(selected) != len(assembly) or len(raw) != len(graph['units']):
        raise ValueError('Unique original and selected representative sources required')
    node = nodes[0]
    spans = node['spans']
    expected = [hypotheses.DOC + ':p130:l' + str(i) for i in range(25, 29)]
    if ([s['unit'] for s in spans] != expected or node['quote'] != QUOTE or node['role'] != 'OPERATIVE'
            or node['legal_reading'] != 'Individual holders cannot independently assert rights whose assertion is entrusted to the common representative, unless the majority resolution expressly permits it.'):
        raise ValueError('Exact supplied representative restriction required')
    rows = []
    for span in spans:
        unit = selected[span['unit']]
        if unit['role'] != 'OPERATIVE':
            raise ValueError('Reviewed representative source role changed')
        rows.append({'span': deepcopy(span), 'selected_text': unit['text'][span['start']:span['end']],
                     'assembly_role': unit['role'],
                     'sources': selected_sources(graph, unit, span['start'], span['end'], raw=raw)})
    if ' '.join(r['selected_text'] for r in rows) != QUOTE:
        raise ValueError('Complete representative restriction text changed')
    return {**groups, 'representative': rows}


def policy(ordinary, profile, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'groups', 'sources',
            'premises', 'expressions', 'scenarios'}
    fields(profile, keys, keys)
    if profile['version'] != VERSION or digest(profile) != expected_profile_sha256:
        raise ValueError('Pinned explicit holder profile changed')
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    if (KEY in ordinary or ordinary.get('report_sha256') != digest(body)
            or digest(ordinary) != profile['ordinary_answer_sha256']):
        raise ValueError('Complete preceding ordinary answer changed')
    review = ordinary.get('default_f_review', {})
    if (review.get('selected_reading', 'missing') is not None
            or review.get('candidate_set_exhaustive') is not False
            or review.get('governing_language') != 'German'
            or review.get('source_meaning_promoted') is not False):
        raise ValueError('Existing unselected default alternatives required')
    if (digest(profile['premises']) != digest(premises())
            or digest(profile['expressions']) != digest(expressions())
            or digest({k: v for k, v in profile['groups'].items() if k != 'representative'}) != digest(review['groups'])):
        raise ValueError('Source or explicit holder hypotheses changed')
    expected_sources = deepcopy(review['sources'])
    base = expected_sources[0]
    if (not isinstance(profile['sources'], list) or len(profile['sources']) != 2
            or any(not isinstance(s, dict) for s in profile['sources'])
            or not isinstance(profile['sources'][0].get('images'), list)
            or len(profile['sources'][0]['images']) != len(base['images']) + 1):
        raise ValueError('Original default sources plus representative page required')
    image = profile['sources'][0]['images'][-1]
    fields(image, {'page', 'path', 'sha256'}, {'page', 'path', 'sha256'})
    if type(image['page']) is not int or image['page'] != 130:
        raise ValueError('Inspected German representative page required')
    base['images'].append(image)
    if digest(profile['sources']) != digest(expected_sources):
        raise ValueError('Original default and representative sources required')
    validate_scenarios(profile['scenarios'])


def metadata(profile):
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': profile['products_sha256'],
        'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'sources': deepcopy(profile['sources']), 'groups': deepcopy(profile['groups']),
        'premises': premises(), 'expressions': expressions(),
        'governing_language': 'German', 'selected_reading': None, 'candidate_set_exhaustive': False,
        'source_meaning_promoted': False, 'actual_holder_authority_established': False,
        'actual_default_established': False, 'independent_legal_acceptance': False,
        'scope': 'Conditional individual exercise of default(f) under each supplied nonexhaustive reading at exercise; no representative exercise or complete grounds(b)/(c) quorum decision.',
        'historical_notice': 'The prior review retains its bundled eligible-holder premise unchanged. These scenarios separately supply holder status, notice form/delivery and authority; no historical facts are inferred.',
        'source_applicability': 'Conditional on the supplied selected contract and unamended clauses; actual mandate, resolution, statutory validity and events remain unestablished.'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    policy(ordinary, profile, expected_profile_sha256)
    if profile['products_sha256'] != digest(products) or digest(profile['groups']) != digest(source_groups(products)):
        raise ValueError('Original products or complete source groups changed')
    for source in profile['sources']:
        for item in [source, *source['images']]:
            if Path(item['path']).is_absolute() or digest(bound_path(root, item['path']).read_bytes()) != item['sha256']:
                raise ValueError('Original PDF or inspected image changed')
    return {KEY: {**metadata(profile), 'scenarios': [analyze(s) for s in profile['scenarios']]}}
