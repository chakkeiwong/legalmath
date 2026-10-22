"""Complete supplied Note20 context; keep financial scopes and residuals explicit."""
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path

from . import basf_equity, basf_statement
from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = 'basf-oci-note-review.v1'
DOCUMENT, PAGE = basf_equity.DOCUMENT, 256
# This is an exposed original-page reading, not automatic paragraph discovery.
GROUPS = {
    'policy_heading': ([5], 'left', 'Accounting policies'),
    'policy': (list(range(14,24)), 'left', 'Future recycling to income is distinguished from non-reclassification; defined-benefit remeasurement is in the latter category.'),
    'pension_heading': ([28], 'left', 'Remeasurement of defined benefit plans'),
    'pension_amounts': (list(range(29,35)), 'left', 'Both yearly pension movements are after taxes; equity-method contributions and deferred taxes are included components, not additions to the stated total.'),
    'pension_transfers': (list(range(35,43)) + [44,45], 'left', 'The2021 disposals and IAS19 tax adjustment transfer amounts within equity to retained earnings; this is distinct from recycling to income.'),
    'pension_onward': ([46,47], 'left', 'Note22 from page261 onward supplies further pension information; its complete interpretation is not supplied here.'),
    'currency_heading': ([4], 'right', 'Currency translation'),
    'currency_amounts': (list(range(6,14)), 'right', 'The yearly equity movements include deferred taxes and equity-accounted investments; the paragraph also names the currencies underlying the movements.'),
    'wintershall_reclassification': (list(range(24,28)), 'right', 'Currency differences on deconsolidating Russian shareholdings held by Wintershall Dea are reclassified to income; this paragraph does not print an explicit year.'),
    'divestment_reclassification': ([48,49,50], 'right', 'The2021 divestiture/consolidation-scope reclassification is after taxes and goes to income.'),
    'hedge_heading': ([51], 'right', 'Cash flow hedges'),
    'hedge_amounts': (list(range(52,58)), 'right', 'The total changes reduce equity after deferred-tax adjustment; separately printed equity-method components retain their own signs.'),
    'hedge_onward': ([58], 'right', 'Note26.5 from page279 onward supplies further hedge accounting; that onward interpretation is not supplied here.'),
}
# id: group, source-unit, exact monetary token, year (None means not printed),
# signed-direction multiplier, supplied accounting scope.
AMOUNTS = {
    'pension_net_2022': ('pension_amounts',30,'€2,586','2022',1,'pension OCI after taxes'),
    'pension_net_2021': ('pension_amounts',31,'€2,709','2021',1,'pension OCI after taxes'),
    'pension_equity_2022': ('pension_amounts',32,'€83','2022',1,'included pension equity-method contribution'),
    'pension_equity_2021': ('pension_amounts',33,'€44','2021',1,'included pension equity-method contribution'),
    'pension_tax_2022': ('pension_amounts',34,'–€1,256','2022',1,'included pension deferred tax'),
    'pension_tax_2021': ('pension_amounts',34,'–€811','2021',1,'included pension deferred tax'),
    'pigments_transfer': ('pension_transfers',36,'€48','2021',1,'pension transfer within equity on pigments disposal'),
    'solenis_transfer': ('pension_transfers',37,'€6','2021',1,'pension transfer within equity on Solenis disposal'),
    'ias19_tax_transfer': ('pension_transfers',42,'–€18','2021',1,'IAS19 deferred tax offset against retained earnings'),
    'currency_net_2022': ('currency_amounts',7,'€1,135','2022',1,'currency equity movement including taxes/equity-accounted investments'),
    'currency_net_2021': ('currency_amounts',7,'€2,205','2021',1,'currency equity movement including taxes/equity-accounted investments'),
    'currency_tax_2022': ('currency_amounts',8,'–€7','2022',1,'included currency deferred tax'),
    'currency_tax_2021': ('currency_amounts',9,'–€19','2021',1,'included currency deferred tax'),
    'currency_equity_2022': ('currency_amounts',10,'€583','2022',1,'included currency equity-accounted contribution'),
    'currency_equity_2021': ('currency_amounts',10,'€697','2021',1,'included currency equity-accounted contribution'),
    'wintershall_recycling': ('wintershall_reclassification',26,'€868',None,1,'currency differences reclassified to income on Wintershall Dea Russian-shareholding deconsolidation'),
    'divestment_recycling': ('divestment_reclassification',49,'€52','2021',1,'currency reclassification after taxes for divestitures/consolidation-scope changes'),
    'hedge_tax_2022': ('hedge_amounts',54,'–€8','2022',1,'included cash-flow-hedge deferred tax'),
    'hedge_tax_2021': ('hedge_amounts',54,'–€10','2021',1,'included cash-flow-hedge deferred tax'),
    'hedge_net_2022': ('hedge_amounts',55,'€33','2022',-1,'cash-flow-hedge equity decrease after deferred-tax adjustment'),
    'hedge_net_2021': ('hedge_amounts',55,'€329','2021',-1,'cash-flow-hedge equity decrease after deferred-tax adjustment'),
    'hedge_equity_2022': ('hedge_amounts',55,'€37','2022',1,'included cash-flow-hedge equity-method contribution'),
    'hedge_equity_2021': ('hedge_amounts',56,'–€381','2021',1,'included cash-flow-hedge equity-method contribution'),
}


