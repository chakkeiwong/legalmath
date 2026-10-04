"""Catala target: verified scalar lowering or direct native rich expressions."""
from ..canonical import digest
from ..catala.native.contracts import validate_task, validate_candidate, literal
from .model import validate, walk, inner, fail
from .ruleir import capabilities as ruleir_capabilities, lower as lower_ruleir


def native_type(typ):
    for constructor in ('list','optional'):
        child = inner(typ, constructor)
        if child is not None: return constructor + '[' + native_type(child) + ']'
    return {'bool':'boolean','money_hkd':'money'}.get(typ,typ)


def capabilities(model):
    m, types = validate(model)
    if m['version']=='2':
        from .catala_structured import capabilities as structured_capabilities
        return structured_capabilities(m)
    if ruleir_capabilities(m)['supported']:
        return {'target':'catala','model_hash':digest(m),'supported':True,'route':'scalar-compatibility','issues':[]}
    issues = []
    if not 1<=len(m['facts'])<=40 or len(m['rules'])>40:
        issues.append({'path':'/facts','reason':'Native interface supports 1–40 inputs and at most 40 outputs'})
    if m['review']['packet'] and len(m['review']['packet']['units'])>100:
        issues.append({'path':'/review/packet','reason':'Native source anchors currently support at most 100 units'})
    if any(d['name'] in ('SharedRule','Native','NativeCheck') for d in m['types']):
        issues.append({'path':'/types','reason':'Type name collides with a reserved native scope'})
    if m['profile'] != 'complete.v1':
        issues.append({'path':'/profile','reason':'Native rich translation currently requires explicit complete.v1 semantics'})
    if m['review']['packet'] is None:
        issues.append({'path':'/review/packet','reason':'Native translation requires the retained interpretation packet'})
    for i, r in enumerate(m['rules']):
        s = r['scope']
        if s['op'] != 'literal' or s['type'] != 'bool' or s['value'] is not True:
            issues.append({'path':f'/rules/{i}/scope','reason':'Rich native rules currently require unconditional outer scope; conditional expressions remain supported'})
        for n, p in walk(r['body'],f'/rules/{i}/body'):
            if n['op'] in ('scale','default'):
                issues.append({'path':p,'reason':'Rich native translation has no reviewed lowering for '+n['op']})
    return {'target':'catala','model_hash':digest(m),'supported':not issues,'route':'native','issues':issues}


def lower(model):
    m, types = validate(model); capability = capabilities(m)
    if not capability['supported']: fail('E_UNSUPPORTED_PROFILE', capability)
    if m['version']=='2':
        from .catala_structured import lower as structured_lower
        return structured_lower(m)
    if capability['route'] == 'scalar-compatibility':
        return {'route':'scalar-compatibility','bundle':lower_ruleir(m)}
    facts = {f['name']:f'f{i}' for i,f in enumerate(m['facts'])}
    rules = {r['id']:f'r{i}' for i,r in enumerate(m['rules'])}
    definitions = []
    for d in m['types']:
        definitions.append({**d, 'fields':[{**f,'type':native_type(f['type'])} for f in d['fields']],
                            'cases':[{**c,'type':native_type(c['type']) if c['type'] else None} for c in d['cases']]})
    packet = m['review']['packet']
    task = {'record_type':'NativeCatalaTask','task_id':'model.'+digest(m), 'packet':packet,
            'question':m['review']['reading']['statement'] if m['review']['reading'] else m['model_id'],
            'entry_scope':'SharedRule','types':definitions,
            'inputs':[{'name':facts[f['name']],'type':native_type(f['type']),'meaning':f['description'],'unit':'Declared in factual description'} for f in m['facts']],
            'outputs':[{'name':rules[r['id']],'type':native_type(r['type']),'meaning':r['id'],'unit':'Declared in shared rule model'} for r in m['rules']],
            'valid_from':m['valid_from'],'valid_until':m['valid_until'],
            'bounds':[{**b,'input':facts[b['input']]} for b in m['bounds']],
            'native_profile':'legalmath.catala.native.v2'}
    task = validate_task(task)
    counter = 0

    def name():
        nonlocal counter
        counter += 1
        return 'v'+str(counter)

    def emit(n, env=None):
        env = env or {}; op = n['op']
        def e(key, local=env): return emit(n[key],local)
        if op == 'literal': return literal(task,native_type(n['type']),n['value'])
        if op == 'fact': return facts[n['name']]
        if op == 'var': return env[n['name']]
        if op == 'rule': return rules[n['name']]
        if op in ('all','any'): return '('+(' and ' if op=='all' else ' or ').join(emit(a,env) for a in n['args'])+')'
        if op == 'not': return '(not '+e('arg')+')'
        if op in ('add','sub','mul','compare'):
            symbol = {'eq':'=','ge':'>=','gt':'>'}[n['cmp']] if op=='compare' else {'add':'+','sub':'-','mul':'*'}[op]
            return '('+e('left')+' '+symbol+' '+e('right')+')'
        if op == 'if': return '(if '+e('condition')+' then '+e('then')+' else '+e('else')+')'
        if op == 'field': return '('+e('arg')+').'+n['field']
        if op == 'list': return '['+'; '.join(emit(a,env) for a in n['args'])+']'
        if op in ('map','filter'):
            v = name(); body = e('body',{**env,n['binding']:v})
            return ('(map each '+v+' among '+e('arg')+' to '+body+')' if op=='map' else
                    '(list of '+v+' among '+e('arg')+' such that '+body+')')
        if op == 'sum': return '(sum '+native_type(types[n['node_id']])+' of '+e('arg')+')'
        if op == 'some': return '(Present content '+e('arg')+')'
        if op == 'none': return 'Absent'
        if op == 'option':
            v=name()
            return '(match '+e('arg')+' with pattern\n -- Present content '+v+': '+e('present',{**env,n['binding']:v})+'\n -- Absent: '+e('absent')+')'
        if op == 'variant':
            return '('+n['type']+'.'+n['case']+(' content '+e('arg') if n['arg'] is not None else '')+')'
        if op == 'match':
            lines=[]
            for arm in n['arms']:
                v=name(); local={**env,**({arm['binding']:v} if arm['binding'] else {})}
                lines.append(' -- '+arm['case']+(' content '+v if arm['binding'] else '')+': '+emit(arm['body'],local))
            return '(match '+e('arg')+' with pattern\n'+'\n'.join(lines)+')'
        fail('E_UNSUPPORTED_PROFILE',op)

    source = '```catala\nscope SharedRule:\n' + '\n'.join('  definition '+rules[r['id']]+' equals '+emit(r['body']) for r in m['rules'])+'\n```'
    candidate = {'record_type':'NativeCatalaCandidate','task_hash':digest(task),'source':source,
                 'interpretation':task['question'],'assumptions':m['review']['reading'].get('assumptions',[]) if m['review']['reading'] else [],
                 'unresolved':list(m['review']['questions']),
                 'anchors':[{'unit_id':u['unit_id'],'quote':u['text'],'code_excerpt':'scope SharedRule:'} for u in packet['units']]}
    return {'route':'native','task':task,'candidate':validate_candidate(task,candidate),'fact_names':facts,'rule_names':rules}
