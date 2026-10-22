"""Separate verifier against the retained reading, never production's spec/parser."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify(value, explanation, profile, graph, baseline, original, sources, root, prose_sha256):
    root = Path(root)
    r = original['reading']
    require(identity(profile['reading']) == identity(r), 'Original supplied reading differs')
    index = {u['id']: u for u in graph['units']}
    require(len(index) == len(graph['units']), 'Duplicate original report occurrence')
    for u in r['report_context']:
        require(identity(index.get(u['id'])) == identity(u), 'Original report source changed')
    files = []
    for name in ('eu1126_original', 'eu1126_20091227'):
        entry = sources[name]
        path = root / entry['units_path']
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry['units_sha256'], 'Original standard bytes changed')
        with gzip.open(path, 'rt') as stream:
            raw = json.load(stream)
        for u in r['sections'][name]:
            require(identity(raw[u['order']]) == identity(u), 'Original standard occurrence changed')
        files.append({'edition': name, 'path': entry['units_path'], 'sha256': entry['units_sha256']})
    for img in r['images']:
        require(hashlib.sha256((root / img['path']).read_bytes()).hexdigest() == img['sha256'], 'Original image changed')
    # These associations are derived from008's original full source review.
    groups = [('presentation', ('presentation_consistency', 'presentation_disclosures', 'IAS8_link', 'opening_comparative')),
              ('policy', ('policy_permission', 'policy_exceptions', 'transition', 'policy_practicability', 'policy_disclosures')),
              ('estimate', ('estimate_definition', 'estimate_treatment')),
              ('error', ('error_definition', 'error_treatment'))]
    mechanisms = {name: {'conditions': deepcopy(r[name]),
                         'source_ids': [u for anchor in anchors for u in r['anchors'][anchor]],
                         'specific_cause_established': False,
                         'retrospective_rewrite_from_estimate_alone': False if name == 'estimate' else None}
                  for name, anchors in groups}
    expected = {
        'version': 'bes-comparative-basis.v1', 'profile_sha256': identity(profile),
        'graph_sha256': identity(graph), 'baseline_sha256': identity(baseline), 'mechanisms': mechanisms,
        'qualifications': {k: deepcopy(r[k]) for k in ('impracticability', 'edition', 'temporal')},
        'reported_adoptions': deepcopy(r['adoptions']), 'adoption_boundaries': deepcopy(r['adoption_boundaries']),
        'findings': deepcopy(r['findings']), 'selected_mechanism': None,
        'missing_evidence': ['specific reason and affected line items/dates',
                             'original-period asset facts and information available at authorization',
                             'applicable period-specific authority and transition provisions'],
        'source_evidence': {'standards': deepcopy(r['sections']), 'standard_files': files,
                            'report_context': deepcopy(r['report_context']),
                            'report_section_ids': deepcopy(r['report_section_ids']),
                            'images': deepcopy(r['images']), 'anchors': deepcopy(r['anchors']),
                            'source_roles': deepcopy(r['source_roles'])},
        'automatic_discovery': False, 'source_authenticity_established': False,
        'independent_legal_acceptance': False, 'may_execute_transaction': False,
    }
    require(identity(value) == identity(expected), 'Conditional accounting result differs from original sources/reading')
    require(hashlib.sha256(explanation.encode()).hexdigest() == prose_sha256, 'Reviewed conditional explanation changed')
    require(len(r['adoptions']) == 27 and len(r['report_context']) == 346
            and sum(map(len, r['sections'].values())) == 635, 'Inspected source scope changed')
    return {'report_occurrences': 346, 'standard_occurrences': 635, 'reported_adoptions': 27,
            'conditional_mechanisms': 4, 'specific_cause_established': False,
            'accounting_compliance': 'UNDETERMINED', 'whole_program_complete': False}
