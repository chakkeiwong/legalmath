"""Author exact-source BASF temporary-global and imported-geography premises."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from legalmath.prospectus.successor import basf, basf_agents, basf_global_exchange as exchange, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_agent_capacity import prepared_request
REL = 'docs/implementation/prospectus-integration-closure/basf-global-exchange'

def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    request = prepared_request(ROOT, graph)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {unit['unit']: unit for unit in assembly['units']}
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in exchange.AUTHORITY_IDS]
    selected, clauses = [], []
    for identity, keys in exchange.PARAGRAPHS.items():
        paragraph = exchange.spans(units, identity)
        for key in keys:
            whole = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}]
            selected.append({'unit': key, 'text_sha256': digest(units[key]['text'].encode()),
                'role': 'OPERATIVE', 'sources': [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)],
                'reason': 'Original pages 108/124 and final terms 3/7 reviewed; exact surviving pieces. Whole line 68 retains the previous agent-change ending.'})
        clauses.append({'id': identity, 'units': keys, 'spans': paragraph,
            'quote': ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in paragraph),
            'effect': 'none', 'effect_scope': ['Q1', 'Q2'],
            'effect_explanation': 'These form, certification and delivery provisions do not themselves create principal-loss or compulsory-conversion authority. They do not establish actual tax eligibility.',
            'actor': 'issuer', 'affected': 'holder', 'modality': 'statement', 'election': 'none',
            'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
            'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
            'global_reading': deepcopy(exchange.READINGS[identity]),
            'source_uses': basf_agents.source_pieces(graph, units, paragraph), 'selection_authority': authority})
    images = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name + '.png'
              for name in ('base-108', 'base-124', 'final-3', 'final-7')]
    packet = {'version': 'basf-global-exchange-review.v1', 'graph_sha256': digest(graph),
        'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
        'prior_clauses_sha256': digest(exchange.prior_readings(request['clauses'])),
        'prior_references_sha256': digest(request['reference_admission']['references']),
        'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                   'reason': 'Complete selected section 1(3)(b), context 1(3)(a), imported contractual geography and final-term choices inspected; actual U.S. tax-law eligibility not evaluated.'},
        'images': {path: digest((ROOT / path).read_bytes()) for path in images},
        'authority_sources': authority, 'context_sources': [anchor(raw[key]) for key in exchange.CONTEXT_IDS],
        'units': selected, 'clauses': clauses,
        'limitations': ['Contractual geography does not determine U.S.-person status or tax eligibility',
                        'No actual certificate, exchange request or delivery assessed',
                        'All nine prior meanings, five references, B54 and the protected construction preserved',
                        'Q1/Q2 UNKNOWN, Q3 PARTIAL, ASSISTED; no independent acceptance']}
    write(ROOT / REL / 'review.json', packet)
    print(ROOT / REL / 'review.json')

if __name__ == '__main__':
    main()
