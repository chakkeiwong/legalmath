"""Source-bound conditional rounding analysis reached by the pension consumer."""
from copy import deepcopy
from pathlib import Path

from .basf_statement import DOCUMENT
from .rounding_enclosure import enclose
from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'basf-pension-reconciliation.v1'
POLICY = (
    '\u00adpresented in euros. They are written in German and translated into',
    'English. All amounts, including the figures for previous years, are',
    'given in million euros unless otherwise indicated. Due to rounding,',
    'individual figures in this report may not add up to the totals shown',
    'and percentages may not correspond exactly to the figures shown.',
)
HYPOTHESES = (
    {'id': 'half-million-error', 'error_bound': '1/2', 'basis': 'SUPPLIED_HYPOTHESIS'},
    {'id': 'one-million-error', 'error_bound': '1', 'basis': 'SUPPLIED_HYPOTHESIS'},
)
ADDED_KEYS = ('pension_reconciliation_review', 'pension_reconciliation_explanation')
SUPPORTED_VALUES = ((3758, 6800, -2641, -431), (2586, 3758, -1256, 83),
                    (3476, 1496, 1935, None), (2709, 3476, -811, 44))


def relations(consumer):
    """Use the already source-validated cells; never feed a reported residual."""
    net = {r['id']: r for r in consumer['pension_note_review']['tables']['net']['rows']}
    statement = {r['id']: r for r in consumer['statement_review']['rows']}

    def statement_cell(row, year):
        q = statement[row]['cells'][year]
        return {'value': q['integer_millions'], 'unit': 'million EUR', 'kind': 'million_eur',
                'literal': q['literal'], 'source': deepcopy(q['source'])}

    out = []
    for year in ('2022', '2021'):
        out.append({'id': 'candidate-remeasurement-bridge:' + year,
            'quantities': [statement_cell('pensions', year)] +
                [deepcopy(net[r]['cells'][year]) for r in ('actuarial', 'return_deviation', 'ceiling')],
            'coefficients': [1, -1, -1, -1],
            'labels': ['statement-remeasurement', 'actuarial', 'return-deviation', 'signed-ceiling'],
            'scope_equivalence_established': False,
            'scope': 'Candidate common complete scope with the statement; not established by the note'})
        out.append({'id': 'statement-nonreclassifiable-subtotal:' + year,
            'quantities': [statement_cell(r, year) for r in ('nonrec', 'pensions', 'pension_tax', 'equity_nonrec')],
            'coefficients': [1, -1, -1, -1],
            'labels': ['nonreclassifiable-subtotal', 'pensions', 'pension-tax', 'equity-method'],
            'scope_equivalence_established': True,
            'scope': 'Same printed statement subtotal and its three printed components'})
    for row in out:
        if any((q['kind'], q['unit']) != ('million_eur', 'million EUR') for q in row['quantities']):
            raise ValueError('Same million-EUR quantity type required for reconciliation')
        if any(q['value'] is not None and type(q['value']) is not int for q in row['quantities']):
            raise ValueError('Exact printed integer amounts or unknowns required')
    return out


def evaluate(graph, consumer, profile, root, *, expected_profile_sha256):
    keys = {'version', 'graph_sha256', 'consumer_sha256', 'source', 'policy', 'hypotheses',
            'actual_rounding_algorithm_established', 'selected_incorporation_reading'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != digest(graph) or profile['consumer_sha256'] != digest(consumer)):
        raise ValueError('Pinned reconciliation profile, graph or complete consumer changed')
    if (profile['hypotheses'] != list(HYPOTHESES)
            or profile['actual_rounding_algorithm_established'] is not False
            or profile['selected_incorporation_reading'] is not None):
        raise ValueError('Supplied hypotheses cannot establish a source algorithm or incorporation')
    source = profile['source']
    source_keys = {'document', 'path', 'sha256', 'image_path', 'image_sha256', 'page'}
    fields(source, source_keys, source_keys)
    if (source['document'] != DOCUMENT or source['page'] != 209
            or source['sha256'] != consumer['pension_note_review']['profile']['source']['sha256']):
        raise ValueError('Same original BASF report and policy page required')
    root = Path(root).resolve()
    for name, expected in (('path', 'sha256'), ('image_path', 'image_sha256')):
        path = (root / source[name]).resolve()
        if (Path(source[name]).is_absolute() or not path.is_relative_to(root)
                or not path.is_file() or digest(path.read_bytes()) != source[expected]):
            raise ValueError('Original policy PDF or image changed')
    if not isinstance(profile['policy'], list) or len(profile['policy']) != len(POLICY):
        raise ValueError('Complete policy context required')
    policy = []
    for line, a, literal in zip(range(24, 29), profile['policy'], POLICY):
        bound = bind(graph, a)
        if (bound['unit'] != DOCUMENT + ':p209:l' + str(line) or bound['start'] != 0
                or bound['end'] != len(literal) or bound['quote'] != literal
                or bound['source_sha256'] != source['sha256'] or bound['page'] != 209):
            raise ValueError('Exact original rounding policy and translation context required')
        policy.append(bound)
    checked = []
    for row, supported in zip(relations(consumer), SUPPORTED_VALUES):
        values = [q['value'] for q in row['quantities']]
        if tuple(values) != supported:
            raise ValueError('Outside the reviewed original BASF amount configuration')
        hypotheses = []
        for h in HYPOTHESES:
            hypotheses.append({**h, **enclose(values, row['coefficients'], [h['error_bound']] * len(values))})
        checked.append({**row, 'hypotheses': hypotheses,
            'symbolic_residual': {'known_part': sum(v * c for v, c in zip(values, row['coefficients']) if v is not None),
                'unknown_terms': [{'label': label, 'coefficient': c} for v, c, label in zip(values, row['coefficients'], row['labels']) if v is None]},
            'rounding_cause_established': False, 'residual_attributed': False})
    return {'version': VERSION, 'profile_sha256': digest(profile), 'source': deepcopy(source),
        'policy': policy, 'relations': checked,
        'actual_rounding_algorithm_established': False, 'source_error_established': False,
        'selected_incorporation_reading': None, 'financial_values_validated': False,
        'answer': {
            'status': 'CONDITIONAL_SOURCE_BOUND_ARITHMETIC',
            '2022_candidate_bridge': 'The displayed difference is EUR30 million. If these amounts have the proposed complete common scope, per-amount errors bounded by half a million permit at most EUR2 million, and errors bounded by one million permit at most EUR4 million. Neither hypothesis explains EUR30 million. The common scope and actual rounding method remain unestablished.',
            '2022_statement_subtotal': 'The separate EUR1 million subtotal difference is within both error enclosures. This does not establish that rounding caused it.',
            '2021_candidate_bridge': 'The residual is EUR45 million minus the unknown signed ceiling amount. The printed dash remains unknown. A separate EUR45 million acquisitions/divestitures entry does not establish a reconciliation.',
            '2021_statement_subtotal': 'The printed subtotal agrees exactly with its three printed components.',
            'unresolved': ['Cause and complete scope of the EUR30 million difference',
                           'Meaning and amount of the 2021 signed-ceiling dash',
                           'Actual rounding method', 'Controlling incorporation reading'],
            'actual_rounding_cause_established': False, 'unique_complete_bridge_established': False,
            'source_error_established': False, 'financial_values_validated': False}}
