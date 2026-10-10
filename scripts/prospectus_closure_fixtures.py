"""Synthetic development inputs shared by tests and optional package exercises.

No testing framework or optional parser package is imported by these builders.
These are software controls, not independent legal readings.
"""
from copy import deepcopy
from legalmath.prospectus.successor import source_graph, contract_assembly, clause_graph, occurrences, annotation_bridge
from legalmath.prospectus.successor.contracts import VERSION, digest

PREFIX = "The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity. "
TIME = "2026-01-01T00:00:00Z"
REVIEW = {"reviewer": "development-reader", "kind": "DEVELOPMENT", "reason": "Explicit synthetic control"}
LOSS = "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."

def request(tmp_path, texts):
    path=tmp_path/"source.txt"
    path.write_text("\f".join(texts))
    bundle={"instrument_id":"synthetic", "purpose":"review","issue_date":TIME,
        "effective_at":TIME,"known_at":TIME,"documents":[{"id":"d","path":path.name,
        "sha256":digest(path.read_bytes()),"format":"text","language":"en","authority":"synthetic",
        "document_date":TIME,"known_from":TIME}],"dependencies":[]}
    graph=source_graph.build(bundle,tmp_path)
    operations=[{"unit":u["id"],"role":"OPERATIVE","reason":"Explicit complete synthetic source",
        "source_text_sha256":u["text_sha256"],"context":"whole"} for u in graph["units"]]
    return {"version":VERSION,"bundle":bundle,"assembly":{"operations":operations},
        "scope":{q:{"complete":True,"reason":"Constructed source"} for q in ("Q1","Q2")}}

def coupon_scenario(tmp_path):
    req = request(tmp_path, ["Explicit hypothetical coupon conventions and entitlement for a development test"])
    graph = source_graph.build(req["bundle"], tmp_path)
    a = [occurrences.anchor(u) for u in graph["units"]]
    s = {"profile": "fixed-coupon.v1", "issue_id": graph["instrument_id"], "source_sha256": graph["documents"][0]["sha256"],
         "premise_kind": "HYPOTHETICAL", "currency": "EUR", "annual_rate": "0.05", "accrual_start": "2024-01-01",
         "accrual_end": "2025-01-01", "due_date": "2025-01-01", "payment_date": "2025-01-02",
         "day_count": "ACT_ACT_ICMA", "references": [{"start": "2024-01-01", "end": "2025-01-01"}],
         "frequency": 1, "eom": False, "stub": "REGULAR", "adjustment": "FOLLOWING",
         "calendar": {"edition": "Explicit test calendar", "valid_from": "2024-01-01", "valid_until": "2026-01-01",
                      "holidays": ["2025-01-01"], "weekend": [5,6], "coverage": "COMPLETE_DECLARED_INTERVAL"},
         "rounding": {"quantum": "0.01", "rule": "HALF_UP", "aggregation": "PER_LEGAL_HOLDER"},
         "holdings": [{"legal_holder_id": "a", "account_id": "a1", "principal": "100.1", "entitled": True},
                      {"legal_holder_id": "a", "account_id": "a2", "principal": "100.1", "entitled": True},
                      {"legal_holder_id": "b", "account_id": "b1", "principal": "100.1", "entitled": True}],
         "event_scope": {k: "REQUIRED" if k in {"accrual_start", "accrual_end", "determination", "record", "payment"} else "NOT_APPLICABLE"
                         for k in ("accrual_start", "accrual_end", "notice", "observation", "determination", "record", "ex_coupon", "payment")},
         "events": [{"id": "start", "kind": "accrual_start", "at": "2024-01-01T00:00:00Z", "order": 0},
                    {"id": "record", "kind": "record", "at": "2024-12-30T00:00:00Z", "order": 0},
                    {"id": "end", "kind": "accrual_end", "at": "2025-01-01T00:00:00Z", "order": 0},
                    {"id": "det", "kind": "determination", "at": "2025-01-01T00:00:00Z", "order": 1},
                    {"id": "pay", "kind": "payment", "at": "2025-01-02T00:00:00Z", "order": 0}]}
    s["evidence"] = {k: {"source": deepcopy(a[0]), "reason": "Explicit development assumption; not issuer facts"}
                     for k in set(s) - {"profile", "issue_id", "source_sha256", "premise_kind"}}
    return graph, s

