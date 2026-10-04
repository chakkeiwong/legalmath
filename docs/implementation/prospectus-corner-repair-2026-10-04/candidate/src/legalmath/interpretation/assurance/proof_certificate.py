"""Registered Lean proof for Boolean lowering, plus separate JVM enumeration.

The kernel checks a theorem about explicitly defined expression/rule semantics.
The independent input parser does not use the production expression compiler.
Concrete JVM correspondence is exhaustive only over the stated finite factual
states at one declared valid/known time. Neither result proves English meaning.
"""
from itertools import product
from pathlib import Path
import re
import subprocess
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ...ir.typecheck import validate_bundle
from ...java.manifest import build_candidate, run_java
from ..search.formal import RULE, project

PROFILE='lean.boolean-lowering.v1'
LEAN=Path('/home/chakwong/.elan/toolchains/leanprover--lean4---v4.20.0/bin/lean')
PRELUDE=Path(__file__).with_name('BooleanLowering.lean')


def parse_source(text,names):
    tokens=re.findall(r'\(|\)|[^\s()]+',text)
    if len(tokens)>2000 or not tokens:raise LegalMathError('E_UNSUPPORTED_PROFILE')
    index=0
    def consume(depth=0):
        nonlocal index
        if depth>40 or index>=len(tokens):raise LegalMathError('E_UNSUPPORTED_PROFILE')
        token=tokens[index];index+=1
        if token=='true':return ('yes',)
        if token=='false':return ('no',)
        if token in names:return ('fact',names.index(token))
        if token!='(' or index>=len(tokens):raise LegalMathError('E_UNSUPPORTED_PROFILE')
        op=tokens[index];index+=1;args=[]
        while index<len(tokens) and tokens[index]!=')':args.append(consume(depth+1))
        if index>=len(tokens):raise LegalMathError('E_UNSUPPORTED_PROFILE')
        index+=1
        if op=='not' and len(args)==1:return ('neg',args[0])
        if op=='if' and len(args)==3:return ('choose',*args)
        if op in ('and','or') and len(args)>=2:
            node=args[0]
            for arg in args[1:]:node=('conj' if op=='and' else 'disj',node,arg)
            return node
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    tree=consume()
    if index!=len(tokens):raise LegalMathError('E_UNSUPPORTED_PROFILE')
    return tree


def parse_ir(node,names,depth=0):
    if depth>40:raise LegalMathError('E_UNSUPPORTED_PROFILE')
    op=node['op']
    if op=='literal' and node['type']=='bool' and type(node['value']) is bool:return ('yes' if node['value'] else 'no',)
    if op=='fact' and node['name'] in names:return ('fact',names.index(node['name']))
    child=lambda n:parse_ir(n,names,depth+1)
    if op=='not':return ('neg',child(node['arg']))
    if op=='if':return ('choose',child(node['condition']),child(node['then']),child(node['else']))
    if op in ('all','any') and len(node['args'])>=2:
        values=list(map(child,node['args']));result=values[0]
        for a in values[1:]:result=('conj' if op=='all' else 'disj',result,a)
        return result
    raise LegalMathError('E_UNSUPPORTED_PROFILE',details='Certificate supports Boolean literals, facts, not, and, or, if only')


def lean_tree(tree):
    if tree[0]=='fact':return f'(Expr.fact {tree[1]})'
    if len(tree)==1:return 'Expr.'+tree[0]
    return '(Expr.'+tree[0]+' '+' '.join(lean_tree(x) for x in tree[1:])+')'


def inputs(reading,bundle):
    formal=reading.get('formalization')
    if not formal or formal['result_type']!='bool' or any(f['type']!='bool' for f in formal['facts']):
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    names=[f['name'] for f in formal['facts']]
    if len(names)>30 or len(names)!=len(set(names)) or validate_bundle(bundle) or len(bundle['rules'])!=1:
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if [(f['name'],f['type']) for f in bundle['facts']]!=[(n,'bool') for n in names]:
        raise LegalMathError('E_REFERENCE')
    rule=bundle['rules'][0]
    if rule['id']!=RULE or rule['type']!='bool':raise LegalMathError('E_UNSUPPORTED_PROFILE')
    source=(parse_source(formal['scope'],names),parse_source(formal['result'],names))
    lowered=(parse_ir(rule['scope'],names),parse_ir(rule['body'],names))
    return names,source,lowered


