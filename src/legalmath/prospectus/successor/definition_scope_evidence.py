"""Printed self-section boundaries, independent of reviewed semantic extents.

UNKNOWN label roles remain UNKNOWN. A printed boundary is a consistency check
on an assisted reading; it establishes neither header authority nor legal scope.
"""
from copy import deepcopy
import hashlib
import re

from .contracts import digest
from .definition_declarations import PURPOSE

LABEL = re.compile(r'(?m)^[ \t]*§[ \t]*([0-9]+)[ \t]*(?=\r?$)')
SELF_SECTION = re.compile(r'Für\s+(?:die\s+)?Zwecke\s+dieses\s+§\s*([0-9]+)', re.I)
SOURCE_KEYS = ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(request):
    require(isinstance(request, dict) and set(request) ==
            {'version', 'text', 'text_sha256', 'source_pieces'}, 'Scope discovery requires source only')
    require(request['version'] == 'definition-scope-evidence-request.v1', 'Scope request version differs')
    text = request['text']
    require(isinstance(text, str) and 0 < len(text) <= 1_000_000, 'Scope source size differs')
    require(hashlib.sha256(text.encode()).hexdigest() == request['text_sha256'], 'Scope source hash differs')
    pieces = request['source_pieces']
    require(isinstance(pieces, list) and 0 < len(pieces) <= 100_000, 'Scope pieces are unbounded')
    position = 0
    for piece in pieces:
        require(isinstance(piece, dict), 'Scope piece is not a mapping')
        a, b = piece.get('start'), piece.get('end')
        require(type(a) is int and type(b) is int and a == position and a < b <= len(text),
                'Scope pieces have gaps, overlap or invalid bounds')
        require(piece.get('text') == text[a:b], 'Scope piece differs from selected text')
        position = b
    require(position == len(text), 'Scope pieces do not cover selected text')
    return text, pieces


def identity(piece):
    """Qualify a complete raw copy and its unique matching assembly use."""
    raw, uses = piece.get('raw_binding'), piece.get('assembly_uses')
    if (piece.get('kind') != 'EXACT_SOURCE_COPY' or not isinstance(raw, dict)
            or not isinstance(uses, list) or len(uses) != 1 or not isinstance(uses[0], dict)):
        return None
    use = uses[0]
    if not all(k in raw for k in SOURCE_KEYS):
        return None
    if (type(raw['start']) is not int or type(raw['end']) is not int or
            not 0 <= raw['start'] < raw['end'] or raw['end'] - raw['start'] != len(piece['text'])
            or raw['quote'] != piece['text']):
        return None
    if (not all(isinstance(raw[k], str) and raw[k] for k in ('unit', 'document', 'source_sha256'))
            or not re.fullmatch('[0-9a-f]{64}', raw['source_sha256'])):
        return None
    if (type(use.get('start')) is not int or type(use.get('end')) is not int
            or not 0 <= use['start'] < use['end']
            or use['end'] - use['start'] != len(piece['text'])
            or not isinstance(use.get('source'), dict) or
            any(use['source'].get(k) != raw[k] for k in SOURCE_KEYS) or
            use.get('unit') != raw['unit'] or
            not isinstance(use.get('context'), str) or not use['context'] or
            not isinstance(use.get('role'), str) or not use['role']):
        return None
    return raw['document'], raw['source_sha256'], use['context']


def interval_evidence(pieces, start, end):
    identities, roles = set(), set()
    for piece in pieces:
        if piece['start'] >= end or piece['end'] <= start:
            continue
        if (piece.get('kind') == 'GENERATED_SEPARATOR' and piece.get('raw_binding') is None
                and not piece.get('assembly_uses') and piece['text'].isspace()):
            continue
        found = identity(piece)
        if found is None:
            return None, []
        identities.add(found)
        roles.add(piece['assembly_uses'][0]['role'])
    return (next(iter(identities)) if len(identities) == 1 else None), sorted(roles)


