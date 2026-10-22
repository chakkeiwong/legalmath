"""Finite source-reviewed statutory readings, separate from operative contracts.

This profile establishes retained readings and their limitations. It does not
discover law, authenticate an agreement, or prove historical applicability.
"""
from copy import deepcopy
import json
from pathlib import Path

from .anchors import bind, fields
from .contracts import digest
from .occurrences import segments

PROFILE_SHA256 = 'd2f9ef77505a840204b5109426431e6b54b9679c213b08823e0e5372c3c92572'


MEASURE_MEANINGS = ['Change of maturity, reduction or exclusion of interest', 'Change of maturity of principal', 'Reduction of principal', 'Subordination of note claims in the debtor insolvency proceedings', 'Conversion or exchange of notes into shares, other securities or other promises of performance', 'Exchange or release of collateral', 'Change of the currency of the notes', 'Waiver or restriction of holders termination rights']

def validate_numbered_measures(spec):
    record = next(r for r in spec['records'] if r['id'] == 'H38')
    rows = record.get('numbered_measures')
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or [r.get('number') for r in rows] != list(range(1, 9))):
        raise ValueError('H38 requires exact ordered statutory measures1-8')
    source = record['legal_sources'][0]; excerpt = source['excerpts'][0]
    import re
    text = excerpt['quote']; start = text.index('(3)'); end = text.index('(4)')
    matches = list(re.finditer(r'(?m)^([1-9]|10)\.\n([^\n]+)', text[start:end]))
    if [int(m[1]) for m in matches] != list(range(1, 11)):
        raise ValueError('H38 primary numbered source changed')
    for row, match, meaning in zip(rows, matches[:8], MEASURE_MEANINGS):
        a = excerpt['start'] + start + match.start(); b = excerpt['start'] + start + match.end()
        expected = {'number': int(match[1]), 'source_path': source['text_path'],
                    'source_sha256': source['text_sha256'], 'start': a, 'end': b,
                    'quote': text[a-excerpt['start']:b-excerpt['start']], 'meaning': meaning}
        if row != expected:
            raise ValueError('H38 numbered measure differs from complete primary source')
    return rows


TIMING_RULES = [{'id': 'principal_presentation', 'source_index': 0, 'quote': 'Der Anspruch aus einer Schuldverschreibung auf den Inhaber erlischt mit dem Ablauf von 30 Jahren nach dem Eintritt der für die Leistung bestimmten Zeit, wenn nicht die Urkunde vor dem Ablauf der 30 Jahre dem Aussteller zur Einlösung vorgelegt wird.', 'meaning': {'clock': 'PRESENTATION', 'default_years': 30, 'origin': 'PERFORMANCE_DUE', 'effect': 'EXTINCTION_IF_NOT_PRESENTED_WITHIN_PERIOD', 'deed_variation': 'SUBJECT_TO_801_3'}}, {'id': 'limitation_after_presentation', 'source_index': 0, 'quote': 'Erfolgt die Vorlegung, so verjährt der Anspruch in zwei Jahren von dem Ende der Vorlegungsfrist an.', 'meaning': {'clock': 'LIMITATION', 'years': 2, 'origin': 'END_OF_PRESENTATION_PERIOD', 'condition': 'PRESENTATION_WITHIN_PERIOD', 'presentation_date_is_origin': False}}, {'id': 'judicial_equivalence', 'source_index': 0, 'quote': 'Der Vorlegung steht die gerichtliche Geltendmachung des Anspruchs aus der Urkunde gleich.', 'meaning': {'judicial_assertion_of_instrument_claim': 'EQUIVALENT_TO_PRESENTATION'}}, {'id': 'coupon_presentation', 'source_index': 0, 'quote': 'Bei Zins-, Renten- und Gewinnanteilscheinen beträgt die Vorlegungsfrist vier Jahre. Die Frist beginnt mit dem Schluss des Jahres, in welchem die für die Leistung bestimmte Zeit eintritt.', 'meaning': {'clock': 'PRESENTATION', 'claim_types': ['INTEREST_COUPON', 'ANNUITY_COUPON', 'PROFIT_SHARE_COUPON'], 'default_years': 4, 'origin': 'END_OF_YEAR_PERFORMANCE_DUE', 'deed_variation': 'SUBJECT_TO_801_3'}}, {'id': 'deed_variation', 'source_index': 0, 'quote': 'Die Dauer und der Beginn der Vorlegungsfrist können von dem Aussteller in der Urkunde anders bestimmt werden.', 'meaning': {'clock': 'PRESENTATION', 'issuer_may_vary_in_deed': ['DURATION', 'BEGINNING']}}, {'id': 'payment_stop_suspension', 'source_index': 1, 'quote': 'Der Beginn und der Lauf der Vorlegungsfrist sowie der Verjährung werden durch die Zahlungssperre zugunsten des Antragstellers gehemmt. Die Hemmung beginnt mit der Stellung des Antrags auf Zahlungssperre; sie endigt mit der Erledigung des Aufgebotsverfahrens und, falls die Zahlungssperre vor der Einleitung des Verfahrens verfügt worden ist, auch dann, wenn seit der Beseitigung des der Einleitung entgegenstehenden Hindernisses sechs Monate verstrichen sind und nicht vorher die Einleitung beantragt worden ist. Auf diese Frist finden die Vorschriften der §§ 206, 210, 211 entsprechende Anwendung.', 'meaning': {'clocks': ['PRESENTATION', 'LIMITATION'], 'effect': 'SUSPENSION_OF_BEGINNING_AND_RUNNING', 'beneficiary': 'APPLICANT', 'begins': 'APPLICATION_FOR_PAYMENT_STOP', 'ends': ['COMPLETION_OF_PUBLIC_NOTICE_PROCEEDINGS', 'IF_STOP_PRECEDES_PROCEEDINGS_SIX_MONTHS_AFTER_IMPEDIMENT_REMOVED_WITHOUT_PRIOR_INITIATION_APPLICATION'], 'onward_provisions': [206, 210, 211], 'onward_application': 'UNRESOLVED'}}]

