"""A supplied, finite bilingual individual-statement reading; no source repair."""
from copy import deepcopy
import re

from .admissions import review
from .anchors import bind, fields
from .contracts import bound_path, digest

PROFILE = 'bes2008-individual-cash-flow.v1'
ADDED = 'source_cash_flow_reconciliation'
YEARS = ('2008', '2007')
COMPONENTS = ('buy_investments', 'sell_investments', 'dividend', 'buy_AFS',
              'sell_AFS', 'HTM', 'buy_fixed', 'sell_fixed')
BRIDGE = ('operating', 'investing', 'financing', 'merger_leasing', 'merger_BESSA')
# Reviewed positions in the original supplied reading. These are not a table
# detector, translation dictionary, or authority for another source edition.
LAYOUT = {
    'en': {
        'buy_investments': (66, 67, 70, 'Acquisition of subsidiaries and associates'),
        'sell_investments': (68, 69, 71, 'Disposal of subsidiaries and associates'),
        'dividend': (72, 73, 74, 'Dividends received'),
        'buy_AFS': (75, 76, 77, 'Acquisition of available-for-sale financial assets'),
        'sell_AFS': (78, 79, 80, 'Sale of available-for-sale financial assets'),
        'HTM': (81, 82, 83, 'Held to maturity investments'),
        'buy_fixed': (84, 85, 86, 'Acquisition of tangible and intangible assets'),
        'sell_fixed': (87, 88, 89, 'Sale of tangible and intangible assets'),
        'investing': (90, 91, 92, 'Net cash flow from investing activities'),
        'operating': (62, 63, 64, 'Net cash flow from operating activities'),
        'financing': (113, 114, 115, 'Net cash flow from financing activities'),
        'merger_leasing': (116, 117, 118, 'Effect of Bes Leasing’s merger on cash and cash equivalents'),
        'merger_BESSA': (119, 120, 121, 'Effect of BESSA’s merger on cash and cash equivalents'),
        'net_change': (122, 123, 124, 'Net changes in cash and cash equivalents'),
    },
    'pt': {
        'buy_investments': (69, 70, 73, 'Aquisição de investimentos em subsidiárias e associadas'),
        'sell_investments': (71, 72, 74, 'Alienação de investimentos em subsidiárias e associadas'),
        'dividend': (75, 76, 77, 'Dividendos recebidos'),
        'buy_AFS': (78, 79, 80, 'Compra de activos financeiros disponíveis para venda'),
        'sell_AFS': (81, 82, 83, 'Venda de activos financeiros disponíveis para venda'),
        'HTM': (84, 85, 86, 'Investimentos detidos até à maturidade'),
        'buy_fixed': (87, 88, 89, 'Compra de imobilizações'),
        'sell_fixed': (90, 91, 92, 'Venda de imobilizações'),
        'investing': (93, 94, 95, 'Fluxos de caixa líquidos das actividades de investimento'),
        'operating': (64, 65, 66, 'Fluxos de caixa líquidos das actividades operacionais'),
        'financing': (116, 117, 118, 'Fluxos de caixa líquidos das actividades de financiamento'),
        'merger_leasing': (120, 121, 122, 'Efeito da fusão do BES Leasing em caixa e seus equivalentes'),
        'merger_BESSA': (123, 124, 125, 'Efeito da fusão do BESSA em caixa e seus equivalentes'),
        'net_change': (126, 127, 128, 'Variação líquida em caixa e seus equivalentes'),
    },
}
HEADINGS = {
    'en': ('Individual Financial Statements and Notes to the Financial Statements',
           'Cash Flow Statement for the years ended 31 December 2008 and 2007',
           'in thousands of euro'),
    'pt': ('Demonstrações Financeiras Individuais e Notas Explicativas',
           'Demonstrações dos Fluxos de Caixa dos Exercícios Findos em 31 de Dezembro de 2008 e 2007',
           'milhares de euros'),
}


def number(literal, language):
    """Parse only printed integer groups in the two reviewed source locales."""
    if not isinstance(literal, str) or language not in LAYOUT:
        raise ValueError('Source integer and supported language required')
    text = literal.strip()
    if text == '-':
        return None
    negative = text.startswith('(') and text.endswith(')')
    body = text[1:-1].strip() if negative else text
    separator = ',' if language == 'en' else ' '
    pattern = r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:' + re.escape(separator) + r'[0-9]{3})+)'
    if not re.fullmatch(pattern, body, flags=re.ASCII):
        raise ValueError('Malformed printed source integer')
    value = int(body.replace(separator, ''))
    return -value if negative else value


