"""Finite Portuguese report-context checks, not general semantic verification."""
from datetime import date
import re

from .contracts import digest

PROFILE = 'portuguese-report-context.v1'
AUDIT_PROFILE = 'portuguese-report-context.v2'
SUPPORTED_PROFILES = frozenset((PROFILE, AUDIT_PROFILE))

# Finite readings inspected in Portuguese003, not a Portuguese role grammar.
# Intervals address the complete retained OCR text, including its source noise.
_SOURCE = 'e7284e7f098ab405b24d461e493e0f0a043ed57f10eca5ac18f31a4bbdee588a'
_INSPECTED = {
    '408f84fac9c9f451d4936dcc59b97ec204e4cb68ddcc891706bf604b822e0ab5': {
        'pages': (245, 246, 247), 'kind': 'STATUTORY_FINANCIAL_AUDIT',
        'roles': {
            'board_responsibilities': (1214, 2198),
            'auditor_responsibility': (2687, 3044),
            'audit_scope': (3054, 4394),
            'management_report_concordance': (4397, 4577),
            'opinion_basis': (4580, 4678),
            'financial_statement_opinion': (4749, 5340),
            'assurance_sentence': (3280, 3421),
            'opinion_materiality': (4864, 4909),
        },
    },
    '243f45067bf23eaf3a92a795fbe004047a7d7835771972fedd12141abdb115af': {
        'pages': (248, 249), 'kind': 'STATUTORY_FINANCIAL_AUDIT',
        'roles': {
            'board_responsibilities': (1031, 2142),
            'auditor_responsibility': (2145, 2501),
            'audit_scope': (3006, 4052),
            'management_report_concordance': (4055, 4223),
            'opinion_basis': (4226, 4324),
            'financial_statement_opinion': (4335, 4872),
            'assurance_sentence': (3232, 3360),
            'opinion_materiality': (4437, 4482),
        },
    },
    'db9babfddd401bee2c8cbb146e3c5cb84d2f820b5a5b68265994cae153ecba4a': {
        'pages': (250, 251), 'kind': 'COMMITTEE_REPORT', 'roles': {},
    },
}
_MONTHS = {name: i for i, name in enumerate(
    ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
     'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'), 1)}
_DATE = r'(?P<day>\d{1,2})\s+de\s+(?P<month>' + '|'.join(_MONTHS) + r')\s+de\s+(?P<year>\d{4})'
_DATES = re.compile(_DATE, re.I)
_CLOSING = re.compile(r'^(?P<place>[^\W\d_]+(?:[ \t]+[^\W\d_]+){0,5}),[ \t]*'
                      r'(?P<date>' + _DATE + r')[ \t]*\.?[ \t]*(?=\n|$)', re.I | re.M)
_SIGNER = re.compile(r'^(?:A\s+)?Comissão\s+de\s+Auditoria\s*$|'
                     r'^(?:Sociedade\s+de\s+)?Revisor(?:es)?\s+Oficia(?:l|is)\s+de\s+Contas\b', re.I)
_NCA = re.compile(r'\bNormas\s+de\s+Contabilidade\s+Ajustadas\b', re.I)
_ALIAS = re.compile(r'''\(\s*["“”]?NCA['’]?s["“”]?\s*\)''', re.I)
_EXCEPTION = re.compile(r'\b(?:com\s+excepção|excepto|exceto|salvo)\b', re.I)


def _span(reading, start, end):
    return {'start': start, 'end': end, 'quote': reading['text'][start:end],
            'source_characters': [c for c in reading['characters'] if start <= c['output'] < end]}


def _covered(fact, text, start, end):
    return fact['status'] == 'SUPPLIED' and all(
        c.isspace() or any(s['start'] <= i < s['end'] for s in fact['spans'])
        for i, c in enumerate(text[start:end], start))


def _date_role(reading, fact):
    text = reading['text']
    candidates = []
    for match in _CLOSING.finditer(text):
        try:
            normalized = date(int(match['year']), _MONTHS[match['month'].casefold()], int(match['day'])).isoformat()
        except ValueError:
            continue
        following = [line for line in re.finditer(r'[^\n]+', text[match.end():]) if line.group().strip()][:3]
        signers = [line for line in following if _SIGNER.search(line.group().strip())]
        if len(signers) != 1:
            continue
        signer = signers[0]
        candidates.append({'normalized_date': normalized,
            'closing_line': _span(reading, match.start(), match.end()),
            'date': _span(reading, match.start('date'), match.end('date')),
            'signatory_cue': _span(reading, match.end() + signer.start(), match.end() + signer.end())})
    status = 'MATCHES_PRINTED_CLOSING_DATE'
    if fact['status'] != 'SUPPLIED':
        status = 'DATE_NOT_SUPPLIED'
    elif len(candidates) != 1:
        status = 'NO_UNIQUE_SUPPORTED_CLOSING_DATE'
    else:
        required = candidates[0]['date']
        if not _covered(fact, text, required['start'], required['end']):
            status = 'REPORT_DATE_ROLE_MISMATCH'
        elif any((m.start(), m.end()) != (required['start'], required['end'])
                 and any(s['start'] < m.end() and m.start() < s['end'] for s in fact['spans'])
                 for m in _DATES.finditer(text)):
            status = 'REPORT_DATE_QUOTES_COMPETING_EVENTS'
    return {'status': status, 'consistent': status == 'MATCHES_PRINTED_CLOSING_DATE',
            'closing_candidates': candidates,
            'limit': 'Printed place/date/signatory form only; no publication, authenticity or arbitrary date-role proof'}


