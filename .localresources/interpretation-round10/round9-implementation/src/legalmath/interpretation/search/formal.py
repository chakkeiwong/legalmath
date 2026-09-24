"""A deliberately restricted expression compiler and executable comparison checks."""
from copy import deepcopy
from datetime import date, timedelta
from itertools import product
from pathlib import Path
import re
from ...canonical import digest
from ...errors import LegalMathError
from ...ir.typecheck import validate_bundle
from ...ir.evaluate import evaluate
from ...ir.trace import verify_result
from ...sources.anchors import make_span
from ...java.manifest import build_candidate, run_java, verify_candidate
from ...analysis.compare import compare as smt_compare
from ..contracts import parse
from .models import Formalization
from .alignment import discover, validate_correspondence, rename_bundle, translate_snapshot

RULE='selected.control'
IDENT=re.compile(r'^[a-z][a-z0-9_.-]*$')


def expression(text, prefix):
    tokens=re.findall(r'\(|\)|[^\s()]+',text)
    if not tokens or len(tokens)>1000: raise LegalMathError('E_RESOURCE_LIMIT')
    position=0;count=0
    def node(depth=0):
        nonlocal position,count
        if depth>32 or position>=len(tokens): raise LegalMathError('E_SCHEMA')
        token=tokens[position];position+=1;count+=1;ident=f'{prefix}.{count}'
        if token!='(':
            if token in ('true','false'):return {'node_id':ident,'op':'literal','type':'bool','value':token=='true'}
            if not IDENT.fullmatch(token):raise LegalMathError('E_SCHEMA',details='Invalid expression atom')
            return {'node_id':ident,'op':'fact','name':token}
        if position>=len(tokens):raise LegalMathError('E_SCHEMA')
        op=tokens[position];position+=1
        if op in ('integer','money_hkd','date'):
            if position+1>=len(tokens) or tokens[position+1]!=')':raise LegalMathError('E_SCHEMA')
            value=tokens[position];position+=2
            return {'node_id':ident,'op':'literal','type':op,'value':value}
        args=[]
        while position<len(tokens) and tokens[position]!=')':args.append(node(depth+1))
        if position>=len(tokens):raise LegalMathError('E_SCHEMA')
        position+=1
        result={'node_id':ident}
        if op in ('and','or') and args:result.update(op='all' if op=='and' else 'any',args=args)
        elif op=='not' and len(args)==1:result.update(op='not',arg=args[0])
        elif op=='if' and len(args)==3:result.update(op='if',condition=args[0],then=args[1],**{'else':args[2]})
        elif op in ('=','>','>=','+','-') and len(args)==2:
            result.update(op='compare' if op in ('=','>','>=') else 'add' if op=='+' else 'sub',left=args[0],right=args[1])
            if result['op']=='compare':result['cmp']={'=':'eq','>':'gt','>=':'ge'}[op]
        else:raise LegalMathError('E_UNSUPPORTED_PROFILE',details='Unsupported operator or arity: '+op)
        return result
    result=node()
    if position!=len(tokens):raise LegalMathError('E_SCHEMA')
    return result


def bundle(reading, packet, at):
    if reading['formalization'] is None:raise LegalMathError('E_UNSUPPORTED_PROFILE')
    formal=parse(Formalization,reading['formalization'])
    units={u['unit_id']:u for u in packet['units']}
    spans={}
    for citation in reading['citations']:
        unit=units[citation['unit_id']]
        if unit['text'].count(citation['quote'])!=1:raise LegalMathError('E_REFERENCE')
        span=unit['span'] or make_span('s.'+unit['unit_id'],'synthetic.'+packet['source_key'],
                                     unit['text'].encode(),unit['text'],0,len(unit['text']))
        spans[span['id']]=span
    result={'spec_version':'0.1','bundle_id':'search.'+digest(reading)[:20],
        'valid_from':at,'valid_until':None,'source_spans':list(spans.values()),
        'interpretations':[{'id':'reading','statement':'Unreviewed interpretation: '+reading['statement'],
            'basis':'synthetic_test' if packet['authority']=='SYNTHETIC_FIXTURE' else 'reviewer_interpretation',
            'source_span_ids':list(spans),'issue_ids':[]}],
        'facts':[{'name':f['name'],'type':f['type'],'description':f['meaning']+'; units: '+f['unit']} for f in formal['facts']],
        'rules':[{'id':RULE,'type':formal['result_type'],'scope':expression(formal['scope'],'scope'),
            'body':expression(formal['result'],'body'),'interpretation_id':'reading','source_span_ids':list(spans)}]}
    errors=validate_bundle(result)
    if errors:raise LegalMathError(errors[0]['code'],details=errors)
    return result