def monetary(token, direction):
    if type(direction) is not int or direction not in (-1, 1) or not isinstance(token, str):
        raise ValueError('Explicit printed sign or source-word decrease required')
    if token.startswith('–€'):
        number = '–' + token[2:]
    elif token.startswith('€'):
        number = token[1:]
    else:
        raise ValueError('Original euro token required')
    value = basf_statement.integer_millions(number)['integer_millions']
    if value is None or (direction == -1 and value < 0):
        raise ValueError('Unknown amount or double-negative decrease is unsupported')
    return {'literal': token, 'integer_millions': value * direction,
            'direction_basis': 'SOURCE_WORDS_REDUCED_EQUITY' if direction == -1 else 'PRINTED_SIGN',
            'unit': 'million EUR'}


def scoped_comparison(name, left, right, *, matched_scope, explanation):
    if type(matched_scope) is not bool or not isinstance(explanation, str) or not explanation.strip():
        raise ValueError('Explicit scope assessment and explanation required')
    if not matched_scope:
        return {'name': name, 'left': deepcopy(left), 'right': deepcopy(right),
                'left_minus_right': None, 'status': 'SCOPE_EQUIVALENCE_NOT_ESTABLISHED',
                'role': 'EXPLANATORY_ONLY', 'scope_basis': 'SUPPLIED_EXPOSED_REVIEW', 'explanation': explanation}
    return {**basf_equity.comparison(name, left, right), 'scope_basis': 'SUPPLIED_EXPOSED_REVIEW', 'explanation': explanation}


def diagnostics(amounts, prior):
    tables = {t['year']: {r['id']: r for r in t['rows']} for t in prior['equity_review']['tables']}
    statement = {r['id']: r for r in prior['statement_review']['rows']}
    out = []
    for year in ('2022','2021'):
        for prefix, column in [('pension','pensions'),('currency','currency')]:
            out.append(scoped_comparison(year + ':' + prefix, [amounts[prefix + '_net_' + year]],
                [tables[year]['oci']['cells'][column]], matched_scope=True,
                explanation='Supplied reading of the same yearly component movement including the paragraph qualifications.'))
        for prefix, row in [('pension_equity','equity_nonrec'),('pension_tax','pension_tax')]:
            out.append(scoped_comparison(year + ':' + prefix, [amounts[prefix + '_' + year]],
                [statement[row]['cells'][year]], matched_scope=True,
                explanation='Direct pension component comparison; it is already included in the stated after-tax amount.'))
    out.append(scoped_comparison('2022:hedge-net', [amounts['hedge_net_2022']],
        [tables['2022']['oci']['cells']['hedges'], tables['2022']['hedge_elimination']['cells']['hedges']],
        matched_scope=True, explanation='Supplied net-movement comparison; the one-million printed difference remains unexplained.'))
    out.append(scoped_comparison('2021:hedge-direct', [amounts['hedge_net_2021']],
        [tables['2021']['oci']['cells']['hedges']], matched_scope=True,
        explanation='Direct displayed2021 comparison; absence of a separate elimination row is not a zero-valued fact.'))
    out.append(scoped_comparison('2021:pension-within-equity',
        [amounts['pigments_transfer'], amounts['solenis_transfer'], amounts['ias19_tax_transfer']],
        [tables['2021']['other']['cells']['pensions']], matched_scope=True,
        explanation='The disclosed48+6-18 transfers within equity total36; equality does not establish complete movement attribution.'))
    out.append(scoped_comparison('wintershall-vs-direct-currency-reclassification', [amounts['wintershall_recycling']],
        [statement['currency_reclass']['cells']['2022']], matched_scope=False,
        explanation='The paragraph concerns shareholdings held by Wintershall Dea and has no explicit year; the direct statement row is a printed dash. Neither common scope nor a zero amount follows.'))
    for year in ('2022','2021'):
        for label, row in [('currency_tax','reclass_tax'), ('hedge_tax','reclass_tax'), ('currency_equity','equity_rec'), ('hedge_equity','equity_rec')]:
            out.append(scoped_comparison(year + ':' + label + '-vs-aggregate', [amounts[label + '_' + year]],
                [statement[row]['cells'][year]], matched_scope=False,
                explanation='This note component and the broader reclassifiable aggregate have different accounting scope; their values must not be equated.'))
    return out


