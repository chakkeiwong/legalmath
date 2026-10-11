"""Author exact-source BASF issue amount, bearer form and holder definition."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from legalmath.prospectus.successor import basf, basf_agents, basf_amount_holder as amount, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_global_records import prepared_request
REL = 'docs/implementation/prospectus-integration-closure/basf-amount-holder'

def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    request = prepared_request(ROOT, graph)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {unit['unit']: unit for unit in assembly['units']}
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in amount.AUTHORITY_IDS]
    selected, clauses = [], []
    for identity, keys in amount.PARAGRAPHS.items():
        paragraph = amount.spans(units, identity)
        for key in keys:
            whole = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}]
            selected.append({'unit': key, 'text_sha256': digest(units[key]['text'].encode()),
                'role': 'OPERATIVE', 'sources': [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)],
                'reason': 'Original pages 108–110 and final terms 2/3/7 reviewed; exact selected issue amount, bearer form and holder pieces exclude CDS alternatives.'})
        clauses.append({'id': identity, 'units': keys, 'spans': paragraph,
            'quote': ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in paragraph),
            'effect': 'none', 'effect_scope': ['Q1', 'Q2'],
            'effect_explanation': 'These issue amount, bearer form and holder provisions alone confer no uncompensated principal-loss or compulsory-conversion authority. They do not establish an actual balance, ownership or procedural standing.',
            'actor': 'issuer', 'affected': 'holder', 'modality': 'statement', 'election': 'none',
            'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
            'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
            'amount_reading': deepcopy(amount.READINGS[identity]),
            'source_uses': basf_agents.source_pieces(graph, units, paragraph), 'selection_authority': authority})
    images = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name + '.png'
              for name in ('base-108', 'base-109', 'base-110', 'final-2', 'final-3', 'final-7')]
    packet = {'version': 'basf-amount-holder-review.v1', 'graph_sha256': digest(graph),
        'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
        'prior_clauses_sha256': digest(amount.prior_readings(request['clauses'])),
        'prior_references_sha256': digest(request['reference_admission']['references']),
        'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                   'reason': 'Complete selected sections 1(1), 1(2), 1(5) and section 1(4) target inspected; issue amount and holder definition do not prove actual balances or ownership.'},
        'images': {path: digest((ROOT / path).read_bytes()) for path in images},
        'authority_sources': authority, 'context_sources': [anchor(raw[key]) for key in amount.CONTEXT_IDS],
        'units': selected, 'clauses': clauses, 'references': [amount.expected_reference(graph, assembly)],
        'limitations': ['No actual balance, event, ownership, proprietary-law classification or standing evaluated',
                        'German controlling reduction wording differs from English; redemption accounting not adjudicated',
                        'All seventeen prior meanings, five references, B54 and the protected construction preserved',
                        'Complete selected NGN reference admitted; Q1/Q2 UNKNOWN, Q3 PARTIAL, ASSISTED; no independent acceptance']}
    if (ROOT / REL / 'review.json').exists():
        raise ValueError('Refusing to overwrite retained amount review')
    write(ROOT / REL / 'review.json', packet)
    print(ROOT / REL / 'review.json')

if __name__ == '__main__':
    main()
