"""Bounded existing-source verification and renders for remaining annual policies."""
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
WORK=ROOT/'.localresources/prospectus-preparation/annual-remaining'
PLAN='docs/plans/prospectus-annual-remaining-policies-2026-10-22.md'


def prepare():
    start=time.monotonic()
    assert not WORK.exists()
    a=Authority(ROOT)
    assert a.spec()[0]['revision']==442
    post=read(AUTH/'reviews/annual-policy-receipt-442/post-record.json')
    assert post['event']['kind']=='RECORD' and a.retained_evidence_valid(post['event'])
    rejected=read(SOURCE/'attempt-018/evidence-reference.json')['original_event']
    assert a.retained_evidence_valid(rejected)
    p1=SOURCE/'attempt-002/original-P1.json.gz'
    assert sha(p1)==read(SOURCE/'attempt-003/candidate-P1-reference.json.gz')['file_sha256']
    assert sha(PDF)=='f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25'
    units=[u for u in read(p1)['payload']['graph']['units'] if u['document']=='bes-2010-en' and 108<=u['page']<=114]
    save(WORK/'source-units.json.gz',units)
    save(WORK/'preparation.json',{'source':str(p1.relative_to(ROOT)),'source_sha256':sha(p1),'pdf_sha256':sha(PDF),
        'prior_charged_seconds':post['costs']['cumulative_charged_seconds'],'prior_bytes':post['costs']['cumulative_bytes'],
        'plan':PLAN,'plan_sha256':sha(ROOT/PLAN),'method_sha256':sha(Path(__file__)),
        'seconds':time.monotonic()-start,'cpu_gpu':'CPU_ONLY; no GPU imports','prior_record':post['event']['sha256']})
    return {'status':'PREPARED','units':len(units)}


def render(page):
    assert page in range(109,115)
    assert sha(PDF)==read(WORK/'preparation.json')['pdf_sha256']
    binary=shutil.which('pdftoppm')
    assert binary
    prefix=WORK/('page-'+str(page))
    assert not prefix.with_suffix('.png').exists()
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
    assert code==0,'Retain failed render; no unchanged retry'
    return {'status':'PASS','page':page}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','render'])
    p.add_argument('--page',type=int)
    args=p.parse_args()
    print(json.dumps(prepare() if args.action=='prepare' else render(args.page)),flush=True)
