"""Changed shape guards around the immutable seven-reading source oracle."""
from scripts import prospectus_unquoted_definitions_oracle as source
from legalmath.prospectus.successor.contracts import digest

KEY = source.KEY
REPORT_KEYS = set('profile_sha256 products_sha256 ordinary_answer_sha256 version '
    'text_sha256 language candidates issues scope_admitted meaning_admitted '
    'general_recall_established automatic_legal_interpretation unsupported '
    'prior_answer_preserved original_records_preserved whole_task_complete '
    'legal_truth_established'.split())
ROW_KEYS = set('kind start end raw region label term value scope condition '
    'printed_scope_address governing_scope meaning review_required '
    'legal_meaning_established source_projection'.split())
KINDS = {'PARENTHETICAL_EXPLICATION', 'REFERENCE_EXPANSION',
         'PURPOSE_CONDITIONED_AMOUNT', 'LEGISLATIVE_ALIAS'}


def mapping(value, required, name):
    assert type(value) is dict, name + ': expected dictionary'
    assert set(value) == required, name + ': missing or unexpected fields'


def span(value, name, *, projected=True):
    required = {'start', 'end', 'raw'} | ({'source_projection'} if projected else set())
    mapping(value, required, name)
    assert type(value['start']) is int and type(value['end']) is int, name + ': integer offsets required'
    assert 0 <= value['start'] < value['end'], name + ': invalid interval'
    assert type(value['raw']) is str and value['raw'], name + ': missing quotation'
    if projected:
        assert type(value['source_projection']) is list, name + ': missing source projection'


def shape(report):
    mapping(report, REPORT_KEYS, 'report')
    assert type(report['candidates']) is list and len(report['candidates']) == 7, 'candidate coverage'
    for row in report['candidates']:
        mapping(row, ROW_KEYS, 'candidate')
        assert type(row['kind']) is str and row['kind'] in KINDS, 'unsupported candidate kind'
        for key in ('start', 'end'):
            assert type(row[key]) is int, 'integer candidate offsets required'
        assert type(row['source_projection']) is list, 'missing expression projection'
        span(row['term'], 'term')
        span(row['value'], 'value')
        if row['kind'] == 'LEGISLATIVE_ALIAS':
            assert row['scope'] is None, 'alias acquired a scope'
        else:
            span(row['scope'], 'scope')
        if row['kind'] == 'REFERENCE_EXPANSION':
            span(row['condition'], 'condition')
        else:
            assert row['condition'] is None, 'unexpected applicability condition'
        if row['kind'] == 'PURPOSE_CONDITIONED_AMOUNT':
            mapping(row['printed_scope_address'], {'section', 'paragraph'}, 'scope address')
        else:
            assert row['printed_scope_address'] is None, 'unexpected scope address'
    assert type(report['issues']) is list, 'missing unsupported-cue report'
    for issue in report['issues']:
        mapping(issue, {'kind', 'start', 'end', 'raw', 'region'}, 'issue')
        assert type(issue['start']) is int and type(issue['end']) is int, 'integer issue offsets required'


def verify(actual, old, products, expected, profile):
    assert type(actual) is dict and KEY in actual, 'missing definition report'
    assert type(actual.get('report_sha256')) is str, 'missing answer digest'
    shape(actual[KEY])
    assert actual[KEY]['profile_sha256'] == digest(profile), 'changed profile identity'
    result = source.verify(actual, old, products, expected)
    return {**result, 'explicit_schema_refusals': True, 'profile_identity_checked': True}