def render_node(node):
    op=node['op']
    if op=='fact':return 'the fact '+node['name']
    if op=='literal':return ('true' if node['value'] else 'false') if node['type']=='bool' else f"{node['type']} value {node['value']}"
    if op in ('all','any'):
        return ('all of these conditions hold' if op=='all' else 'at least one of these conditions holds')+': ['+'; '.join(render_node(a) for a in node['args'])+']'
    if op=='not':return 'it is not the case that ['+render_node(node['arg'])+']'
    if op=='if':return 'if ['+render_node(node['condition'])+'], then ['+render_node(node['then'])+'], otherwise ['+render_node(node['else'])+']'
    relation={'compare':{'eq':'equals','gt':'is strictly greater than','ge':'is greater than or equal to'}.get(node.get('cmp')),
              'add':'plus','sub':'minus'}[op]
    return '['+render_node(node['left'])+'] '+relation+' ['+render_node(node['right'])+']'


def reconstruction_request(reading, compiled):
    # No source interpretation, original AST, original formula or peer output is sent.
    from .models import GRAMMAR
    rule=compiled['rules'][0]
    return {'protocol':'legalmath.search.v1','task':'RECONSTRUCT',
        'instructions':'Reconstruct the following controlled-English rule using the supplied grammar. '
        'Preserve exact fact definitions and source_unit_ids. Do not infer a legal interpretation. '
        'Report ambiguity. '+GRAMMAR,
        'fact_definitions':reading['formalization']['facts'],
        'scope_text':render_node(rule['scope']),'result_text':render_node(rule['body']),
        'result_type':rule['type'],
        'unknown_semantics':'Strong Kleene Boolean values; unknown condition yields UNKNOWN; conflicts block.'}


def project(result):
    return {k:result[k] for k in ('status','type','value') if k in result}


def snapshots(bundles, at, maximum=128):
    """Boundary probes are counterexample candidates, never an exhaustive-domain claim."""
    literals={'integer':set(), 'money_hkd':set(), 'date':set()}
    def walk(value):
        if isinstance(value,dict):
            if value.get('op')=='literal' and value.get('type') in literals:literals[value['type']].add(value['value'])
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for b in bundles:walk(b['rules'])
    facts=bundles[0]['facts'];choices={}
    for f in facts:
        typ=f['type']
        if typ=='bool':values=[False,True]
        elif typ=='date':
            values=sorted({(date.fromisoformat(v)+timedelta(days=d)).isoformat() for v in literals[typ] for d in (-1,0,1)}) or [at[:10]]
        else:values=[str(n) for n in sorted({-1,0,1}|{int(v)+d for v in literals[typ] for d in (-1,0,1)})]
        choices[f['name']]=[None,*values]
    # Begin with known facts. A truncated Cartesian product starting with UNKNOWN
    # can otherwise leave the first several facts unknown in every single probe.
    known=tuple(choices[f['name']][-1] for f in facts)
    assignments=[known,tuple(choices[f['name']][1] for f in facts)]
    for i,f in enumerate(facts):
        for value in choices[f['name']]:
            variation=list(known);variation[i]=value;assignments.append(tuple(variation))
    from itertools import chain
    seen=set()
    for values in chain(assignments,product(*(choices[f['name']] for f in facts))):
        if values in seen:continue
        if len(seen)>=maximum:return
        seen.add(values)
        result={}
        for f,value in zip(facts,values):
            entry={'type':f['type'],'status':'unknown','reason':'MISSING'}
            if value is not None:entry={'type':f['type'],'status':'known','value':value,
                'evidence_ids':['search.probe'],'valid_from':at,'valid_until':None,'recorded_at':at}
            result[f['name']]=entry
        yield {'subject_id':'synthetic.search.probe','facts':result}


