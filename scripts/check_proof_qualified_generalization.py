#!/usr/bin/env python3
"""Retain a bounded, machine-evaluated engineering campaign, without answer keys."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import time

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.qualification import assurance, prospective
from legalmath.translation.resources import preflight
from tests.catala.backend_support import JDK, TOOLCHAIN
from tests.translation.support import AT, snapshot
from tests.translation.v2_support import fixture_v2, as_model, library_fixture, structured_fixture


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def q(n,d=1):
    f=Fraction(n,d);return {'numerator':str(f.numerator),'denominator':str(f.denominator)}


def cases(model, values, at=AT):
    return [{'id':str(i),'snapshot':snapshot(model,v),'valid_at':at,'known_at':at} for i,v in enumerate(values)]


def programs(seed):
    rng=random.Random(seed)
    coefficients=[rng.randrange(-19,20) for _ in range(4)]
    outputs=[('result'+str(i),'integer','true',
        f'(if gate (+ (scale x {n} 1) (integer {i+11})) (- x (integer {i+11})))')
        for i,n in enumerate(coefficients)]
    def affine(threshold):
        return as_model(*fixture_v2([('x','integer'),('gate','bool')],
            outputs+[('threshold','bool','true',f'(> x (integer {threshold}))')],profile='complete.v1',
            text=f'Synthetic formal domain with generated integer expressions and threshold {threshold}.'))
    a=affine(100);b=affine(120)
    integer_values=[{'x':str(x),'gate':gate} for x,gate in
                    [(0,False),(100,True),(110,True),(120,False),(-10**40,True),(10**40,True)]]
    libraries=as_model(*library_fixture())
    library_values=[{'start':start,'offset':str(offset),'begin':str(begin),'end':str(end),
                     'x':q(rng.randrange(-100,100),7),'y':q(rng.randrange(-100,100),11)}
                    for start,offset,begin,end in [('2024-01-31',1,0,9),('2023-03-31',-1,5,2),
                                                  ('2000-02-29',12,-3,4),('9999-12-31',1,0,10001)]]
    rich=as_model(*structured_fixture());rich_values=[]
    for count in (0,1,5):
        entries=[{'active':bool(rng.randrange(2)),'amount':q(rng.randrange(-30,30),7)} for _ in range(count)]
        rich_values.append({'entry':{'active':True,'amount':q(5,3)},'entries':entries,
                            'rate':None if not count else {'present':q(-2,3)},
                            'choice':{'case':'Empty','value':None} if not count else {'case':'Fixed','value':q(4,7)}})
    return [('affine',a,cases(a,integer_values)),('amended',b,cases(b,integer_values)),
            ('libraries',libraries,cases(libraries,library_values)),('structured',rich,cases(rich,rich_values))]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True);parser.add_argument('--seed',type=int,default=2026092802)
    args=parser.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1];started=time.monotonic()
    method=assurance.method_manifest();data=programs(args.seed)
    manifest={'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'command':sys.argv,'python':sys.version,'executable':sys.executable,
              'cpu_gpu':'CPU-only; no GPU framework imported','seed':args.seed,
              'data':'Algorithmically generated formal-domain cases, not legal answer labels',
              'classification':'DEVELOPMENT_CHALLENGES; not prospective legal evidence',
              'plan':'docs/plans/proof-qualified-generalization.md',
              'result':str(out/'results.json'),'method_hash':digest(method),
              'generator_sha256':raw_digest(Path(__file__).read_bytes()),
              'selected':[{ 'id':name,'model_hash':digest(m),'cases_hash':digest(c),'cases':len(c)} for name,m,c in data]}
    write(out/'manifest-start.json',manifest);write(out/'method.json',method)
    rows=[]
    for name,m,c in data:
        print('Checking '+name,flush=True)
        try:
            result=assurance.run(m,c,out/name,JDK,toolchain=TOOLCHAIN)
            verified=assurance.verify(out/name,m,JDK,compiler=TOOLCHAIN['compiler'])
            rows.append({'id':name,'status':'CHECKED','report_hash':verified['report_hash'],'summary':result['summary']})
        except (LegalMathError,FileNotFoundError,subprocess.TimeoutExpired) as exc:
            rows.append({'id':name,'status':'FAILED','error':getattr(exc,'code',type(exc).__name__),
                         'detail':str(getattr(exc,'details',exc))})
    # Revision challenge: the old compiled qualification cannot answer the amendment.
    stale_rejected=False
    try:assurance.verify(out/'affine',data[1][1],JDK,compiler=TOOLCHAIN['compiler'])
    except LegalMathError as exc:stale_rejected=exc.code=='E_STALE_REVIEW'
    # Resource rejection stays visible. It is not relabeled successful abstention.
    large=deepcopy(data[0][1]);large['review'].update(origin='manual',reading=None)
    large['facts'].extend({'name':'unused'+str(i),'type':'integer','description':'Synthetic capacity probe'} for i in range(39))
    envelope=preflight(large);write(out/'resource-rejection.json',envelope)
    end=(datetime.now(timezone.utc)+timedelta(days=30)).isoformat().replace('+00:00','Z')
    window=prospective.freeze(out/'future-window',digest(method),['public-regulatory-amendments'],ends_at=end,
        development_sources=[assurance.identity(m)['source_hash'] for _,m,_ in data])
    future=prospective.report(out/'future-window',window['window_hash'],expected_head=window['window_hash'])
    write(out/'future-window-report.json',future)
    unchanged=method==assurance.method_manifest()
    result={'rows':rows,'selected_candidates':len(data),'retained_candidates':len(rows),
            'stale_amendment_rejected':stale_rejected,'resource_overflow_rejected':not envelope['supported'],
            'source_unchanged':unchanged,'future_publications_observed':0,
            'unknown_future_legal_generalization':'NOT_ESTABLISHED','human_quality_evidence':False,
            'status':'PASS' if unchanged and stale_rejected and not envelope['supported'] and all(r['status']=='CHECKED' for r in rows) else 'FAIL'}
    write(out/'results.json',result)
    write(out/'manifest.json',{**manifest,'wall_ms':round((time.monotonic()-started)*1000),'status':result['status'],
          'artifacts':{str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*'))
                       if p.is_file() and p.suffix in ('.json','.lean','.log') and p.name!='manifest.json'}})
    print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