def annotation_fixture(tmp_path):
    req = request(tmp_path, [PREFIX + LOSS + ' The exception applies.'])
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    nodes = clause_graph.nominate(assembly)
    next(n for n in nodes if n['effect'] == 'principal_loss')['exceptions'] = ['exception']
    nodes[-1].update(id='exception', effect='none', actor='issuer', affected='holder', predicate='exempt')
    raw = graph['units'][0]
    source = {'document': raw['document'], 'source_sha256': raw['source_sha256'], 'text_sha256': digest(raw['raw'].encode())}
    groups = [{'id': str(i), 'label': node['effect'], 'spans': [{'start': s['start'], 'end': s['end'],
               'quote': raw['raw'][s['start']:s['end']]} for s in node['spans']]} for i,node in enumerate(nodes)]
    loss_group = str(next(i for i, n in enumerate(nodes) if n['effect'] == 'principal_loss'))
    exception_group = str(next(i for i, n in enumerate(nodes) if n['id'] == 'exception'))
    packet = annotation_bridge.export(raw['raw'], source, groups,
        [{'id': 'authored-exception', 'from': loss_group, 'to': exception_group, 'kind': 'exceptions'}])
    req['annotation_admission'] = {'version': 'reviewed-annotation-meaning.v1', 'assembly_sha256': digest(assembly),
        'review': REVIEW, 'packets': [{'id': 'reading', 'packet': packet, 'map': [{'start': 0, 'end': len(raw['raw']),
            'source': occurrences.anchor(raw), 'use': raw['id']}]}],
        'meanings': [{'groups': ['reading:' + str(i)], 'clause': {k:v for k,v in n.items()
            if k not in {'spans','units','quote','role','questions','origin'}}} for i,n in enumerate(nodes)]}
    return req

def term_fixture(tmp_path):
    from legalmath.prospectus.successor import contract_terms
    premise_dir = tmp_path / 'premises'
    premise_dir.mkdir()
    _, scenario = coupon_scenario(premise_dir)
    names = sorted(contract_terms.REQUIRED)
    texts = ['5%' if key == 'annual_rate' else str(scenario[key]) for key in names]
    req = request(tmp_path, texts + ['Hypothetical development event and calendar premises.'])
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    terms = {}
    for key, unit in zip(names, graph['units']):
        rule = 'percent' if key == 'annual_rate' else 'integer' if key == 'frequency' else 'literal' if key == 'currency' else 'reviewed-convention'
        terms[key] = {'value': scenario[key], 'source': occurrences.anchor(unit), 'use': unit['id'],
                      'rule': rule, 'reason': 'Declared development term interpretation'}
    packet = {'version': 'selected-coupon-terms.v1', 'assembly_sha256': digest(assembly), 'review': REVIEW, 'terms': terms}
    req['term_interpretations'] = packet
    scenario['source_sha256'] = graph['documents'][0]['sha256']
    for row in scenario['evidence'].values():
        row['source'] = occurrences.anchor(graph['units'][-1])
    for key in names:
        del scenario[key]
        del scenario['evidence'][key]
    req['contract_calculation'] = {'version': 'selected-coupon-calculation.v1',
        'terms_sha256': digest(contract_terms.admit(graph, assembly, packet)), 'premises': scenario}
    return req


def full_term_fixture(tmp_path):
    """A rounding counterexample: two 100.10 units pay 10.02, not 10.01."""
    from legalmath.prospectus.successor import contract_terms
    premise_dir = tmp_path / 'premises'
    premise_dir.mkdir()
    _, scenario = coupon_scenario(premise_dir)
    scenario.update(calculation_amount='100.1', fixed_coupon_amount='5.01')
    scenario['rounding']['aggregation'] = 'PER_CALCULATION_AMOUNT'
    values = {k: scenario[k] for k in contract_terms.REQUIRED | contract_terms.EXTENDED
              if k in scenario}
    values.update(issue_principal='1000', maturity_date='2026-01-01')
    quotes = {'annual_rate':'5%', 'currency':'EUR', 'frequency':'1',
              'issue_principal':'EUR 1,000', 'calculation_amount':'EUR 100.1', 'fixed_coupon_amount':'EUR 5.01',
              'accrual_start':'1 January 2024', 'accrual_end':'1 January 2025',
              'due_date':'1 January 2025', 'maturity_date':'1 January 2026'}
    names = sorted(values)
    req = request(tmp_path, [quotes.get(k, str(values[k])) for k in names] + ['Hypothetical event and calendar premises.'])
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    rules = {'annual_rate':'percent', 'currency':'literal', 'frequency':'integer',
             'issue_principal':'amount', 'calculation_amount':'amount', 'fixed_coupon_amount':'amount',
             'accrual_start':'english-date', 'accrual_end':'english-date', 'due_date':'english-date', 'maturity_date':'english-date'}
    terms = {k:{'value':values[k], 'source':occurrences.anchor(u), 'use':u['id'],
                'rule':rules.get(k, 'reviewed-convention'), 'reason':'Explicit development interpretation'}
             for k,u in zip(names, graph['units'])}
    packet = {'version':'selected-coupon-terms.v2', 'assembly_sha256':digest(assembly), 'review':REVIEW, 'terms':terms}
    for key in names:
        scenario.pop(key, None)
        scenario['evidence'].pop(key, None)
    scenario['source_sha256'] = graph['documents'][0]['sha256']
    for row in scenario['evidence'].values():
        row['source'] = occurrences.anchor(graph['units'][-1])
    req['term_interpretations'] = packet
    req['contract_calculation'] = {'version':'selected-coupon-calculation.v1',
        'terms_sha256':digest(contract_terms.admit(graph, assembly, packet)), 'premises':scenario}
    return req


