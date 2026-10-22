"""Current BGB source readings linked to a preserved conditional H28 answer."""
from copy import deepcopy
import json

from .contracts import bound_path, digest

KEY = 'bgb802_onward_review'
REGISTERED_PROFILE_SHA256 = 'c9abef511b9313f795c6bbfd031f2a78d80b0b9fd35a3432efea3090d2918c24'
VERSION = 'bgb802-onward-readings.v1'
SCOPE = 'BGB802_PRE_INITIATION_SIX_MONTH_PERIOD'

# Literal primary wording is kept distinct from the local correspondence.
LITERAL = {
    '206': {
        'effect': 'SUSPENSION_WHILE_PREVENTED',
        'conditions': ['CREDITOR_PREVENTED_FROM_PURSUING_RIGHT', 'FORCE_MAJEURE',
                       'WITHIN_LAST_SIX_MONTHS_OF_LIMITATION'],
        'exceptions': [],
    },
    '210': {
        'effect': 'PREVENTION_OF_EXPIRY',
        'conditions': ['PERSON_INCAPABLE_OR_LIMITED_LEGAL_CAPACITY',
                       'NO_LEGAL_REPRESENTATIVE', 'LIMITATION_FOR_OR_AGAINST_PERSON'],
        'after_event_months': 6,
        'alternative_events': ['UNRESTRICTED_LEGAL_CAPACITY', 'REPRESENTATION_DEFECT_REMEDIED'],
        'exceptions': ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS',
                       'PARAGRAPH1_EXCLUDED_INSOFAR_LIMITED_CAPACITY_PERSON_HAS_PROCEDURAL_CAPACITY'],
    },
    '211': {
        'effect': 'PREVENTION_OF_EXPIRY',
        'conditions': ['CLAIM_BELONGS_TO_OR_IS_DIRECTED_AGAINST_ESTATE'],
        'after_event_months': 6,
        'alternative_events': ['INHERITANCE_ACCEPTED_BY_HEIR', 'ESTATE_INSOLVENCY_OPENED',
                               'CLAIM_CAN_BE_ASSERTED_BY_OR_AGAINST_REPRESENTATIVE'],
        'exceptions': ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS'],
        'actual_event_priority_established': False,
    },
}
CHECKS = {
    '206': ['Die Verjährung ist gehemmt, solange der Gläubiger innerhalb der letzten sechs Monate der Verjährungsfrist durch höhere Gewalt an der Rechtsverfolgung gehindert ist.'],
    '210': ['(1) Ist eine geschäftsunfähige oder in der Geschäftsfähigkeit beschränkte Person ohne gesetzlichen Vertreter, so tritt eine für oder gegen sie laufende Verjährung nicht vor dem Ablauf von sechs Monaten nach dem Zeitpunkt ein, in dem die Person unbeschränkt geschäftsfähig oder der Mangel der Vertretung behoben wird.',
            'Ist die Verjährungsfrist kürzer als sechs Monate, so tritt der für die Verjährung bestimmte Zeitraum an die Stelle der sechs Monate.',
            '(2) Absatz 1 findet keine Anwendung, soweit eine in der Geschäftsfähigkeit beschränkte Person prozessfähig ist.'],
    '211': ['Die Verjährung eines Anspruchs, der zu einem Nachlass gehört oder sich gegen einen Nachlass richtet, tritt nicht vor dem Ablauf von sechs Monaten nach dem Zeitpunkt ein, in dem die Erbschaft von dem Erben angenommen oder das Insolvenzverfahren über den Nachlass eröffnet wird oder von dem an der Anspruch von einem oder gegen einen Vertreter geltend gemacht werden kann.',
            'Ist die Verjährungsfrist kürzer als sechs Monate, so tritt der für die Verjährung bestimmte Zeitraum an die Stelle der sechs Monate.'],
}
SIX_MONTHS = 'falls die Zahlungssperre vor der Einleitung des Verfahrens verfügt worden ist, auch dann, wenn seit der Beseitigung des der Einleitung entgegenstehenden Hindernisses sechs Monate verstrichen sind und nicht vorher die Einleitung beantragt worden ist.'
ONWARD = 'Auf diese Frist finden die Vorschriften der §§ 206, 210, 211 entsprechende Anwendung.'


def _require(condition, message):
    if not condition:
        raise ValueError('BGB onward: ' + message)


def _source(root, row):
    path = bound_path(root, row['text_path'])
    raw = path.read_bytes()
    _require(digest(raw) == row['text_sha256'], 'retained text bytes changed')
    text = raw.decode('utf-8', errors='strict')
    _require(type(row['excerpts']) is list and bool(row['excerpts']), 'exact excerpts required')
    for excerpt in row['excerpts']:
        a, b = excerpt['start'], excerpt['end']
        _require(type(a) is int and type(b) is int and 0 <= a < b <= len(text), 'invalid source offsets')
        _require(text[a:b] == excerpt['quote'], 'source quotation changed')
    return text


