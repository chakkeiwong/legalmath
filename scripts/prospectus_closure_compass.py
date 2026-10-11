"""Source-bound conditional first coupon, XS3232968985; development evidence."""
from copy import deepcopy
from legalmath.prospectus.successor import source_graph, contract_assembly, contract_terms, service
from legalmath.prospectus.successor.contracts import VERSION, digest, write
from legalmath.prospectus.successor.occurrences import anchor


def request(root):
    sources = [('final', 'compass-2035-final.pdf', '2026-01-13'),
               ('base', 'compass-2025-base.pdf', '2025-06-13'),
               ('supplement', 'compass-2025-supplement.pdf', '2025-12-18')]
    docs = []
    for name, filename, published in sources:
        path = root/'docs/prospectus/classification-holdout/originals'/filename
        docs.append({'id':name, 'path':str(path.relative_to(root)), 'sha256':digest(path.read_bytes()),
                     'language':'en', 'authority':'Retained Compass issuer publication; development interpretation',
                     'document_date':published+'T00:00:00Z', 'known_from':published+'T00:00:00Z'})
    time = '2026-01-15T00:00:00Z'
    req = {'version':VERSION, 'bundle':{'instrument_id':'XS3232968985', 'purpose':'issue_formation',
           'issue_date':time, 'effective_at':time, 'known_at':time, 'documents':docs, 'dependencies':[]}}
    graph = source_graph.build(req['bundle'], root)
    units = {u['id']:u for u in graph['units']}
    def citation(identity, quote=None):
        u = units[identity]
        if quote is None:
            return anchor(u)
        start = u['raw'].index(quote)
        if u['raw'].find(quote, start+1) != -1:
            raise ValueError('Ambiguous local quotation')
        return anchor(u, start, start+len(quote))
    terms = {}
    def term(key, value, identity, rule='reviewed-convention', quote=None, reason=''):
        terms[key] = {'value':value, 'source':citation(identity, quote), 'use':identity, 'rule':rule,
                      'reason':reason or 'Implementer interpretation of the retained final terms and applicable fixed-rate conditions; independent review pending'}
    term('currency','EUR','final:p2:l32','literal','EUR')
    term('issue_principal','750000000','final:p2:l35','amount')
    term('calculation_amount','1000','final:p2:l50','amount')
    term('fixed_coupon_amount','35','final:p3:l15','amount','EUR 35.00')
    term('annual_rate','0.035','final:p3:l6','percent','3.500 per cent.')
    term('accrual_start','2026-01-15','final:p2:l56','english-date',
         reason='Final Terms 7(iii) sets interest commencement to the Issue Date in 7(ii)')
    term('maturity_date','2035-01-15','final:p2:l63','english-date')
    for key in ('accrual_end','due_date'):
        term(key,'2027-01-15','final:p3:l10','first-annual-date')
        terms[key]['continuations'] = [{'source':citation('final:p3:l11'),'use':'final:p3:l11'}]
    term('frequency',1,'final:p3:l10','annual','in each year')
    term('day_count','ACT_ACT_ICMA','final:p3:l21')
    term('eom',False,'final:p3:l10',reason='Express 15 January anniversary, never a month-end adjustment')
    term('stub','REGULAR','final:p3:l18',reason='No broken amount; issue 15 January 2026 and first annual payment 15 January 2027')
    term('references',[{'start':'2026-01-15','end':'2027-01-15'}],'final:p3:l10',
         reason='One annual ICMA reference period from commencement to first payment under Final Terms 7 and 14')
    term('adjustment','FOLLOWING','base:p57:l18',reason='Condition 10(g), subject to global-note payment-day override on printed page 27')
    term('rounding',{'quantum':'0.01','rule':'HALF_UP','aggregation':'PER_CALCULATION_AMOUNT'},'base:p41:l54',
         reason='Condition 6(d): round calculation amount to euro cents then scale; published EUR35 in 6(c)/Final Terms 14(iii) controls this regular coupon')
    selected = {t['use'] for t in terms.values()} | {'final:p3:l11'}
    selected |= {f'final:p2:l{i}' for i in [45,46,47,49,55,58,59,62,69,70,71,72]}
    selected |= {f'final:p3:l{i}' for i in [2,3,5,9,12,14,17,20,29,30,31,60,61,62,63]}
    # Keep the complete short fixed-rate provision and payment-day context,
    # not the whole prospectus, within this supplied conditional selection.
    selected |= {u['id'] for u in graph['units'] if u['document']=='base' and
                 (u['page']==41 and u['order']>=27 or u['page']==29 and 0<=u['order']<=16 or
                  u['page']==57 and 14<=u['order']<=25)}
    req['assembly'] = {'operations':[{'unit':u['id'], 'role':'OPERATIVE', 'source_text_sha256':u['text_sha256'],
        'reason':'Supplied Q5 fixed-rate interpretation only; remaining contract retained UNKNOWN',
        'questions':['Q5'], 'context':'conditional-first-coupon'} for u in graph['units'] if u['id'] in selected]}
    assembly = contract_assembly.assemble(graph, req['assembly'])
    packet = {'version':'selected-coupon-terms.v2', 'assembly_sha256':digest(assembly),
              'review':{'reviewer':'implementer-development-review', 'kind':'DEVELOPMENT',
                        'reason':'Retained original sources inspected; no independent legal acceptance'}, 'terms':terms}
    req['term_interpretations'] = packet
    core_events = {'accrual_start','accrual_end','determination','payment'}
    scenario = {'profile':'fixed-coupon.v1', 'issue_id':'XS3232968985', 'source_sha256':docs[0]['sha256'],
        'premise_kind':'HYPOTHETICAL', 'payment_date':'2027-01-15',
        'calendar':{'edition':'Hypothetical TARGET and London open on 15 January 2027; limited interval',
                    'valid_from':'2027-01-14','valid_until':'2027-01-19', 'holidays':[], 'weekend':[5,6],
                    'coverage':'COMPLETE_DECLARED_INTERVAL'},
        'holdings':[{'legal_holder_id':'hypothetical-entitled-bearer','account_id':'hypothetical-account',
                     'principal':'100000','entitled':True}],
        'event_scope':{k:'REQUIRED' if k in core_events else 'NOT_APPLICABLE' for k in
                       ('accrual_start','accrual_end','notice','observation','determination','record','ex_coupon','payment')},
        'events':[{'id':'start','kind':'accrual_start','at':time,'order':0},
                  {'id':'end','kind':'accrual_end','at':'2027-01-15T00:00:00Z','order':0},
                  {'id':'det','kind':'determination','at':'2027-01-15T00:00:00Z','order':1},
                  {'id':'pay','kind':'payment','at':'2027-01-15T00:00:00Z','order':2}]}
    assumption = ('Hypothetical entitled EUR100,000 bearer holding with timely presentation, no transfer, early redemption, '
                  'default, tax deduction or currency change. Calendar is assumed for the declared interval. '
                  'Event times/order are calculation premises; no registered-note record date is asserted.')
    scenario['evidence'] = {k:{'source':citation('final:p2:l46'), 'reason':assumption} for k in
                           ('payment_date','calendar','holdings','event_scope','events')}
    req['contract_calculation'] = {'version':'selected-coupon-calculation.v1',
        'terms_sha256':digest(contract_terms.admit(graph, assembly, packet)), 'premises':scenario}
    return req


