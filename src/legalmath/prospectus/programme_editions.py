"""Optional review of printed Japanese programme editions; no legal application."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import re

from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'japanese-programme-edition-review.v1'
DATE = r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'


def printed_date(text):
    match = re.fullmatch(DATE, text.strip())
    if match is None:
        raise ValueError('Expected one complete printed Japanese date')
    return date(*(int(v) for v in match.groups())).isoformat()


def period(text):
    match = re.fullmatch('(' + DATE + r')\s*から\s*(' + DATE + r')\s*まで', text.strip())
    if match is None:
        raise ValueError('Expected complete printed issuance period')
    # Outer captures preserve each literal alongside the individual date fields.
    start, end = printed_date(match.group(1)), printed_date(match.group(5))
    if start > end:
        raise ValueError('Printed issuance period is reversed')
    return {'start': start, 'end': end, 'raw': text}


def screen_editions(target_date, issuer, candidates):
    """A date/issuer screen nominates candidates; it never proves legal scope."""
    date.fromisoformat(target_date)
    rows = []
    for candidate in candidates:
        date.fromisoformat(candidate['date'])
        status = ('ISSUER_MISMATCH' if candidate['issuer'] != issuer else
                  'EDITION_MISMATCH' if candidate['date'] != target_date else
                  'EDITION_COMPATIBLE_REQUIRES_REVIEW')
        rows.append({**candidate, 'status': status})
    matched = [r for r in rows if r['status'] == 'EDITION_COMPATIBLE_REQUIRES_REVIEW']
    state = 'MISSING_TARGET' if not matched else 'COMPATIBLE_CANDIDATE' if len(matched) == 1 else 'AMBIGUOUS_TARGET'
    return {'target_state': state, 'candidates': rows, 'accepted_relations': [], 'legal_effect_established': False}


def review(graph, profile, root, *, expected_profile_sha256):
    keys = {'version', 'source_graph_sha256', 'reviewer', 'sources', 'programmes', 'correction', 'accepted_relations'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['source_graph_sha256'] != digest(graph)):
        raise ValueError('Pinned edition profile or source graph changed')
    if profile['accepted_relations'] != []:
        raise ValueError('Edition review cannot accept legal relations')
    reviewer = profile['reviewer']
    fields(reviewer, {'identity', 'basis', 'independent'}, {'identity', 'basis', 'independent'})
    if (not isinstance(reviewer['identity'], str) or not reviewer['identity'].strip()
            or reviewer['basis'] != 'AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported reviewer or independent acceptance')
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']) or any(u['text_sha256'] != digest(u['raw'].encode()) for u in units.values()):
        raise ValueError('Duplicate occurrence or changed source text')
    root = Path(root).resolve()
    sources = {}
    for source in profile['sources']:
        expected = {'document', 'source_path', 'source_sha256', 'cover_path', 'cover_sha256'}
        fields(source, expected, expected)
        if source['document'] in sources:
            raise ValueError('Duplicate original source descriptor')
        for path_key, hash_key in (('source_path', 'source_sha256'), ('cover_path', 'cover_sha256')):
            name = source[path_key]
            path = (root / name).resolve()
            if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != source[hash_key]:
                raise ValueError('Original source or cover image changed')
        source_units = [u for u in units.values() if u['document'] == source['document']]
        if not source_units or any(u['source_sha256'] != source['source_sha256'] for u in source_units):
            raise ValueError('Foreign original source')
        sources[source['document']] = source

    def full(anchor, document):
        bound = bind(graph, anchor)
        unit = units[bound['unit']]
        if (document not in sources or bound['document'] != document or bound['page'] != 1
                or anchor['start'] != 0 or anchor['end'] != len(unit['raw'])):
            raise ValueError('Complete cover occurrence required for the named source')
        return anchor['quote']

    def identity(row):
        document = row['document']
        if full(row['issuer_label'], document) != '【発行者の名称】':
            raise ValueError('Issuer field label changed')
        if full(row['publication_label'], document) != '【公表日】':
            raise ValueError('Publication field label changed')
        issuer = full(row['issuer'], document)
        if not issuer.strip():
            raise ValueError('Empty issuer')
        return {'document': document, 'issuer': issuer, 'date': printed_date(full(row['publication_date'], document))}

    row_keys = {'document', 'issuer_label', 'issuer', 'publication_label', 'publication_date'}
    candidates = []
    for row in profile['programmes']:
        fields(row, row_keys, row_keys)
        candidates.append(identity(row))
    # Repeated compatible candidate records remain explicitly ambiguous, never
    # silently deduplicated or promoted to one governing edition.
    correction = profile['correction']
    extra = {'target_context', 'before_label', 'after_label', 'before_period_label', 'after_period_label', 'before_period', 'after_period'}
    fields(correction, row_keys | extra, row_keys | extra)
    correction_id = identity(correction)
    doc = correction['document']
    if any(c['document'] == doc for c in candidates):
        raise ValueError('Correction cannot be its own programme target')
    context = correction['target_context']
    if not isinstance(context, list) or not context:
        raise ValueError('Complete correction target context required')
    text = ''.join(full(a, doc) for a in context)
    order = [units[a['unit']]['order'] for a in context]
    if order != list(range(order[0], order[-1] + 1)):
        raise ValueError('Omitted or reordered target context')
    match = re.match(r'この訂正プログラム情報は、(' + DATE + r')付プログラム情報', text)
    if (match is None or '本プログラム情報により公表された情報と併せて検討した上で' not in text
            or not text.endswith('投資判断を行う必要があります。')):
        raise ValueError('Explicit target and joint-reading qualification required')
    target = printed_date(match.group(1))
    for key, literal in (('before_label', '（訂正前）'), ('after_label', '（訂正後）'),
                         ('before_period_label', '【発行予定期間】'), ('after_period_label', '【発行予定期間】')):
        if full(correction[key], doc) != literal:
            raise ValueError('Correction before/after field label changed')
    source_order = [units[correction[key]['unit']]['order'] for key in
        ('before_label', 'before_period_label', 'before_period', 'after_label', 'after_period_label', 'after_period')]
    if source_order != sorted(set(source_order)):
        raise ValueError('Correction before/after scope reordered')
    before = period(full(correction['before_period'], doc))
    after = period(full(correction['after_period'], doc))
    result = screen_editions(target, correction_id['issuer'], candidates)
    return {**result, 'version': VERSION, 'profile_sha256': digest(profile),
        'correction_publication_date': correction_id['date'], 'target_programme_date': target,
        'printed_before_period': before, 'printed_after_period': after,
        'context': deepcopy(context), 'field_associations': 'SUPPLIED_EXPOSED_REVIEW',
        'independent_legal_acceptance': False, 'complete_amendment_scope': False,
        'profile': deepcopy(profile)}


def consume(products, profile, root, *, expected_profile_sha256):
    from .successor.service import consume as ordinary_consume
    edition_review = review(products['P1']['payload']['graph'], profile, root,
                            expected_profile_sha256=expected_profile_sha256)
    return {'answer': ordinary_consume(products, root, include_artifacts=True), 'edition_review': edition_review}