def discover(request):
    text, pieces = validate(request)
    labels = []
    for match in LABEL.finditer(text):
        a, b = match.span()
        found, roles = interval_evidence(pieces, a, b)
        labels.append({'start': a, 'end': b, 'raw': text[a:b], 'section': match.group(1),
                       'identity': found, 'roles': roles,
                       'printed_copy': found is not None and len(roles) == 1
                       and roles[0] in ('HEADER', 'UNKNOWN')})
    output = []
    for match in PURPOSE.finditer(text):
        a, b = match.span()
        row = {'start': a, 'end': b, 'raw': text[a:b], 'status': 'REVIEW_REQUIRED',
               'extent': None, 'section': None, 'source_identity': None, 'label_roles': [],
               'boundary_roles': [], 'legal_scope_established': False,
               'remaining': ['PURPOSE_REQUIRES_INTERPRETATION']}
        explicit = SELF_SECTION.fullmatch(match.group())
        if explicit:
            row['remaining'] = ['PRINTED_SELF_SECTION_NOT_UNIQUELY_BOUND']
            preceding = [i for i, label in enumerate(labels) if label['end'] <= a]
            if preceding and preceding[-1] + 1 < len(labels):
                i = preceding[-1]
                left, right = labels[i:i+2]
                origin, roles = interval_evidence(pieces, a, b)
                continuous, _ = interval_evidence(pieces, left['start'], right['end'])
                same = [label for label in labels if label['section'] == explicit.group(1)
                        and label['identity'] == origin]
                if (left['section'] == explicit.group(1) and b <= right['start']
                        and left['printed_copy'] and right['printed_copy']
                        and origin is not None and roles == ['OPERATIVE'] and
                        left['identity'] == right['identity'] == continuous == origin and len(same) == 1):
                    row.update(status='EXPLICIT_SECTION', section=explicit.group(1),
                               extent=[left['start'], right['start']], source_identity=list(origin),
                               label_roles=left['roles'], boundary_roles=right['roles'],
                               remaining=['LEGAL_SCOPE_AUTHORITY_NOT_ESTABLISHED'])
        output.append(row)
    report = {'version': 'definition-scope-evidence-report.v1', 'request_sha256': digest(request),
              'text_sha256': request['text_sha256'], 'restrictions': output,
              'legal_scope_established': False, 'document_authenticity_established': False,
              'whole_task_complete': False, 'general_recall_established': False}
    return {**report, 'report_sha256': digest(report)}


def check_rules(text, source_pieces, rules):
    """Check supplied readings only after source-only boundary derivation."""
    request = {'version': 'definition-scope-evidence-request.v1', 'text': text,
               'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'source_pieces': source_pieces}
    report = discover(request)
    checked = []
    for rule in rules:
        for premise in rule['premises']:
            a, b = premise['start'], premise['end']
            require(type(a) is int and type(b) is int and 0 <= a < b <= len(text)
                    and text[a:b] == premise['quote'], 'Definition scope premise differs from source')
            for restriction in report['restrictions']:
                if not (a <= restriction['start'] < restriction['end'] <= b
                        and SELF_SECTION.fullmatch(restriction['raw'])):
                    continue
                require(restriction['status'] == 'EXPLICIT_SECTION',
                        'Definition explicit section lacks continuous printed source evidence')
                require(rule['extents'] == [restriction['extent']],
                        'Definition supplied extent conflicts with printed self-section')
                checked.append({'rule': rule['id'], 'restriction_start': restriction['start'],
                                'extent': deepcopy(restriction['extent'])})
    for restriction in report['restrictions']:
        if SELF_SECTION.fullmatch(restriction['raw']):
            require(sum(row['restriction_start'] == restriction['start'] for row in checked) == 1,
                    'Definition explicit restriction is missing or duplicated in supplied premises')
    return {'checked': checked, 'source_report_sha256': report['report_sha256'],
            'legal_scope_established': False}
