"""Source-bound authority editions and bounded provision closure.

Catalog assertions have explicit evidence and provenance. Exact matching checks
identity and retained bytes; it cannot prove the legal interpretation of a date,
incorporation or selected context. Unknowns are preserved as first-class results.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs
from typing import Literal
from pydantic import Field
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, Hash, parse
from .sources import extract_document, official_url


class Anchor(Strict):
    edition_id: Id
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: Text


class Authority(Strict):
    authority_id: Id
    issuer: Text
    jurisdiction: Text
    kind: Literal['CODE', 'FAQ', 'CIRCULAR', 'LEGISLATION', 'CASE_LAW', 'OFFICIAL_EXAMPLE', 'SOURCE_INDEX']
    title: Text
    identity_evidence: list[Anchor] = Field(min_length=1, max_length=12)


class Edition(Strict):
    edition_id: Id
    authority_id: Id
    url: Text
    raw_sha256: Hash
    text_sha256: Hash
    media_type: Literal['application/pdf', 'application/json', 'text/html', 'text/plain']
    path: Text
    retrieved_at: Text
    published_on: str | None
    effective_from: str | None
    effective_until: str | None
    temporal_evidence: list[Anchor] = Field(max_length=12)
    temporal_status: Literal['DOCUMENTED_INTERVAL', 'UNKNOWN']


class Region(Strict):
    region_id: Id
    role: Literal['PROVISION', 'HEADING', 'DEFINITION', 'QUALIFICATION', 'FOOTNOTE', 'CONTEXT']
    anchor: Anchor


class Provision(Strict):
    provision_id: Id
    authority_id: Id
    edition_id: Id
    locator: Text
    regions: list[Region] = Field(min_length=1, max_length=100)
    requires: list[Id] = Field(max_length=100)
    unresolved_references: list[Text] = Field(max_length=100)
    context_status: Literal['REVIEWED_SELECTION', 'PROPOSED_SELECTION']
    selection_basis: Text


class Alias(Strict):
    locator: Text
    authority_id: Id
    provision_locator: Text
    evidence: list[Anchor] = Field(min_length=1, max_length=12)
    basis: Text


class Relationship(Strict):
    relationship_id: Id
    source_provision_id: Id
    target_provision_id: Id
    kind: Literal['CITES', 'INCORPORATES', 'AMENDS', 'REPLACES']
    evidence: list[Anchor] = Field(min_length=1, max_length=12)
    basis: Text


class Catalog(Strict):
    version: Literal['authority-catalog.v1']
    authorities: list[Authority] = Field(max_length=100)
    editions: list[Edition] = Field(max_length=200)
    provisions: list[Provision] = Field(max_length=500)
    aliases: list[Alias] = Field(max_length=500)
    relationships: list[Relationship] = Field(max_length=500)


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise LegalMathError('E_TIME')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise LegalMathError('E_TIME') from exc


def key(locator):
    return re.sub(r'\s+', ' ', locator).strip().casefold()


class AuthorityCatalog:
    def __init__(self, value, documents):
        self.value = parse(Catalog, value)
        self.hash = digest(self.value)
        self.documents = documents
        self.authorities = self._index('authorities', 'authority_id')
        self.editions = self._index('editions', 'edition_id')
        self.provisions = self._index('provisions', 'provision_id')
        self._index('relationships', 'relationship_id')
        for eid, edition in self.editions.items():
            if edition['authority_id'] not in self.authorities:
                raise LegalMathError('E_REFERENCE')
            official_url(edition['url'])
            for field in ('published_on', 'effective_from', 'effective_until'):
                if edition[field] is not None:
                    iso_date(edition[field])
            if edition['effective_until'] and (not edition['effective_from'] or
                    edition['effective_until'] <= edition['effective_from']):
                raise LegalMathError('E_TIME')
            if edition['temporal_status'] == 'DOCUMENTED_INTERVAL' and (
                    edition['effective_from'] is None or not edition['temporal_evidence']):
                raise LegalMathError('E_REFERENCE', details='Applicable interval requires retained temporal evidence')
            doc = documents.get(eid)
            if doc is not None and (raw_digest(doc['data']) != edition['raw_sha256'] or
                                   doc['text_sha256'] != edition['text_sha256'] or
                                   doc['url'] != edition['url'] or doc['media_type'] != edition['media_type']):
                raise LegalMathError('E_HASH_MISMATCH')
        for provision in self.provisions.values():
            edition = self.editions.get(provision['edition_id'])
            if not edition or edition['authority_id'] != provision['authority_id']:
                raise LegalMathError('E_REFERENCE')
            if len({r['region_id'] for r in provision['regions']}) != len(provision['regions']):
                raise LegalMathError('E_DUPLICATE_ID')
            if any(r['anchor']['edition_id'] != provision['edition_id'] for r in provision['regions']):
                raise LegalMathError('E_REFERENCE')
            if not any(r['role'] == 'PROVISION' for r in provision['regions']):
                raise LegalMathError('E_REFERENCE')
            # Missing requires are allowed only as explicitly unresolved closure.
        for alias in self.value['aliases']:
            if alias['authority_id'] not in self.authorities:
                raise LegalMathError('E_REFERENCE')
        for rel in self.value['relationships']:
            if rel['source_provision_id'] not in self.provisions or rel['target_provision_id'] not in self.provisions:
                raise LegalMathError('E_REFERENCE')
        self._verify_anchors(self.value)

    def _index(self, collection, field):
        rows = self.value[collection]; result = {r[field]: r for r in rows}
        if len(result) != len(rows):
            raise LegalMathError('E_DUPLICATE_ID')
        return result

    def _verify_anchors(self, value):
        if isinstance(value, dict):
            if set(value) == {'edition_id', 'start', 'end', 'quote'}:
                if value['edition_id'] not in self.editions:
                    raise LegalMathError('E_REFERENCE')
                doc = self.documents.get(value['edition_id'])
                if doc is not None and (value['start'] >= value['end'] or
                        doc['text'][value['start']:value['end']] != value['quote']):
                    raise LegalMathError('E_REFERENCE', details='Authority span differs from retained text')
            for item in value.values():
                self._verify_anchors(item)
        elif isinstance(value, list):
            for item in value:
                self._verify_anchors(item)

    def _available_evidence(self, anchors):
        return bool(anchors) and all(a['edition_id'] in self.documents for a in anchors)

    @classmethod
    def load(cls, path):
        path = Path(path).resolve(); value = parse(Catalog, loads(path.read_bytes())); documents = {}
        for edition in value['editions']:
            source = (path.parent / edition['path']).resolve()
            if not source.is_relative_to(path.parent):
                raise LegalMathError('E_REFERENCE', details='Catalog files must remain within the catalog directory')
            if not source.is_file():
                continue
            raw = source.read_bytes()
            if raw_digest(raw) != edition['raw_sha256']:
                raise LegalMathError('E_HASH_MISMATCH')
            doc = {'data': raw, 'url': official_url(edition['url']), 'media_type': edition['media_type']}
            documents[edition['edition_id']] = {**doc, **extract_document(doc)}
        return cls(value, documents)

    def resolve(self, locator, at, *, issuer='Securities and Futures Commission', jurisdiction='Hong Kong'):
        when = iso_date(at[:10]); requested = key(locator)
        matches = [a for a in self.value['aliases'] if key(a['locator']) == requested and
                   self.authorities[a['authority_id']]['issuer'] == issuer and
                   self.authorities[a['authority_id']]['jurisdiction'] == jurisdiction]
        result = {'locator': locator, 'catalog_hash': self.hash, 'at': str(when), 'status': 'UNAVAILABLE',
                  'considered': [], 'provision_id': None, 'legal_applicability_proved': False}
        identities = {(a['authority_id'], a['provision_locator']) for a in matches}
        if len(identities) > 1:
            return {**result, 'status': 'AMBIGUOUS_IDENTITY', 'considered': [list(i) for i in sorted(identities)]}
        if not identities:
            return result
        aid, ploc = next(iter(identities))
        if not any(self._available_evidence(a['evidence']) for a in matches) or not self._available_evidence(self.authorities[aid]['identity_evidence']):
            return result
        candidates = [p for p in self.provisions.values() if p['authority_id'] == aid and p['locator'] == ploc]
        if not candidates:
            return {**result, 'status': 'MISSING_PROVISION'}
        applicable, unknown = [], []
        for p in candidates:
            e = self.editions[p['edition_id']]
            result['considered'].append({'provision_id': p['provision_id'], 'edition_id': e['edition_id'],
                                         'raw_sha256': e['raw_sha256'], 'temporal_status': e['temporal_status']})
            if e['temporal_status'] == 'UNKNOWN' or not self._available_evidence(e['temporal_evidence']):
                unknown.append(p)
            elif iso_date(e['effective_from']) <= when and (e['effective_until'] is None or when < iso_date(e['effective_until'])):
                applicable.append(p)
        if unknown:
            return {**result, 'status': 'UNKNOWN_VERSION'}
        if len(applicable) != 1:
            return {**result, 'status': 'AMBIGUOUS_VERSION' if applicable else 'WRONG_EDITION'}
        p = applicable[0]; e = self.editions[p['edition_id']]
        if e['edition_id'] not in self.documents:
            return result
        return {**result, 'status': 'RESOLVED', 'authority_id': aid, 'edition_id': e['edition_id'],
                'provision_id': p['provision_id'], 'raw_sha256': e['raw_sha256'],
                'temporal_basis': e['temporal_evidence'], 'matching_aliases': matches}

    def select(self, resolution, *, max_provisions=32, max_bytes=60000):
        if type(max_provisions) is not int or not 1 <= max_provisions <= 100 or type(max_bytes) is not int or not 1000 <= max_bytes <= 150000:
            raise LegalMathError('E_RESOURCE_LIMIT')
        result = {'status': 'CONTEXT_INCOMPLETE', 'catalog_hash': self.hash,
                  'resolution': resolution, 'provision_ids': [], 'documents': [], 'findings': [],
                  'semantic_context_completeness': False}
        if resolution.get('catalog_hash') != self.hash or resolution.get('status') != 'RESOLVED':
            result['findings'].append({'kind': 'UNRESOLVED_AUTHORITY_VERSION'}); return result
        pid = resolution['provision_id']
        # Re-resolve to prevent a caller supplying a forged successful resolution.
        if self.resolve(resolution['locator'], resolution['at']) != resolution:
            raise LegalMathError('E_REFERENCE')
        pending = [pid]; visited = set(); regions = {}
        while pending:
            current = pending.pop(0)
            if current in visited:
                continue
            if len(visited) >= max_provisions:
                result['findings'].append({'kind': 'AUTHORITY_CONTEXT_LIMIT', 'unvisited': sorted(set(pending + [current]))}); break
            visited.add(current); p = self.provisions.get(current)
            if p is None:
                result['findings'].append({'kind': 'MISSING_CONTEXT_PROVISION', 'provision_id': current}); continue
            e = self.editions[p['edition_id']]
            if p['edition_id'] not in self.documents:
                result['findings'].append({'kind': 'SOURCE_UNAVAILABLE', 'edition_id': p['edition_id']}); continue
            # A referenced provision has its own date and version requirements.
            if e['temporal_status'] != 'DOCUMENTED_INTERVAL' or not self._available_evidence(e['temporal_evidence']) or not (
                    e['effective_from'] <= resolution['at'] and (e['effective_until'] is None or resolution['at'] < e['effective_until'])):
                result['findings'].append({'kind': 'CONTEXT_VERSION_UNRESOLVED', 'provision_id': current})
            if p['context_status'] != 'REVIEWED_SELECTION':
                result['findings'].append({'kind': 'PROPOSED_CONTEXT_SELECTION', 'provision_id': current})
            result['findings'] += [{'kind': 'UNRESOLVED_CONTEXT_REFERENCE', 'details': q, 'provision_id': current}
                                   for q in p['unresolved_references']]
            for r in p['regions']:
                a = r['anchor']; regions.setdefault(p['edition_id'], {})[(a['start'], a['end'])] = r
            pending += p['requires']
            pending += [r['target_provision_id'] for r in self.value['relationships']
                        if r['source_provision_id'] == current and r['kind'] in ('CITES', 'INCORPORATES')]
        result['provision_ids'] = sorted(visited)
        for eid, rows in regions.items():
            doc = self.documents[eid]; ordered = sorted(rows)
            merged = []
            for start, end in ordered:
                if merged and start <= merged[-1][1]:
                    merged[-1][1] = max(end, merged[-1][1])
                else:
                    merged.append([start, end])
            selection = {'catalog_hash': self.hash, 'edition_id': eid, 'raw_sha256': doc['raw_sha256'],
                         'text_sha256': doc['text_sha256'], 'ranges': merged,
                         'regions': list(rows.values()), 'provision_ids': sorted(visited),
                         'omitted_characters': len(doc['text']) - sum(b - a for a, b in merged),
                         'semantic_context_completeness': False}
            result['documents'].append({**deepcopy(doc), 'selection': selection})
            result['findings'] += [{**f, 'edition_id': eid} for f in doc['findings']]
        used = sum(len(d['text'][a:b].encode()) for d in result['documents'] for a, b in d['selection']['ranges'])
        result['selected_bytes'] = used
        if used > max_bytes:
            result['findings'].append({'kind': 'AUTHORITY_CONTEXT_BYTE_LIMIT', 'required': used, 'maximum': max_bytes})
            # Keep span decisions but do not present a partially truncated excerpt.
            result['documents'] = []
        if not result['findings']:
            result['status'] = 'DECLARED_CONTEXT_CHECKED'
        return result

    def version_dependencies(self, provision_ids, at):
        """Stable keys, hashes of affected closure including missing requirements."""
        versions = {}
        for pid in provision_ids:
            visited = set(); pending = [pid]; rows = []
            while pending and len(visited) <= 500:
                item = pending.pop(0)
                if item in visited:
                    continue
                visited.add(item); p = self.provisions.get(item)
                if p is None:
                    rows.append({'missing_provision': item}); continue
                e = self.editions[p['edition_id']]
                authority=self.authorities[p['authority_id']]
                aliases=[a for a in self.value['aliases'] if a['authority_id']==p['authority_id'] and a['provision_locator']==p['locator']]
                rows.append({'provision': p, 'edition': e, 'authority':authority, 'aliases':aliases,
                             'available': p['edition_id'] in self.documents})
                pending += p['requires']
                rels = [r for r in self.value['relationships'] if r['source_provision_id'] == item]
                rows.extend(rels)
                pending += [r['target_provision_id'] for r in rels]
            evidence_editions=set()
            def evidence(value):
                if isinstance(value,dict):
                    if set(value)=={'edition_id','start','end','quote'}:evidence_editions.add(value['edition_id'])
                    for child in value.values():evidence(child)
                elif isinstance(value,list):
                    for child in value:evidence(child)
            evidence(rows)
            rows.extend({'evidence_edition':self.editions[eid],'available':eid in self.documents}
                        for eid in sorted(evidence_editions))
            versions['authority.' + pid] = digest({'closure': rows, 'at': at})
        return versions


def root_reference(locator, documents):
    """Recognize only the explicit SFC refNo locator bound to official JSON metadata."""
    match = re.fullmatch(r'SFC circular, refNo=([0-9]{2}EC[0-9]+)(?: \(official locator in source packet\))?', locator)
    if not match:
        return None
    found = []
    for doc in documents:
        if doc['media_type'] != 'application/json':
            continue
        official_url(doc['url']); data = loads(doc['data'])
        url = urlsplit(doc['url'])
        if url.hostname != 'apps.sfc.hk' or parse_qs(url.query).get('refNo') != [match[1]]:
            continue
        if data.get('refNo') == match[1] and data.get('title') and data.get('releasedDate'):
            found.append({'status': 'RESOLVED_ROOT_IDENTITY', 'locator': locator, 'url': doc['url'],
                          'refNo': data['refNo'], 'title': data['title'], 'releasedDate': data['releasedDate'],
                          'raw_sha256': raw_digest(doc['data']), 'legal_applicability_proved': False})
    return found[0] if len(found) == 1 else None
