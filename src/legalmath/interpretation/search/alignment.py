"""Explicit fact correspondence; a proposed semantic match is always conditional."""
from collections import defaultdict
from copy import deepcopy
from pydantic import Field
from ...canonical import digest
from ...errors import LegalMathError
from ..contracts import Strict, Id, Hash, Text, parse
from .models import Formalization, Quote, commitment


class FactLink(Strict):
    left: Id
    right: Id
    assumption: Text | None


class Correspondence(Strict):
    source_packet_hash: Hash
    left_commitment: Hash
    right_commitment: Hash
    links: list[FactLink] = Field(max_length=30)
    rationale: Text
    output_meaning_assumption: Text
    citations: list[Quote] = Field(min_length=1, max_length=30)


def declarations(reading):
    if reading['formalization'] is None:
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    formal = parse(Formalization, reading['formalization'])
    facts = {f['name']: f for f in formal['facts']}
    if len(facts) != len(formal['facts']):
        raise LegalMathError('E_DUPLICATE_ID')
    return facts


def metadata(fact):
    return {k: v for k, v in fact.items() if k != 'name'}


def field_differences(left, right):
    return {k: {'left': left[k], 'right': right[k]}
            for k in metadata(left) if left[k] != right[k]}


def discover(left, right):
    """A name/ordering change is safe only with identical declared metadata.

    Anchor exact same-name declarations first. Remaining identical declarations
    must have unique partners; do not choose one of several possible bijections.
    """
    a, b = declarations(left), declarations(right)
    matches = {n: n for n in a.keys() & b.keys() if metadata(a[n]) == metadata(b[n])}
    left_groups, right_groups = defaultdict(list), defaultdict(list)
    for n in sorted(a.keys() - matches.keys()):
        left_groups[digest(metadata(a[n]))].append(n)
    for n in sorted(b.keys() - set(matches.values())):
        right_groups[digest(metadata(b[n]))].append(n)
    ambiguous = []
    for signature, names in left_groups.items():
        others = right_groups.get(signature, [])
        if len(names) == len(others) == 1:
            matches[names[0]] = others[0]
        elif others:
            ambiguous.append({'left': names, 'right': others})
    complete = len(matches) == len(a) == len(b)
    return {'status': 'EXACT_DECLARED_CORRESPONDENCE' if complete else 'REVIEW_REQUIRED',
            'mapping': dict(sorted(matches.items())) if complete else None,
            'exact_partial_links': dict(sorted(matches.items())),
            'unmatched_left': sorted(a.keys() - matches.keys()),
            'unmatched_right': sorted(b.keys() - set(matches.values())),
            'ambiguous_matches': ambiguous,
            'same_name_changes': {n: field_differences(a[n], b[n])
                                  for n in sorted(a.keys() & b.keys()) if metadata(a[n]) != metadata(b[n])},
            'legal_source_commitment_resolved': False}


def validate_correspondence(proposal, left, right, packet):
    value = parse(Correspondence, proposal)
    if (value['source_packet_hash'] != digest(packet)
            or value['left_commitment'] != commitment(left)
            or value['right_commitment'] != commitment(right)):
        raise LegalMathError('E_STALE_REVIEW', details='Correspondence refers to different source/readings')
    a, b = declarations(left), declarations(right)
    names_a = [p['left'] for p in value['links']]
    names_b = [p['right'] for p in value['links']]
    if (len(set(names_a)) != len(names_a) or len(set(names_b)) != len(names_b)
            or set(names_a) != set(a) or set(names_b) != set(b)):
        raise LegalMathError('E_REFERENCE', details='Fact correspondence must be a total bijection')
    units = {u['unit_id']: u['text'] for u in packet['units']}
    for quote in value['citations']:
        if units.get(quote['unit_id'], '').count(quote['quote']) != 1:
            raise LegalMathError('E_REFERENCE', details='Correspondence citation is absent or ambiguous')
    changes = []
    for link in value['links']:
        x, y = a[link['left']], b[link['right']]
        if x['type'] != y['type'] or (x['type'] != 'bool' and x['unit'] != y['unit']):
            raise LegalMathError('E_UNSUPPORTED_PROFILE', details='No type or measurement-unit conversion is supported')
        delta = field_differences(x, y)
        if delta and (not link['assumption'] or not link['assumption'].strip()):
            raise LegalMathError('E_SCHEMA', details='Every changed fact declaration needs an explicit assumption')
        if delta:
            changes.append({'left': link['left'], 'right': link['right'],
                            'fields': delta, 'assumption': link['assumption']})
    if not value['rationale'].strip() or not value['output_meaning_assumption'].strip():
        raise LegalMathError('E_SCHEMA')
    return {'proposal': value, 'proposal_hash': digest(value),
            'mapping': {p['left']: p['right'] for p in value['links']},
            'changed_declarations': changes, 'status': 'CONDITIONAL_CORRESPONDENCE',
            'legal_source_commitment_resolved': False}


def rename_bundle(right_bundle, left_bundle, mapping):
    """Simultaneously rename AST fact leaves, never text or operators."""
    a = {f['name'] for f in left_bundle['facts']}
    b = {f['name'] for f in right_bundle['facts']}
    if set(mapping) != a or set(mapping.values()) != b or len(set(mapping.values())) != len(mapping):
        raise LegalMathError('E_REFERENCE')
    reverse = {v: k for k, v in mapping.items()}

    def visit(node):
        if isinstance(node, dict):
            if node.get('op') == 'fact':
                node['name'] = reverse[node['name']]
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)

    value = deepcopy(right_bundle)
    visit(value['rules'])
    value['facts'] = deepcopy(left_bundle['facts'])
    value['bundle_id'] = 'search.aligned.' + digest({'right': digest(right_bundle), 'mapping': mapping})[:20]
    return value


def translate_snapshot(snapshot, mapping):
    if len(set(mapping.values())) != len(mapping) or not set(snapshot['facts']) <= set(mapping):
        raise LegalMathError('E_REFERENCE')
    value = deepcopy(snapshot)
    value['facts'] = {mapping[n]: deepcopy(f) for n, f in snapshot['facts'].items()}
    return value


def review_packet(left, right, packet):
    """Side-by-side evidence, not a preferred mapping or legal reference label."""
    return {'source_packet_hash': digest(packet), 'source_packet': deepcopy(packet),
            'left_commitment': commitment(left), 'right_commitment': commitment(right),
            'left': deepcopy(left), 'right': deepcopy(right),
            'fact_correspondence': discover(left, right),
            'review_questions': [
                'Do the same events, actors, dates, quantities and exceptions supply both sets of facts?',
                'Does the same Boolean or scalar result mean the same thing in both statements?',
                'Which correspondence assumptions are contradicted, unresolved or supported by the retained source?',
                'Does the source require additional facts or referenced authorities absent from either reading?'],
            'semantic_mapping_approved': False, 'release_eligible': False,
            'authority': 'GENERATED_CANDIDATE_REVIEW_NOT_BLIND_REFERENCE_ANNOTATION'}
