"""Deliver the retained management/individual reading without resolving source conflicts."""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-05'
HISTORICAL = BASE / 'attempt-016'
HISTORICAL_FILES = ('source-units.json', 'profile.json', 'analysis.json', 'images.json',
                    'reading.py', 'SOURCE-REVIEW.md', 'IMPLEMENTATION-REVIEW.md')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def ref(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def evaluator():
    spec = importlib.util.spec_from_file_location('retained_management_reading', HISTORICAL / 'reading.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DISTINCTIONS = {
    'historical_flags_scope': 'UNCHANGED_FLAGS_DESCRIBE_ATTEMPT_016',
    'delivery_scope': 'SUPPLIED_COMPLETE_PAGES_51_54_READING_WITH_UNRESOLVED_SOURCE_UNIT_CONFLICT',
    'individual_balance_printed_unit': 'EUR million',
    'individual_income_printed_unit': 'EUR thousands',
    'unit_conflict_resolved': False,
    'numeral_agreement_is_financial_equality': False,
    'dash_imputed_as_zero': False,
    'of_which_rows_added_twice': False,
    'gross_adjustment_net_are_separate_columns': True,
    'individual_comparative_date': '2009-06-30',
    'arithmetic_bridge_proves_accounting_rationale': False,
    'page51_equity_restores_page59_clipping': False,
    'individual_bank_is_bes_finance': False,
    'individual_parent_and_group_profit_are_distinct': True,
    'selected_incorporation': None,
    'source_authority_or_incorporation_resolved': False,
    'financial_or_legal_truth_verified': False,
    'general_automatic_interpretation': False,
}


def make_reading(units):
    retained_units = read(HISTORICAL / 'source-units.json')
    require(units == retained_units, 'Retained management source differs from original graph')
    require(len(units) == len({u['id'] for u in units}) == 640, 'Complete 640 original occurrences required')
    profile = read(HISTORICAL / 'profile.json')
    analysis = read(HISTORICAL / 'analysis.json')
    lookup = {u['id']: u for u in units}
    tables = deepcopy(profile['reading']['tables'])
    for table in tables.values():
        for row in table['rows']:
            for cell in row['cells']:
                unit = lookup[cell['source_unit']]
                require(unit['raw'] == cell['quote'], 'Original management cell quote differs')
                cell['source'] = {'id': unit['id'], 'quote': unit['raw']}
    return {
        'version': 'bes-h1-management-consumer-reading.v1',
        'historical_evidence': {name: ref(HISTORICAL / name) for name in HISTORICAL_FILES},
        'prior_comparison_evidence': ref(BASE / 'attempt-015/answer-supplement.json.gz'),
        'retained_016_reading': {'source_units': retained_units, 'profile': profile, 'analysis': analysis},
        'tables': tables,
        'distinctions': deepcopy(DISTINCTIONS),
        'source_scope': {'original_pages': [51, 52, 53, 54],
            'origin': 'RETAINED_SUPPLIED_DEVELOPMENT_READING',
            'historical_flags_are_not_current_delivery_status': True,
            'original_source_unit_conflict': 'UNRESOLVED'},
    }


def validate(actual, units):
    require(actual == make_reading(units), 'Retained management reading or source association changed')
    retained = actual['retained_016_reading']
    profile, analysis = retained['profile'], retained['analysis']
    require(profile['source_units'] == [{'id': u['id'], 'quote': u['raw']} for u in units],
            'Historical management quote inventory changed')
    require(profile['images'] == read(HISTORICAL / 'images.json') and
            all(ref(ROOT / item['path'])['sha256'] == item['sha256'] for item in profile['images']),
            'Original management images changed')
    require(profile['prior_sha256'] == actual['prior_comparison_evidence']['sha256'],
            'Original comparison evidence changed')
    calculated = evaluator().evaluate(units, profile['reading'])
    extras = {'conditional_scope', 'limits', 'statement_readings'}
    require(calculated == {key: value for key, value in analysis.items() if key not in extras},
            'Historical management evaluator result differs')
    prior = read(BASE / 'attempt-015/answer-supplement.json.gz')
    expected_scope = [{'construction': c['id'],
        'management_and_individual_statements_included': {51, 52, 53, 54} <= set(c['pages'])}
        for c in prior['h1_scope_review']['candidates']]
    require(analysis['conditional_scope'] == expected_scope and analysis['limits'] == profile['limits'],
            'Historical management scope or limits changed')
    require(analysis['statement_readings'] == {
        '51-52': 'CURRENT_CONSOLIDATED_MANAGEMENT_READING',
        '53-54': 'CURRENT_INDIVIDUAL_BANK_READING',
        '56-58': 'PRIOR_CONSOLIDATED_STATEMENTS_RETAINED',
        '59': 'PRIOR_TRUNCATION_LIMITS_RETAINED'}, 'Historical statement status changed')
    require(analysis['cell_statuses'] == {'SOURCE_NUMBER': 360, 'DASH_UNKNOWN': 80},
            'Management unknowns or numeric census changed')
    require(not any(profile['limits'].values()), 'Historical unsupported acceptance flag changed')
    return {'original_occurrences': 640, 'tables': 8, 'positions': 440,
        'numeric_cells': 360, 'unknown_dashes': 80, 'historical_reading_preserved': True,
        'historical_evaluator_reproduced': True, 'historical_scope_additions_preserved': True,
        'direct_comparisons': len(analysis['internal_checks']['direct_comparisons']),
        'unit_conflict_resolved': False, 'independent_reading': False,
        'arithmetic_role': 'EXPLANATORY_ONLY', 'financial_or_legal_truth_verified': False}


def adverse_readings(reading):
    original = evaluator()
    for name in original.MUTATIONS:
        changed = deepcopy(reading)
        changed['retained_016_reading']['profile'] = original.altered(
            reading['retained_016_reading']['profile'], name)
        require(changed != reading, 'Historical mutation did not change an existing value: ' + name)
        yield 'historical-' + name, changed
    cases = [
        ('current-column', ('tables', 'individual_assets', 'columns', 3), '2009-12-31 net'),
        ('current-unit', ('tables', 'individual_assets', 'rows', 18, 'cells', 2, 'printed_unit'), 'EUR thousands'),
        ('current-dash', ('tables', 'individual_assets', 'rows', 0, 'cells', 1, 'value'), 0),
        ('current-parent', ('tables', 'management_assets', 'rows', 6, 'parent_row'), None),
        ('cell-reference', ('tables', 'management_equity', 'rows', 10, 'cells', 0, 'source', 'quote'), '0'),
        ('historical-scope', ('retained_016_reading', 'analysis', 'conditional_scope', 0,
                              'management_and_individual_statements_included'), False),
        ('historical-limits', ('retained_016_reading', 'analysis', 'limits', 'production_integration_claimed'), True),
        ('unit-equality', ('distinctions', 'numeral_agreement_is_financial_equality'), True),
        ('rationale', ('distinctions', 'arithmetic_bridge_proves_accounting_rationale'), True),
        ('clipped-equity', ('distinctions', 'page51_equity_restores_page59_clipping'), True),
        ('incorporation', ('distinctions', 'selected_incorporation'), 'overall-range'),
    ]
    for name, path, value in cases:
        changed = deepcopy(reading)
        node = changed
        for key in path[:-1]:
            node = node[key]
        require(node[path[-1]] != value, 'Mutation must change an existing value: ' + name)
        node[path[-1]] = value
        yield name, changed
    changed = deepcopy(reading)
    del changed['tables']['individual_income']
    yield 'lost-table', changed
