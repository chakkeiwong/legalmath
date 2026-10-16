"""Restricted, source-bound Boolean AST adapter for the retained LE parser.

Explicit true/false predicates avoid negation-as-failure on missing client facts.
The parser's actual clauses are checked and interpreted, not merely printed.
"""
from itertools import product
from pathlib import Path
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.translation.expressions import expression
from legalmath.interpretation.assurance.semantics import check_quotes
from scripts.legal_gap_program import ROOT, RES, command, read, save, ref

PARSER = ROOT / 'artifacts/legal-tool-gap-validation/2026-10-08/G1/attempt-2/logical-english/patched-source'

PROLOG = r'''
:- op(800, fx, user:(<-)).
:- use_module(library(http/json)).
:- use_module(library(readutil)).
:- initialization(main, main).
atom_row(is_true(X), _{node:X,value:true}) :- atom(X), !.
atom_row(is_false(X), _{node:X,value:false}) :- atom(X), !.
body_rows(true, []) :- !.
body_rows((A,B), Rows) :- !, body_rows(A,RA), body_rows(B,RB), append(RA,RB,Rows).
body_rows(A, [R]) :- atom_row(A,R).
clause_row(if(_,H,B), _{head:HR,body:BR}) :- ground((H,B)), atom_row(H,HR), body_rows(B,BR).
prove(_,Facts,Goal,_) :- memberchk(Goal,Facts), !.
prove(Rules,Facts,Goal,Seen) :- \+ memberchk(Goal,Seen), member(if(_,Goal,Body),Rules),
    prove_body(Rules,Facts,Body,[Goal|Seen]).
prove_body(_,_,true,_) :- !.
prove_body(R,F,(A,B),S) :- !, prove_body(R,F,A,S), prove_body(R,F,B,S).
prove_body(R,F,G,S) :- prove(R,F,G,S).
fact(D, G) :- atom_string(N,D.node), (D.value == true -> G=is_true(N); G=is_false(N)).
value(R,F,N,V) :- (prove(R,F,is_true(N),[]) -> T=true;T=false),
    (prove(R,F,is_false(N),[]) -> B=true;B=false),
    (T==true,B==false -> V=true; T==false,B==true -> V=false; V=invalid).
run_case(R,Case,_{scope:S,result:V}) :- maplist(fact,Case,F), value(R,F,scope,S), value(R,F,result,V).
main :-
 current_prolog_flag(argv,[Module,Input,Cases,Output]), use_module(Module),
 read_file_to_string(Input,Text,[]), atom_string(Atom,Text), le_input:clear_errors,
 catch((le_input:text_to_logic(Atom,T) -> Parsed=true;Parsed=false,T=[]),
       E,(Parsed=false,T=[],term_string(E,Exception))),
 findall(S,(le_input:error_notice(A,B,C,D),term_string(error_notice(A,B,C,D),S)),Errors),
 include(is_clause,T,Rules),
 (maplist(clause_row,Rules,Rows) -> Supported=true; Supported=false,Rows=[]),
 open(Cases,read,In), json_read_dict(In,CasesList), close(In),
 (Parsed==true,Errors==[],Supported==true -> maplist(run_case(Rules),CasesList,Values);Values=[]),
 (var(Exception)->Exception="";true),
 open(Output,write,Out), json_write_dict(Out,_{parsed:Parsed,errors:Errors,exception:Exception,
     supported:Supported,rules:Rows,values:Values}), close(Out).
is_clause(if(_,_,_)).
'''

def identity():
    return {'profile': 'logical-english.boolean-explicit-truth.v1',
            'files': [ref(Path(__file__)), ref(RES / 'swipl/usr/bin/swipl')]
                     + [ref(p) for p in sorted(PARSER.glob('*.pl'))],
            'maximum_facts': 8, 'maximum_nodes': 128,
            'limit': 'Proposed Boolean conditional only; no source-equivalence or legal-warrant verdict.'}