def _source(index, supplied, language, page, position, literal=None):
    keys = {'unit', 'document', 'source_sha256', 'start', 'end', 'quote'}
    fields(supplied, keys, keys)
    identity = f'bes-2008-{language}:p{page}:l{position}'
    unit = index.get(identity)
    if (unit is None or unit.get('language') != language or unit.get('page') != page
            or supplied.get('unit') != identity or supplied.get('start') != 0
            or supplied.get('end') != len(unit['raw'])
            or literal is not None and unit['raw'].strip() != literal):
        raise ValueError('Cash-flow source position, context or language differs')
    return bind({'units': [unit]}, supplied)


def relation(rows, year, name, target, components):
    cells = [rows[k]['cells'][year] for k in (target, *components)]
    known = sum((1 if i == 0 else -1) * q['value']
                for i, q in enumerate(cells) if q['value'] is not None)
    unknown = [{'row': k, 'coefficient': 1 if i == 0 else -1}
               for i, (k, q) in enumerate(zip((target, *components), cells)) if q['value'] is None]
    return {'id': name + ':' + year, 'year': year, 'unit': 'EUR thousands',
            'target': target, 'components': list(components),
            'status': 'INCOMPLETE_UNKNOWN' if unknown else 'COMPLETE_EQUALITY' if known == 0 else 'PRINTED_ARITHMETIC_DISCREPANCY',
            'known_residual_part': known, 'unknown_terms': unknown,
            'residual': None if unknown else known,
            'component_sum': None if unknown else sum(q['value'] for q in cells[1:]),
            'official_correction_established': False}