def _criteria(reading, facts):
    if facts['identity'].get('value') != 'STATUTORY_FINANCIAL_AUDIT':
        return {'status': 'NOT_APPLICABLE_TO_THIS_REPORT_KIND', 'consistent': True, 'definitions': []}
    text = reading['text']
    starts = list(_NCA.finditer(text))
    exceptions = list(_EXCEPTION.finditer(text))
    if not starts and not exceptions:
        return {'status': 'NO_LOCAL_EXCEPTION_RULE_TRIGGERED', 'consistent': True, 'definitions': [],
                'limit': 'No recognized trigger is not proof that all accounting qualifications were checked'}
    definitions = []
    for index, start in enumerate(starts):
        stop = min(start.start() + 1500, starts[index + 1].start() if index + 1 < len(starts) else len(text))
        alias = _ALIAS.search(text, start.end(), stop)
        if alias is None:
            continue
        definition = text[start.start():alias.end()]
        if (_EXCEPTION.search(definition) and re.search(r'\bBanco\s+de\s+Portugal\b', definition, re.I)
                and re.search(r'\bNormas\s+Internacionais\s+de\s+Relato\s+Financeiro\b', definition, re.I)):
            definitions.append(_span(reading, start.start(), alias.end()))
    if (not definitions or any(not any(d['start'] <= e.start() and e.end() <= d['end'] for d in definitions)
                               for e in exceptions)):
        status = 'UNRESOLVED_ACCOUNTING_EXCEPTION_CONTEXT'
    elif not all(_covered(facts['criteria'], text, d['start'], d['end']) for d in definitions):
        status = 'OMITTED_LOCAL_ACCOUNTING_QUALIFICATION'
    else:
        status = 'FULL_LOCAL_DEFINITION_RETAINED'
    return {'status': status, 'consistent': status == 'FULL_LOCAL_DEFINITION_RETAINED',
            'definitions': definitions,
            'limit': 'Exact retained NCA-definition coverage only; no independent judgment of applicable accounting law'}


def _provenance(reading):
    text, seen, origins = reading['text'], set(), set()
    for char in reading['characters']:
        out, offset, unit = char['output'], char['source_offset'], char['unit']
        if (type(out) is not int or not 0 <= out < len(text) or out in seen or
                type(offset) is not int or offset < 0 or not isinstance(unit, str) or not unit or
                (unit, offset) in origins or char['character'] != text[out]):
            raise ValueError('Portuguese report character provenance changed')
        seen.add(out)
        origins.add((unit, offset))
    if any(i not in seen for i, c in enumerate(text) if not c.isspace()):
        raise ValueError('Portuguese report has unmapped source characters')


def _role(reading, fact, interval):
    text = reading['text']
    a, b = interval
    consistent = _covered(fact, text, a, b)
    status = 'REQUIRED_SOURCE_ROLE_RETAINED' if consistent else 'REQUIRED_SOURCE_ROLE_NOT_SUPPLIED'
    if consistent and any(not c.isspace() and not a <= i < b
                          for s in fact['spans']
                          for i, c in enumerate(text[s['start']:s['end']], s['start'])):
        consistent, status = False, 'SUPPLIED_QUOTATIONS_INCLUDE_OTHER_SOURCE_ROLES'
    return {'consistent': consistent, 'status': status, 'required_spans': [_span(reading, a, b)]}


def _audit_roles(reading, facts):
    inspected = _INSPECTED.get(digest(reading['text'].encode()))
    known = (inspected is not None and reading['source_sha256'] == _SOURCE and
             reading['pages'] == [{'page': p, 'mode': 'raw'} for p in inspected['pages']])
    checks = {'source_structure': {
        'consistent': known,
        'status': 'EXACT_INSPECTED_SOURCE_READING' if known else 'UNRECOGNIZED_OR_CHANGED_SOURCE_READING',
        'limit': 'Finite full-text, PDF edition and ordered-page identity; no authenticity or unseen-language proof'}}
    if not known:
        return checks, {}
    _provenance(reading)
    if facts['identity'].get('value') not in (None, inspected['kind']):
        raise ValueError('Inspected Portuguese report contradicts supplied report category')
    roles = inspected['roles']
    if roles:
        checks['conclusion'] = _role(reading, facts['conclusion'], roles['financial_statement_opinion'])
        checks['assurance_level'] = _role(reading, facts['assurance_level'], roles['assurance_sentence'])
    return checks, {name: _span(reading, a, b) for name, (a, b) in roles.items()}


def check(reading, facts, profile=PROFILE):
    """Use full P2 text and already bound supplied spans, never expected targets."""
    if not isinstance(profile, str) or profile not in SUPPORTED_PROFILES:
        raise ValueError('Explicit supported report context profile required')
    checks = {'report_date': _date_role(reading, facts['report_date']), 'criteria': _criteria(reading, facts)}
    roles = {}
    if profile == AUDIT_PROFILE:
        audit_checks, roles = _audit_roles(reading, facts)
        checks.update(audit_checks)
    return {'profile': profile, 'checks': checks,
            'unresolved_fields': sorted(name for name, result in checks.items() if not result['consistent']),
            'general_semantic_truth_established': False,
            **({'distinct_source_statements': roles} if roles else {})}