def name(i):
    return 'node' + chr(97 + i // 26) + chr(97 + i % 26)

def compile_reading(packet, reading):
    check_quotes(reading['citations'], packet)
    formal = reading.get('formalization')
    if not formal: raise ValueError('UNFORMALIZED')
    if formal['result_type'] != 'bool' or any(f['type'] != 'bool' for f in formal['facts']):
        raise ValueError('NON_BOOLEAN_PROFILE')
    facts = formal['facts']
    if len(facts) > 8: raise ValueError('FACT_CAPACITY')
    ids = {u['unit_id'] for u in packet['units']}
    if len({f['name'] for f in facts}) != len(facts): raise ValueError('DUPLICATE_FACT')
    if any(not set(f['source_unit_ids']) <= ids for f in facts): raise ValueError('FOREIGN_FACT_SOURCE')
    names = {f['name']: 'fact' + chr(97 + i) for i, f in enumerate(facts)}
    rules = []; nodes = []
    def atom(n,v): return {'node': n, 'value': v}
    def rule(n,v,body): rules.append({'head': atom(n,v), 'body': body})
    def compile_node(node):
        if len(nodes) >= 128: raise ValueError('NODE_CAPACITY')
        n = name(len(nodes)); nodes.append(n)
        op = node['op']
        if op == 'literal' and node.get('type') == 'bool': rule(n,node['value'],[])
        elif op == 'fact':
            if node['name'] not in names: raise ValueError('UNDECLARED_FACT')
            for v in (True,False): rule(n,v,[atom(names[node['name']],v)])
        elif op == 'not':
            a = compile_node(node['arg'])
            for v in (True,False): rule(n,v,[atom(a,not v)])
        elif op in ('all','any'):
            children = [compile_node(a) for a in node['args']]
            joint = op == 'all'
            rule(n,joint,[atom(a,joint) for a in children])
            for a in children: rule(n,not joint,[atom(a,not joint)])
        elif op == 'if':
            c,t,f = [compile_node(node[k]) for k in ('condition','then','else')]
            for v in (True,False):
                rule(n,v,[atom(c,True),atom(t,v)]);rule(n,v,[atom(c,False),atom(f,v)])
        else: raise ValueError('UNSUPPORTED_OPERATOR:' + op)
        return n
    trees = {k: expression(formal[k],k) for k in ('scope','result')}
    for key, tree in trees.items():
        n=compile_node(tree)
        for v in (True,False): rule(key,v,[atom(n,v)])
    def phrase(a): return a['node'] + (' is true' if a['value'] else ' is false')
    sentences = [phrase(r['head']) + ('\n    if ' + '\n    and '.join(map(phrase,r['body'])) if r['body'] else '') + '.' for r in rules]
    text = ('the target language is: prolog.\nthe templates are:\n'
            '    *a condition* is true,\n    *a condition* is false.\n'
            'the knowledge base candidate includes:\n' + '\n'.join(sentences) + '\n')
    return {'text':text,'rules':rules,'facts':names,'trees':trees,
            'source_packet_hash':digest(packet),'reading_hash':digest(reading),
            'fact_definitions':facts,'citations':reading['citations'],
            'interpretation':{k:reading[k] for k in ('statement','distinction','assumptions','questions')}}

def evaluate(node, facts):
    op=node['op']
    if op=='literal': return node['value']
    if op=='fact': return facts[node['name']]
    if op=='not': return not evaluate(node['arg'],facts)
    if op=='all': return all(evaluate(a,facts) for a in node['args'])
    if op=='any': return any(evaluate(a,facts) for a in node['args'])
    if op=='if': return evaluate(node['then'] if evaluate(node['condition'],facts) else node['else'],facts)
    raise ValueError(op)

def conditional_values(rows, known):
    """Exact finite completions; unknown is never converted into false."""
    if any(type(v) is not bool for v in known.values()): raise ValueError('Known values must be Boolean')
    names=set(rows[0]['facts']) if rows else set()
    if not set(known)<=names: raise ValueError('Foreign known fact')
    selected=[r for r in rows if all(r['facts'][k]==v for k,v in known.items())]
    if not selected: raise ValueError('No compatible completion')
    return {k: next(iter(values)) if len(values:={r[k] for r in selected})==1 else 'UNKNOWN'
            for k in ('scope','result')}

def check(packet, candidates, work):
    rows=[]
    for cid,reading in candidates.items():
        try: compiled=compile_reading(packet,reading)
        except (ValueError,LegalMathError) as exc:
            rows.append({'candidate_id':cid,'reading_hash':digest(reading),'status':'UNSUPPORTED',
                         'reason':getattr(exc,'code',str(exc))});continue
        folder=work/digest(cid)[:20];folder.mkdir(parents=True,exist_ok=False)
        (folder/'candidate.le').write_text(compiled['text']);(folder/'adapter.pl').write_text(PROLOG)
        save(folder/'mapping.json',compiled)
        assignments=[dict(zip(compiled['facts'],v)) for v in product((False,True),repeat=len(compiled['facts']))]
        save(folder/'cases.json',[[{'node':compiled['facts'][k],'value':v} for k,v in a.items()] for a in assignments])
        command([RES/'swipl/usr/bin/swipl','-q','-f','none','-s',folder/'adapter.pl','--',
                 PARSER/'le_input.pl',folder/'candidate.le',folder/'cases.json',folder/'parsed.json'],folder,'parse',
                env={'SWI_HOME_DIR':str(RES/'swipl/usr/lib/swi-prolog'),'LD_LIBRARY_PATH':str(RES/'swipl/usr/lib')},timeout=40)
        parsed=read(folder/'parsed.json')
        expected=[{k:evaluate(t,a) for k,t in compiled['trees'].items()} for a in assignments]
        ok=(parsed['parsed'] and parsed['supported'] and not parsed['errors'] and not parsed['exception']
            and parsed['rules']==compiled['rules'] and parsed['values']==expected
            and not any(line.startswith('ERROR:') for line in (folder/'parse.log').read_text().splitlines()))
        truth=[{'facts':a,**v} for a,v in zip(assignments,parsed['values'])]
        save(folder/'conditional-values.json',truth)
        rows.append({'candidate_id':cid,'reading_hash':digest(reading),'status':'PASS' if ok else 'FAILED',
                     'exact_parsed_rules':parsed['rules']==compiled['rules'],'consequences_equal':parsed['values']==expected,
                     'unknown_inputs':conditional_values(truth,{}) if ok else None,
                     'mapping':ref(folder/'mapping.json'),'parsed':ref(folder/'parsed.json'),
                     'conditional_values':ref(folder/'conditional-values.json')})
    return {'status':'FAILED' if any(r['status']=='FAILED' for r in rows) else 'PASS' if any(r['status']=='PASS' for r in rows) else 'UNSUPPORTED',
            'tool':'Logical English','readings':rows,'candidate_bindings':{k:digest(v) for k,v in candidates.items()},
            'limit':'Exact proposed Boolean mapping and finite consequences only; source warrant and general English meaning are unassessed.'}
