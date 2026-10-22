"""Build the reviewed H1 relationship candidate from retained source-audit evidence."""
from copy import deepcopy
from pathlib import Path

from scripts import prospectus_h1_statement_consumer as common

ROOT = common.ROOT
MODULE = 'src/legalmath/prospectus/h1_source_relationships.py'
WRAPPER = 'src/legalmath/prospectus/h1_incorporation_scope.py'
TEMPLATE = '.localresources/prospectus-preparation/h1-current-relationships-064/h1_source_relationships.py'
VERSION = 'bes-h1-current-relationships.v1'
LIMITS = {'source_specific_supplied_review': True,
    'target_availability_is_financial_reconciliation': False,
    'financial_reconciliation_established': False, 'source_authenticity_established': False,
    'legal_incorporation_selected': False, 'automatic_interpretation_proved': False,
    'original_task_complete': False}
CASES = ('stale-prior', 'changed-pin', 'wrong-source-role', 'wrong-note-target',
    'financial-reconciliation', 'missing-unit-result', 'missing-profile', 'missing-link')
REFUSALS = {
    'stale-prior': 'Pinned H1 relationship profile, graph or complete prior answer changed',
    'changed-pin': 'Pinned H1 relationship profile, graph or complete prior answer changed',
    'wrong-source-role': 'H1 source relationships differ from the reviewed source map',
    'wrong-note-target': 'H1 source relationships differ from the reviewed source map',
    'financial-reconciliation': 'H1 relationship availability cannot establish financial or legal correctness',
    'missing-unit-result': 'Current H1 unit review required for source relationships',
    'missing-profile': 'H1 relationship profile missing for supplied identity',
    'missing-link': 'H1 source relationships differ from the reviewed source map',
}


def anchor(source):
    return {'unit': source['id'], 'document': source['document'],
        'source_sha256': source['source_sha256'], 'start': 0, 'end': len(source['quote']),
        'quote': source['quote'], 'bbox': source['bbox']}


def relationships(audit):
    common.require(audit['status'] == 'SUPPLIED_ASSOCIATIONS_CHECKED_CURRENT_LINK_GAPS_RETAINED',
        'Successful source association audit required')
    rows = []
    for row in audit['residual_associations']:
        contexts = [p for p in row['current_context_paths'] if p.startswith('/source_statement_cells/')]
        common.require(contexts, 'Original inner context required')
        rows.append({'source': anchor(row['source']), 'role': row['reviewed_role'],
            'context_paths': contexts, 'targets': deepcopy(row['reviewed_targets']),
            'target_available': True, 'association_basis': 'SUPPLIED_ORIGINAL_SOURCE_REVIEW',
            'meaning_independently_proved': False})
    for row in audit['equity_references']:
        caution = {
            12: 'Net-of-tax equity movements are not gross staff costs; no tax reconciliation is established.',
            37: 'The treasury table includes a full-year 2009 comparator; separate equity half-year movements are not equated.',
            38: 'Other changes are not the entire NCI movement; the December duration tension remains.',
        }[row['note']]
        if 'relationship' in row:
            caution = 'Preference-share dividends are not prospectus note coupons; June accounting, declaration and July payment dates differ.'
        rows.append({'source': anchor(row['source']), 'role': row.get('relationship', 'EQUITY_ROW_NOTE_REFERENCE'),
            'reference_path': row['current_reference_path'], 'note': row['note'],
            'period': deepcopy(row.get('period')), 'targets': deepcopy(row['reviewed_targets']),
            'target_available': True, 'financial_reconciliation_established': False,
            'relationship_limit': caution, 'association_basis': 'SUPPLIED_ORIGINAL_SOURCE_REVIEW'})
    common.require(len(rows) == 48 and len({r['source']['unit'] for r in rows}) == 48,
        'Complete distinct reviewed 38 context and 10 equity links required')
    return rows


def profile(graph, prior, audit):
    return {'version': VERSION, 'graph_sha256': common.digest(graph),
        'prior_sha256': common.digest(prior), 'relationships': relationships(audit), 'limits': deepcopy(LIMITS)}


