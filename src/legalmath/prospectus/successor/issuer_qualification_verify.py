"""Independent categorical table and staged truth-set publication checker."""
from copy import deepcopy
from itertools import product

HOME = ('GERMANY', 'OTHER_EU_EEA', 'NEITHER')
ADMISSION = ('ONLY_GERMANY_ORGANISED', 'ONLY_OTHER_EU_EEA', 'NEITHER_EXCLUSIVE')
TABLE = ((True, 'UNLESS_FOREIGN_DUTY', True), (True, False, False), (False, False, False))


def qualification(facts):
    keys = ('home_state', 'admission_scope', 'foreign_transparency_duties')
    missing = [k for k in keys if facts[k] is None]
    conflicts = [k for k in keys if facts[k] == 'conflict']
    outcomes = set()
    if not conflicts:
        homes = range(3) if facts['home_state'] is None else (HOME.index(facts['home_state']),)
        admissions = range(3) if facts['admission_scope'] is None else (ADMISSION.index(facts['admission_scope']),)
        for i, j in product(homes, admissions):
            item = TABLE[i][j]
            if item == 'UNLESS_FOREIGN_DUTY':
                value = facts['foreign_transparency_duties']
                outcomes.update((False, True) if value is None else (not value,))
            else: outcomes.add(item)
    return {'status': 'CONFLICT' if conflicts else 'YES' if outcomes == {True} else 'NO' if outcomes == {False} else 'UNKNOWN',
        'missing': missing, 'conflicts': conflicts}


def truth(values, function):
    if any(v == 'conflict' for v in values): return 'conflict'
    outcomes = {function(*w) for w in product(*[(False, True) if v is None else (v,) for v in values])}
    return True if outcomes == {True} else False if outcomes == {False} else None

def status(value):
    return 'CONFLICT' if value == 'conflict' else 'UNKNOWN' if value is None else 'YES' if value else 'NO'


def publication_decisions(p):
    trigger = truth([p[k] for k in ('inlandsemittent_qualified', 'admitted_security_rights_change',
        'nonshare_terms_change_affecting_rights', 'relevant_third_country_information')],
        lambda issuer, rights, terms, third: issuer and (rights or terms or third))
    duties = truth([trigger] + [p[k] for k in ('statutory_reading_applies', 'implementing_rules_satisfied',
        'simultaneous_bafin_notification', 'simultaneous_register_transmission')], lambda *v: all(v))
    values = [p[k] for k in ('german_seat', 'bundesanzeiger_publication', 'section13_notice_satisfied', 'prompt_publication')] + [duties]
    broad = truth(values, lambda g, b, n, p, s: not g or (p and ((b and n) or s)))
    retained = truth(values, lambda g, b, n, p, s: not g or (p and n and (b or s)))
    common = [p[k] for k in ('contract_reading_applies', 'suitable_public_announcement_at_issuer_expense', 'separate_website_duty_satisfied')]
    routes = {'broad_replacement': broad, 'section13_retained': retained}
    return {'qualified_information': status(trigger), 'statutory_conditions': status(duties),
        'german_seat_routes': {k: status(v) for k, v in routes.items()},
        'conditional_contract_readings': {k: status(truth([v] + common, lambda *w: all(w))) for k, v in routes.items()}}


def verify_answer(answer, ordinary, profile, *, expected_profile_sha256):
    from .contracts import digest
    from .issuer_qualification import KEY, metadata, policy
    cases = policy(ordinary, profile, expected_profile_sha256)
    body = {k: v for k, v in answer.items() if k != 'report_sha256'}
    if (answer.get('report_sha256') != digest(body)
            or digest({k: v for k, v in body.items() if k != KEY})
            != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Complete preceding answer changed')
    review = answer.get(KEY, {})
    if digest({k: v for k, v in review.items() if k != 'scenarios'}) != digest(metadata(profile)):
        raise ValueError('Issuer context or scope changed')
    expected = []
    for row in profile['scenarios']:
        q = qualification(row['qualification']); base = cases[row['base_case']]
        derived = deepcopy(base); derived['id'] = row['id']
        derived['premises']['inlandsemittent_qualified'] = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}[q['status']]
        old = publication_decisions(base['premises']); new = publication_decisions(derived['premises'])
        expected.append({**row, 'qualification_result': q, 'derived_publication_scenario': derived,
            'publication_decisions': new, 'baseline_decisions': old, 'answer_changed': old != new})
    if digest(review.get('scenarios')) != digest(expected):
        raise ValueError('Issuer qualification or downstream consequence changed')
    return {'status': 'PASS', 'scenarios': len(expected),
        'changed_scenarios': sum(r['answer_changed'] for r in expected),
        'complete_ordinary_preserved': True, 'actual_issuer_status_established': False}