def proof_text(reading,bundle):
    names,source,lowered=inputs(reading,bundle)
    text=PRELUDE.read_text()+'\nopen LegalMathBoolean\n'
    for name,tree in zip(('sourceScope','sourceBody','loweredScope','loweredBody'),(*source,*lowered)):
        text+=f'def {name} : Expr := {lean_tree(tree)}\n'
    text+='theorem translation_preserved (facts : Nat → Tri) (conflict : Bool) :\n'
    text+='  decideRule facts conflict sourceScope sourceBody = decideRule facts conflict loweredScope loweredBody := by\n'
    text+='  apply congruence <;> rfl\n#print axioms translation_preserved\n'
    return text


def kernel(reading,bundle,work):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    text=proof_text(reading,bundle);p=work/'Translation.lean';p.write_text(text)
    result=subprocess.run([str(LEAN),str(p)],capture_output=True,text=True,timeout=60,cwd=work)
    (work/'lean.log').write_text(result.stdout+result.stderr)
    if result.returncode or 'sorry' in result.stdout or 'depends on axioms' in result.stdout:
        raise LegalMathError('E_INTEGRITY',details='Lean rejected the declared Boolean lowering or used an axiom')
    return {'tool_sha256':raw_digest(LEAN.read_bytes()),'prelude_sha256':raw_digest(PRELUDE.read_bytes()),
        'certificate_sha256':raw_digest(text.encode()),'log_sha256':raw_digest((result.stdout+result.stderr).encode()),
        'theorem':'translation_preserved','status':'KERNEL_CHECKED',
        'proposition':'For every valuation of declared Boolean facts in TRUE/FALSE/UNKNOWN, and either conflict flag, '
                      'the independently parsed formal proposal and lowered RuleIR have the same declared result semantics.',
        'assumptions':['Formal expression meaning is the semantics in BooleanLowering.lean.',
                       'Fact definitions and legal applicability are supplied premises.'],
        'excludes':['English interpretation','Java compiler correctness','evidence/history/time selection','arithmetic and dates']}


def tri_eval(tree,values):
    op=tree[0]
    if op=='fact':return values[tree[1]]
    if op in ('yes','no'):return op
    a=tri_eval(tree[1],values)
    if op=='neg':return {'yes':'no','no':'yes','unknown':'unknown'}[a]
    if op=='choose':return tri_eval(tree[2 if a=='yes' else 3],values) if a!='unknown' else 'unknown'
    b=tri_eval(tree[2],values)
    if op=='conj':return 'no' if 'no' in (a,b) else 'yes' if a==b=='yes' else 'unknown'
    return 'yes' if 'yes' in (a,b) else 'no' if a==b=='no' else 'unknown'