def anchored_coupon_fixture(tmp_path, *, selected):
    """Explicit synthetic 30-August anchor; February is a temporary clamp."""
    from legalmath.prospectus.successor import contract_terms
    premise_dir = tmp_path/'premises'
    premise_dir.mkdir()
    _, scenario = coupon_scenario(premise_dir)
    scenario.update(profile='fixed-coupon.v2',coupon_anchor='2023-08-30',
        accrual_start='2024-02-29',accrual_end='2024-08-30',due_date='2024-08-30',
        payment_date='2024-08-30',frequency=2,adjustment='UNADJUSTED',
        references=[{'start':'2024-02-29','end':'2024-08-30'}],
        calculation_amount='100.1',fixed_coupon_amount='2.50')
    scenario['calendar'].update(valid_from='2023-01-01',valid_until='2026-01-01',holidays=[])
    scenario['rounding']['aggregation']='PER_CALCULATION_AMOUNT'
    scenario['event_scope']['record']='NOT_APPLICABLE'
    scenario['events']=[
        {'id':'start','kind':'accrual_start','at':'2024-02-29T00:00:00Z','order':0},
        {'id':'end','kind':'accrual_end','at':'2024-08-30T00:00:00Z','order':0},
        {'id':'det','kind':'determination','at':'2024-08-30T00:00:00Z','order':1},
        {'id':'pay','kind':'payment','at':'2024-08-30T00:00:00Z','order':2}]
    values={k:scenario[k] for k in contract_terms.REQUIRED | contract_terms.EXTENDED | {'coupon_anchor'} if k in scenario}
    values.update(issue_principal='1000',maturity_date='2025-08-30')
    quotes={'annual_rate':'5%','currency':'EUR','frequency':'2',
        'issue_principal':'EUR 1,000','calculation_amount':'EUR 100.1','fixed_coupon_amount':'EUR 2.50',
        'coupon_anchor':'30 August 2023','accrual_start':'29 February 2024',
        'accrual_end':'30 August 2024','due_date':'30 August 2024','maturity_date':'30 August 2025'}
    names=sorted(values)
    req=request(tmp_path,[quotes.get(k,str(values[k])) for k in names]+['Explicit hypothetical calendar, holdings and event premises.'])
    graph=source_graph.build(req['bundle'],tmp_path)
    assembly=contract_assembly.assemble(graph,req['assembly'])
    rules={'annual_rate':'percent','currency':'literal','frequency':'integer',
        'issue_principal':'amount','calculation_amount':'amount','fixed_coupon_amount':'amount',
        'coupon_anchor':'english-date','accrual_start':'english-date','accrual_end':'english-date',
        'due_date':'english-date','maturity_date':'english-date'}
    terms={k:{'value':values[k],'source':occurrences.anchor(u),'use':u['id'],
        'rule':rules.get(k,'reviewed-convention'),'reason':'Explicit synthetic convention; not real instrument facts'}
        for k,u in zip(names,graph['units'])}
    scenario['source_sha256']=graph['documents'][0]['sha256']
    scenario['evidence']={k:{'source':occurrences.anchor(graph['units'][-1]),
        'reason':'Hypothetical synthetic premise; not actual events or entitlement'}
        for k in set(scenario)-{'profile','issue_id','source_sha256','premise_kind','evidence'}}
    scenario['evidence']['coupon_anchor']={'source':terms['coupon_anchor']['source'],
        'reason':'Exact quoted original anchor date for the hypothetical date lattice'}
    if selected:
        packet={'version':'selected-coupon-terms.v3','assembly_sha256':digest(assembly),'review':REVIEW,'terms':terms}
        for key in names:
            scenario.pop(key,None)
            scenario['evidence'].pop(key,None)
        req['term_interpretations']=packet
        req['contract_calculation']={'version':'selected-coupon-calculation.v1',
            'terms_sha256':digest(contract_terms.admit(graph,assembly,packet)),'premises':scenario}
    else:
        req['financial_scenario']=scenario
    return req


