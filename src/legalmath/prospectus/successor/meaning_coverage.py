"""Explain BASF coverage without treating source bookkeeping as legal scope."""
from collections import Counter

from .contracts import digest

CATEGORIES = ('BODY_CANDIDATE', 'MARGIN_INSTRUCTION', 'PAGE_HEADER', 'OTHER_DOSSIER_SOURCE')


def explain(graph, construction, assembly, clauses):
    """Reconcile retained units and exact nonspace semantic coverage.

    Source category is inherited from construction. It neither excludes context
    nor changes the source role, clause effect, or any answer.
    """
    def unique(rows, key):
        result = {row[key]: row for row in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate meaning-coverage identity: ' + key)
        return result

    source = unique(graph['units'], 'id')
    selected = unique(assembly['units'], 'unit')
    accounting = unique(construction['unit_accounting'], 'unit')
    if set(source) != set(selected) or set(source) != set(accounting):
        raise ValueError('Meaning coverage requires all source, assembly and accounting identities')
    if set(row['role'] for row in accounting.values()) - set(CATEGORIES):
        raise ValueError('Unsupported construction source category')
    if assembly['source_graph_sha256'] != digest(graph) or clauses['assembly_sha256'] != digest(assembly):
        raise ValueError('Meaning coverage source or assembly binding changed')
    nodes = unique(clauses['nodes'], 'id')
    # Coverage is deliberately per source occurrence, not a text-string match.
    known, unknown = {}, {}
    for node in nodes.values():
        if not node['spans'] and node['quote']:
            raise ValueError('Meaning coverage has an unbound quotation')
        fragments = []
        previous = {}
        for span in node['spans']:
            key, start, end = span['unit'], span['start'], span['end']
            if (key not in selected or key not in node['units'] or
                    type(start) is not int or type(end) is not int or
                    not 0 <= start < end <= len(selected[key]['text']) or
                    start < previous.get(key, 0)):
                raise ValueError('Meaning coverage interval is invalid')
            previous[key] = end
            text = selected[key]['text']
            fragments.append(text[start:end])
            target = unknown if node['effect'] == 'unknown' else known
            target.setdefault(key, set()).update(i for i in range(start, end) if not text[i].isspace())
        if ' '.join(fragments) != node['quote']:
            raise ValueError('Meaning coverage quotation differs from selected occurrences')

    summaries = {}
    pending = []
    for category in CATEGORIES:
        ids = [key for key in selected if accounting[key]['role'] == category]
        roles = Counter(selected[key]['role'] for key in ids)
        totals = Counter()
        for key in ids:
            unit = selected[key]
            if unit['role'] not in ('OPERATIVE', 'UNKNOWN'):
                continue
            characters = {i for i, ch in enumerate(unit['text']) if not ch.isspace()}
            understood = characters & known.get(key, set())
            unresolved = characters & unknown.get(key, set())
            uncovered = characters - understood - unresolved
            totals.update(nonspace=len(characters), known_only=len(understood - unresolved),
                          unknown_only=len(unresolved - understood),
                          mixed=len(understood & unresolved), uncovered=len(uncovered))
            if category == 'BODY_CANDIDATE' and (unit['role'] == 'UNKNOWN' or unresolved or uncovered):
                pending.append({'unit': key, 'page': source[key]['page'],
                                'role_unresolved': unit['role'] == 'UNKNOWN',
                                'unknown_characters': len(unresolved),
                                'uncovered_characters': len(uncovered)})
        values = {name: totals[name] for name in ('nonspace', 'known_only', 'unknown_only', 'mixed', 'uncovered')}
        if values['nonspace'] != sum(values[k] for k in ('known_only', 'unknown_only', 'mixed', 'uncovered')):
            raise ValueError('Meaning character categories do not reconcile')
        summaries[category] = {'units': len(ids), 'unit_ids_sha256': digest(ids),
                               'assembly_roles': dict(sorted(roles.items())), 'active_characters': values}
    return {'version': 'basf-meaning-coverage.v1',
            'source_graph_sha256': digest(graph), 'construction_sha256': digest(construction),
            'assembly_sha256': digest(assembly), 'clauses_sha256': digest(clauses),
            'source_categories': summaries, 'selected_body_pending': pending,
            'interpretation': 'Selected German body, marginal instructions, page headers and other dossier sources are counted separately. Other dossier sources include authority and context; this distinction does not exclude them from the legal questions.',
            'meaning': 'Known means a supplied or nominated non-unknown effect, not an independently accepted legal reading. Mixed characters retain both kinds of interpretation.',
            'legal_scope_resolved': False, 'independent_legal_acceptance': False}