def candidates(value):
    module = (ROOT / TEMPLATE).read_text()
    for token, replacement in {
        '__REVIEWED_MAP_SHA256__': common.compact_digest(value['relationships']),
        '__REVIEWED_GRAPH_SHA256__': value['graph_sha256'],
        '__REVIEWED_PRIOR_SHA256__': value['prior_sha256'],
    }.items():
        common.require(module.count(token) == 1, 'Unreviewed module placeholder')
        module = module.replace(token, replacement)
    wrapper = (ROOT / WRAPPER).read_text()
    replacements = [
        ('            expected_unit_profile_sha256=None):',
         '            expected_unit_profile_sha256=None, relationship_profile=None,\n'
         '            expected_relationship_profile_sha256=None):'),
        ("            raise ValueError('H1 unit profile missing for supplied identity')\n        return answer",
         "            raise ValueError('H1 unit profile missing for supplied identity')\n"
         "        if relationship_profile is not None or expected_relationship_profile_sha256 is not None:\n"
         "            raise ValueError('Current H1 unit review required for source relationships')\n        return answer"),
        ("    return {**answer, 'h1_individual_unit_review': unit_review,\n"
         "            'h1_individual_unit_explanation': h1_unit_conflict.explain(unit_review)}",
         "    answer = {**answer, 'h1_individual_unit_review': unit_review,\n"
         "              'h1_individual_unit_explanation': h1_unit_conflict.explain(unit_review)}\n"
         "    if relationship_profile is None:\n"
         "        if expected_relationship_profile_sha256 is not None:\n"
         "            raise ValueError('H1 relationship profile missing for supplied identity')\n"
         "        return answer\n"
         "    from . import h1_source_relationships\n"
         "    relationships = h1_source_relationships.evaluate(products['P1']['payload']['graph'],\n"
         "        answer, relationship_profile, expected_profile_sha256=expected_relationship_profile_sha256)\n"
         "    return {**answer, 'h1_source_relationship_review': relationships,\n"
         "            'h1_source_relationship_explanation': h1_source_relationships.explain(relationships)}"),
    ]
    for old, new in replacements:
        common.require(wrapper.count(old) == 1, 'Public wrapper baseline changed')
        wrapper = wrapper.replace(old, new)
    return {MODULE: module, WRAPPER: wrapper}


def consume(products, profiles, value, case=None):
    from legalmath.prospectus import h1_incorporation_scope as scope
    from legalmath.prospectus.successor.contracts import digest
    argument = deepcopy(value)
    pin = None
    unit = profiles['unit']
    unit_pin = digest(unit)
    if case == 'stale-prior':
        argument['prior_sha256'] = '0' * 64
    elif case == 'changed-pin':
        pin = '0' * 64
    elif case == 'wrong-source-role':
        row = next(r for r in argument['relationships'] if r['source']['unit'].endswith(':p125:l105'))
        row['role'] = 'TOTAL_DATA_ROW'
    elif case == 'wrong-note-target':
        rows = argument['relationships']
        next(r for r in rows if r.get('note') == 12)['targets'] = deepcopy(next(r for r in rows if r.get('note') == 37)['targets'])
    elif case == 'financial-reconciliation':
        argument['limits']['financial_reconciliation_established'] = True
    elif case == 'missing-unit-result':
        unit, unit_pin = None, None
    elif case == 'missing-profile':
        pin, argument = digest(argument), None
    elif case == 'missing-link':
        argument['relationships'].pop()
    common.require(case is None or case in CASES, 'Unknown relationship corruption')
    return scope.consume(products, profiles['cash'], profiles['risk'], profiles['scope'], ROOT,
        expected_cash_profile_sha256=digest(profiles['cash']), expected_risk_profile_sha256=digest(profiles['risk']),
        expected_profile_sha256=digest(profiles['scope']), unit_profile=unit, expected_unit_profile_sha256=unit_pin,
        relationship_profile=argument, expected_relationship_profile_sha256=pin if pin is not None else digest(argument))


def verify(answer, baseline, value, audit):
    added = {'h1_source_relationship_review', 'h1_source_relationship_explanation'}
    common.require(set(answer) == set(baseline) | added and
        {k: v for k, v in answer.items() if k not in added} == baseline, 'Complete 063 answer changed')
    expected = relationships(audit)
    common.require(value['relationships'] == expected, 'Prepared source links differ from independent audit')
    review = answer['h1_source_relationship_review']
    common.require(review == {'version': VERSION, 'status': 'SUPPLIED_CURRENT_SOURCE_RELATIONSHIPS',
        'graph_sha256': value['graph_sha256'], 'prior_sha256': value['prior_sha256'],
        'profile_sha256': common.digest(value), 'reviewed_map_sha256': common.compact_digest(expected),
        'relationships': expected, 'limits': LIMITS}, 'Current source relationship result differs')
    explanation = answer['h1_source_relationship_explanation']
    common.require(explanation == {
        'basis': 'Supplied source-specific review of the retained H1 report.',
        'relationships': expected,
        'meaning': 'The listed source passages and relevant current fields are available together. '
            'Their links identify report context, table headings, footnotes and referenced note clauses.',
        'financial_reconciliation': 'The links do not reconcile net-of-tax equity movements with staff costs, '
            'align different reporting periods, or equate other changes with the full non-controlling-interest movement.',
        'preserved_limits': 'The clipped equity totals and currency, individual-statement unit conflict, '
            'source authority, Portuguese priority and alternative incorporation readings remain unresolved.',
        'limits': LIMITS}, 'Required source relationship explanation differs')
    return {'whole_063_preserved': True, 'reviewed_source_links': 38, 'equity_references': 10,
        'target_availability_distinct_from_reconciliation': True,
        'original_task_complete': False, 'source_truth_established': False}
