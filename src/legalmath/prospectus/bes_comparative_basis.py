"""Finite source-bound accounting alternatives for the original BES comparison.

The specification admits one inspected reading. It is not an accounting-law
classifier and must not be used to select a cause from a numerical identity.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from .successor.anchors import fields
from .successor.contracts import bound_path, digest

VERSION = 'bes-comparative-basis.v1'
SPEC = Path(__file__).with_name('bes_comparative_spec.json')
MECHANISM_ANCHORS = {
    'presentation': ['presentation_consistency', 'presentation_disclosures', 'IAS8_link', 'opening_comparative'],
    'policy': ['policy_permission', 'policy_exceptions', 'transition', 'policy_practicability', 'policy_disclosures'],
    'estimate': ['estimate_definition', 'estimate_treatment'],
    'error': ['error_definition', 'error_treatment'],
}


def make_profile(graph, baseline, reading):
    return {'version': VERSION, 'graph_sha256': digest(graph), 'baseline_sha256': digest(baseline),
            'review': {'kind': 'DEVELOPMENT', 'independent': False}, 'reading': deepcopy(reading)}


def evaluate(graph, baseline, profile, root, *, expected_profile_sha256):
    keys = {'version', 'graph_sha256', 'baseline_sha256', 'review', 'reading'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != digest(graph) or profile['baseline_sha256'] != digest(baseline)
            or digest(profile['review']) != digest({'kind': 'DEVELOPMENT', 'independent': False})):
        raise ValueError('Comparative profile, current graph, entire baseline or review changed')
    spec = json.loads(SPEC.read_text())
    reading = profile['reading']
    fields(reading, spec['reading_fields'], spec['reading_fields'])
    for name, expected in spec['reading_fields'].items():
        if digest(reading[name]) != expected:
            raise ValueError('Inspected comparative source interpretation changed: ' + name)
    # Verify complete current occurrences, not merely strings copied into a profile.
    units = {u['id']: u for u in graph['units']}
    if len(units) != len(graph['units']):
        raise ValueError('Duplicate comparative source occurrence')
    for unit in reading['report_context']:
        if not unit['visible'] or digest(units.get(unit['id'])) != digest(unit):
            raise ValueError('Original comparative report occurrence changed: ' + unit['id'])
    source_files = []
    for name in ('eu1126_original', 'eu1126_20091227'):
        source = spec['standards'][name]
        path = bound_path(root, source['path'])
        if digest(path.read_bytes()) != source['sha256']:
            raise ValueError('Historical standard bytes changed')
        with gzip.open(path, 'rt') as stream:
            source_units = json.load(stream)
        index = {u['id']: u for u in source_units}
        if len(index) != len(source_units):
            raise ValueError('Duplicate standard occurrence')
        for selected in reading['sections'][name]:
            if digest(index.get(selected['id'])) != digest(selected):
                raise ValueError('Historical standard quotation changed')
        source_files.append({'edition': name, **source})
    for img in reading['images']:
        if digest(bound_path(root, img['path']).read_bytes()) != img['sha256']:
            raise ValueError('Comparative original report image changed')
    mechanisms = {}
    for name, anchors in MECHANISM_ANCHORS.items():
        mechanisms[name] = {
            'conditions': deepcopy(reading[name]),
            'source_ids': [i for key in anchors for i in reading['anchors'][key]],
            'specific_cause_established': False,
            'retrospective_rewrite_from_estimate_alone': False if name == 'estimate' else None,
        }
    return {
        'version': VERSION, 'profile_sha256': digest(profile), 'graph_sha256': digest(graph),
        'baseline_sha256': digest(baseline), 'mechanisms': mechanisms,
        'qualifications': {k: deepcopy(reading[k]) for k in ('impracticability', 'edition', 'temporal')},
        'reported_adoptions': deepcopy(reading['adoptions']),
        'adoption_boundaries': deepcopy(reading['adoption_boundaries']),
        'findings': deepcopy(reading['findings']), 'selected_mechanism': None,
        'missing_evidence': ['specific reason and affected line items/dates',
                             'original-period asset facts and information available at authorization',
                             'applicable period-specific authority and transition provisions'],
        'source_evidence': {'standards': deepcopy(reading['sections']), 'standard_files': source_files,
                            'report_context': deepcopy(reading['report_context']),
                            'report_section_ids': deepcopy(reading['report_section_ids']),
                            'images': deepcopy(reading['images']), 'anchors': deepcopy(reading['anchors']),
                            'source_roles': deepcopy(reading['source_roles'])},
        'automatic_discovery': False, 'source_authenticity_established': False,
        'independent_legal_acceptance': False, 'may_execute_transaction': False,
    }


def explain(review):
    amount = review['findings']['movement_amount_thousand_euros']
    return (
        f'The retained comparison shows an offsetting {amount:,} thousand-EUR change between '
        'held-for-sale assets and Other assets. Matching combined totals do not identify its cause. '
        'The inspected policy 2.1 and Note 45 do not state the specific reason. '
        'BES reports revised IAS 1 adoption with presentation effects; that general statement does '
        'not connect IAS 1 to this movement. IFRIC 17 and the IFRS 5 subsidiary amendment are '
        'reported as not yet applied; the latter is stated to apply prospectively from 1 January 2010.\n\n'
        'A presentation reclassification requires the IAS 1 consistency conditions and disclosure '
        'of its nature, affected amounts and reason, with the impracticability qualifications. '
        'An accounting-policy change follows any specific transition provisions first; otherwise '
        'retrospective application is subject to practicability and the required disclosures. '
        'An estimate revision affects the current and relevant future periods; an estimate change '
        'alone does not justify rewriting the prior comparative. A material prior-period error '
        'requires omitted or misused information available and reasonably obtainable at original '
        'authorization, with retrospective correction subject to the earliest-practicable-date rules.\n\n'
        'Retrospective estimates must use evidence of circumstances at the original date and '
        'information available at original authorization; hindsight is prohibited. IFRS 5 paragraph '
        '40 cannot be displaced by a general comparability preference, and it does not prohibit '
        'every properly supported correction. The two historical source editions retain their '
        'different wording and dates; the consolidation is a documentation tool.\n\n'
        'The full conditions and source passages accompany these alternatives. No mechanism is '
        'selected and neither compliance nor violation is established. Resolving the cause requires '
        'the specific reason, affected items and dates, original-period facts and applicable '
        'transition basis. Absence of a displayed row does not establish disposal or economic zero.'
    )
