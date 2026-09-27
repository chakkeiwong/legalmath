"""Version-2 typed result layout and evidence codec; no rule evaluation."""
from .model import SCALARS, inner, fail

STATES = {0:'VALUE', 1:'UNKNOWN', 2:'CONFLICT', 3:'ERROR', 4:'OUT_OF_SCOPE'}
CODES = {0:None, 1:'E_INEXACT_SCALE', 2:'E_DATE_RANGE', 3:'E_RESOURCE_LIMIT', 4:'EXCEPTION_OVERLAP'}


def field(name, typ):
    return {'name':name,'type':typ,'meaning':'Generated shared model encoding','unit':'Explicit shared type'}


class Layout:
    def __init__(self, model, node_types):
        self.defs={d['name']:d for d in model['types']}
        self.boxes={};self.payloads={};self.fields={};self.cases={};self.types=[];self.sizes={}
        self.types.append({'name':'Meta','kind':'record','fields':[
            field('s','integer'),field('c','integer'),field('refs','list[integer]')],'cases':[]})
        required=set(node_types.values())|{f['type'] for f in model['facts']}
        required.update(p['type'] for h in model.get('helpers',[]) for p in h['parameters'])
        for typ in sorted(required): self.add(typ)
        if len(self.types)>30: fail('E_RESOURCE_LIMIT','Generated interface exceeds 30 native types')

    def add(self, typ):
        if typ in self.boxes: return
        item,option=inner(typ,'list'),inner(typ,'optional')
        if item is not None or option is not None:
            child=item if item is not None else option;self.add(child)
            payload=('list' if item is not None else 'optional')+'['+self.boxes[child]+']'
            size=6+self.sizes[child]
        elif typ in SCALARS:
            # Monetary payloads are exact integer MINOR UNITS, never native money
            # multiplication whose conversion can round before our explicit node.
            payload={'bool':'boolean','money_hkd':'integer'}.get(typ,typ)
            size=6
        else:
            d=self.defs[typ]
            for f in d['fields']: self.add(f['type'])
            for c in d['cases']:
                if c['type']: self.add(c['type'])
            size=6+sum(self.sizes[f['type']] for f in d['fields'])+sum(self.sizes[c['type']] for c in d['cases'] if c['type'])
            payload='P'+str(len(self.boxes))
            self.fields[typ]={f['name']:'x'+str(i) for i,f in enumerate(d['fields'])}
            self.cases[typ]={c['name']:'Case'+str(i) for i,c in enumerate(d['cases'])}
            self.types.append({'name':payload,'kind':d['kind'],
                'fields':[field(self.fields[typ][f['name']],self.boxes[f['type']]) for f in d['fields']],
                'cases':[{'name':self.cases[typ][c['name']],'type':self.boxes[c['type']] if c['type'] else None} for c in d['cases']]})
        if size>10000: fail('E_RESOURCE_LIMIT','Expanded structured type exceeds 10000 fields')
        self.sizes[typ]=size
        self.payloads[typ]=payload;self.boxes[typ]='B'+str(len(self.boxes))
        self.types.append({'name':self.boxes[typ],'kind':'record','fields':[
            field('s','integer'),field('c','integer'),field('refs','list[integer]'),field('v',payload)],'cases':[]})

    def empty(self, typ):
        if inner(typ,'list') is not None: return []
        if inner(typ,'optional') is not None: return None
        if typ=='bool': return False
        if typ in ('integer','money_hkd'): return '0'
        if typ=='decimal': return {'numerator':'0','denominator':'1'}
        if typ=='date': return '2000-01-01'
        d=self.defs[typ]
        if d['kind']=='record':
            return {self.fields[typ][f['name']]:self.empty_box(f['type']) for f in d['fields']}
        c=d['cases'][0];case=self.cases[typ][c['name']]
        if not any(c['type'] for c in d['cases']): return case
        return {'case':case,'value':self.empty_box(c['type']) if c['type'] else None}

    def empty_box(self, typ, *, state=0, refs=(), code=0):
        return {'s':str(state),'c':str(code),'refs':list(refs),'v':self.empty(typ)}

    def encode(self, typ, observation, path, index):
        state={'known':0,'unknown':1,'conflict':2}[observation['status']]
        result=self.empty_box(typ,state=state,refs=[index[path]])
        if state: return result
        value=observation['value'];item,option=inner(typ,'list'),inner(typ,'optional')
        if item is not None:
            result['v']=[self.encode(item,x,path+'/'+str(i),index) for i,x in enumerate(value)]
        elif option is not None:
            result['v']=None if value is None else {'present':self.encode(option,value['present'],path+'/present',index)}
        elif typ in SCALARS: result['v']=value
        else:
            d=self.defs[typ]
            if d['kind']=='record':
                result['v']={self.fields[typ][f['name']]:self.encode(f['type'],value[f['name']],path+'/'+f['name'],index) for f in d['fields']}
            else:
                case=value if isinstance(value,str) else value['case']
                c=next(c for c in d['cases'] if c['name']==case)
                result['v']=(self.cases[typ][case] if not any(c['type'] for c in d['cases']) else
                             {'case':self.cases[typ][case],'value':self.encode(c['type'],value['value'],path+'/value',index) if c['type'] else None})
        return result

    def decode(self, typ, box, provenance):
        """Decode a compiler-computed tree and its referenced evidence paths."""
        if box['s'] not in {str(s) for s in STATES} or box['c'] not in {str(c) for c in CODES}: fail('E_INTEGRITY')
        refs=set(box['refs'])
        if not refs<=set(provenance): fail('E_INTEGRITY','Unknown generated evidence reference')
        state=int(box['s']);code=int(box['c']);tree={'status':STATES[state],'type':typ}
        if state:
            tree.update(value=None,reason=CODES[code])
            return tree,refs
        value=box['v'];item,option=inner(typ,'list'),inner(typ,'optional');complete=True

        def child(t,b):
            nonlocal complete
            decoded,used=self.decode(t,b,provenance);refs.update(used)
            complete &= decoded['status']=='VALUE'
            return decoded

        if item is not None:
            children=[child(item,x) for x in value];raw=[x['value'] for x in children]
        elif option is not None:
            children=None if value is None else {'present':child(option,value['present'])}
            raw=None if children is None else {'present':children['present']['value']}
        elif typ in SCALARS: children=None;raw=value
        else:
            d=self.defs[typ]
            if d['kind']=='record':
                children={f['name']:child(f['type'],value[self.fields[typ][f['name']]]) for f in d['fields']}
                raw={k:v['value'] for k,v in children.items()}
            else:
                alias=value if isinstance(value,str) else value['case']
                c=next(c for c in d['cases'] if self.cases[typ][c['name']]==alias)
                if not any(c['type'] for c in d['cases']): children=None;raw=c['name']
                else:
                    children={'case':c['name'],'value':child(c['type'],value['value']) if c['type'] else None}
                    raw={'case':c['name'],'value':children['value']['value'] if c['type'] else None}
        if complete: tree['value']=raw
        else: tree.update(status='PARTIAL',value=None,children=children)
        return tree,refs


def inputs(model, node_types, lower, boundary):
    layout=Layout(model,node_types)
    paths=sorted(boundary['observations'])
    index={p:str(i) for i,p in enumerate(paths)}
    provenance={index[p]:{'path':p,**boundary['observations'][p]} for p in paths}
    encoded={lower['fact_names'][f['name']]:layout.encode(f['type'],boundary['snapshot']['facts'][f['name']],'/'+f['name'],index) for f in model['facts']}
    return encoded,provenance


def result_fields(model, node_types, typ, box, provenance):
    tree,refs=Layout(model,node_types).decode(typ,box,provenance)
    status=tree['status']
    if status=='VALUE' and typ=='bool': status='TRUE' if tree['value'] else 'FALSE'
    result={'status':status,'value':tree['value'],'reason':tree.get('reason'),
            'missing_inputs':sorted({provenance[r]['path'] for r in refs if provenance[r]['status']=='unknown'}),
            'blocking_inputs':sorted({provenance[r]['path'] for r in refs if provenance[r]['status']=='conflict'}),
            'used_evidence':{provenance[r]['path']:provenance[r]['evidence_ids'] for r in sorted(refs) if provenance[r]['evidence_ids']}}
    if status=='PARTIAL': result['partial_value']=tree
    return result