def anchored_direct_fixture(tmp_path):
    return anchored_coupon_fixture(tmp_path,selected=False)


def anchored_selected_fixture(tmp_path):
    return anchored_coupon_fixture(tmp_path,selected=True)


def cross_document_fixture(tmp_path):
    req = request(tmp_path, [PREFIX + LOSS])
    path = tmp_path/'exception.txt'
    path.write_text('The exception applies.')
    req['bundle']['documents'].append({**req['bundle']['documents'][0], 'id':'exception-document',
        'path':path.name, 'sha256':digest(path.read_bytes())})
    graph = source_graph.build(req['bundle'], tmp_path)
    req['assembly']['operations'] = [{'unit':u['id'],'role':'OPERATIVE','reason':'Complete synthetic two-document source',
        'source_text_sha256':u['text_sha256'],'context':'whole'} for u in graph['units']]
    assembly = contract_assembly.assemble(graph, req['assembly'])
    nodes = clause_graph.nominate(assembly)
    loss = next(n for n in nodes if n['effect']=='principal_loss')
    loss['exceptions'] = ['exception']
    nodes[-1].update(id='exception',effect='none',actor='issuer',affected='holder',predicate='exempt')
    packets, meanings = [], []
    endpoint_keys = {}
    for raw in graph['units']:
        local = [n for n in nodes if n['units']==[raw['id']]]
        groups = [{'id':n['id'],'label':n['effect'],'spans':[
            {'start':s['start'],'end':s['end'],'quote':raw['raw'][s['start']:s['end']]} for s in n['spans']]} for n in local]
        source = {'document':raw['document'],'source_sha256':raw['source_sha256'],'text_sha256':digest(raw['raw'].encode())}
        packet = annotation_bridge.export(raw['raw'],source,groups,[])
        packets.append({'id':raw['document'],'packet':packet,'map':[{'start':0,'end':len(raw['raw']),
            'source':occurrences.anchor(raw),'use':raw['id']}]})
        for n in local:
            endpoint_keys[n['id']] = {'packet':raw['document'],'packet_sha256':digest(packet),'group':n['id']}
            meanings.append({'groups':[raw['document']+':'+n['id']], 'clause':{k:v for k,v in n.items()
                             if k not in {'spans','units','quote','role','questions','origin'}}})
    req['annotation_admission'] = {'version':'reviewed-annotation-meaning.v2','assembly_sha256':digest(assembly),
        'review':REVIEW,'packets':packets,'meanings':meanings,
        'cross_document_relations':[{'id':'distant-exception','from':endpoint_keys[loss['id']],
             'to':endpoint_keys['exception'],'kind':'exceptions','review':REVIEW}]}
    return req


def ast_reference_fixture(tmp_path):
    req = request(tmp_path,['Condition 2 applies.',PREFIX])
    graph = source_graph.build(req['bundle'],tmp_path)
    a = [occurrences.anchor(u) for u in graph['units']]
    req['assembly']['ast'] = {'version':'contract-ast.v2','root':'s','nodes':[
        {'id':'s','kind':'Sequence','children':['a','b']},
        {'id':'a','kind':'Text','source':a[0]}, {'id':'b','kind':'Text','source':a[1]}]}
    ref = graph['references'][0]
    req['reference_dispositions'] = {ref['id']:{'source_sha256':ref['source_sha256'],
        'reason':'Explicit synthetic definition','targets':['d:p2:l0']}}
    return req


def large_z3_fixture(tmp_path):
    req = request(tmp_path,[PREFIX])
    graph = source_graph.build(req['bundle'],tmp_path)
    source = occurrences.anchor(graph['units'][0])
    expr = {'all':['f'+str(i) for i in range(13)]}
    req.update(predicate_engine='z3',law_bases=[{'id':'law','authority':'Synthetic','jurisdiction':'X','edition':'1',
        'source':source,'instrument_id':req['bundle']['instrument_id'],'valid_from':TIME,'known_from':TIME,'premises':expr}])
    req['facts'] = [{'name':name,'basis_id':'law','instrument_id':req['bundle']['instrument_id'],
        'jurisdiction':'X','source':source,'value':True,'valid_from':TIME,'known_from':TIME,'observed_at':TIME} for name in expr['all']]
    req['assembly']['ast'] = {'version':'contract-ast.v2','root':'a','nodes':[{'id':'a','kind':'Text','source':source}],
        'constraints':[{'any':[expr,{'not':expr}]}]}
    return req
