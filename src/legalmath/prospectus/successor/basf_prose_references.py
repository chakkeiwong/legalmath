"""Source-specific BASF prose links; supplied review is not legal acceptance."""
from copy import deepcopy

from . import basf, basf_agents, basf_global_exchange, basf_notices, basf_status_pledge
from .admissions import dispositions
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

VERSION = 'basf-prose-references.v1'
NOTICE_SOURCES = [(118, 34), (119, 9), (119, 58), (120, 52), (122, 55),
                  (125, 41), (129, 39), (130, 72), (131, 17)]
SOURCE_IDS = [f'{basf.KEY}:p{p}:l{n}' for p, n in NOTICE_SOURCES + [(113, 92), (114, 2), (126, 50)]]
REVIEW = {'reviewer': 'Codex original-page source review', 'kind': 'DEVELOPMENT',
          'reason': 'Exact selected German Option I reference occurrences and already reviewed targets; no new paragraph meanings or independent legal acceptance.'}


def expected(graph, assembly):
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}

    def targets(ids):
        spans = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in ids]
        return [{**p, 'language': raw[p['source']['unit']]['language']}
                for p in basf_agents.source_pieces(graph, units, spans)]

    def row(identity, page, line, text, target_rows, reason, form='relative'):
        unit = raw[f'{basf.KEY}:p{page}:l{line}']
        if unit['raw'].count(text) != 1:
            raise ValueError('Reference source must be unique: ' + identity)
        start = unit['raw'].index(text)
        source = anchor(unit, start, start + len(text))
        return {'id': identity, 'form': form, 'source': source, 'authority': source,
                'from_use': unit['id'], 'language': unit['language'], 'targets': target_rows,
                'questions': ['Q1', 'Q2'], 'reason': reason,
                'discovery_ids': [r['id'] for r in graph['references'] if r['unit'] == unit['id']
                                  and start <= r['start'] < r['end'] <= source['end']]}

    notice_ids = basf_notices.lines(132, 20, 29) + basf_notices.lines(132, 35, 39)
    rows = [row(f'prose-notice-{p}-{n}', p, n, '§ 13', targets(notice_ids),
                'The selected clause explicitly imports section 13. Retain all three selected notice paragraphs, their conditions and the ownership-proof onward reference.')
            for p, n in NOTICE_SOURCES]
    for line in (25, 27):
        rows.append(row(f'clearing-publication-{line}', 132, line, 'Absatz (1)',
                        targets(basf_notices.PARAGRAPHS['basf-notices:publication']),
                        'Section 13(2) refers to the selected exchange-publication paragraph 13(1), not the excluded unlisted-note alternative.'))
    rows.append(row('payment-exchange-certification', 113, 92, '§ 1',
                    targets(basf_global_exchange.PARAGRAPHS[basf_global_exchange.EXCHANGE]),
                    'The reference continues on source p114:l2 as Absatz (3)(b); both source lines are required. Import complete selected exchange/certification paragraph 1(3)(b), not 1(3)(a).'))
    rows.append(row('default-debt-definition', 126, 50, '§ 2 Absatz (2)',
                    targets(basf_status_pledge.PARAGRAPHS[basf_status_pledge.DEFINITION]),
                    'The words wie ... definiert import the complete capital-market-indebtedness definition at the end of 2(2); actual default and debt classification remain unevaluated.'))
    proof = []
    for line, left, right in [(72, '(a) den', None), (73, None, None), (74, None, None), (75, None, ' und (c)')]:
        unit = raw[f'{basf.KEY}:p132:l{line}']
        start = unit['raw'].index(left) if left else 0
        end = unit['raw'].index(right) if right else len(unit['raw'])
        proof.append({'source': anchor(unit, start, end), 'use': unit['id'], 'language': unit['language']})
    rows.append(row('holding-proof-information', 132, 77, 'vorstehend unter (a) und (b)', proof,
                    'The clearing-system declaration refers back to the certificate information in (a) and (b): holder name/address and booked principal/date. Do not import the distinct (c) requirement into its own target.'))
    context = anchor(raw[f'{basf.KEY}:p114:l2'])
    if not context['quote'].startswith('Absatz (3)(b).'):
        raise ValueError('Split payment citation continuation changed')
    selected = []
    for key in SOURCE_IDS:
        unit = units[key]
        if unit['role'] != 'UNKNOWN':
            raise ValueError('Prose source baseline role changed: ' + key)
        spans = [{'unit': key, 'start': 0, 'end': len(unit['text'])}]
        selected.append({'unit': key, 'text_sha256': digest(unit['text'].encode()), 'role': 'OPERATIVE',
                         'sources': [p['source'] for p in basf_agents.source_pieces(graph, units, spans)],
                         'reason': 'Original Option I page and retained construction reviewed; this surviving reference line is operative under the existing final-terms selection. Its full paragraph meaning remains unknown.'})
    return rows, selected, [context]


def prepare(graph, assembly, request, packet):
    if (packet.get('version') != VERSION or packet.get('graph_sha256') != digest(graph)
            or packet.get('assembly_sha256') != digest(assembly)
            or packet.get('request_sha256') != digest(request)):
        raise ValueError('BASF prose reference baseline changed')
    refs, selected, context = expected(graph, assembly)
    if packet.get('references') != refs or packet.get('units') != selected or packet.get('context_sources') != context:
        raise ValueError('Exact complete source, context and target spans required')
    result = deepcopy(request)
    result['reviewed_dispositions']['units'].extend(deepcopy(selected))
    result['reviewed_dispositions']['review'] = deepcopy(packet['review'])
    # The original dispositions bind the raw assembly, not the already reviewed one.
    overlay = {'version': 'reviewed-dispositions.v1', 'assembly_sha256': digest(assembly),
               'review': packet['review'], 'units': selected}
    after = dispositions(graph, assembly, overlay)
    after['reviewed_dispositions'] = deepcopy(result['reviewed_dispositions'])
    result['reference_admission']['assembly_sha256'] = digest(after)
    result['reference_admission']['references'].extend(deepcopy(refs))
    result['reference_admission']['review'] = deepcopy(packet['review'])
    admit(graph, after, result['reference_admission'])
    return result, after