def evaluate(graph, prior, profile, root, *, expected_profile_sha256):
    keys = {'version','graph_sha256','prior_sha256','reviewer','source','metadata','heading',
            'groups','typographic_occurrences','amounts','selected_reading','financial_values_validated'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['graph_sha256'] != digest(graph) or profile['prior_sha256'] != digest(prior)):
        raise ValueError('Pinned Note20 or full preceding consumer changed')
    if profile['selected_reading'] is not None or profile['financial_values_validated'] is not False:
        raise ValueError('Note20 cannot select incorporation or validate financial accounts')
    reviewer = profile['reviewer']
    fields(reviewer, {'identity','basis','independent'}, {'identity','basis','independent'})
    if (not isinstance(reviewer['identity'],str) or not reviewer['identity'].strip()
            or reviewer['basis'] != 'AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported Note20 review authority')
    source = profile['source']
    skeys = {'document','page','path','sha256','image_path','image_sha256'}
    fields(source, skeys, skeys)
    if source['document'] != DOCUMENT or source['page'] != PAGE:
        raise ValueError('This supplied reading is original annual2022 Note20 page256')
    root = Path(root).resolve()
    for pk,hk in [('path','sha256'),('image_path','image_sha256')]:
        name = source[pk]; path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != source[hk]:
            raise ValueError('Original Note20 PDF or inspected image changed')
    units = {u['id']:u for u in graph['units']}
    page = [u for u in graph['units'] if u['document'] == DOCUMENT and u['page'] == PAGE and u['visible']]
    if len(units) != len(graph['units']) or len(page) != 59 or any(u['source_sha256'] != source['sha256'] or u['text_sha256'] != digest(u['raw'].encode()) for u in page):
        raise ValueError('Complete original Note20 inventory changed')
    used = []
    def full(a):
        bound = bind(graph,a); u = units[a['unit']]
        if (bound['document'] != DOCUMENT or bound['page'] != PAGE or a['start'] != 0
                or a['end'] != len(u['raw']) or a['source_sha256'] != source['sha256']):
            raise ValueError('Complete original Note20 occurrence required')
        b = bound['bbox']
        if (not isinstance(b,list) or len(b)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in b)
                or b[0]>=b[2] or b[1]>=b[3]):
            raise ValueError('Finite original Note20 geometry required')
        used.append(u['id']); return bound
    def ids(anchors):
        return [int(a['unit'].rsplit(':l',1)[1]) for a in anchors]
    metadata = [full(a) for a in profile['metadata']]
    heading = full(profile['heading'])
    if ids(metadata) != [0,1,2] or ids([heading]) != [3] or heading['quote'] != '20 Other comprehensive income':
        raise ValueError('Note20 identity or metadata changed')
    if list(profile['groups']) != list(GROUPS):
        raise ValueError('Complete ordered Note20 paragraph inventory required')
    groups = {}
    last_bottom = {'left': heading['bbox'][3], 'right': max(a['bbox'][3] for a in metadata)}
    left_edge = units[DOCUMENT + ':p256:l5']['bbox'][0]
    right_edge = units[DOCUMENT + ':p256:l4']['bbox'][0]
    for key,(expected_ids,column,meaning) in GROUPS.items():
        group = profile['groups'][key]
        fields(group, {'column','meaning','anchors'}, {'column','meaning','anchors'})
        bound = [full(a) for a in group['anchors']]
        if group['column'] != column or group['meaning'] != meaning or ids(bound) != expected_ids:
            raise ValueError('Original paragraph, column or supplied scope changed')
        for a in bound:
            box = a['bbox']
            if box[1] <= last_bottom[column] or (column == 'left' and box[2] >= right_edge) or (column == 'right' and box[0] < right_edge) or box[0] < left_edge:
                raise ValueError('Paragraph geometry or reading order changed')
            last_bottom[column] = box[3]
        groups[key] = {**deepcopy(group), 'anchors': bound}
    auxiliary = [full(a) for a in profile['typographic_occurrences']]
    if ids(auxiliary) != [43] or auxiliary[0]['quote'] != '\xad':
        raise ValueError('Original isolated soft-hyphen occurrence must be preserved')
    if Counter(used) != Counter(u['id'] for u in page):
        raise ValueError('Every original Note20 occurrence must be retained exactly once')
    if list(profile['amounts']) != list(AMOUNTS):
        raise ValueError('Complete supplied monetary associations required')
    amounts = {}
    for key,(group,n,token,year,direction,scope) in AMOUNTS.items():
        item = profile['amounts'][key]
        fields(item, {'group','year','direction','scope','source'}, {'group','year','direction','scope','source'})
        if type(item['direction']) is not int or (item['group'],item['year'],item['direction'],item['scope']) != (group,year,direction,scope):
            raise ValueError('Amount year, direction or financial scope changed')
        src = bind(graph,item['source'])
        u = units[DOCUMENT + ':p256:l' + str(n)]
        if (src['unit'] != u['id'] or src['quote'] != token or src['start'] != u['raw'].index(token)
                or src['end'] != u['raw'].index(token)+len(token)):
            raise ValueError('Exact original monetary token required')
        amounts[key] = {**monetary(token,direction), 'id':key,'year':year,'scope':scope,'source':src,
            'context':deepcopy(groups[group]),
            'period_basis':'NO_EXPLICIT_YEAR_IN_PARAGRAPH_CURRENT_REPORT_CONTEXT_ONLY' if year is None else 'SUPPLIED_YEAR_ASSOCIATION_WITH_COMPLETE_PARAGRAPH'}
    incorporation = prior['answer']['incorporation']
    if incorporation['status'] != 'UNRESOLVED' or incorporation['selected_reading'] is not None:
        raise ValueError('Both unresolved incorporation readings must remain')
    alternatives = [{'id':r['id'],'condition':r['condition'],'page256_in_candidate_scope':PAGE in r['candidate_pages'],
                     'legal_incorporation_established':False} for r in incorporation['readings']]
    if [r['page256_in_candidate_scope'] for r in alternatives] != [True,True]:
        raise ValueError('Expected Note20 within both candidate page sets')
    return {'version':VERSION,'profile_sha256':digest(profile),'page':PAGE,'heading':heading,
        'metadata':metadata,'groups':groups,'typographic_occurrences':auxiliary,'amounts':amounts,
        'source_occurrences_accounted':len(used),'monetary_associations':len(amounts),
        'comparisons':diagnostics(amounts,prior),'incorporation_alternatives':alternatives,
        'rounding_context':deepcopy(prior['statement_review']['rounding_context']),
        'rounding_warning_is_proven_cause':False,'onward_requirements':[
            {'note':'22','first_page':261,'full_meaning_reviewed':False,'source':groups['pension_onward']},
            {'note':'26.5','first_page':279,'full_meaning_reviewed':False,'source':groups['hedge_onward']}],
        'field_associations':'SUPPLIED_EXPOSED_REVIEW','independent_legal_acceptance':False,
        'financial_values_validated':False,'selected_reading':None,'profile':deepcopy(profile)}


def consume(products, statement_profile, equity_profile, profile, root, *, expected_statement_profile_sha256,
            expected_equity_profile_sha256, expected_profile_sha256):
    prior = basf_equity.consume(products,statement_profile,equity_profile,root,
        expected_statement_profile_sha256=expected_statement_profile_sha256,
        expected_profile_sha256=expected_equity_profile_sha256)
    review = evaluate(products['P1']['payload']['graph'],prior,profile,root,expected_profile_sha256=expected_profile_sha256)
    return {**prior,'oci_note_review':review}
