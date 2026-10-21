"""Read-only reconstruction diagnostic; no response dispatch or reservation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
sys.path.insert(0, str(Path.cwd()))
from scripts.legal_integration_master import TOKENIZER
from scripts.legal_integration_synthesis_resolution import ROOT, WORK, PREDECESSORS
from scripts.legal_integration_campaign import provider, tokenizer
from scripts.legal_integration_phased_live import configure
from scripts.legal_mission_execution import read, save, ref
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits
from legalmath.interpretation.assurance.bounded_product import BoundDispatch, NOTE
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import downstream_input, downstream_instructions
from legalmath.interpretation.assurance.phased.grouping import pack_items

q, level = sys.argv[1], int(sys.argv[2])
old = Path(PREDECESSORS[q])
envelope = read(ROOT/configure().ENVELOPE)
p = object.__new__(PhasedProduct)
p.directory = ROOT/WORK/'frontier-diagnostic'/q
p.root = ROOT
p.route = SimpleNamespace(envelope=envelope, input_hash=digest(envelope), limits=Limits(),
    records=read(ROOT/old/'source-store.json'),
    units={u['unit_id']:u for u in envelope['source_packet']['units']}, encode=tokenizer(ROOT/TOKENIZER))
p.downstream_input_profile = downstream_input.PROFILE
p.downstream_capacity_profile = None
p.dispatch = BoundDispatch(provider(), p.directory/'calls', p.route)
question = next(r for r in envelope['original_questions'] if r['question_id'] == q)
rows = read(ROOT/old/f'reduction-{q}-{level-1}.json')

def build(group):
    request = p.request('SYNTHESIZE_FINDINGS', question, p.source_records(group),
        payload=group, expected=[r['id'] for r in group])
    request['synthesis_scope'] = ('Produce a bounded source-supported synthesis for the original '
        'question, preserving operative conditions, exceptions, supported alternatives and '
        'unresolved dependencies. A single member is normalized once for subsequent combination. '
        'This summary is a proposal: complete original accounts and sources remain separately '
        'retained for independent answer review. Do not equate considered-ID coverage with '
        'semantic completeness. State any unfinished analysis explicitly in unresolved.')
    return request

def measure(group):
    try:
        return p.dispatch.measure(downstream_instructions.annotate(build(group)), NOTE)
    except LegalMathError as exc:
        if exc.code != 'E_RESOURCE_LIMIT': raise
        return None

def differences(a,b,path=''):
    if a == b: return []
    if isinstance(a,dict) and isinstance(b,dict):
        return [x for k in set(a)|set(b) for x in differences(a.get(k),b.get(k),path+'/'+str(k))]
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        return [z for i,(x,y) in enumerate(zip(a,b)) for z in differences(x,y,path+'/'+str(i))]
    return [dict(path=path,current=repr(a)[:140],historical=repr(b)[:140])]

historical = read(ROOT/old/f'reduction-{q}-{level}-membership.json')
contracts_only = len(sys.argv)>3 and sys.argv[3]=='contracts'
if contracts_only:
    by_id = {r['id']:r for r in rows}
    groups = [dict(members=[by_id[k] for k in members]) for members in historical['groups']]
    blocked = []
else:
    groups, blocked = pack_items(rows, measure, maximum_items=6)
report = dict(question=q, level=level, blocked=[r['id'] for r in blocked],
    current_members=[[r['id'] for r in g['members']] for g in groups],
    historical_members=historical['groups'], requests=[])
for i,g in enumerate(groups):
    key = f'reduce-{q}-{level}-{i}'
    saved = ROOT/old/'calls'/key/'request.json'
    if saved.exists():
        current, prior = build(g['members']),downstream_instructions.base_request(read(saved))
        delta = differences(current,prior)
        reorder_fields = ('records','verified_locator_bindings')
        report['requests'].append(dict(key=key,equal=not delta, differences=delta[:25],count=len(delta),
            exact_source_population=sorted(map(digest,current['records']))==sorted(map(digest,prior['records'])),
            exact_binding_population=sorted(map(digest,current['verified_locator_bindings']))==sorted(map(digest,prior['verified_locator_bindings'])),
            other_fields_equal={k:v for k,v in current.items() if k not in reorder_fields}==
                {k:v for k,v in prior.items() if k not in reorder_fields}))
save(ROOT/WORK/f'frontier-configured-{q}-{level}{"-contracts" if contracts_only else ""}.json',report)
print(__import__('json').dumps(dict(question=q,level=level,input_hash=p.route.input_hash,
    same_groups=report['current_members']==report['historical_members'],
    blocked=report['blocked'], requests=[{k:v for k,v in r.items() if k!='differences'}
        for r in report['requests'] if not r['equal']]),indent=2))
