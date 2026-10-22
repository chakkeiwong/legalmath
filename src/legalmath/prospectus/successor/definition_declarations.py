"""Finite German naming syntax, with source provenance and no legal promotion.

The detector never receives reviewed definitions. Reconciliation is a separate
operation: exact naming tokens refine broad excerpts without selecting meaning,
governing scope, historical law or actual facts.
"""
from copy import deepcopy
import re

from .contracts import digest
from .definition_discovery import discover as quoted_labels
from . import reference_mentions as raw
from . import reference_resolution as sources

ARTICLE = r'(?:der|die|das|den|dem|des|ein|eine|einen|einer|einem|eines)'
QUOTE = r'"[^"\r]{1,256}"'
ALIAS = r'(?:(?:jeweils|zusammen),?\s+)?(?:' + ARTICLE + r'\s+)?' + QUOTE
PAREN = re.compile(r'\s*' + ALIAS + r'(?:\s+(?:oder|und)\s+' + ALIAS + r')*\s*', re.I)
COORDINATED = re.compile(r'[^";!?]{1,200}\bjeweils\s+' + ARTICLE + r'\s+' + QUOTE +
                         r'\s+und\s+zusammen\s+' + ARTICLE + r'\s+' + QUOTE + r'\s*', re.I)
DASH = re.compile(r'[^"();!?]{1,160}\s+[–—-]\s*' + QUOTE + r'\s*')
PURPOSE = re.compile(r'\bFür\s+(?:diese\s+Zwecke|(?:die\s+)?Zwecke\s+(?:'
                     r'dieses\s+§\s*[0-9]+|dieser\s+\w+|dieses\s+\w+|des\s+Vorstehenden))\b', re.I)
NEGATIVE = re.compile(r'\b(?:nicht|kein(?:e|en|er|es|em)?)\b', re.I)


def validate(request):
    raw.fields(request, ('version', 'language', 'source', 'layout'), 'Declaration request')
    raw.require(request['version'] == 'definition-declaration-request.v1', 'Declaration version differs')
    raw.require(request['language'] == 'de', 'Only the declared German grammar is supported')
    return sources.validate({'version': 'reference-resolution-request.v1',
                             'source': request['source'], 'layout': request['layout']})


def evidence(request, layout, start, end):
    text = request['source']['text']
    projection = raw.projection(request['source'], start, end)
    identities = sources.identities(projection, layout)
    bound = sources.fully_bound(text, projection) and len(identities) == 1
    roles = {layout[p['source']['unit']]['role'] for p in projection if p['source']}
    return {'start': start, 'end': end, 'raw': text[start:end], 'source_projection': projection,
            'source_bound': bound, 'operative': bound and roles == {'OPERATIVE'}}


def parentheses(text):
    """Ignore parentheses inside quoted labels such as a named Call day."""
    stack, output, quoted = [], [], False
    for pos, char in enumerate(text):
        if char == '"':
            quoted = not quoted
        elif not quoted and char == '(':
            stack.append(pos)
        elif not quoted and char == ')' and stack:
            output.append((stack.pop(), pos + 1))
    return output