def validate_timing_rules(spec):
    record = next(r for r in spec['records'] if r['id'] == 'H28')
    rows = record.get('timing_rules')
    if (not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)
            or [r.get('id') for r in rows] != [r['id'] for r in TIMING_RULES]):
        raise ValueError('H28 complete ordered timing rules required')
    for row, rule in zip(rows, TIMING_RULES):
        source = record['legal_sources'][rule['source_index']]
        matches = [e for e in source['excerpts'] if rule['quote'] in e['quote']]
        if len(matches) != 1 or matches[0]['quote'].count(rule['quote']) != 1:
            raise ValueError('H28 exact timing source missing or ambiguous')
        start = matches[0]['start'] + matches[0]['quote'].index(rule['quote'])
        expected = {'id': rule['id'], 'source_path': source['text_path'],
            'source_sha256': source['text_sha256'], 'start': start,
            'end': start + len(rule['quote']), 'quote': rule['quote'], 'meaning': rule['meaning']}
        if row != expected:
            raise ValueError('H28 timing meaning or exact source changed')
    return rows


def specification():
    value = json.loads(Path(__file__).with_name('statutory_references_spec.json').read_text())
    if digest(value) != PROFILE_SHA256:
        raise ValueError('Statutory reference registered profile changed')
    validate_numbered_measures(value)
    validate_timing_rules(value)
    return value


def packet(evidence_state='RETAINED'):
    spec = specification()
    return {'profile': spec['profile'], 'evidence_state': evidence_state,
            'records': deepcopy(spec['records'])}


def admit(graph, assembly, request):
    if 'statutory_references' not in request:
        return None
    value = request['statutory_references']
    fields(value, {'profile', 'evidence_state', 'records'},
           {'profile', 'evidence_state', 'records'})
    spec = specification()
    if (value['profile'] != spec['profile'] or value['evidence_state'] not in ('RETAINED', 'NOT_SUPPLIED')
            or digest(value['records']) != digest(spec['records'])):
        raise ValueError('Statutory reference requires the exact registered source reading and edition')
    raw = {u['id']: u for u in graph['units']}
    selected = {u['unit']: u for u in assembly['units']}
    if len(raw) != len(graph['units']) or len(selected) != len(assembly['units']):
        raise ValueError('Statutory reference duplicate occurrence identity')
    records = []
    for expected in spec['records']:
        for part in expected['contract_selection']:
            source = part['original']
            bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
            actual = selected.get(part['selected']['unit'])
            if (actual != part['selected'] or actual['role'] != 'OPERATIVE'
                    or segments(graph, actual, _raw=raw) != part['segments']):
                raise ValueError('Statutory reference selected contract context changed')
        for source in expected['context_anchors']:
            bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
        # A statute cannot be resolved to an operative contract with the same
        # section number. Preserve generic unresolved discovery edges unchanged.
        for discovery in expected['discovery_bindings']:
            found = [r for r in graph['references'] if r['id'] == discovery['reference']['id']]
            if found != [discovery['reference']]:
                raise ValueError('Statutory reference discovery identity changed')
            if discovery['reference']['id'] in request.get('reference_dispositions', {}):
                raise ValueError('Statutory reference cannot target an operative contract clause')
        for row in (request.get('reference_admission') or {}).get('references', []):
            source = row['source']
            if any(source['unit'] == p['original']['unit']
                   and source['start'] < p['original']['end'] and p['original']['start'] < source['end']
                   for p in expected['contract_selection']):
                raise ValueError('Statutory reference cannot use contract reference admission')
        record = deepcopy(expected)
        record['availability'] = ('RETAINED_PRIMARY_READING' if value['evidence_state'] == 'RETAINED'
                                  else 'NOT_SUPPLIED')
        record['application'] = 'UNKNOWN'
        record['uncertainties'] = ['HISTORICAL_EDITION_NOT_PROVED', 'ONWARD_SCOPE_OPEN',
                                   'APPLICATION_PREMISES_NOT_ESTABLISHED']
        if value['evidence_state'] == 'NOT_SUPPLIED':
            record['uncertainties'].insert(0, 'PRIMARY_READING_NOT_SUPPLIED')
            record['legal_sources'] = []
        records.append(record)
    bundle = request['bundle']
    return {'version': 'statutory-reference-review.v1', 'profile': spec['profile'],
            'profile_sha256': digest(spec), 'evidence_state': value['evidence_state'],
            'as_of': {k: bundle[k] for k in ('issue_date', 'effective_at', 'known_at')},
            'records': records, 'automatic_discovery': False,
            'historical_application_proved': False, 'complete_reference_graph': False,
            'meaning': 'Reviewed source readings with unresolved historical and conditional application'}


