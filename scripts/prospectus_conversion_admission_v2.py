"""Retain bounded actual-consumer evidence for conversion admission repair."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
import gzip
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash
from legalmath.prospectus.successor import cases,financial_profiles,service
from legalmath.prospectus import closure_mechanisms as kernels

PLAN='docs/plans/prospectus-conversion-admission-repair-2026-10-17.md'
REVIEW=ROOT/REL/'reviews/conversion-admission'
HERE=ROOT/REL/'attempts/entitlement/attempt-006'
FAILED=ROOT/REL/'attempts/entitlement/attempt-005'
REPAIR=ROOT/REL/'reviews/conversion-admission-r2'
CARRIER=ROOT/REL/'attempts/law-applicability/attempt-006'
PRODUCTION=['src/legalmath/prospectus/closure_mechanisms.py',
            'src/legalmath/prospectus/successor/financial_profiles.py',
            'src/legalmath/prospectus/master_mechanisms.py']
TESTS=['tests/prospectus_successor/test_conversion_admission.py',
       'tests/prospectus/test_closure_mechanisms.py',
       'tests/prospectus_successor/test_repairs.py',
       'tests/prospectus_successor/test_closure_finance.py']


def require(value,reason):
    if not value: raise ValueError(reason)


def load(path):
    raw=path.read_bytes(); return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def compressed(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),mtime=0))


def methods():
    paths={p for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths|={ROOT/p for p in TESTS}|{Path(__file__)}
    return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted(paths)}


def seconds():
    return read(REVIEW/'reproduction.json')['seconds']+sum(read(p)['seconds'] for folder in (FAILED,HERE) for p in (folder/'stages').glob('*/result.json'))


def storage():
    paths=[REVIEW,REPAIR,FAILED,HERE,ROOT/PLAN,Path(__file__),ROOT/TESTS[0],
        ROOT/'scripts/prospectus_conversion_admission.py',
        ROOT/'docs/plans/prospectus-conversion-admission-2026-10-17.md',
        ROOT/REL/'proposals/conversion-admission-226.json',
        ROOT/REL/'proposals/conversion-admission-226-review.json',
        ROOT/REL/'revisions/0226.json',ROOT/REL/'closure-routes-2026-10-17-conversion-repair-226.json',
        ROOT/REL/'proposals/conversion-admission-225.json',
        ROOT/REL/'proposals/conversion-admission-225-review.json',
        ROOT/REL/'revisions/0225.json',ROOT/REL/'closure-routes-2026-10-17-after-interval-225.json']
    files=set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    return sum(p.stat().st_size for p in files if p.exists())


def authenticate():
    auth=Authority(ROOT); program,tasks,_=auth.spec(); admission=read(HERE/'admission.json')
    require(program['revision']==226 and admission['binding']==auth.binding(tasks['entitlement']),'Admission drift')
    for n,h in read(REVIEW/'source-bindings.json').items():
        require(file_hash(ROOT/n)==h,'Original source changed')
    for n,h in read(FAILED/'outputs.json').items():
        require(file_hash(FAILED/n)==h,'Failed005 evidence changed')
    require(file_hash(ROOT/'scripts/prospectus_conversion_admission.py')==file_hash(FAILED/'methods/scripts/prospectus_conversion_admission.py'),'Original runner changed')
    current=methods(); before=read(REVIEW/'before-methods.json')
    require({n for n in current if n.startswith('src/')}==set(before),'Production file set changed')
    require(sorted(n for n,h in before.items() if current[n]!=h)==sorted(PRODUCTION),'Production edit exceeds reviewed scope')
    pin=HERE/'repaired-methods.json'
    if pin.exists(): require(read(pin)==current,'Repaired method changed')
    else:
        write(pin,current,exclusive=True)
        for n in [*PRODUCTION,*TESTS,str(Path(__file__).relative_to(ROOT))]:
            target=HERE/'methods'/n;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as stream:stream.write((ROOT/n).read_bytes())
    require(storage()+1024**2<48*1024**2 and seconds()<300,'Cumulative resource bound')
    return admission


def tests():
    argv=[sys.executable,'-c',
        'import sys; sys.path[:0]=[sys.argv[1],sys.argv[2]]; import pytest; raise SystemExit(pytest.main(sys.argv[3:]))',
        str(ROOT/'src'),str(ROOT),'-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')]
    write(HERE/'test-command.json',{'argv':argv},exclusive=True)
    with (HERE/'tests.stdout').open('xb') as out,(HERE/'tests.stderr').open('xb') as err:
        result=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err,timeout=50,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    require(result.returncode==0,'Focused regression failure; inspect retained logs')
    xml=ET.parse(HERE/'tests.xml').getroot()
    counts={k:sum(int(s.get(k,'0')) for s in xml.iter('testsuite')) for k in ['tests','failures','errors','skipped']}
    require(counts['tests']>0 and not any(counts[k] for k in ['failures','errors','skipped']),'Invalid test record')
    return counts


def assess(s):
    return financial_profiles.assess({'instrument_id':s['issue_id'],
        'documents':[{'sha256':s['source_sha256']}]},s)


def independent(s,result):
    """Independent decimal price construction and integer rational share allocation."""
    key=s['issue_id']; q=result['value']['calculation']
    if not q.get('conversion'): return {'scope':'NO_CONVERSION_BRANCH; no share allocation'}
    if key.startswith('bbva'):
        candidates=[Decimal(s['adjusted_floor_price']),Decimal(s['nominal_share_value'])]
        if s['listed']:
            mean=sum(Decimal(v) for v in s['five_eligible_closing_prices'])/Decimal(5)
            candidates.append(mean.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
        price=Fraction(max(candidates)); amount='liquidation_preference'; pricekey='conversion_price'
    else:
        rate=Decimal(s['usd_per_sek'])
        candidates=[Decimal(s['adjusted_floor_usd']),Decimal(s['quota_value_sek'])*rate]
        if s['listed']:candidates.append(Decimal(s['reviewed_current_market_price_sek'])*rate)
        price=Fraction(max(candidates)); amount='principal';pricekey='conversion_price_usd'
    require(Fraction(q[pricekey])==price,'Independent price mismatch')
    groups={}
    for row in s['holdings']:
        groups[row['legal_holder_id']]=groups.get(row['legal_holder_id'],Fraction())+Fraction(row[amount])
    expected=[]
    for holder,total in sorted(groups.items()):
        shares=(total.numerator*price.denominator)//(total.denominator*price.numerator)
        expected.append({'holder':holder,'amount':str(total),'shares':shares,'fraction':str(total/price-shares)})
    actual=[{'holder':r['legal_holder_id'],'amount':r['amount'],'shares':r['shares'],
             'fraction':r['fraction_without_cash_compensation']} for r in q['holder_entitlements']]
    require(actual==expected,'Independent holder/share mismatch')
    return {'price':str(price),'holders':expected,'method':'Decimal source quantities; integer division after exact holder sum'}


def consumers():
    baseline=read(REVIEW/'baseline.json'); current=cases.financial_cases(ROOT)
    require(current==baseline,'Complete original valid financial cases changed')
    write(HERE/'original-valid.json',current,exclusive=True)
    rows=[];full=[]
    for case in current:
        if case['instrument_id'].startswith('deutsche'): continue
        original=case['question']['value']['inputs']; issue=original['issue_id']
        for variant in ('active','inactive','unlisted','separate-holders'):
            s=deepcopy(original)
            if variant=='inactive':
                s.update(issuer_determined_cet1_ratio='0.1',capital_reduction=False) if issue.startswith('bbva') else s.update(bank_cet1_ratio='0.1',group_cet1_ratio='0.1')
            if variant=='unlisted':
                s['listed']=False
                if issue.startswith('bbva'):s['five_eligible_closing_prices']=[]
                else:del s['reviewed_current_market_price_sek']
            if variant=='separate-holders':
                s['holdings'][0]['legal_holder_id']=' holder '
                s['holdings'][1]['legal_holder_id']='holder'
            result=assess(s);require(result['status']=='CONDITIONAL','Valid control refused')
            oracle=independent(s,result)
            full.append({'issue':issue,'variant':variant,'input':s,'result':result,'oracle':oracle})
        fields=['adjusted_floor_price','nominal_share_value'] if issue.startswith('bbva') else [
            'usd_per_sek','adjusted_floor_usd','quota_value_sek','reviewed_current_market_price_sek']
        for field in fields:
            for active in (False,True):
                for bad in ['0','-1',True,'1/0']:
                    s=deepcopy(original)
                    if not active:
                        s.update(issuer_determined_cet1_ratio='0.1',capital_reduction=False) if issue.startswith('bbva') else s.update(bank_cet1_ratio='0.1',group_cet1_ratio='0.1')
                    s[field]=bad; result=assess(s)
                    require(result['status']=='UNSUPPORTED','Invalid conversion domain admitted')
                    rows.append({'issue':issue,'field':field,'active':active,'bad':bad,'input':s,'result':result})
        rate_fields=['issuer_determined_cet1_ratio'] if issue.startswith('bbva') else ['bank_cet1_ratio','group_cet1_ratio']
        for active in (False,True):
            extra=[(field,None) for field in rate_fields]+[('holdings', 'liquidation_preference' if issue.startswith('bbva') else 'principal')]
            if issue.startswith('bbva'):extra.append(('five_eligible_closing_prices',0))
            for field,nested in extra:
                s=deepcopy(original)
                if not active:
                    s.update(issuer_determined_cet1_ratio='0.1',capital_reduction=False) if issue.startswith('bbva') else s.update(bank_cet1_ratio='0.1',group_cet1_ratio='0.1')
                if field=='holdings':s[field][0][nested]='1/0'
                elif nested is not None:s[field][nested]='1/0'
                else:s[field]='1/0'
                result=assess(s);require(result['status']=='UNSUPPORTED','Rational denominator crash or acceptance')
                rows.append({'issue':issue,'field':field,'nested':nested,'active':active,'bad':'1/0','input':s,'result':result})
        for field in ('legal_holder_id','registration_name'):
            for active in (False,True):
                for bad in ['', ' ', '\t\n', '\u00a0']:
                    s=deepcopy(original)
                    if not active:
                        s.update(issuer_determined_cet1_ratio='0.1',capital_reduction=False) if issue.startswith('bbva') else s.update(bank_cet1_ratio='0.1',group_cet1_ratio='0.1')
                    s['holdings'][0][field]=bad;result=assess(s)
                    require(result['status']=='UNSUPPORTED','Blank conversion identity admitted')
                    rows.append({'issue':issue,'field':field,'active':active,'bad':bad,'input':s,'result':result})
    # Recreate the original validator for a known-bad integration control.
    ns={'__name__':'legalmath.prospectus.successor._old_financial_profiles',
        '__package__':'legalmath.prospectus.successor'}
    exec(compile((REVIEW/'before'/PRODUCTION[1]).read_text(),str(REVIEW/'before'/PRODUCTION[1]),'exec'),ns)
    old_validate=financial_profiles.validate_scenario
    bad=deepcopy(next(r for r in read(REVIEW/'reproduction.json')['cases'] if 'inactive' in r)['inactive']['input'])
    try:
        financial_profiles.validate_scenario=ns['validate_scenario']
        require(assess(bad)['status']=='CONDITIONAL','Known-bad validator did not recreate original failure')
    finally:financial_profiles.validate_scenario=old_validate
    # Exercise the same secondary financial_cases route used by jobs.p5.
    products=load(CARRIER/'common-products.json.gz');products['P4']=load(CARRIER/'open-P4.json.gz')
    prior=service.consume(products,ROOT,mode='current')
    products['P5']=service.financial_product(products['P1'],products['P2'],products['P3'],cases=current)
    answer=service.consume(products,ROOT,mode='current')
    require(answer['financial_cases']==baseline and answer['questions']==prior['questions'],'Valid secondary report altered unrelated questions')
    compressed(HERE/'valid-report.json.gz',{'P5':products['P5'],'answer':answer})
    negative=deepcopy(baseline)
    for item in negative:
        if item['instrument_id'].startswith('deutsche'):continue
        s=deepcopy(item['question']['value']['inputs']);s['holdings'][0]['legal_holder_id']=' '
        actual=cases.financial_cases(ROOT,{item['instrument_id']:s})[0]
        item.clear();item.update(actual)
    products['P5']=service.financial_product(products['P1'],products['P2'],products['P3'],cases=negative)
    rejected_report=service.consume(products,ROOT,mode='current')
    require(rejected_report['financial_cases']==negative and rejected_report['questions']==prior['questions'],'Refusal report lost evidence or altered carrier')
    require(all(r['question']['status']=='UNSUPPORTED' for r in negative if not r['instrument_id'].startswith('deutsche')),'Secondary report hid refusal')
    compressed(HERE/'refusal-report.json.gz',{'P5':products['P5'],'answer':rejected_report})
    compressed(HERE/'valid-controls.json.gz',full); compressed(HERE/'adverse-controls.json.gz',rows)
    return {'original_complete_equal':3,'valid_exact_controls':len(full),'malformed_refusals':len(rows),
        'secondary_reports':2,'known_bad_validator_detected':True,
        'no_direct_original_P1_to_P6_claim':True}


def seal():
    require(all(read(HERE/'stages'/s/'result.json')['status']=='PASS' for s in ('tests','consumers')),'Missing required stage')
    return read(HERE/'stages/consumers/result.json')['detail']


def main():
    stage=sys.argv[1];require(stage in {'tests','consumers','seal'},'Unknown stage')
    folder=HERE/'stages'/stage
    write(folder/'started.json',{'command':['.venv/bin/python','scripts/prospectus_conversion_admission_v2.py',stage],
        'at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'},exclusive=True)
    signal.alarm(60);start=time.monotonic()
    try:
        admission=authenticate(); detail=globals()[stage]()
        require(methods()==read(HERE/'repaired-methods.json'),'Methods changed during stage')
        require(seconds()+time.monotonic()-start<300 and storage()+1024**2<48*1024**2,'Resource ceiling')
        result={'status':'PASS','seconds':time.monotonic()-start,'detail':detail}
    except Exception as exc:
        write(folder/'result.json',{'status':'FAIL','seconds':time.monotonic()-start,'error':type(exc).__name__+': '+str(exc)},exclusive=True)
        raise
    write(folder/'result.json',result,exclusive=True)
    if stage=='seal':
        require((HERE/'RESULT.md').is_file(),'Detailed result required')
        write(HERE/'run-manifest.json',{'git_commit':admission['git_commit'],'plan':PLAN,
            'result':str((HERE/'RESULT.md').relative_to(ROOT)),'python':sys.version,'interpreter':sys.executable,
            'environment':'Existing .venv; current worktree src pinned','cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
            'random_seeds':'N/A deterministic','sources':read(REVIEW/'source-bindings.json'),
            'methods':'repaired-methods.json','failed_predecessor':str(FAILED.relative_to(ROOT)),
            'failed_outputs_sha256':file_hash(FAILED/'outputs.json'),'commands':[read(p) for p in sorted((HERE/'stages').glob('*/started.json'))],
            'stages':{p.parent.name:read(p) for p in (HERE/'stages').glob('*/result.json')},
            'known_seconds_including_preparation':seconds(),'historical_unmeasured_seconds':'UNKNOWN',
            'new_bytes_before_manifest':storage()},exclusive=True)
        write(HERE/'result.json',{'task':'entitlement','status':'PASS','whole_task_complete':False,
            'whole_program_complete':False,'scope':'CONVERSION_INPUT_ADMISSION_V2','summary':detail},exclusive=True)
        write(HERE/'outputs.json',{str(p.relative_to(HERE)):file_hash(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and p.name not in {'admission.json','outputs.json'} and '__pycache__' not in p.parts},exclusive=True)
    signal.alarm(0);print(json.dumps({'stage':stage,**result}))

if __name__=='__main__':main()