def syntax(text, name, pairs):
    a, b = name['quote_start'], name['quote_end']
    enclosing = [(left, right) for left, right in pairs if left < a < b < right and right-left <= 800]
    for left, right in sorted(enclosing, key=lambda p: p[1]-p[0]):
        body = text[left+1:right-1]
        for kind, pattern in [('PARENTHETICAL_NAMING', PAREN), ('COORDINATED_NAMING', COORDINATED),
                              ('DASH_NAMING', DASH)]:
            if pattern.fullmatch(body):
                return kind, left, right
    before, after = text[max(0, a-160):a], text[b:min(len(text), b+240)]
    # The finite predicate grammar is declarative. A question or explicit
    # negation is not affirmative naming evidence. Sentence punctuation is a
    # syntactic boundary, not a claim to parse every abbreviation or meaning.
    clause_before = re.split(r'[.;!?]', before)[-1]
    ending = re.search(r'[.;!?]', after)
    tail_clause = after[:ending.start()] if ending else after
    if (ending and ending.group() == '?') or NEGATIVE.search(clause_before):
        return None
    if re.search(r'\b(?:wenn|falls|ob)\b', clause_before, re.I):
        return None
    suffix = re.match(r'\s+(bedeutet|bezeichnet|ist)\b', after, re.I)
    prefix = re.search(r'\b(bedeutet|bezeichnet|ist|gilt)\s+(?:' + ARTICLE + r'\s+)?$', before, re.I)
    if suffix and not NEGATIVE.search(after[suffix.end():suffix.end()+32]):
        word = suffix.group(1).lower()
        if word != 'ist' or re.match(r'\s+' + ARTICLE + r'\b', after[suffix.end():], re.I):
            return ('COPULAR_PREDICATE' if word == 'ist' else 'DEFINING_VERB', a, b+suffix.end())
    if prefix and not NEGATIVE.search(tail_clause[:40]):
        left = max(0, a-160)+prefix.start()
        word = prefix.group(1).lower()
        if word in ('bedeutet', 'bezeichnet'):
            return 'DEFINING_VERB', left, b
        if word == 'ist' and re.match(r'\s+' + ARTICLE + r'\b', after, re.I):
            return 'COPULAR_PREDICATE', left, b
        if word == 'gilt':
            event = re.match(r'[^";.!?]{0,140}\bals\s+eingetreten\b', after, re.I)
            if event:
                return 'CONDITIONAL_EVENT_PREDICATE', left, b+event.end()
    equating = re.match(r'\s+(?:in\s+Bezug\s+auf\s+[^";.!?]{1,120}?\s+)?entspricht\b', after, re.I)
    if equating and not NEGATIVE.search(after[:equating.end()+32]):
        return 'EQUATING_PREDICATE', a, b+equating.end()
    return None


def discover(request):
    text, layout = validate(request)
    lexical = quoted_labels({'text': text, 'text_sha256': request['source']['text_sha256'],
        'language': 'de', 'regions': [{'id': 'selected', 'start': 0, 'end': len(text),
                                    'language': 'de', 'selected': True}]})
    pairs, names = parentheses(text), []
    for name in lexical['names']:
        token = evidence(request, layout, name['start'], name['end'])
        found = syntax(text, name, pairs)
        cue = evidence(request, layout, found[1], found[2]) if found else None
        status = ('UNRESOLVED_SOURCE' if not token['source_bound'] or (cue and not cue['source_bound']) else
                  'NON_OPERATIVE' if not token['operative'] or (cue and not cue['operative']) else
                  'DECLARATION_SYNTAX' if found else 'QUOTED_LABEL_ONLY')
        names.append({'id': digest({'start': name['start'], 'end': name['end'], 'request': digest(request)}),
            'label': name['label'], **token, 'status': status,
            'observed_syntax': found[0] if found else None,
            'syntax': found[0] if found and status == 'DECLARATION_SYNTAX' else None,
            'syntax_evidence': cue, 'review_required': True,
            'legal_declaration_established': False, 'governing_scope': None})
    restrictions = []
    for match in PURPOSE.finditer(text):
        restrictions.append({**evidence(request, layout, match.start(), match.end()),
            'kind': 'PRINTED_PURPOSE_RESTRICTION', 'resolved_extent': None,
            'governing_scope_established': False})
    report = {'version': 'definition-declaration-report.v1', 'request_sha256': digest(request),
        'text_sha256': request['source']['text_sha256'], 'names': names, 'restrictions': restrictions,
        'issues': deepcopy(lexical['issues']), 'legal_truth_established': False,
        'general_recall_established': False, 'document_authenticity_established': False,
        'whole_task_complete': False, 'meaning_admitted': False, 'scope_admitted': False,
        'unsupported_mechanisms': ['unquoted definitions', 'unrestricted German grammar',
                                  'non-ASCII quotation', 'morphology', 'legal scope and precedence']}
    return {**report, 'report_sha256': digest(report)}


