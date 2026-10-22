"""Bounded review of retained Note1 introduction and annual income Notes5–10."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True
from scripts.prospectus_annual_basis_source import AUTH,SOURCE,PDF,read,save,sha
from legalmath.prospectus.execution_authority import Authority
WORK=ROOT/'.localresources/prospectus-preparation/annual-income'
PLAN='docs/plans/prospectus-annual-income-source-review-2026-10-22.md'
PAGES=(97,120,121,122)


def check_costs():
    prior=read(AUTH/'reviews/annual-remaining-443/post-record.json')['costs']
    seconds=sum(read(p)['seconds'] for p in WORK.glob('render-*.json'))
    seconds+=read(WORK/'preparation.json')['seconds']
    size=sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file())
    extra=sum(p.stat().st_size for p in [ROOT/PLAN,Path(__file__),AUTH/'reviews/annual-remaining-443/post-record.json',AUTH/'continuation-reviews/after-443.json'])
    assert seconds<50 and prior['cumulative_charged_seconds']+seconds<3360
    assert size+extra<8*1024**2 and prior['cumulative_bytes']+size+extra+2*1024**2<760*1024**2
    return {'new_seconds':seconds,'new_bytes':size+extra,'cumulative_charged_seconds':prior['cumulative_charged_seconds']+seconds}


def prepare():
    start=time.monotonic()
    assert not WORK.exists()
    a=Authority(ROOT)
    assert a.spec()[0]['revision']==443
    post=read(AUTH/'reviews/annual-remaining-443/post-record.json')
    assert post['event']['kind']=='RECORD' and a.retained_evidence_valid(post['event'])
    p1=SOURCE/'attempt-002/original-P1.json.gz'
    assert sha(p1)=='a40cb25513d12a49535157c5f4e675249acec32bbbe8c87f93f46adc2d75706f'
    assert sha(PDF)=='f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'
    us=[u for u in read(p1)['payload']['graph']['units'] if u['document']=='bes-2010-en' and u['page'] in PAGES]
    save(WORK/'source-units.json.gz',us)
    (WORK/'source.txt').write_text('\n'.join(u['id']+' '+u['raw'] for u in us)+'\n')
    save(WORK/'preparation.json',{'source':str(p1.relative_to(ROOT)),'source_sha256':sha(p1),'pdf_sha256':sha(PDF),
        'seconds':time.monotonic()-start,'cpu_gpu':'CPU_ONLY; no GPU imports','prior_record':post['event']['sha256'],
        'plan':PLAN,'plan_sha256':sha(ROOT/PLAN),'method_sha256':sha(Path(__file__)),'command':sys.argv})
    return {'status':'PREPARED','units':len(us),'costs':check_costs()}


def render(page):
    assert page in PAGES and sha(PDF)==read(WORK/'preparation.json')['pdf_sha256']
    prefix=WORK/('page-'+str(page))
    assert not prefix.with_suffix('.png').exists()
    binary=shutil.which('pdftoppm')
    assert binary
    cmd=[binary,'-f',str(page),'-l',str(page),'-scale-to','2000','-singlefile','-png',str(PDF),str(prefix)]
    start=time.monotonic()
    with (WORK/('render-'+str(page)+'.log')).open('x') as log:
        try:
            code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=10,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'}).returncode
        except subprocess.TimeoutExpired:
            code=-1
    save(WORK/('render-'+str(page)+'.json'),{'argv':cmd,'exit_code':code,'seconds':time.monotonic()-start,
        'image_sha256':sha(prefix.with_suffix('.png')) if prefix.with_suffix('.png').exists() else None,
        'renderer_sha256':sha(Path(binary)),'source_sha256':sha(PDF),'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    assert code==0,'Retain failure; no unchanged retry'
    return {'status':'PASS','page':page,'costs':check_costs()}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','render'])
    p.add_argument('--page',type=int)
    args=p.parse_args()
    print(json.dumps(prepare() if args.action=='prepare' else render(args.page)),flush=True)
