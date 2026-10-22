"""Bounded actual service probe for an interim-review applicability bypass."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT),str(ROOT/'tests/prospectus_successor')]
sys.dont_write_bytecode=True
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.successor import service, report_scope
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_h1_current_acceptance import sha, require
from test_interim_review import TEXT, fixture, exact_span, products

OUT=ROOT/'.localresources/prospectus-preparation/interim-review-applicability'


def save(name,value):
    p=OUT/name; p.parent.mkdir(exist_ok=True,parents=True)
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
    if p.suffix=='.gz':raw=gzip.compress(raw,mtime=0)
    with p.open('xb') as stream:stream.write(raw)


def main():
    tick=time.monotonic()
    require(not (OUT/'probe.json').exists(),'No unchanged retry')
    original=ROOT/'docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-05/attempt-001/limited-review.txt'
    require(original.read_text().strip()==TEXT.strip(),'Fixture is not original retained review text')
    mutations={'exact':TEXT,
        'scope-qualification':TEXT.replace('\nConclusion\n','\nThis review excludes some financial statements.\nConclusion\n'),
        'conclusion-qualification':TEXT.replace('\nLisbon, 13','\nExcept for an unresolved qualification.\nLisbon, 13'),
        'changed-criteria':TEXT.replace('as required by the CVM;','under other criteria;')}
    rows=[]
    for mutation,text in mutations.items():
        with tempfile.TemporaryDirectory(prefix='prospectus-interim-probe-') as folder:
            p1,p2,scope,retained=fixture(Path(folder),text)
            selected=p2['payload']['source_report_readings']
            for category in ('LIMITED_FINANCIAL_REVIEW','STATUTORY_FINANCIAL_AUDIT'):
                supplied=deepcopy(scope);facts=supplied['reports'][0]['facts']
                facts['identity']['value']=category
                for field,value in report_scope.PROFILES[category].items():facts[field]['value']=value
                try:
                    answer=service.consume(products(p1,p2,supplied),Path(folder),mode='current',include_artifacts=True)
                    report=answer['source_reports'][0]
                    summary={'status':report['status'],'use_assessment':report['use_assessment'],'refused':False}
                    save(mutation+'-'+category+'.json.gz',{'source_variant':text,'scope':supplied,'selected':selected,'answer':answer})
                except ValueError as exc:
                    summary={'refused':True,'reason':str(exc)}
                    save(mutation+'-'+category+'.json.gz',{'source_variant':text,'scope':supplied,'selected':selected,'error':str(exc)})
                rows.append({'mutation':mutation,'category':category,**summary})
    false=[r for r in rows if r['category']=='STATUTORY_FINANCIAL_AUDIT' and not r['refused']
        and r['use_assessment']['financial_statement_audit_opinion']=='SUPPLIED_SOURCE_SUPPORT']
    save('probe.json',{'status':'DEFECT_REPRODUCED' if false else 'NO_DEFECT_REPRODUCED',
        'rows':rows,'false_support_cases':len(false),'seconds':time.monotonic()-tick,
        'original':{'path':str(original.relative_to(ROOT)),'sha256':sha(original)},
        'method':{'path':str(Path(__file__).relative_to(ROOT)),'sha256':sha(__file__)},
        'source_variants_are_original_documents':False})
    print(json.dumps({'status':'DEFECT_REPRODUCED' if false else 'NO_DEFECT_REPRODUCED','rows':rows}),flush=True)


if __name__=='__main__':main()
