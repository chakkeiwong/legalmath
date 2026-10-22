"""Retain the approved network fallback and its explicitly limited source result."""
from datetime import datetime, timezone
import json, re, sys, time
from scripts import prospectus_h43_accounting as r
from scripts.prospectus_statutory_sources_accounted import SourceHTML

NOTE = 'docs/implementation/prospectus-execution-authority/reviews/h43-accounting-320/NETWORK-ADJUSTMENT.md'
METHOD = 'scripts/prospectus_h43_finalize.py'
HERE = r.HERE


def frozen():
    r.source.PREP=r.PREP
    r.source.HERE=HERE
    r.source.frozen()


def resources(extra=0):
    result=r.costs(extra+2.111532+0.819984764)
    result['combined_bytes']+=(r.ROOT/METHOD).stat().st_size
    assert result['combined_bytes']<2044*1024**2
    assert result['combined_bytes']-r.read(r.PREP/'accounting-start.json')['prior']['combined_bytes']<40*1024**2
    result.update(new_GETs=2,maximum_new_GETs=2,
        measured_network_seconds=2.111532,
        network_measurement='curl time_total; approval and tool overhead UNKNOWN',
        failure_finalization_seconds=0.819984764)
    return result


def extract():
    folder=HERE/'requests/section'
    failed=r.read(folder/'receipt.json')
    assert failed['exit_code']==6 and failed['http_code']==0
    assert not (HERE/'requests/index').exists()
    raw=(folder/'trusted-body').read_bytes()
    assert len(raw)==5531 and b'charset=iso-8859-1' in raw
    decoded=raw.decode('iso-8859-1')
    assert decoded.encode('iso-8859-1')==raw
    parser=SourceHTML();parser.feed(decoded)
    text=re.sub(r'\n[ \t]*\n+','\n\n',''.join(parser.text))
    assert '§ 50' in text and 'Inlandsemittent' in text and 'zentrale europäische Zugangsportal' in text
    (folder/'trusted-text.txt').write_text(text,encoding='utf-8')
    r.save(folder/'trusted-receipt.json',{'status':'RESPONSE_RETAINED',
        'url':r.source.URLS['section'],'effective_url':r.source.URLS['section'],
        'http_code':200,'curl_exit_code':0,'redirects':0,'bytes':len(raw),
        'transfer_seconds':2.111532,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'source':'actual approved exec result; request preserved in NETWORK-ADJUSTMENT',
        'raw_sha256':r.sha(folder/'trusted-body'),'headers_sha256':r.sha(folder/'trusted-headers'),
        'text_sha256':r.sha(folder/'trusted-text.txt'),'declared_encoding':'iso-8859-1',
        'byte_roundtrip':True,'parser':'SourceHTML; blank-line normalization','links':parser.links,
        'historical_application_proved':False})
    r.save(HERE/'source-preparation-adjustment.json',{'review':NOTE,'review_sha256':r.sha(r.ROOT/NOTE),
        'method':METHOD,'method_sha256':r.sha(r.ROOT/METHOD),'two_requests_counted':True,
        'index_status':'NOT_RUN; second request used for mandatory trusted retry',
        'planned_utf8_extraction':'NOT_RUN; returned source declares ISO8859-1',
        'frozen_methods_changed':False,'product_integration':False})
    return {'status':'PASS','characters':len(text),'historical_application_proved':False}


def seal():
    note=HERE/'SOURCE-REVIEW.md'
    assert note.is_file() and note.stat().st_size>1000
    assert r.read(HERE/'stages/local/result.json')['status']=='PASS'
    assert r.read(HERE/'stages/trusted-extract/result.json')['status']=='PASS'
    receipt=r.read(HERE/'requests/section/trusted-receipt.json')
    assert r.sha(HERE/'requests/section/trusted-body')==receipt['raw_sha256']
    result={'status':'PASS','task':'basf-references','result_kind':'H43_CURRENT_SOURCE_PREPARATION',
        'original_task_complete':False,'production_changed':False,'historical_application_proved':False,
        'downstream_integration_complete':False,'source_review':r.rel(note),
        'source_review_sha256':r.sha(note),'resources':resources(),
        'next_action':'Integrate qualified H43 publication analysis while edition, issuer qualification, actual compliance and further sources remain open'}
    r.save(HERE/'result.json',result)
    r.save(HERE/'run-manifest.json',{'git_commit':r.read(HERE/'admission.json')['git_commit'],
        'commands':[r.read(p)['command'] for p in sorted(HERE.glob('stages/*/started.json'))],
        'trusted_acquisition':'Exact approved curl command in source-preparation-adjustment review',
        'environment':str(r.ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','data_version':receipt['raw_sha256'],
        'wall_time':resources(),'plan':r.PLAN,'adjustment':NOTE,'result':r.rel(HERE/'result.json')})
    return result


def main():
    stage=sys.argv[1];assert stage in ('trusted-extract','seal-source')
    frozen();resources()
    folder=HERE/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    r.save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_h43_finalize',stage],
        'method_sha256':r.sha(r.ROOT/METHOD),'review_sha256':r.sha(r.ROOT/NOTE),
        'started_at':datetime.now(timezone.utc).isoformat()})
    started=time.monotonic()
    result=extract() if stage=='trusted-extract' else seal()
    result['wall_seconds']=time.monotonic()-started;resources(result['wall_seconds'])
    r.save(folder/'result.json',result)
    if stage=='seal-source':
        r.save(HERE/'outputs.json',{str(p.relative_to(HERE)):r.sha(p)
            for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    print(json.dumps(result))


if __name__=='__main__':main()
