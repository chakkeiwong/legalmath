from copy import deepcopy
from legalmath.translation.model import from_reading
from .support import AT,fixture


def fixture_v2(facts, outputs, *, types=(), helpers=(), profile='partial.v1', text):
    t,g=fixture();r=g['readings'][0]
    t['question']=text
    t['packet']['source_key']='synthetic.translator.v2'
    t['packet']['units'][0]['text']=text
    t['packet']['selected_slice']='Synthetic shared translator semantics'
    r.update(local_id='shared',family='scope',subject='Synthetic calculation',
             distinction='Declared compiler and evidence semantics',statement=text,
             citations=[{'unit_id':'p1','quote':text}],assumptions=[],questions=[])
    g['coverage'][0]['reason']='All synthetic calculation requirements represented'
    interface=[{'name':n,'type':typ,'meaning':'Synthetic '+n,'unit':'Money is in minor units; decimals are exact; dates are Gregorian',
                'source_unit_ids':['p1'],'requires_judgment':False} for n,typ in facts]
    os=[{'id':name,'result_type':typ,'scope':scope,'result':expr} for name,typ,scope,expr in outputs]
    r['formalization']={'version':'2','facts':interface,'types':list(types),'outputs':os,'helpers':list(helpers)}
    t.pop('result_type');t.update(version='2',facts=interface,types=list(types),profile=profile,
        outputs=[{k:o[k] for k in ('id','result_type')} for o in os])
    return t,g


def as_model(t,g):
    return from_reading(g['readings'][0],t['packet'],AT,profile=t['profile'],
                        coverage=g['coverage'],dimensions=g['dimensions'])


def numeric_fixture():
    return fixture_v2([('gate','bool'),('left','bool'),('right','bool'),('cash','money_hkd'),('ratio','decimal')],
        [('scoped','money_hkd','gate','(scale cash 1 2)'),
         ('exact','money_hkd','true','(scale cash 1 2)'),
         ('rounded','money_hkd','true','(round money_hkd nearest_away ratio)'),
         ('floor','integer','true','(round integer floor ratio)'),
         ('ceiling','integer','true','(round integer ceiling ratio)'),
         ('truncate','integer','true','(round integer toward_zero ratio)'),
         ('defaults','integer','true','(default (integer 1) (exception a left (integer 7)) (exception b right (integer 7)))'),
         ('lazy','integer','true','(default (scale (integer 3) 1 2) (exception a left (integer 7)))'),
         ('and','bool','true','(and left right)'),('or','bool','true','(or left right)'),
         ('branch','integer','true','(if gate (integer 9) (scale (integer 3) 1 2))'),
         ('helper','decimal','true','(call double ratio)'),
         ('distinct','integer','true','(default (integer 1) (exception a left (integer 7)) (exception b right (integer 8)))'),
         ('overlap.unknown','integer','true','(default (integer 1) (exception a true (integer 7)) (exception b true (integer 7)) (exception c right (integer 9)))'),
         ('guard.error','integer','true','(default (integer 1) (exception a true (integer 7)) (exception b true (integer 7)) (exception c (= (scale (integer 3) 1 2) (integer 0)) (integer 9)))'),
         ('all.error','bool','true','(and false (= (scale (integer 3) 1 2) (integer 0)))'),
         ('rule.ref','money_hkd','true','(rule exact)'),
         ('empty.default','integer','true','(default (integer 1))')],
        helpers=[{'name':'double','parameters':[{'name':'x','type':'decimal'}],'result_type':'decimal','body':'(call add x x)'},
                 {'name':'add','parameters':[{'name':'x','type':'decimal'},{'name':'y','type':'decimal'}],
                  'result_type':'decimal','body':'(+ x y)'}],
        text='Synthetic calculation: the scoped cash output applies only when gate holds and halves cash exactly. '
             'The exact output halves cash unconditionally. Round the ratio in minor units with ties away from zero, '
             'and separately take its floor, ceiling and truncation. The default is one, with independent left and right '
             'exceptions each returning seven; overlapping exceptions conflict. A lazy default uses an inexact three-halves '
             'unless left selects seven. Return the conjunction and disjunction of left and right. The branch returns nine '
             'when gate holds and otherwise attempts inexact three-halves. A reusable double calculation adds the ratio to itself. '
             'Additional controls give the right exception eight, overlap two always-true exceptions with an uncertain third guard, '
             'and replace that guard with inexact arithmetic; guard errors take precedence over overlap. False conjunction with '
             'an error still errors. A rule reference returns exact and a default without exceptions returns one.')


def library_fixture():
    return fixture_v2([('start','date'),('offset','integer'),('begin','integer'),('end','integer'),('x','decimal'),('y','decimal')],
        [('months','date','true','(library date.add_months_clamped start offset)'),
         ('days','date','true','(library date.add_days start offset)'),
         ('month.end','date','true','(library date.month_end start)'),
         ('sequence','list[integer]','true','(library list.sequence begin end)'),
         ('length','integer','true','(library list.length (library list.sequence begin end))'),
         ('min','decimal','true','(library numeric.min x y)'),
         ('max','decimal','true','(library numeric.max x y)')],
        text='Synthetic calculations: add the offset in months to start, clamping to month end; separately add the offset '
             'in days and return the last day of the starting month. Produce integers from begin inclusive to end exclusive '
             'and count them. Return the minimum and maximum of the exact ratios x and y.')


ENTRY={'name':'Entry','kind':'record','fields':[
    {'name':'active','type':'bool','meaning':'Whether the entry contributes','unit':'Boolean'},
    {'name':'amount','type':'decimal','meaning':'Exact amount','unit':'ratio'}],'cases':[]}
CHOICE={'name':'Choice','kind':'enum','fields':[],'cases':[{'name':'Fixed','type':'decimal'},{'name':'Empty','type':None}]}


def structured_fixture():
    return fixture_v2([('entry','Entry'),('entries','list[Entry]'),('rate','optional[decimal]'),('choice','Choice')],
        [('field','decimal','true','(field entry amount)'),
         ('record','Entry','true','(record Entry (active (field entry active)) (amount (field entry amount)))'),
         ('sum','decimal','true','(sum (map e entries (field e amount)))'),
         ('filtered','decimal','true','(sum (map e (filter e entries (field e active)) (field e amount)))'),
         ('optional','decimal','true','(option rate x x (decimal 0 1))'),
         ('choice','decimal','true','(match choice (Fixed x x) (Empty _ (decimal 0 1)))'),
         ('some','optional[decimal]','true','(some (field entry amount))'),
         ('variant','Choice','true','(variant Choice Fixed (field entry amount))'),
         ('empty','optional[decimal]','true','(none decimal)')],types=[ENTRY,CHOICE],
        text='Synthetic calculation: return entry amount and reconstruct its record. Sum all entry amounts, and separately '
             'sum amounts of active entries. Return a known optional rate or zero when absent; missing evidence stays unknown. '
             'A fixed choice yields its amount and Empty yields zero. Also wrap entry amount as a present option and Fixed '
             'choice, and return an explicitly absent option. Incomplete collection membership prevents aggregation.')


def observed(typ,value,*,path='fixture',structured=False,complete=True):
    return {'status':'structured' if structured else 'known','type':typ,'value':deepcopy(value),
            'evidence_ids':['evidence:'+path],'valid_from':AT,'valid_until':None,'recorded_at':AT,'complete':complete}


def unknown(typ,reason='MISSING'):
    return {'status':'unknown','type':typ,'reason':reason}


def conflict(typ):
    return {'status':'conflict','type':typ,'evidence_ids':['first','second']}
