"""Retain actual direct/selected coupon products, exact fractions and rejections."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'coupon-anchor'
PLAN=ROOT/'docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import read,write,digest
from legalmath.prospectus.successor.fixed_coupon import year_fraction
from scripts.prospectus_closure_fixtures import anchored_direct_fixture,anchored_selected_fixture

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if sys.flags.optimize:
        raise RuntimeError('Consumer validation requires Python assertions enabled')
    admission=read(PACKAGE/'execution-admission.json')
    assert admission['status']=='INTEGRATED_VALIDATION_PENDING'
    baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert baseline==admission['baseline_git_commit']
    number=1
    while (PACKAGE/f'attempt-{number:03d}').exists():
        number+=1
    folder=PACKAGE/f'attempt-{number:03d}'
    folder.mkdir()
    paths=[*sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py')),
        ROOT/'scripts/prospectus_closure_fixtures.py',ROOT/'tests/prospectus_successor/test_closure_coupon_anchor.py',
        Path(__file__),PLAN,PACKAGE/'execution-admission.json']
    method={str(p.relative_to(ROOT)):sha(p) for p in paths}
    command=[str(ROOT/'.venv/bin/python'),str(Path(__file__).relative_to(ROOT))]
    write(folder/'started.json',dict(command=command,baseline_git_commit=baseline,method=method,
        started_at=datetime.now(timezone.utc).isoformat(),timeout_seconds=120,evidence_limit_bytes=30_000_000,
        metadata_reserve_bytes=1_048_576,plan_file=str(PLAN.relative_to(ROOT)),
        cpu_gpu='CPU; GPU intentionally hidden',environment={'python':sys.executable,'version':sys.version,'CUDA_VISIBLE_DEVICES':'-1'},
        random_seeds='N/A; deterministic synthetic source/date controls',
        data_version='Source-bound synthetic August/February fixtures; per-case source hashes in requests',
        result_file=str((folder/'result.json').relative_to(ROOT))))
    tick=time.monotonic()
    try:
        outcomes={}
        for name,builder in (('direct',anchored_direct_fixture),('selected',anchored_selected_fixture)):
            case=folder/name
            case.mkdir()
            request=builder(case)
            write(case/'request.json',request)
            report=service.assess(request,case)
            write(case/'report.json',report)
            p1=service.source_product(request,case)
            p2=service.construction_product(p1,case)
            p3=service.interpretation_product(p1,p2)
            products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
            write(case/'products.json',products)
            assert service.consume(products,case,mode='current')['questions']==report['questions']
            answer=report['questions']['Q5']
            assert answer['status']=='CONDITIONAL'
            value=answer['value']
            calc=value['calculation'] if name=='selected' else value
            assert calc['profile']=='fixed-coupon.v2' and calc['coupon_anchor']=='2023-08-30'
            assert calc['day_fraction']=='1/2' and calc['payment_date']=='2024-08-30'
            assert [p['amount'] for p in calc['transfers']]==['5','5/2']
            assert calc['source_evidence']['coupon_anchor']['source']['quote']=='30 August 2023'
            assert calc['actual_event']=='NOT_ESTABLISHED' and not calc['full_settlement_supported']
            if name=='selected':
                assert value['regular_due_dates']==['2024-08-30','2025-02-28','2025-08-30']
                assert value['contract_terms']['version']=='admitted-coupon-terms.v2'
            negative={}
            for mutation in ('missing','changed','source') + (('override',) if name=='selected' else ()):
                changed=deepcopy(request)
                if name=='selected':
                    terms=changed['term_interpretations']['terms']
                    if mutation=='missing': terms.pop('coupon_anchor')
                    elif mutation=='changed': terms['coupon_anchor']['value']='2023-08-29'
                    elif mutation=='source': terms['coupon_anchor']['source']['quote']='29 August 2023'
                    else: changed['contract_calculation']['premises']['coupon_anchor']='2023-08-30'
                else:
                    scenario=changed['financial_scenario']
                    if mutation=='missing': scenario.pop('coupon_anchor')
                    elif mutation=='changed': scenario['coupon_anchor']='2023-08-29'
                    else: scenario['evidence']['coupon_anchor']['source']['quote']='29 August 2023'
                try:
                    actual=service.assess(changed,case)['questions']['Q5']
                except ValueError as exc:
                    assert name=='selected'
                    actual={'status':'REJECTED','reason':str(exc)}
                else:
                    assert name=='direct' and actual['status']=='UNSUPPORTED'
                negative[mutation]={'request_sha256':digest(changed),'actual':actual}
            write(case/'negative-controls.json',negative)
            outcomes[name]={'question_sha256':digest(answer),'source_graph_sha256':digest(report['source_map']),
                'day_fraction':calc['day_fraction'],'transfers':calc['transfers'],
                'regular_due_dates':value.get('regular_due_dates'),'negative_controls':negative,
                'current_consume_equal':True,'actual_event':'NOT_ESTABLISHED'}
        dates=['2023-08-30','2024-02-29','2024-08-30','2025-02-28']
        refs=[{'start':a,'end':b} for a,b in zip(dates,dates[1:])]
        oracles=[]
        for label,a,b,periods,expected in (
            ('second_regular',dates[1],dates[2],refs[1:2],'1/2'),
            ('two_period_union',dates[0],dates[2],refs[:2],'1'),
            ('short_first','2023-12-30',dates[1],refs[:1],'1/6'),
            ('long_first','2023-11-30',dates[2],refs[:2],'137/183'),
            ('short_final',dates[1],'2024-05-30',refs[1:2],'91/366'),
            ('long_final',dates[1],'2024-11-30',refs[1:],'137/182')):
            actual=str(year_fraction(a,b,'ACT_ACT_ICMA',references=periods,frequency=2,eom=False,coupon_anchor=dates[0]))
            assert actual==expected
            oracles.append(dict(case=label,start=a,end=b,references=periods,expected=expected,actual=actual))
        legacy=[]
        for row in oracles[:2]:
            try:
                year_fraction(row['start'],row['end'],'ACT_ACT_ICMA',references=row['references'],frequency=2,eom=False)
            except ValueError as exc:
                legacy.append({'case':row['case'],'error':str(exc),'expected_historical_rejection':True})
            else:
                raise ValueError('Legacy unanchored behavior changed')
        write(folder/'exact-fractions.json',{'oracles':oracles,'legacy':legacy})
        assert method=={str(p.relative_to(ROOT)):sha(p) for p in paths}
        assert time.monotonic()-tick<=120
        size=sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        assert size+1_048_576<=30_000_000
        result=dict(status='PASS',outcomes=outcomes,exact_fractions=oracles,legacy_rejections=legacy,
            evidence_payload_bytes=size,method_unchanged=True)
    except Exception as exc:
        result=dict(status='FAIL',error=type(exc).__name__+': '+str(exc))
    result.update(method=method,command=command,git_commit=baseline,plan_file=str(PLAN.relative_to(ROOT)),
        wall_seconds=time.monotonic()-tick,cpu_gpu='CPU; GPU intentionally hidden',seeds='N/A; deterministic',
        engineering_scope='Explicit hypothetical anchored ICMA calculation; full selected contract remains regular-only',
        actual_entitlement='NOT_ESTABLISHED',external_acceptance='NOT_ESTABLISHED')
    write(folder/'result.json',result)
    write(folder/'manifest.json',{'files':{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}})
    print(json.dumps({'directory':str(folder.relative_to(ROOT)),'status':result['status'],'error':result.get('error'),
        'wall_seconds':result['wall_seconds']}))
    if result['status']!='PASS':
        raise SystemExit(1)

if __name__=='__main__':
    main()
