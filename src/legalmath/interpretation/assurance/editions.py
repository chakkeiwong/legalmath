"""Select provisions from one explicitly described clean edition of a document.

The manifest is an inspected structural proposal, not an effectiveness judgment.
Its hash must be bound by the caller's evidence workflow. Marked revisions remain
available as history but cannot enter the active source-packet units.
"""
from copy import deepcopy
from pathlib import Path
from typing import Literal
from pydantic import Field

from ...canonical import digest, raw_digest
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, Hash, Packet, parse


class Edition(Strict):
    edition_id: Id
    kind: Literal['CLEAN', 'MARKED_CHANGES']
    first_page: int = Field(ge=1)
    last_page: int = Field(ge=1)
    printed_edition: Text


class Provision(Strict):
    provision_id: Id
    edition_id: Id
    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    quote: Text
    required_links: list[Id] = Field(max_length=100)
    relationship: Literal['SECTION', 'CONTINUATION', 'FOOTNOTE', 'APPLICATION', 'VERSION_NOTICE']


class Manifest(Strict):
    source_sha256: Hash
    page_hashes: list[Hash] = Field(min_length=1, max_length=1000)
    editions: list[Edition] = Field(min_length=1, max_length=100)
    provisions: list[Provision] = Field(min_length=1, max_length=1000)
    structural_review: Text
    unresolved_authority_questions: list[Text] = Field(max_length=100)


def select(pdf, page_texts, manifest, *, expected_manifest_hash, edition_id, provision_ids):
    if digest(manifest) != expected_manifest_hash:
        raise LegalMathError('E_STALE_REVIEW')
    m = parse(Manifest, manifest)
    if raw_digest(Path(pdf).read_bytes()) != m['source_sha256']:
        raise LegalMathError('E_HASH_MISMATCH')
    if [raw_digest(p.encode()) for p in page_texts] != m['page_hashes']:
        raise LegalMathError('E_HASH_MISMATCH')
    editions = {e['edition_id']: e for e in m['editions']}
    provisions = {p['provision_id']: p for p in m['provisions']}
    if len(editions) != len(m['editions']) or len(provisions) != len(m['provisions']):
        raise LegalMathError('E_DUPLICATE_ID')
    used_pages = set()
    for e in editions.values():
        if not 1 <= e['first_page'] <= e['last_page'] <= len(page_texts):
            raise LegalMathError('E_REFERENCE')
        pages = set(range(e['first_page'], e['last_page']+1))
        if pages & used_pages:
            raise LegalMathError('E_REFERENCE', details='Overlapping edition ranges')
        used_pages |= pages
    for p in provisions.values():
        e = editions.get(p['edition_id'])
        if e is None or not e['first_page'] <= p['page'] <= e['last_page']:
            raise LegalMathError('E_REFERENCE')
        text = page_texts[p['page']-1]
        if not 0 <= p['start'] < p['end'] <= len(text) or text[p['start']:p['end']] != p['quote']:
            raise LegalMathError('E_REFERENCE')
        if len(set(p['required_links'])) != len(p['required_links']) or not set(p['required_links']) <= set(provisions):
            raise LegalMathError('E_REFERENCE')
    selected = set(provision_ids)
    if not selected or len(selected) != len(provision_ids) or not selected <= set(provisions):
        raise LegalMathError('E_REFERENCE')
    e = editions.get(edition_id)
    if e is None or e['kind'] != 'CLEAN':
        raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Active packets require an explicitly selected clean edition')
    if any(provisions[i]['edition_id'] != edition_id for i in selected):
        raise LegalMathError('E_REFERENCE', details='Cross-edition active provisions are forbidden')
    missing = {link for i in selected for link in provisions[i]['required_links']} - selected
    if missing:
        raise LegalMathError('E_DEPENDENCY', details={'missing_provisions': sorted(missing)})
    units = [{'unit_id': i, 'locator': f"{edition_id}, PDF page {provisions[i]['page']}, offsets {provisions[i]['start']}:{provisions[i]['end']}",
              'text': provisions[i]['quote'], 'normative': True,
              'span': {'source_sha256': m['source_sha256'], 'page': provisions[i]['page'],
                       'start': provisions[i]['start'], 'end': provisions[i]['end']}}
             for i in sorted(selected)]
    packet = {'source_key': 'edition.'+digest(m)[:24], 'authority': 'RETAINED_SOURCE',
              'selected_slice': f'Selected provisions of {edition_id}; effectiveness unresolved',
              'units': units, 'dependencies': [
                  {'dependency_id': 'authority.'+digest(q)[:24], 'source_hash': None}
                  for q in m['unresolved_authority_questions']], 'family_ids': ['edition.'+edition_id]}
    parse(Packet, packet)
    return {'packet': packet, 'manifest_hash': expected_manifest_hash,
        'selected_edition': deepcopy(e), 'selected_provision_ids': sorted(selected),
        'required_relationships': {i: provisions[i]['required_links'] for i in sorted(selected)},
        'excluded_editions': [deepcopy(v) for k, v in editions.items() if k != edition_id],
        'unresolved_authority_questions': m['unresolved_authority_questions'],
        'source_effectiveness': 'NOT_ESTABLISHED', 'all_qualifications_identified': False,
        'release_eligible': False}