def enumerate_java(reading,bundle,at,work,jdk,*,maximum_cases=4096):
    names,source,_=inputs(reading,bundle)
    if type(maximum_cases)is not int or not 1<=maximum_cases<=4096:raise LegalMathError('E_RESOURCE_LIMIT')
    count=4**len(names)
    if count>maximum_cases:return {'status':'NOT_RUN_DOMAIN_LIMIT',
        'required_cases':str(count),'count_representation':'exact nonnegative integer string',
        'maximum_cases':maximum_cases}
    def used(tree):
        if tree[0]=='fact':return {tree[1]}
        return set().union(*(used(t) for t in tree[1:])) if len(tree)>1 else set()
    dependency_indices=used(source[0])|used(source[1])
    cases=[];expected=[];values_list=[]
    for i,values in enumerate(product(('yes','no','unknown','conflict'),repeat=len(names))):
        facts={}
        for name,v in zip(names,values):
            facts[name]=({'type':'bool','status':'unknown','reason':'MISSING'} if v=='unknown' else
                {'type':'bool','status':'conflict','evidence_ids':['first','second']} if v=='conflict' else
                {'type':'bool','status':'known','value':v=='yes','evidence_ids':['enumeration'],
                 'valid_from':at,'valid_until':None,'recorded_at':at})
        if any(values[i]=='conflict' for i in dependency_indices):status='CONFLICT'
        else:
            scope=tri_eval(source[0],values)
            status='OUT_OF_SCOPE' if scope=='no' else 'UNKNOWN' if scope=='unknown' else {
                'yes':'TRUE','no':'FALSE','unknown':'UNKNOWN'}[tri_eval(source[1],values)]
        row={'status':status,'type':'bool'}
        if status in ('TRUE','FALSE'):row['value']=status=='TRUE'
        expected.append(row);values_list.append(list(values))
        cases.append({'bundle':bundle,'snapshot':{'subject_id':'proof.'+str(i),'facts':facts},
                      'rule_id':RULE,'valid_at':at,'known_at':at,'mode':'draft'})
    build=build_candidate(bundle,Path(work)/'java',jdk)
    actual=run_java(build['jar'],cases,jdk,build['class_name'])
    rows=[{'values':v,'expected':e,'java':project(a)} for v,e,a in zip(values_list,expected,actual)]
    Path(work,'enumeration.json').write_bytes(canonical(rows))
    if any(r['expected']!=r['java'] for r in rows):
        raise LegalMathError('E_INTEGRITY',details='Generated Java differs from independent Boolean semantics')
    return {'status':'EXHAUSTIVE_FINITE_JAVA_CHECK','states':['TRUE','FALSE','UNKNOWN','CONFLICT'],
        'cases':count,'fact_order':names,'at':at,'jar_sha256':build['manifest']['jar_sha256'],
        'build':build,'rows_sha256':raw_digest(Path(work,'enumeration.json').read_bytes()),
        'scope':'All declared Boolean state assignments at the recorded assessment time; supplied evidence encoding.'}


def produce(reading,bundle,at,work,jdk):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    checked=kernel(reading,bundle,work)
    runtime=enumerate_java(reading,bundle,at,work,jdk)
    certificate={'profile':PROFILE,'reading_hash':digest(reading),'bundle_hash':digest(bundle),
                 'at':at,'kernel':checked,'runtime':runtime,'legal_correctness_established':False,'release_eligible':False}
    (work/'certificate.json').write_bytes(canonical(certificate));return certificate


def verify(certificate,reading,bundle,work,jdk):
    if (set(certificate)!={'profile','reading_hash','bundle_hash','at','kernel','runtime','legal_correctness_established','release_eligible'}
        or certificate['profile']!=PROFILE or certificate['reading_hash']!=digest(reading) or
        certificate['bundle_hash']!=digest(bundle) or certificate['legal_correctness_established'] is not False or
        certificate['release_eligible'] is not False):raise LegalMathError('E_INTEGRITY')
    # Regenerate fixed proof code and executable from data. Never execute a
    # certificate's supplied Lean script, path, subprocess command or JAR.
    rebuilt=produce(reading,bundle,certificate['at'],work,jdk)
    if certificate['kernel']!=rebuilt['kernel']:raise LegalMathError('E_INTEGRITY',details='Proof claim or kernel changed')
    old,new=certificate['runtime'],rebuilt['runtime']
    if {k:v for k,v in old.items() if k!='build'}!={k:v for k,v in new.items() if k!='build'}:
        raise LegalMathError('E_INTEGRITY',details='Runtime claim differs from independently executed check')
    if old.get('build',{}).get('manifest')!=new.get('build',{}).get('manifest'):
        raise LegalMathError('E_INTEGRITY',details='Executable commitment differs')
    return {'profile':PROFILE,'status':'VERIFIED','kernel':rebuilt['kernel']['status'],
            'runtime':new['status'],'legal_correctness_established':False,'release_eligible':False}
