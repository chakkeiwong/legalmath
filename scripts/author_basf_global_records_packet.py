"""Author exact-source BASF global-note form and ICSD records premises."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from legalmath.prospectus.successor import basf, basf_agents, basf_global_records as records, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_global_exchange import prepared_request
REL = 'docs/implementation/prospectus-integration-closure/basf-global-records'

def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    request = prepared_request(ROOT, graph)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {unit['unit']: unit for unit in assembly['units']}
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in records.AUTHORITY_IDS]
    selected, clauses = [], []
    for identity, keys in records.PARAGRAPHS.items():
        paragraph = records.spans(units, identity)
        for key in keys:
            whole = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}]
            selected.append({'unit': key, 'text_sha256': digest(units[key]['text'].encode()),
                'role': 'OPERATIVE', 'sources': [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)],
                'reason': 'Original pages 108–110 and final terms 3/7 reviewed; exact surviving pieces exclude CBF, CGN and CDS alternatives.'})
        clauses.append({'id': identity, 'units': keys, 'spans': paragraph,
            'quote': ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in paragraph),
            'effect': 'none', 'effect_scope': ['Q1', 'Q2'],
            'effect_explanation': 'These form and recordkeeping provisions alone do not confer uncompensated principal-loss or compulsory-equity-conversion authority. Actual records/events and the bilingual redemption wording remain unevaluated or unresolved.',
            'actor': 'issuer', 'affected': 'holder', 'modality': 'statement', 'election': 'none',
            'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
            'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
            'records_reading': deepcopy(records.READINGS[identity]),
            'source_uses': basf_agents.source_pieces(graph, units, paragraph), 'selection_authority': authority})
    images = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name + '.png'
              for name in ('base-108', 'base-109', 'base-110', 'final-3', 'final-7')]
    packet = {'version': 'basf-global-records-review.v1', 'graph_sha256': digest(graph),
        'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
        'prior_clauses_sha256': digest(records.prior_readings(request['clauses'])),
        'prior_references_sha256': digest(request['reference_admission']['references']),
        'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                   'reason': 'Complete selected section 1(3)(a) and section 1(4) paragraphs inspected; preserve German/English reduction wording discrepancy and unresolved incoming section 1(1) reference.'},
        'images': {path: digest((ROOT / path).read_bytes()) for path in images},
        'authority_sources': authority, 'context_sources': [anchor(raw[key]) for key in records.CONTEXT_IDS],
        'comparison_sources': [anchor(raw[key]) for key in records.COMPARISON_IDS],
        'units': selected, 'clauses': clauses,
        'limitations': ['No actual balance, event, statement, custody or compliance evaluated',
                        'German controlling reduction wording differs from English; redemption accounting not adjudicated',
                        'All eleven prior meanings, five references, B54 and the protected construction preserved',
                        'Incoming NGN reference remains unresolved; Q1/Q2 UNKNOWN, Q3 PARTIAL, ASSISTED; no independent acceptance']}
    write(ROOT / REL / 'review.json', packet)
    print(ROOT / REL / 'review.json')

if __name__ == '__main__':
    main()