def dependencies(report):
    if report is None:
        return []
    return [{'id': 'statutory-reference:' + r['id'], 'kind': 'LEGAL_AUTHORITY',
             'questions': ['Q1', 'Q2', 'Q4'], 'status': 'UNRESOLVED',
             'profile_sha256': report['profile_sha256'], 'record_sha256': digest(r),
             'source_uses': [p['selected']['unit'] for p in r['contract_selection']],
             'availability': r['availability'], 'historical_validity': r['historical_validity'],
             'literal_extent': r['literal_extent'], 'onward_scope': r['onward_scope'],
             'application': r['application'], 'uncertainties': r['uncertainties']}
            for r in report['records']]


def verify_consumed(graph, assembly, request, semantic):
    expected = admit(graph, assembly, request)
    if expected is None:
        if 'statutory_references' in semantic:
            raise ValueError('Consumed statutory reference lacks supplied evidence')
    elif digest(semantic.get('statutory_references')) != digest(expected):
        raise ValueError('Consumed statutory reference reading differs from reconstruction')
    if expected is not None:
        required = dependencies(expected)
        observed = [d for d in semantic['dependencies'] if d['id'].startswith('statutory-reference:')]
        if digest(observed) != digest(required):
            raise ValueError('Consumed statutory dependencies differ from reconstruction')
        ids = {d['id'] for d in required}
        for key in ('Q1', 'Q2'):
            parent = semantic['questions'][key]
            for answer in (parent, *parent.get('subquestions', {}).values()):
                actual = [i for i in answer['unresolved'] if i.startswith('statutory-reference:')]
                if set(actual) != ids or len(actual) != len(ids):
                    raise ValueError('Consumed statutory question hides or invents uncertainty')
                if answer['status'] not in ('UNKNOWN', 'CONFLICT') or answer['value'] is not None:
                    raise ValueError('Consumed statutory question resolves uncertainty')
    return expected


def law_question(conditional, report):
    if report is None:
        return conditional
    value = deepcopy(conditional)
    value.update(status='CONFLICT' if value['status'] == 'CONFLICT' else 'UNKNOWN', value=None)
    value['unresolved'] = list(dict.fromkeys([*value['unresolved'],
                                            *(d['id'] for d in dependencies(report))]))
    return value


def verify_law(legal, source_request, graph, report):
    if report is None:
        if 'statutory_references' in legal or 'conditional_question' in legal:
            raise ValueError('Consumed statutory law result lacks supplied evidence')
        return
    from . import law_facts
    request = {**source_request, **(legal.get('law_input') or {})}
    conditional = law_facts.assess(
        request['bundle'], request.get('law_bases', []), request.get('facts', []), graph,
        request.get('law_relation'), predicate_engine=request.get('predicate_engine', 'finite'),
        ratio_facts=request.get('ratio_facts'), calendar_facts=request.get('calendar_facts'),
        law_explanation=request.get('law_explanation'))
    if (digest(legal.get('conditional_question')) != digest(conditional)
            or digest(legal.get('statutory_references')) != digest(report)
            or digest(legal['question']) != digest(law_question(conditional, report))):
        raise ValueError('Consumed statutory law uncertainty differs from reconstruction')