def evaluate(products, ordinary, profile, root, expected_profile_sha256=None):
    _require(type(profile) is dict and digest(profile) == expected_profile_sha256 == REGISTERED_PROFILE_SHA256,
             'registered profile identity required')
    _require(profile['version'] == VERSION, 'unsupported reading version')
    _require(profile['products_sha256'] == digest(products), 'source products changed')
    _require(profile['ordinary_answer_sha256'] == digest(ordinary), 'complete prior answer changed')
    _require(ordinary['report_sha256'] == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'}),
             'invalid prior report digest')
    h28s = [r for r in ordinary['statutory_references']['records'] if r['id'] == 'H28']
    _require(len(h28s) == 1, 'unique original H28 required')
    h28 = h28s[0]
    _require(h28['availability'] == 'RETAINED_PRIMARY_READING' and h28['application'] == 'UNKNOWN',
             'H28 retained reading and unresolved application required')
    _require(digest(h28) == profile['h28_record_sha256'], 'original H28 record changed')
    _require(profile['scope']['antecedent'] == SCOPE and
             profile['scope']['status'] == 'LOCAL_GRAMMATICAL_CONSTRUCTION' and
             profile['scope']['application_to_all_clocks_proved'] is False, 'scope cannot be broadened')
    scope_text = _source(root, profile['scope']['source'])
    _require([e['quote'] for e in profile['scope']['source']['excerpts']] == [SIX_MONTHS, ONWARD],
             'complete802 six-month antecedent and onward sentence required')
    _require(profile['scope']['source']['text_path'] == h28['legal_sources'][1]['text_path'] and
             profile['scope']['source']['text_sha256'] == h28['legal_sources'][1]['text_sha256'],
             'scope source must be original H28 BGB802')
    _require(scope_text.count(SIX_MONTHS) == scope_text.count(ONWARD) == 1, 'ambiguous802 anchor')
    _require(profile['scope']['source']['excerpts'][0]['end'] <
             profile['scope']['source']['excerpts'][1]['start'], '802 antecedent must precede reference')
    _require([r['section'] for r in profile['readings']] == ['206', '210', '211'],
             'complete ordered onward readings required')
    for row in profile['readings']:
        section = row['section']
        _require(row['literal_rule'] == LITERAL[section], 'literal conditions, exceptions or effect changed')
        text = _source(root, row['source'])
        quote = '\n'.join(e['quote'] for e in row['source']['excerpts'])
        _require(all(part in quote for part in CHECKS[section]), 'complete primary rule and exceptions required')
        _require('§ ' + section + ' ' in text, 'wrong primary section')
        _require(row['local_corresponding_application']['target_period'] == SCOPE and
                 row['local_corresponding_application']['application_proved'] is False and
                 row['local_corresponding_application']['construction'], 'conditional mapping required')
        _require(row['historical_application_proved'] is False and bool(row['unresolved']),
                 'historical/application uncertainty required')
        source = row['source']
        _require(digest(bound_path(root, source['raw_path']).read_bytes()) == source['raw_sha256'],
                 'retained original HTML changed')
        receipt_bytes = bound_path(root, source['receipt_path']).read_bytes()
        _require(digest(receipt_bytes) == source['receipt_sha256'], 'request receipt changed')
        receipt = json.loads(receipt_bytes)
        _require(receipt['url'] == 'https://www.gesetze-im-internet.de/bgb/__' + section + '.html' and
                 receipt['http_code'] == 200 and receipt['exit_code'] == 0 and
                 receipt['files']['body'] == source['raw_sha256'], 'wrong official source receipt')
    for name in ('historical_application_proved', 'actual_deadline_computed',
                 'automatic_legal_interpretation', 'whole_task_complete', 'whole_build_complete'):
        _require(profile[name] is False, 'false legal or completion promotion')
    _require(profile['unresolved'] == ['HISTORICAL_WORDING', 'CORRESPONDING_APPLICATION',
             'PERSON_AND_CLAIM_FACTS', 'EVENT_DATES', 'CIVIL_COUNTING_CONVENTIONS'],
             'application uncertainties missing')
    report = {k: deepcopy(v) for k, v in profile.items()}
    report.update(profile_sha256=digest(profile), original_h28_preserved=True,
                  complete_prior_answer_preserved=True,
                  finding='Current literal conditions retained;802 antecedent is a local construction;actual application remains unknown')
    return {KEY: report}
