"""Author the reviewed, exact-source BASF section 6(3) development packet."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from legalmath.prospectus.successor import basf, basf_agent_capacity, basf_agents, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from scripts.prospectus_closure_basf_agent_notices import prepared_request

REL = 'docs/implementation/prospectus-integration-closure/basf-agent-capacity'


def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    request = prepared_request(ROOT, graph)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {unit['unit']: unit for unit in assembly['units']}
    selected = []
    paragraph = basf_agent_capacity.spans(units)
    for span in paragraph:
        selected.append({'unit': span['unit'], 'text_sha256': digest(units[span['unit']]['text'].encode()),
                         'role': 'OPERATIVE',
                         'sources': [piece['source'] for piece in basf_agents.source_pieces(graph, units, [span])],
                         'reason': 'Complete original p124 section 6(3) reviewed; exact surviving character pieces, including the concluding mandate/trust sentence.'})
    authority = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-agent-notices/review.json')['authority_sources']
    clause = {'id': basf_agent_capacity.IDENTITY, 'units': basf_agent_capacity.UNITS,
              'spans': paragraph, 'quote': ' '.join(units[key]['text'] for key in basf_agent_capacity.UNITS),
              'effect': 'none', 'effect_scope': ['Q1', 'Q2'],
              'effect_explanation': 'This contractual allocation of agency roles does not itself create principal-loss or compulsory-conversion authority; it does not decide statutory duties.',
              'actor': 'agent', 'affected': 'holder', 'modality': 'statement', 'election': 'none',
              'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
              'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
              'capacity_reading': deepcopy(basf_agent_capacity.READING),
              'source_uses': basf_agents.source_pieces(graph, units, paragraph),
              'selection_authority': authority}
    images = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/base-124.png',
              'docs/implementation/prospectus-basf-continuation-2026-10-05/review-images/basf-2032-final-7.png']
    packet = {'version': 'basf-agent-capacity-review.v1', 'graph_sha256': digest(graph),
              'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
              'prior_clauses_sha256': digest(basf_agent_capacity.prior_readings(request['clauses'])),
              'prior_references_sha256': digest(request['reference_admission']['references']),
              'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                         'reason': 'Original p124 section 6(3) and final-term agent/language labels inspected; contractual capacity only, not independent legal adjudication.'},
              'images': {path: digest((ROOT / path).read_bytes()) for path in images},
              'authority_sources': authority, 'units': selected, 'clauses': [clause],
              'limitations': ['No statutory-duty or actual-agency-breach conclusion',
                              'All eight prior notice/agent meanings and five references preserved',
                              'B54 name/office remains unresolved',
                              'Q1/Q2 UNKNOWN, Q3 PARTIAL, ASSISTED; no independent acceptance']}
    write(ROOT / REL / 'review.json', packet)
    print(ROOT / REL / 'review.json')


if __name__ == '__main__':
    main()
