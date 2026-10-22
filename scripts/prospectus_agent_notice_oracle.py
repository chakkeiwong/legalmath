"""Independent integer date arithmetic and enumerated notice truth tables."""
from copy import deepcopy
from itertools import product
from scripts.prospectus_calendar_oracle import civil_number, instant_number


def condition(values):
    if any(v == 'conflict' for v in values.values()):
        return 'CONFLICT'
    keys = list(values)
    possibilities = [([False, True] if values[k] is None else [values[k]]) for k in keys]
    outcomes = set()
    for row in product(*possibilities):
        w = dict(zip(keys, row))
        outcomes.add(w['insolvency'] or (w['section13_notice'] and w['lower'] and w['upper']))
    return 'UNKNOWN' if len(outcomes) == 2 else 'YES' if True in outcomes else 'NO'


def expected(row):
    interval = row['interval']; exact = {}; lower = upper = None
    if interval['start'] is not None and interval['end'] is not None:
        start, end, conv = interval['start']['value'], interval['end']['value'], interval['convention']
        if conv == 'ELAPSED_24_HOUR_DAYS':
            left = instant_number(end) - instant_number(start); scale = 86_400_000_000; unit = 'microseconds'
        else:
            gap = civil_number(end) - civil_number(start)
            if gap < 0: raise ValueError('Independent reversed interval')
            left = gap if conv == 'CIVIL_DATE_GAP' else max(0, gap - 1); scale = 1; unit = 'civil_days'
        if left < 0: raise ValueError('Independent reversed interval')
        lower, upper = left >= 30 * scale, left <= 45 * scale
        exact = {k: {'left': str(left), 'right': str(days*scale), 'operator': op, 'unit': unit, 'convention': conv}
                 for k,days,op in (('lower',30,'GE'),('upper',45,'LE'))}
    status = condition({'insolvency':row['insolvency'], 'section13_notice':row['section13_notice'], 'lower':lower, 'upper':upper})
    applies = row['reading_applies']
    if status == 'CONFLICT' or applies == 'conflict': applied = 'CONFLICT'
    else:
        a = [False,True] if status == 'UNKNOWN' else [status == 'YES']
        b = [False,True] if applies is None else [applies]
        possibilities = {x and y for x in a for y in b}
        applied = 'UNKNOWN' if len(possibilities)==2 else 'YES' if True in possibilities else 'NO'
    return {'notice_precondition':status, 'conditional_notice_precondition':applied, 'exact_interval':exact}


def scenarios(instrument):
    identity = {'instrument_id':instrument, 'agent_id':'hypothetical-calculation-agent', 'change_event_id':'hypothetical-agent-change'}
    def operand(value,role): return {**identity,'value':value,'role':role}
    base = {'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT','identity':identity,
            'interval':{'convention':None,'start':None,'end':None},
            'insolvency':None,'section13_notice':None,'reading_applies':None}
    rows=[deepcopy(base)]
    def dated(label,end,conv='CIVIL_DATE_GAP',start='2024-01-01'):
        row=deepcopy(base);row.update(id=label,insolvency=False,section13_notice=True,reading_applies=True)
        row['interval']={'convention':conv,'start':operand(start,'HOLDERS_INFORMED'),'end':operand(end,'PROPOSED_CHANGE')}
        return row
    for days,end in ((29,'2024-01-30'),(30,'2024-01-31'),(45,'2024-02-15'),(46,'2024-02-16')):
        rows.append(dated(str(days)+'-civil',end))
    for label,end in (('30-minus-microsecond','2024-01-30T23:59:59.999999Z'),
                      ('30-elapsed','2024-01-31T00:00:00Z'),('45-elapsed','2024-02-15T00:00:00Z'),
                      ('45-plus-microsecond','2024-02-15T00:00:00.000001Z')):
        rows.append(dated(label,end,'ELAPSED_24_HOUR_DAYS','2024-01-01T00:00:00Z'))
    rows.append(dated('same-instant-offsets','2024-01-31T01:00:00+01:00','ELAPSED_24_HOUR_DAYS','2024-01-01T00:00:00Z'))
    rows.append(dated('30-gap-clear-days','2024-01-31','CLEAR_CIVIL_DAYS'))
    rows.append(dated('31-gap-clear-days','2024-02-01','CLEAR_CIVIL_DAYS'))
    for name,value in (('insolvency',None),('insolvency','conflict'),('section13_notice',False),
                       ('section13_notice',None),('section13_notice','conflict'),('reading_applies',None),
                       ('reading_applies',False),('reading_applies','conflict')):
        row=dated(name+'-'+str(value),'2024-01-31');row[name]=value;rows.append(row)
    for part in ('start','end'):
        row=dated('missing-'+part,'2024-01-31');row['interval'][part]=None;rows.append(row)
    row=deepcopy(base);row.update(id='insolvency-exception-without-dates',insolvency=True,reading_applies=True);rows.append(row)
    row=dated('insolvency-exception-outside-window','2024-02-16');row['insolvency']=True;rows.append(row)
    row=dated('unknown-insolvency-outside-window','2024-02-16');row['insolvency']=None;rows.append(row)
    return rows


def check_source(products, answer, context):
    nodes = products['P3']['payload']['clauses']['nodes']
    node = next(n for n in nodes if n['id']=='basf-agents:effectiveness-reference')
    assert context['agent_clause']==node
    ref=next(r for r in products['P3']['payload']['interpretation_input']['reference_admission']['references'] if r['id']=='agent-change-notices')
    assert context['notice_reference']==ref
    assert len(ref['targets'])==15 and ref['source']['quote']=='§ 13'
    raw={u['id']:u for u in products['P1']['payload']['graph']['units']}
    for r in node['source_uses']+ref['targets']:
        s=r['source'];u=raw[s['unit']]
        assert u['source_sha256']==s['source_sha256'] and u['raw'][s['start']:s['end']]==s['quote']
    assert len(context['notice_clauses'])==3
    assert 'dritten Tag' in context['notice_clauses'][0]['quote']
    assert 'siebten Tag' in context['notice_clauses'][1]['quote']
    assert answer['basf_agents']['calculation_agent_office']=='UNRESOLVED'
    assert context['holders_informed_date_derived'] is False
    return {'source_pieces':len(node['source_uses']),'onward_targets':15,'office':'UNRESOLVED'}
