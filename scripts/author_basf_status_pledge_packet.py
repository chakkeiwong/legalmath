"""Author complete German Option I status, issuer pledge and definition."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from legalmath.prospectus.successor import basf, basf_agents, basf_status_pledge as pledge, jobs, source_graph
from legalmath.prospectus.successor.contracts import digest, read, write
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_amount_holder import prepared_request
REL = 'docs/implementation/prospectus-integration-closure/basf-status-pledge'


def main():
    graph = source_graph.build(jobs.basf_request(ROOT)['bundle'], ROOT)
    request = prepared_request(ROOT, graph)
    construction = basf.construct(graph, read(ROOT / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    units = {unit['unit']: unit for unit in assembly['units']}
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in pledge.AUTHORITY_IDS]
    comparison = pledge.source_comparison(graph)
    selected, clauses = [], []
    for identity, keys in pledge.PARAGRAPHS.items():
        paragraph = pledge.spans(units, identity)
        for key in keys:
            whole = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}]
            selected.append({'unit': key, 'text_sha256': digest(units[key]['text'].encode()),
                'role': 'OPERATIVE', 'sources': [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)],
                'reason': 'Original selected German Option I status, complete issuer negative pledge and debt definition; excluded guarantor wording and non-controlling English comparison kept distinct.'})
        node = {'id': identity, 'units': keys, 'spans': paragraph,
            'quote': ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in paragraph),
            'effect': 'none', 'effect_scope': ['Q1', 'Q2'],
            'effect_explanation': 'These status, covenant and definition provisions alone confer no uncompensated principal-loss or compulsory-conversion authority. Statutory priority, remedies and actual compliance remain unevaluated.',
            'actor': 'issuer', 'affected': 'holder', 'modality': 'statement', 'election': 'none',
            'assets': [], 'role': 'OPERATIVE', 'polarity': True, 'conditions': [], 'exceptions': [],
            'questions': ['Q1', 'Q2'], 'origin': 'development-source-review',
            'pledge_reading': deepcopy(pledge.READINGS[identity]),
            'references': [deepcopy(pledge.DEFINITION_REFERENCE)] if identity == pledge.PLEDGE else [],
            'source_uses': basf_agents.source_pieces(graph, units, paragraph), 'selection_authority': authority}
        if identity == pledge.STATUS:
            node['source_comparison'] = deepcopy(comparison)
        clauses.append(node)
    images = ['docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name + '.png'
              for name in ('base-108', 'base-109', 'base-110', 'base-111', 'final-2', 'final-7')]
    images += [REL + f'/option-review/base-{page:03d}.png' for page in (65, 66, 67, 68, 89)]
    packet = {'version': 'basf-status-pledge-review.v1', 'graph_sha256': digest(graph),
        'construction_sha256': digest(construction), 'baseline_assembly_sha256': digest(assembly),
        'prior_clauses_sha256': digest(pledge.prior_readings(request['clauses'])),
        'prior_references_sha256': digest(request['reference_admission']['references']),
        'review': {'reviewer': 'Codex implementer original-page review', 'kind': 'DEVELOPMENT',
                   'reason': 'Complete selected German section 2 status, issuer covenant and debt definition inspected with selected option and controlling-language authority; corrected the inherited wrong-option comparison citation.'},
        'images': {path: digest((ROOT / path).read_bytes()) for path in images},
        'authority_sources': authority, 'context_sources': [anchor(raw[key]) for key in pledge.CONTEXT_IDS],
        'source_comparison': comparison, 'units': selected, 'clauses': clauses,
        'limitations': ['No actual security, priority, breach, remedy, holder receipt or recovery evaluated',
                        'Definition edge is supplied semantic review, not automatic reference discovery',
                        'All twenty prior meanings, six references, B54 and protected construction preserved',
                        'Historical English citation used Option II; corrected Option I has the same disputed reduction wording',
                        'German controls; English equally/ratably is not imported as adjudicated proportionality',
                        'Q1/Q2 UNKNOWN, Q3 PARTIAL, ASSISTED; no independent acceptance']}
    if (ROOT / REL / 'review.json').exists():
        raise ValueError('Refusing to overwrite retained pledge review')
    write(ROOT / REL / 'review.json', packet)
    print(ROOT / REL / 'review.json')


if __name__ == '__main__':
    main()
