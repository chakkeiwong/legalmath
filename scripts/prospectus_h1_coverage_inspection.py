"""Read-only preparatory audit; references are not semantic acceptance."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-05'
PLAN='docs/plans/prospectus-h1-coverage-reconciliation-2026-10-22.md'
CONTEXT_KEYS={'source_groups','retained_context','source_context','source_scope'}


def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def references(value,path=(),context=False):
    if isinstance(value,dict):
        if isinstance(value.get('id'),str) and isinstance(value.get('quote'),str):
            yield value['id'],value['quote'],path,context
        for key,child in value.items():
            if key not in ('id','quote'):
                yield from references(child,(*path,str(key)),context or key in CONTEXT_KEYS)
    elif isinstance(value,list):
        for n,child in enumerate(value):
            yield from references(child,(*path,str(n)),context)


def inspect(attempt,suffix=''):
    tick=time.monotonic()
    folder=BASE/f'attempt-{attempt:03d}'
    if suffix not in ('','-repair001'):
        raise ValueError('Unreviewed diagnostic suffix')
    target=ROOT/f'.localresources/prospectus-preparation/h1-coverage-reconciliation/snapshot-{attempt:03d}{suffix}.json'
    if target.exists():
        raise ValueError('Retain prior diagnostic; do not overwrite')
    reading_path=folder/'reading.json.gz'
    graph_path=BASE/'attempt-007/products.json.gz'
    graph=read(graph_path)['P1']['payload']['graph']
    units=[u for u in graph['units'] if u['document']=='bes-interim-h1-2010']
    by_id={u['id']:u for u in units}
    if len(by_id)!=len(units):
        raise ValueError('Duplicate original identity')
    reading=read(reading_path)
    context_refs=defaultdict(list)
    noncontext_refs=defaultdict(list)
    mismatches=[]
    for uid,quote,path,context in references(reading):
        if uid not in by_id or quote!=by_id[uid]['raw']:
            mismatches.append({'id':uid,'path':list(path),'quote':quote})
        (context_refs if context else noncontext_refs)[uid].append('/'.join(path))
    if mismatches:
        raise ValueError('Source quote mismatch in preparatory audit')
    policy_units=sorted([u for u in units if 67<=u['page']<=93],
                        key=lambda u:(u['page'],u['order'],u['id']))
    headings=[]
    for u in policy_units:
        m=re.match(r'^2\.(\d{1,2})\.\s',u['raw'])
        if m:
            headings.append({'policy':'2.'+m[1],'id':u['id'],'page':u['page'],
                             'order':u['order'],'quote':u['raw']})
    page_rows=[]
    for page in range(51,174):
        items=[u for u in units if u['page']==page]
        page_rows.append({'page':page,'original_occurrences':len(items),
            'context_references':sum(u['id'] in context_refs for u in items),
            'noncontext_references':sum(u['id'] in noncontext_refs for u in items),
            'no_noncontext_reference':[u for u in items if u['id'] not in noncontext_refs]})
    outcome={'status':'INSPECTION_RETAINED','snapshot_attempt':attempt,
        'plan':PLAN,'reading':{'path':str(reading_path.relative_to(ROOT)),'sha256':sha(reading_path)},
        'original_graph':{'path':str(graph_path.relative_to(ROOT)),'sha256':sha(graph_path)},
        'wall_seconds':time.monotonic()-tick,
        'question':'Which original occurrences have explicit references outside context containers?',
        'interpretation_limits':[
            'Reference presence is not semantic correctness or completeness.',
            'Missing references can include metadata or alternate source-reference schemas.',
            'Current snapshot may not yet be sealed or recorded; inspect actual result before promotion.',
            'No source authority, legal incorporation or whole-task acceptance follows.'],
        'policy_headings':headings,'pages':page_rows,
        'noncontext_reference_paths':dict(noncontext_refs),
        'source_quote_mismatches':mismatches,
        'fields':list(reading),
        'source_context':reading.get('source_context'),
        'scope':reading.get('scope')}
    raw=(json.dumps(outcome,ensure_ascii=False,indent=2)+'\n').encode()
    if len(raw)>16*1024**2:
        raise ValueError('Preparatory output cap exceeded')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    missing=[u for u in policy_units if u['id'] not in noncontext_refs]
    return {'status':outcome['status'],'snapshot':attempt,'seconds':outcome['wall_seconds'],
        'bytes':len(raw),'policy_headings':headings,
        'policy_unreferenced_count':len(missing),
        'policy_unreferenced_raw_counts':dict(Counter(u['raw'] for u in missing)),
        'statement_reading_scope':reading.get('scope'),
        'output':str(target.relative_to(ROOT))}


if __name__=='__main__':
    # A genuine policy-scope passage is substantive; merely retained context is not.
    probe={'policy2_2':{'scope':{'sources':[{'id':'actual','quote':'scope passage'}]}},
           'source_groups':{'scope':[{'id':'context','quote':'retained context'}]}}
    assert {uid:context for uid,quote,path,context in references(probe)}=={'actual':False,'context':True}
    result=inspect(int(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else '')
    print(json.dumps(result,ensure_ascii=False))