def reconcile(request, report, lineage):
    """Attach exact reviewed tokens after discovery; conserve existing readings."""
    text, layout = validate(request)
    raw.require(report == discover(request), 'Declaration report differs from source-only result')
    raw.fields(lineage, ('version', 'text_sha256', 'source_answer_sha256', 'records', 'naming_tokens',
                         'uses', 'dependencies'), 'Reviewed lineage')
    raw.require(lineage['version'] == 'reviewed-definition-lineage.v1', 'Lineage version differs')
    raw.require(lineage['text_sha256'] == request['source']['text_sha256'], 'Lineage source differs')
    raw.require(raw.checksum(lineage['source_answer_sha256']), 'Source answer identity missing')
    for key in ('records', 'naming_tokens', 'dependencies', 'uses'):
        raw.require(isinstance(lineage[key], list) and len(lineage[key]) <= 10000, 'Unbounded lineage '+key)
    records = {r['id']: r for r in lineage['records']}
    raw.require(len(records) == len(lineage['records']) and records, 'Duplicate/empty records')
    for rec in records.values():
        raw.require(raw.checksum(rec['original_record_sha256']), 'Record identity missing')
        for decl in rec['declarations']:
            a, b = decl['start'], decl['end']
            raw.require(type(a) is int and type(b) is int and 0 <= a < b <= len(text) and
                        text[a:b] == decl['quote'], 'Declaration excerpt source differs')
    names = {(n['start'], n['end']): n for n in report['names']}
    matched, keys = {ident: [] for ident in records}, set()
    for token in lineage['naming_tokens']:
        raw.fields(token, ('record', 'start', 'end', 'raw'), 'Naming token')
        ident, a, b = token['record'], token['start'], token['end']
        raw.require(ident in records and type(a) is int and type(b) is int and 0 < a < b < len(text), 'Naming token bounds differ')
        raw.require(text[a:b] == token['raw'] and text[a-1] == text[b] == '"', 'Naming token source differs')
        raw.require((ident, a, b) not in keys, 'Duplicate naming token')
        keys.add((ident, a, b))
        rec = records[ident]
        raw.require(' '.join(token['raw'].split()) in [' '.join(f.split()) for f in rec['forms']], 'Naming token/form differs')
        raw.require(any(d['start'] <= a < b <= d['end'] for d in rec['declarations']), 'Naming token outside declaration excerpt')
        name = names.get((a, b))
        matched[ident].append({'token': deepcopy(token), 'detected_name': name['id'] if name else None,
            'status': name['status'] if name else 'NOT_DISCOVERED',
            'syntax': name['syntax'] if name else None,
            'source_projection': raw.projection(request['source'], a, b), 'legal_meaning_established': False})
    for use in lineage['uses']:
        a, b = use['start'], use['end']
        raw.require(use['record'] in records and use['origin'] in ('ORIGINAL', 'SUPPLEMENTAL'), 'Use lineage differs')
        raw.require(type(a) is int and type(b) is int and 0 <= a < b <= len(text) and text[a:b] == use['quote'], 'Use source differs')
    raw.require({d['record'] for d in lineage['dependencies']} == set(records) and
                len(lineage['dependencies']) == len(records), 'Dependency record coverage differs')
    for dep in lineage['dependencies']:
        raw.require(all(type(i) is int and 0 <= i < len(lineage['uses']) and
                        lineage['uses'][i]['record'] == dep['record'] for i in dep['use_indices']), 'Dependency use indices differ')
    reconciled = [{'record': ident, 'naming_tokens': matched[ident],
        'disposition': 'EXACT_NAMING_TOKEN_ACCOUNTED' if matched[ident] else 'OUTSIDE_QUOTED_NAMING_SCOPE',
        'retained_record_sha256': digest(rec), 'remaining_premises': deepcopy(next(
            d['remaining_premises'] for d in lineage['dependencies'] if d['record'] == ident))}
        for ident, rec in records.items()]
    result = {'version': 'definition-declaration-reconciliation.v1', 'request_sha256': digest(request),
        'discovery_sha256': report['report_sha256'], 'reviewed_lineage_sha256': digest(lineage),
        'retained_lineage': deepcopy(lineage), 'records': reconciled,
        'extra_names': [n['id'] for n in report['names'] if not any((a,b)==(n['start'],n['end']) for _,a,b in keys)],
        'legal_truth_established': False, 'general_recall_established': False, 'whole_task_complete': False,
        'meaning_changed': False, 'governing_scope_resolved': False, 'premises_removed': False}
    return {**result, 'report_sha256': digest(result)}