def exercise(folder, root):
    import QuantLib as ql
    req = request(root)
    write(folder/'request.json', req)
    report = service.assess(req, root)
    write(folder/'report.json', report)
    answer = report['questions']['Q5']
    expected_dates = [f'{year}-01-15' for year in range(2027,2036)]
    qdate = ql.DateParser.parseISO
    schedule = ql.Schedule(qdate('2026-01-15'),qdate('2035-01-15'),ql.Period(1,ql.Years),
                           ql.NullCalendar(),ql.Unadjusted,ql.Unadjusted,ql.DateGeneration.Forward,False)
    qdates = [d.ISO() for d in list(schedule)[1:]]
    value = answer['value']
    fraction = ql.ActualActual(ql.ActualActual.ISMA).yearFraction(qdate('2026-01-15'),qdate('2027-01-15'),
                                                               qdate('2026-01-15'),qdate('2027-01-15'))
    if (answer['status'] != 'CONDITIONAL' or value['regular_due_dates'] != expected_dates or qdates != expected_dates or
            value['calculation']['day_fraction'] != '1' or fraction != 1.0 or
            [t['amount'] for t in value['calculation']['transfers']] != ['3500']):
        raise ValueError('Real-instrument conditional coupon or independent schedule differs')
    if report['questions']['Q3']['status'] != 'PARTIAL':
        raise ValueError('Conditional coupon cannot certify full contract completeness')
    # Reuse the verified input graph/assembly for term mutations; one full service
    # run above proves that finance consumes these same admissions.
    mutations = []
    for name,value in [('annual_rate','0.04'),('accrual_end','2027-02-15'),('issue_principal','800000000')]:
        packet = deepcopy(req['term_interpretations'])
        packet['terms'][name]['value'] = value
        try:
            contract_terms.admit(report['source_map'], report['assembly'], packet)
        except ValueError as exc:
            mutations.append({'term':name, 'result':'REJECTED', 'reason':str(exc)})
        else:
            raise ValueError('Unbound real-source term admitted: '+name)
    write(folder/'comparisons.json', {'independent_due_dates':expected_dates, 'quantlib_due_dates':qdates,
        'independent_payment':'100000 / 1000 * 35 = 3500 EUR', 'quantlib_fraction':fraction,
        'mutations':mutations, 'quantlib_version':ql.__version__})
    write(folder/'development-exposure.json', {'instrument':'XS3232968985','issuer_family':'Compass Group PLC EMTN',
        'status':'DEVELOPMENT_EXPOSED', 'exclude_related_family_from_unseen_evaluation':True,
        'sources':req['bundle']['documents'], 'independent_review':False,
        'supplement_review':'18 December 2025 supplement inspected in full; annual-report incorporation remains unclosed',
        'scope':'First fixed coupon conditional on supplied no-call/default, entitlement/presentation and calendar premises'})
    return {'real_instrument':True, 'independent_legal_review':False, 'coupon':'3500 EUR',
            'schedule_dates':len(expected_dates), 'mutations_rejected':len(mutations), 'full_contract':'PARTIAL',
            'quantlib_version':ql.__version__, 'family_exposure':'DEVELOPMENT'}
