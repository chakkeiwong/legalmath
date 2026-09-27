"""Compile shared version-2 expressions and result states into native Catala."""
from ..canonical import digest
from ..errors import LegalMathError
from ..catala.native.contracts import validate_task, validate_candidate, literal, catala_type
from .model import validate, inner, fail
from .structured import Layout, field


class Compiler:
    def __init__(self, model, types):
        self.model=model;self.types=types;self.layout=Layout(model,types);self.counter=0
        self.facts={f['name']:'f'+str(i) for i,f in enumerate(model['facts'])}
        self.rules={r['id']:'r'+str(i) for i,r in enumerate(model['rules'])}
        self.helpers={h['name']:'Helper'+str(i) for i,h in enumerate(model['helpers'])}
        self.task=validate_task({'record_type':'NativeCatalaTask','task_id':'structured.'+digest(model),
            'packet':model['review']['packet'],'question':model['model_id'],'entry_scope':'SharedRule',
            'types':self.layout.types,
            'inputs':[field(self.facts[f['name']],self.layout.boxes[f['type']]) for f in model['facts']],
            'outputs':[field(self.rules[r['id']],self.layout.boxes[r['type']]) for r in model['rules']],
            'valid_from':model['valid_from'],'valid_until':model['valid_until'],'bounds':[],
            'native_profile':'legalmath.catala.native.v2',
            'imports':['Integer_en','Decimal_en','Date_en','List_en']})

    def name(self):
        self.counter+=1
        return 'v'+str(self.counter)

    def bind(self, expr, continuation):
        name=self.name()
        return '(let '+name+' equals '+expr+' in '+continuation(name)+')'

    def many(self, expressions, continuation, values=()):
        if not expressions: return continuation(list(values))
        return self.bind(expressions[0],lambda v:self.many(expressions[1:],continuation,(*values,v)))

    def meta(self, value):
        return 'Meta { -- s: '+value+'.s -- c: '+value+'.c -- refs: '+value+'.refs }'

    def merge(self, metas):
        if not metas: return 'Meta { -- s: 0 -- c: 0 -- refs: [] }'
        return self.merge_list('['+'; '.join(metas)+']')

    def merge_list(self, expression):
        a,b=self.name(),self.name()
        return ('(combine all '+b+' among '+expression+' in '+a+
                ' initially Meta { -- s: 0 -- c: 0 -- refs: [] } with Meta { -- s: '+
                '(if '+b+'.s > '+a+'.s then '+b+'.s else '+a+'.s) -- c: '+
                '(if '+b+'.s > '+a+'.s then '+b+'.c else '+a+'.c) -- refs: ('+a+'.refs ++ '+b+'.refs) })')

    def box(self, typ, value=None, *, meta=None, state=None, code=None, refs=None):
        if value is None: value=literal(self.task,self.layout.payloads[typ],self.layout.empty(typ))
        s=str(state) if state is not None else meta+'.s' if meta else '0'
        c=str(code) if code is not None else meta+'.c' if meta else '0'
        r=refs if refs is not None else meta+'.refs' if meta else '[]'
        return self.layout.boxes[typ]+' { -- s: '+s+' -- c: '+c+' -- refs: '+r+' -- v: '+value+' }'

    def append_meta(self, typ, expr, meta):
        return self.bind(expr,lambda result:self.bind(self.merge([meta,self.meta(result)]),
            lambda m:self.box(typ,result+'.v',meta=m)))

    def strict(self, typ, expressions, calculation):
        def done(args):
            return self.bind(self.merge([self.meta(a) for a in args]),lambda m:
                '(if '+m+'.s = 0 then '+calculation(args,m)+' else '+self.box(typ,meta=m)+')')
        return self.many(expressions,done)

    def emit(self, n, env=None):
        env=env or {};op=n['op'];typ=self.types[n['node_id']]
        def e(key,local=env): return self.emit(n[key],local)
        if op=='literal':
            return self.box(typ,literal(self.task,self.layout.payloads[typ],n['value']))
        if op=='fact': return self.facts[n['name']]
        if op=='var': return env[n['name']]
        if op=='rule': return self.rules[n['name']]
        if op=='not': return self.strict(typ,[e('arg')],lambda a,m:self.box(typ,'(not '+a[0]+'.v)',meta=m))
        if op in ('add','sub','mul','compare'):
            symbol={'eq':'=','ge':'>=','gt':'>'}[n['cmp']] if op=='compare' else {'add':'+','sub':'-','mul':'*'}[op]
            return self.strict(typ,[e('left'),e('right')],lambda a,m:self.box(typ,'('+a[0]+'.v '+symbol+' '+a[1]+'.v)',meta=m))
        if op in ('all','any'):
            def boolean(args):
                decisive=' or '.join('('+a+'.s = 0 and '+('not ' if op=='all' else '')+a+'.v)' for a in args)
                val='false' if op=='all' else 'true'
                return self.bind(self.merge([self.meta(a) for a in args]),lambda m:
                    '(if '+m+'.s >= 2 then '+self.box(typ,meta=m)+' else if '+decisive+' then '+
                    self.box(typ,val,meta=m,state=0,code=0)+' else if '+m+'.s = 1 then '+self.box(typ,meta=m)+
                    ' else '+self.box(typ,'true' if op=='all' else 'false',meta=m)+')')
            return self.many([self.emit(a,env) for a in n['args']],boolean)
        if op=='if':
            return self.bind(e('condition'),lambda c:'(if '+c+'.s = 0 then '+
                self.append_meta(typ,'(if '+c+'.v then '+e('then')+' else '+e('else')+')',self.meta(c))+
                ' else '+self.box(typ,meta=c)+')')
        if op=='scale':
            def scale(args,m):
                rational='(('+args[0]+'.v * '+n['numerator']+') / '+n['denominator']+')'
                return self.bind(rational,lambda x:self.bind('(integer of '+x+')',lambda q:
                    '(if (decimal of '+q+') = '+x+' then '+self.box(typ,q,meta=m)+
                    ' else '+self.box(typ,meta=m,state=3,code=1)+')'))
            return self.strict(typ,[e('arg')],scale)
        if op=='round':
            def rounding(args,m):
                x=args[0]+'.v'
                def rounded(q):
                    mode=n['mode']
                    if mode=='toward_zero': value=q
                    elif mode=='floor': value='(if (decimal of '+q+') > '+x+' then '+q+' - 1 else '+q+')'
                    elif mode=='ceiling': value='(if (decimal of '+q+') < '+x+' then '+q+' + 1 else '+q+')'
                    else: value='(integer of (if '+x+' >= 0.0 then '+x+' + 0.5 else '+x+' - 0.5))'
                    return self.box(typ,value,meta=m)
                return self.bind('(integer of '+x+')',rounded)
            return self.strict(typ,[e('arg')],rounding)
        if op=='default':
            def defaults(guards):
                selected=e('base')
                for g,ex in reversed(list(zip(guards,n['exceptions']))):
                    selected='(if '+g+'.v then '+self.emit(ex['value'],env)+' else '+selected+')'
                count=' + '.join('(if '+g+'.s = 0 and '+g+'.v then 1 else 0)' for g in guards) or '0'
                return self.bind(self.merge([self.meta(g) for g in guards]),lambda m:
                    '(if '+m+'.s >= 2 then '+self.box(typ,meta=m)+' else if ('+count+') > 1 then '+
                    self.box(typ,meta=m,state=2,code=4)+' else if '+m+'.s = 1 then '+self.box(typ,meta=m)+
                    ' else '+self.append_meta(typ,selected,m)+')')
            return self.many([self.emit(ex['guard'],env) for ex in n['exceptions']],defaults)
        if op=='record':
            fields={f['name']:f['value'] for f in n['fields']}
            payload=self.layout.payloads[typ]+' { '+ ' '.join('-- '+self.layout.fields[typ][f['name']]+': '+self.emit(fields[f['name']],env) for f in self.layout.defs[typ]['fields'])+' }'
            return self.box(typ,payload)
        if op=='field':
            source_type=self.types[n['arg']['node_id']]
            return self.bind(e('arg'),lambda a:'(if '+a+'.s = 0 then '+
                self.append_meta(typ,a+'.v.'+self.layout.fields[source_type][n['field']],self.meta(a))+
                ' else '+self.box(typ,meta=a)+')')
        if op=='list': return self.box(typ,'['+'; '.join(self.emit(a,env) for a in n['args'])+']')
        if op=='map':
            v=self.name()
            return self.bind(e('arg'),lambda a:'(if '+a+'.s = 0 then '+
                self.box(typ,'(map each '+v+' among '+a+'.v to '+e('body',{**env,n['binding']:v})+')',meta=a)+
                ' else '+self.box(typ,meta=a)+')')
        if op=='filter':
            v,acc=self.name(),self.name()
            def filtering(a):
                body=self.bind(e('body',{**env,n['binding']:v}),lambda p:
                    self.bind(self.merge([self.meta(acc),self.meta(p)]),lambda m:
                        '(if '+m+'.s = 0 then '+self.box(typ,'(if '+p+'.v then '+acc+'.v ++ ['+v+'] else '+acc+'.v)',meta=m)+
                        ' else '+self.box(typ,meta=m)+')'))
                return '(if '+a+'.s = 0 then (combine all '+v+' among '+a+'.v in '+acc+' initially '+self.box(typ,meta=a)+' with '+body+') else '+self.box(typ,meta=a)+')'
            return self.bind(e('arg'),filtering)
        if op=='sum':
            v,acc=self.name(),self.name()
            def summing(a):
                body=self.bind(self.merge([self.meta(acc),self.meta(v)]),lambda m:
                    '(if '+m+'.s = 0 then '+self.box(typ,'('+acc+'.v + '+v+'.v)',meta=m)+' else '+self.box(typ,meta=m)+')')
                return '(if '+a+'.s = 0 then (combine all '+v+' among '+a+'.v in '+acc+' initially '+self.box(typ,meta=a)+' with '+body+') else '+self.box(typ,meta=a)+')'
            return self.bind(e('arg'),summing)
        if op=='some': return self.box(typ,'(Present content '+e('arg')+')')
        if op=='none': return self.box(typ,'Absent')
        if op=='option':
            v=self.name()
            return self.bind(e('arg'),lambda a:'(if '+a+'.s = 0 then '+self.append_meta(typ,
                '(match '+a+'.v with pattern\n -- Present content '+v+': '+e('present',{**env,n['binding']:v})+
                '\n -- Absent: '+e('absent')+')',self.meta(a))+' else '+self.box(typ,meta=a)+')')
        if op=='variant':
            case=self.layout.payloads[typ]+'.'+self.layout.cases[typ][n['case']]
            return self.box(typ,'('+case+(' content '+e('arg') if n['arg'] is not None else '')+')')
        if op=='match':
            source_type=self.types[n['arg']['node_id']];arms=[]
            for arm in n['arms']:
                v=self.name();local={**env,**({arm['binding']:v} if arm['binding'] else {})}
                arms.append(' -- '+self.layout.cases[source_type][arm['case']]+(' content '+v if arm['binding'] else '')+': '+self.emit(arm['body'],local))
            return self.bind(e('arg'),lambda a:'(if '+a+'.s = 0 then '+self.append_meta(typ,
                '(match '+a+'.v with pattern\n'+'\n'.join(arms)+')',self.meta(a))+' else '+self.box(typ,meta=a)+')')
        if op=='call':
            def call(args,m):
                result='(output of '+self.helpers[n['name']]+' with { '+ ' '.join('-- p'+str(i)+': '+a for i,a in enumerate(args))+' }).result'
                return self.append_meta(typ,result,m)
            return self.strict(typ,[self.emit(a,env) for a in n['args']],call)
        if op=='library':
            return self.strict(typ,[self.emit(a,env) for a in n['args']],lambda a,m:self.library(n,typ,a,m))
        fail('E_UNSUPPORTED_PROFILE',op)

    def library(self,n,typ,args,m):
        op=n['name'];a=[x+'.v' for x in args]
        if op in ('numeric.min','numeric.max'):
            namespace='Decimal' if typ=='decimal' else 'Integer'
            return self.box(typ,'('+namespace+'.'+op.split('.')[1]+' of '+', '.join(a)+')',meta=m)
        if op=='list.length': return self.box(typ,'(number of '+a[0]+')',meta=m)
        if op=='list.sequence':
            v=self.name()
            value='(map each '+v+' among (List.sequence of '+', '.join(a)+') to '+self.box('integer',v)+')'
            return '(if '+a[1]+' <= '+a[0]+' then '+self.box(typ,'[]',meta=m)+' else if '+a[1]+' - '+a[0]+' > 10000 then '+self.box(typ,meta=m,state=3,code=3)+' else '+self.box(typ,value,meta=m)+')'
        if op=='date.month_end': return self.box(typ,'(Date.last_day_of_month of '+a[0]+')',meta=m)
        if op=='date.add_months_clamped':
            index='((Date.get_year of '+a[0]+') * 12 + (Date.get_month of '+a[0]+') - 1 + '+a[1]+')'
            return self.bind(index,lambda i:'(if '+i+' < 12 or '+i+' > 119999 then '+self.box(typ,meta=m,state=3,code=2)+
                ' else '+self.box(typ,'(Date.add_round_down of '+a[0]+', ('+a[1]+' * 1 month))',meta=m)+')')
        if op=='date.add_days':
            return '(if '+a[1]+' < -3652058 or '+a[1]+' > 3652058 then '+self.box(typ,meta=m,state=3,code=2)+' else '+self.bind(
                '(Date.add_round_down of '+a[0]+', ('+a[1]+' * 1 day))',lambda d:'(if '+d+' < |0001-01-01| or '+d+' > |9999-12-31| then '+
                self.box(typ,meta=m,state=3,code=2)+' else '+self.box(typ,d,meta=m)+')')+')'
        fail('E_UNSUPPORTED_PROFILE',op)

    def lower(self):
        lines=['```catala']
        for h in self.model['helpers']:
            scope=self.helpers[h['name']]
            lines+=['declaration scope '+scope+':']
            lines+=['  input p'+str(i)+' content '+catala_type(self.layout.boxes[p['type']]) for i,p in enumerate(h['parameters'])]
            lines+=['  output result content '+self.layout.boxes[h['type']],'scope '+scope+':',
                    '  definition result equals '+self.emit(h['body'],{p['name']:'p'+str(i) for i,p in enumerate(h['parameters'])})]
        lines+=['scope SharedRule:']
        for r in self.model['rules']:
            body=self.bind(self.emit(r['scope']),lambda s:'(if '+s+'.s = 0 then (if '+s+'.v then '+
                self.append_meta(r['type'],self.emit(r['body']),self.meta(s))+' else '+self.box(r['type'],meta=s,state=4)+
                ') else '+self.box(r['type'],meta=s)+')')
            lines+=['  definition '+self.rules[r['id']]+' equals '+body]
        lines+=['```']
        candidate=validate_candidate(self.task,{'record_type':'NativeCatalaCandidate','task_hash':digest(self.task),
            'source':'\n'.join(lines),'interpretation':self.model['review']['reading']['statement'] if self.model['review']['reading'] else self.model['model_id'],
            'assumptions':self.model['review']['reading'].get('assumptions',[]) if self.model['review']['reading'] else [],
            'unresolved':list(self.model['review']['questions']),
            'anchors':[{'unit_id':u['unit_id'],'quote':u['text'],'code_excerpt':'scope SharedRule:'} for u in self.task['packet']['units']]})
        return {'route':'native','encoding':'structured.v1','task':self.task,'candidate':candidate,
                'fact_names':self.facts,'rule_names':self.rules}


def capabilities(model):
    m,types=validate(model);issues=[]
    if m['review']['packet'] is None:
        issues.append({'path':'/review/packet','reason':'Native translation requires retained source text'})
    else:
        try: Compiler(m,types).lower()
        except LegalMathError as exc:
            issues.append({'path':'/generated_interface','reason':exc.code,'details':exc.details})
    return {'target':'catala','model_hash':digest(m),'supported':not issues,'route':'native','encoding':'structured.v1','issues':issues}


def lower(model):
    m,types=validate(model)
    return Compiler(m,types).lower()
