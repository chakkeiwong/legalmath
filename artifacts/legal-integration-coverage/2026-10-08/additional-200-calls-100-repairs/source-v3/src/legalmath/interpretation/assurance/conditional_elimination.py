"""Replayed Boolean witnesses reject candidates only under declared premises.

The parser/evaluator does not use the production expression parser, IR evaluator,
SMT encoder or compiled program. Its deliberately narrow domain is total Boolean
facts. Unknown/conflict states, dates and rich values are outside this contract.
"""
from copy import deepcopy
from itertools import product
import re

from ...canonical import canonical, digest
from ...errors import LegalMathError
from ..search.models import commitment
from .semantics import check_quotes

PROFILE = 'legalmath.conditional-elimination.boolean.v1'


def unsupported(message): raise LegalMathError('E_UNSUPPORTED_PROFILE', details=message)


def names_checked(names):
    if (not isinstance(names, list) or not 1 <= len(names) <= 8 or len(names) != len(set(names)) or
            any(not isinstance(n,str) or not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', n) or n in ('true','false') for n in names)):
        unsupported('One to eight distinct nonliteral Boolean fact names required')
    return names


def parse_boolean(text, names):
    names_checked(names)
    if not isinstance(text,str) or not text or len(text)>16000: unsupported('Boolean expression size')
    tokens = re.findall(r'\(|\)|[^\s()]+', text)
    stack = [[]]
    for token in tokens:
        if token=='(':
            stack.append([])
            if len(stack)>33: unsupported('Boolean expression depth')
        elif token==')':
            if len(stack)==1 or not stack[-1]: unsupported('Malformed Boolean expression')
            node=stack.pop(); stack[-1].append(node)
        else: stack[-1].append(token)
    if len(stack)!=1 or len(stack[0])!=1: unsupported('Malformed Boolean expression')
    def verify(node):
        if isinstance(node,str):
            if node not in [*names,'true','false']: unsupported('Unsupported Boolean token: '+node)
            return node
        if not node or not isinstance(node[0],str): unsupported('Invalid Boolean operator')
        op,*args=node
        if not ((op=='not' and len(args)==1) or (op in ('and','or') and 1<=len(args)<=16) or
                (op=='if' and len(args)==3) or (op=='=' and len(args)==2)):
            unsupported('Unsupported Boolean operator or arity')
        return [op,*[verify(a) for a in args]]
    return verify(stack[0][0])


def evaluate(tree, values):
    if any(type(v) is not bool for v in values.values()): unsupported('Only total Boolean valuations are admitted')
    if isinstance(tree,str):
        if tree=='true': return True
        if tree=='false': return False
        if tree not in values: unsupported('Missing Boolean fact')
        return values[tree]
    op,*args=tree
    values_of=[evaluate(a,values) for a in args]
    if op=='not': return not values_of[0]
    if op=='and': return all(values_of)
    if op=='or': return any(values_of)
    if op=='if': return values_of[1] if values_of[0] else values_of[2]
    if op=='=': return values_of[0]==values_of[1]
    unsupported('Unvalidated operator')


def enumerate_grammar(names, *, maximum_depth=1, maximum_expressions=256):
    names_checked(names)
    if (type(maximum_depth)is not int or not 0<=maximum_depth<=3 or
            type(maximum_expressions)is not int or not len(names)+2<=maximum_expressions<=2048):
        raise LegalMathError('E_RESOURCE_LIMIT')
    result=['false','true',*names]; seen=set(result); completed=0; frontier=None
    for depth in range(1,maximum_depth+1):
        prior=result[:]
        def layer():
            for a in prior: yield '(not '+a+')'
            for op in ('and','or'):
                for a,b in product(prior,repeat=2): yield '('+op+' '+a+' '+b+')'
        for cursor,expression in enumerate(layer()):
            if expression in seen: continue
            if len(result)==maximum_expressions:
                frontier={'depth':depth,'construction_cursor':cursor,'next_expression':expression,
                          'prior_layer_expressions':prior}
                break
            seen.add(expression); result.append(expression)
        if frontier: break
        completed=depth
    return {'profile':'finite-boolean-grammar.v1','facts':names,'maximum_depth':maximum_depth,
        'maximum_expressions':maximum_expressions,'operators':['not','binary-and','binary-or'],
        'expressions':result,'completed_depth':completed,'frontier':frontier,
        'declared_grammar_complete':frontier is None,'all_legal_interpretations_found':False,
        'selection':'Breadth first, syntax order; no probability or legal preference'}


def obligations_checked(obligations, packet, question, names):
    if not isinstance(obligations,list) or len(obligations)>32: raise LegalMathError('E_RESOURCE_LIMIT')
    ids=[]
    for row in obligations:
        if (not isinstance(row,dict) or set(row)!= {'obligation_id','packet_hash','question_hash','when',
                'expected','evidence','premise_status','rationale'} or
                not isinstance(row['obligation_id'],str) or not row['obligation_id'] or
                type(row['expected'])is not bool or row['premise_status']!='PROPOSED_FORMAL_PREMISE' or
                not isinstance(row['rationale'],str) or not row['rationale']):
            raise LegalMathError('E_SCHEMA')
        if row['packet_hash']!=digest(packet) or row['question_hash']!=digest(question):
            raise LegalMathError('E_STALE_REVIEW')
        if not row['evidence']: raise LegalMathError('E_REFERENCE')
        check_quotes(row['evidence'],packet); parse_boolean(row['when'],names);ids.append(row['obligation_id'])
    if len(ids)!=len(set(ids)): raise LegalMathError('E_DUPLICATE_ID')
    return obligations


def check(packet, reading, question, obligations):
    result={'profile':PROFILE,'source_packet_hash':digest(packet),'candidate_hash':commitment(reading),
        'question_hash':digest(question),'obligations_hash':digest(obligations),
        'domain':'Complete Boolean valuations only; no unknown/conflict states',
        'status':'UNSUPPORTED','witnesses':[],'valuations_checked':0,
        'source_entailment':'NOT_ESTABLISHED','legal_elimination':False,'original_candidate_retained':True}
    formal=reading.get('formalization')
    if formal is None: return {**result,'reason':'Candidate has no formal program'}
    if len(obligations)>32:return {**result,'reason':'Formal obligation limit; all premise identities remain retained'}
    try:
        if formal.get('version')=='2' or formal['result_type']!='bool' or any(f['type']!='bool' for f in formal['facts']):
            unsupported('Total scalar Boolean profile required')
        names=names_checked([f['name'] for f in formal['facts']])
        scope=parse_boolean(formal['scope'],names);body=parse_boolean(formal['result'],names)
        obligations_checked(obligations,packet,question,names)
        guards={o['obligation_id']:parse_boolean(o['when'],names) for o in obligations}
    except LegalMathError as exc:
        if exc.code!='E_UNSUPPORTED_PROFILE': raise
        return {**result,'reason':exc.details}
    witnesses=[]; values=[]
    for row in product((False,True),repeat=len(names)):
        assignment=dict(zip(names,row)); active=evaluate(scope,assignment); actual=evaluate(body,assignment)
        values.append({'assignment':assignment,'scope':active,'result':actual})
        for obligation in obligations:
            if evaluate(guards[obligation['obligation_id']],assignment) and (not active or actual!=obligation['expected']):
                if not any(w['obligation_id']==obligation['obligation_id'] for w in witnesses):
                    witnesses.append({'obligation_id':obligation['obligation_id'],'assignment':assignment,
                                      'scope':active,'actual':actual,'expected':obligation['expected']})
    result.update(status='CONDITIONALLY_REJECTED' if witnesses else 'NO_DECLARED_OBLIGATION_VIOLATION' if obligations else
                  'NO_FORMAL_OBLIGATIONS',witnesses=witnesses,valuations_checked=len(values),
                  truth_table_hash=digest(values),facts=names,checked_obligations=deepcopy(obligations))
    return result


def verify(certificate, packet, reading, question, obligations):
    expected=check(packet,reading,question,obligations)
    if canonical(certificate)!=canonical(expected):
        raise LegalMathError('E_INTEGRITY',details='Conditional elimination does not replay against the original premises')
    return expected
