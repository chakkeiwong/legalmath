"""Versioned domains for the closed library interface, included in method identity."""
from copy import deepcopy
from ..canonical import digest

OPERATIONS = {
    'numeric.min': {'inputs':'two values of the same integer, money_hkd or decimal type',
                    'result':'the smaller exact value','domain':'all values in the declared type'},
    'numeric.max': {'inputs':'two values of the same integer, money_hkd or decimal type',
                    'result':'the larger exact value','domain':'all values in the declared type'},
    'date.add_days': {'inputs':'Gregorian date and integer day count','result':'calendar date plus the count',
                      'domain':'years 0001..9999; out of range is E_DATE_RANGE'},
    'date.add_months_clamped': {'inputs':'Gregorian date and integer month count',
                               'result':'shift the month and clamp the day to the destination month end',
                               'domain':'years 0001..9999; out of range is E_DATE_RANGE'},
    'date.month_end': {'inputs':'Gregorian date','result':'last date of the same month','domain':'years 0001..9999'},
    'list.length': {'inputs':'a typed list','result':'number of elements','domain':'accepted observed lists within resource limits'},
    'list.sequence': {'inputs':'integer begin and end','result':'begin inclusive to end exclusive, empty when end <= begin',
                       'domain':'at most 10000 elements; excess is E_RESOURCE_LIMIT'},
}


def manifest():
    result={'version':'shared-library-domains.v1','operations':deepcopy(OPERATIONS),
            'dependency_identity':'The actual native build manifest binds its pinned Catala compiler, runtime and standard library.',
            'extension_requirements':['Typed signature and domain','Explicit uncertainty and error semantics',
                                      'Pinned dependency identity','Independent mathematical evaluator',
                                      'Boundary and interaction challenges','New method/freeze identity'],
            'arbitrary_imports':'UNSUPPORTED','human_quality_evidence':False}
    return {**result,'registry_hash':digest(result)}