class Comparisons:
    def __init__(self,directory,jdk,at,domain=None):
        self.directory=Path(directory);self.jdk=Path(jdk);self.at=at;self.domain=domain;self.builds={}

    def build(self,b):
        key=digest(b)
        if key not in self.builds:self.builds[key]=build_candidate(b,self.directory/key,self.jdk)
        return self.builds[key]

    def verify(self,reading,packet):
        compiled=bundle(reading,packet,self.at);built=self.build(compiled)
        probes=list(snapshots([compiled],self.at,maximum=24))
        cases=[{'id':'probe.'+str(i),'bundle':compiled,'snapshot':s,'rule_id':RULE,
                'valid_at':self.at,'known_at':self.at,'expected':{}}
               for i,s in enumerate(probes)]
        result=verify_candidate(built,cases,self.jdk)
        return {'status':'JAVA_PYTHON_CONFORMANCE','cases':len(cases),'verification':result,
                'build_manifest':built['manifest'],'legal_source_commitment_resolved':False,
                'oracle':'Python/Java differential probes, not independent legal answers'}

    def replay(self, bundles, snapshot):
        results=[]
        for b in bundles:
            case={'bundle':b,'snapshot':snapshot,'rule_id':RULE,'valid_at':self.at,'known_at':self.at}
            python=evaluate(b,snapshot,RULE,self.at,self.at)
            built=self.build(b);java=run_java(built['jar'],[case],self.jdk,built['class_name'])[0]
            verify_result(b,snapshot,RULE,python);verify_result(b,snapshot,RULE,java)
            strip=lambda v:{k:x for k,x in v.items() if k not in ('engine_version','result_hash')}
            if strip(python)!=strip(java):raise LegalMathError('E_INTEGRITY',details='Generated Java differs from Python')
            results.append({'python':python,'java':java,'build_manifest':built['manifest']})
        return results

    def compare(self,left,right,packet):
        a,b=(bundle(r,packet,self.at) for r in (left,right))
        if left['formalization']['facts']==right['formalization']['facts']:
            return self._compare_bundles(a,b)
        found=discover(left,right)
        if found['mapping'] is None:
            return {'status':'INCOMPARABLE_FACT_BINDINGS','legal_source_commitment_resolved':False,
                    'fact_correspondence':found}
        return self._mapped_comparison(a,b,found['mapping'],found)

    def compare_conditional(self,left,right,packet,proposal):
        checked=validate_correspondence(proposal,left,right,packet)
        a,b=(bundle(r,packet,self.at) for r in (left,right))
        result=self._mapped_comparison(a,b,checked['mapping'],checked)
        # No caller, reviewer or matching formula can convert assumptions into
        # unconditional behavioral equivalence or legal authority.
        return {'status':'CONDITIONAL_ANALYSIS','encoded_comparison':result,
                'correspondence':checked,'source_packet_hash':digest(packet),
                'legal_source_commitment_resolved':False,'release_eligible':False,
                'review_required':True,'meaning_of_result':'Only under the stated fact and output-meaning assumptions'}

    def _mapped_comparison(self,a,b,mapping,evidence):
        normalized=rename_bundle(b,a,mapping)
        result=self._compare_bundles(a,normalized)
        result.update(fact_correspondence=evidence,left_bundle_hash=digest(a),right_bundle_hash=digest(b),
                      normalized_right_bundle_hash=digest(normalized))
        if result['status']=='DIFFERENT':
            left_snapshot=result['snapshot'];right_snapshot=translate_snapshot(left_snapshot,mapping)
            original=self.replay([a],left_snapshot)+self.replay([b],right_snapshot)
            if [project(r['python']) for r in original]!=[project(r['python']) for r in result['replays']]:
                raise LegalMathError('E_INTEGRITY',details='Renamed comparison differs from original rules')
            result['replays']=original
            result['original_snapshots']={'left':left_snapshot,'right':right_snapshot}
        return result

    def _compare_bundles(self,a,b):
        evidence={'legal_source_commitment_resolved':False,'target':'status/type/value',
                  'left_bundle_hash':digest(a),'right_bundle_hash':digest(b)}
        domain=self.domain
        if domain is not None:
            evidence['domain_origin']='CALLER_DECLARED'
        elif all(f['type']=='bool' for f in a['facts']):
            # No sampled numerical bounds: T/F/U covers the valid non-conflicting
            # Boolean inputs of this fragment. It says nothing about legal meaning
            # or whether every combination is feasible in a bank's business data.
            domain={f['name']:{'states':['T','F','U']} for f in a['facts']}
            evidence['domain_origin']='COMPLETE_DECLARED_BOOLEAN_STATE_SPACE'
        if domain is not None:
            evidence['domain']=domain
            built=self.build(a)
            result=smt_compare(a,b,RULE,domain,self.at,self.at,java_jar=built['jar'],jdk=self.jdk)
            evidence['solver']=result
            if result['status']=='COUNTEREXAMPLE':
                return {**evidence,'status':'DIFFERENT','snapshot':result['snapshot'],
                    'replays':self.replay([a,b],result['snapshot'])}
            if result['status']=='NO_COUNTEREXAMPLE_IN_DECLARED_DOMAIN':
                return {**evidence,'status':'EQUIVALENT_WITHIN_DOMAIN'}
            if result['status']=='INCONSISTENT_DOMAIN':return {**evidence,'status':'INCONSISTENT_DOMAIN'}
            if self.domain is not None:
                # The generic probes do not enforce caller restrictions. A
                # witness outside those restrictions would answer another question.
                return {**evidence,'status':result['status'],'reason':result.get('reason'),
                        'method':'DECLARED_DOMAIN_NO_UNBOUNDED_FALLBACK','probes':0,
                        'equivalence_established':False}
        examined=0
        for snapshot in snapshots([a,b],self.at):
            examined+=1
            results=[evaluate(v,snapshot,RULE,self.at,self.at) for v in (a,b)]
            if project(results[0])!=project(results[1]):
                return {**evidence,'status':'DIFFERENT','method':'FINITE_BOUNDARY_PROBE',
                    'snapshot':snapshot,'probes':examined,'replays':self.replay([a,b],snapshot)}
        return {**evidence,'status':'NO_DIFFERENCE_IN_FINITE_PROBES','probes':examined,
                'equivalence_established':False}