def admit(graph, profile):
    keys = {'version', 'graph_sha256', 'review', 'editions'}
    fields(profile, keys, keys)
    if profile['version'] != PROFILE or profile['graph_sha256'] != digest(graph):
        raise ValueError('Unsupported cash-flow profile or changed source graph')
    review(profile['review'])
    editions = profile['editions']
    if not isinstance(editions, list) or len(editions) != 2:
        raise ValueError('Both individual cash-flow editions required')
    index = {u['id']: u for u in graph['units']}
    if len(index) != len(graph['units']):
        raise ValueError('Duplicate cash-flow source occurrence')
    output, languages = [], set()
    for edition in editions:
        keys = {'language', 'document', 'source_sha256', 'context', 'image', 'rows', 'capital_increase'}
        fields(edition, keys, keys)
        lang = edition['language']
        if lang not in LAYOUT or lang in languages or edition['document'] != 'bes-2008-' + lang:
            raise ValueError('Distinct original cash-flow document/language required')
        languages.add(lang)
        context = edition['context']
        keys = {'individual', 'title', 'unit', 'years'}
        fields(context, keys, keys)
        if not isinstance(context['years'], list) or len(context['years']) != 2:
            raise ValueError('Both original cash-flow date columns required')
        anchors = [_source(index, context[k], lang, page, line, text) for k, page, line, text in
                   zip(('individual', 'title', 'unit'), (165, 170, 170), (1, 0, 1), HEADINGS[lang])]
        dates = [_source(index, a, lang, 170, n, '31.12.' + year)
                 for a, n, year in zip(context['years'], (4, 5), YEARS)]
        image = edition['image']
        fields(image, {'document', 'page', 'path', 'sha256'}, {'document', 'page', 'path', 'sha256'})
        if (image['document'] != edition['document'] or type(image['page']) is not int or image['page'] != 170
                or not isinstance(image['path'], str) or not image['path']
                or not isinstance(image['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', image['sha256'])):
            raise ValueError('Bound cash-flow page image required')
        rows = edition['rows']
        if not isinstance(rows, dict) or set(rows) != set(LAYOUT[lang]):
            raise ValueError('Complete reviewed cash-flow row inventory required')
        selected = {}
        for name, (label, first, second, text) in LAYOUT[lang].items():
            row = rows[name]
            fields(row, {'label', 'cells'}, {'label', 'cells'})
            if not isinstance(row['cells'], list) or len(row['cells']) != 2:
                raise ValueError('Both cash-flow cell columns required')
            label_source = _source(index, row['label'], lang, 170, label, text)
            cells = {}
            for year, position, supplied in zip(YEARS, (first, second), row['cells']):
                source = _source(index, supplied, lang, 170, position)
                value = number(source['quote'], lang)
                cells[year] = {'literal': source['quote'], 'value': value, 'unit': 'EUR thousands',
                               'status': 'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER', 'source': source}
            selected[name] = {'label': label_source, 'cells': cells}
        capital = edition['capital_increase']
        if lang == 'en':
            fields(capital, {'status', 'label'}, {'status', 'label'})
            if capital['status'] != 'SUPPLIED_VISUAL_BLANKS':
                raise ValueError('English capital-increase blanks must remain unknown')
            blank = {'status': capital['status'], 'label': _source(index, capital['label'], lang, 170, 94, 'Capital increase'),
                     'cells': {y: {'status': 'VISIBLE_BLANK_UNKNOWN', 'value': None,
                                   'unit': 'EUR thousands', 'source': None} for y in YEARS}}
        else:
            fields(capital, {'status'}, {'status'})
            if capital['status'] != 'ABSENT_IN_SUPPLIED_READING':
                raise ValueError('Portuguese absent capital-increase row cannot become zero')
            blank = {'status': capital['status'], 'cells': None}
        all_sources = anchors + dates + [r['label'] for r in selected.values()] + [
            c['source'] for r in selected.values() for c in r['cells'].values()]
        if lang == 'en':
            all_sources.append(blank['label'])
        if any(s['document'] != edition['document'] or s['source_sha256'] != edition['source_sha256'] for s in all_sources):
            raise ValueError('Cash-flow source edition changed')
        output.append({'language': lang, 'document': edition['document'], 'source_sha256': edition['source_sha256'],
                       'context': dict(zip(('individual', 'title', 'unit'), anchors), years=dates),
                       'image': deepcopy(image), 'rows': selected, 'capital_increase': blank,
                       'relations': [relation(selected, year, name, target, components) for year in YEARS
                                     for name, target, components in (('investing', 'investing', COMPONENTS),
                                                                    ('net-change', 'net_change', BRIDGE))]})
    output.sort(key=lambda x: x['language'])
    comparisons = [{'row': name, 'year': year, 'unit': 'EUR thousands',
                    'en': output[0]['rows'][name]['cells'][year]['value'],
                    'pt': output[1]['rows'][name]['cells'][year]['value']}
                   for name in LAYOUT['en'] for year in YEARS]
    for item in comparisons:
        item['difference_en_minus_pt'] = None if item['en'] is None or item['pt'] is None else item['en'] - item['pt']
        item['status'] = 'INCOMPLETE_UNKNOWN' if item['difference_en_minus_pt'] is None else 'AGREE' if item['difference_en_minus_pt'] == 0 else 'UNRESOLVED_SOURCE_DISCREPANCY'
    result = {'version': PROFILE, 'profile_sha256': digest(profile), 'graph_sha256': profile['graph_sha256'],
              'review': deepcopy(profile['review']), 'editions': output, 'bilingual_comparisons': comparisons,
              'scope': 'BES Bank individual cash-flow statements; supplied page170 rows,2008/2007; not consolidated or BES Finance Ltd standalone',
              'automatic_discovery': False, 'source_authenticity_established': False,
              'resolved_amount': None, 'controlling_edition': None, 'accounting_cause': None,
              'official_correction_established': False, 'financial_calculation_authorized': False,
              'independent_legal_acceptance': False, 'may_execute_transaction': False}
    result['explanation'] = explanation(result)
    return result


def validate_images(admitted, root):
    for edition in admitted['editions']:
        image = edition['image']
        if digest(bound_path(root, image['path']).read_bytes()) != image['sha256']:
            raise ValueError('Cash-flow source image bytes changed')


def explanation(admitted):
    en, pt = admitted['editions']
    e, p = en['relations'][0], pt['relations'][0]
    def shown(value):
        return 'unknown' if value is None else str(value)
    dated = []
    for edition in (en, pt):
        for item in edition['relations']:
            if item['status'] == 'INCOMPLETE_UNKNOWN':
                outcome = (f'incomplete, with known-part residual {item["known_residual_part"]} '
                           f'and {len(item["unknown_terms"])} unknown term(s)')
            else:
                outcome = f'complete, with printed-minus-component residual {item["residual"]}'
            dated.append(f'{edition["language"]} {item["id"]}: {outcome} thousand euros.')
    return (f'The supplied 2008 individual cash-flow statements are in thousands of euros. '
            f'The eight printed investing components sum to {shown(e["component_sum"])} in English '
            f'and {shown(p["component_sum"])} in Portuguese. The printed subtotals are '
            f'{shown(en["rows"]["investing"]["cells"]["2008"]["value"])} and '
            f'{shown(pt["rows"]["investing"]["cells"]["2008"]["value"])}, respectively. '
            f'The English printed-minus-component residual is {shown(e["residual"])} thousand euros; '
            f'the Portuguese residual is {shown(p["residual"])}. ' + ' '.join(dated) + ' '
            'A known-part residual with unknown terms is not a complete arithmetic discrepancy. '
            'The English blank capital-increase cells and '
            'the row absent from the supplied Portuguese reading remain distinct. '
            'Both editions are preserved. No controlling edition, official corrected amount, '
            'accounting cause or financial authorization is established.')
