"""Deliver the retained partial equity reading without completing clipped cells."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-05'
HISTORICAL = BASE / 'attempt-010'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def ref(path):
    return {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


DISTINCTIONS = {
    'historical_flags_scope': 'UNCHANGED_FLAGS_DESCRIBE_ATTEMPT_010',
    'delivery_scope': 'SUPPLIED_PARTIAL_PAGE_59_READING',
    'currency_inferred': False,
    'total_equity_reconstructed': False,
    'dash_imputed_as_zero': False,
    'parent_and_subitem_rows_added_together': False,
    'movement_and_balance_periods_distinct': True,
    'ordinary_and_preference_dividends_are_note_coupons': False,
    'bes_finance_standalone_accounts_supplied': False,
    'note_references': ['12', '37', '38'],
    'note_reference_resolution': 'RETAINED_NOT_AUTOMATICALLY_RESOLVED_BY_FIELD_DELIVERY',
    'selected_incorporation': None,
    'source_authority_or_incorporation_resolved': False,
    'financial_or_legal_truth_verified': False,
    'general_automatic_interpretation': False,
}


def make_reading(units):
    retained = read(HISTORICAL / 'reading.json.gz')
    require(units == retained['source_units'], 'Retained equity source differs from original graph')
    require(len(units) == 463 and [u['order'] for u in units] == list(range(463)),
            'Complete ordered page 59 required')
    def q(order):
        u = units[order]
        return {'id': u['id'], 'quote': u['raw']}
    # These explicit references permit inspection of the historical integer-index
    # schema without treating mere full-page context as downstream interpretation.
    rows = []
    for row in retained['rows']:
        rows.append({'label_source': q(row['label']), 'period': deepcopy(row['period']),
            'cells': [{'column': cell['column'],
                'source': None if cell['source_unit'] is None else q(cell['source_unit']),
                'status': cell['status'], 'value': cell['value']} for cell in row['cells']]})
    return {
        'version': 'bes-h1-equity-consumer-reading.v1',
        'historical_evidence': {name: ref(HISTORICAL / name) for name in
            ('reading.json.gz', 'profile.json', 'SOURCE-REVIEW.md',
             'IMPLEMENTATION-REVIEW.md', 'answer-explanation.json')},
        'retained_010_reading': retained,
        'retained_010_explanation': read(HISTORICAL / 'answer-explanation.json'),
        'columns': [{'name': c['name'], 'headers': [q(n) for n in c['header_units']]}
                    for c in retained['columns']],
        'rows': rows,
        'metadata_sources': [q(n) for n in retained['metadata_units']],
        'distinctions': deepcopy(DISTINCTIONS),
        'source_scope': {'original_page': 59, 'complete_numeric_reading': False,
                         'origin': 'RETAINED_SUPPLIED_DEVELOPMENT_READING',
                         'historical_flags_are_not_current_delivery_status': True},
    }


def validate(actual, units):
    from scripts import prospectus_h1_equity_reading as original
    require(actual == make_reading(units), 'Retained equity reading or source association changed')
    retained = actual['retained_010_reading']
    rows, metadata = original.map_source(units)
    require(rows == retained['rows'] and metadata == retained['metadata_units'],
            'Historical equity row/column mapping changed')
    require(retained['cell_statuses'] ==
            {'SOURCE_NUMBER': 125, 'SOURCE_INCOMPLETE': 39, 'DASH_UNKNOWN': 226},
            'Unknown or intact equity cell census changed')
    require(retained['unit']['scale'] == 'thousands' and retained['unit']['currency'] is None,
            'Clipped currency cannot be completed from context')
    used = [r['label'] for r in rows] + metadata + [c['source_unit']
        for row in rows for c in row['cells'] if c['source_unit'] is not None]
    require(len(used) == len(set(used)) == 463 and set(used) == set(range(463)),
            'Complete equity source partition required')
    require(all(row['cells'][9]['value'] is None and
                row['cells'][9]['status'] == 'SOURCE_INCOMPLETE' for row in rows),
            'Clipped equity totals remain unknown')
    require(retained['footnotes'] == original.FOOTNOTES and
            retained['limits'] == original.LIMITS, 'Historical footnotes or limits changed')
    return {'original_occurrences': 463, 'rows': 39, 'numeric_cells': 125,
            'unknown_dashes': 226, 'unknown_total_positions': 39,
            'missing_total_occurrences': 4, 'historical_reading_preserved': True,
            'complete_source_partition': True, 'independent_reading': False,
            'arithmetic_role': 'EXPLANATORY_ONLY',
            'complete_numeric_reading': False, 'financial_or_legal_truth_verified': False}
