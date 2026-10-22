"""Retain complete pending-body intervals before implementing their review."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import signal
import sys
import time
from scripts import prospectus_basf_oci_source as base
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger

ROOT, BASE = base.ROOT, base.BASE
HERE = BASE/'basf-meanings/attempt-012'
PRIOR = BASE/'basf-references/attempt-004'
PLAN = 'docs/plans/prospectus-basf-body-coverage-2026-10-15.md'
base.HERE, base.PRIOR, base.PLAN = HERE, PRIOR, PLAN
save, load, bindings = base.save, base.load, base.bindings
IMAGE_ROOT = ROOT/'docs/implementation/prospectus-basf-scope-repair/source-review-001'


def prepare():
    protected = {str((PRIOR/p).relative_to(ROOT)): h for p,h in read(PRIOR/'outputs.json').items()}
    protected[str((PRIOR/'outputs.json').relative_to(ROOT))] = file_hash(PRIOR/'outputs.json')
    assert all(file_hash(ROOT/p)==h for p,h in protected.items())
    save('protected-inputs.json', protected)
    names = [Path(__file__), Path(base.__file__), ROOT/PLAN, HERE/'EXECUTION-AUDIT.md', Path(process_ledger.__file__)]
    save('source-methods.json', {str(p.relative_to(ROOT)):file_hash(p) for p in names})
    for p in names:
        target = HERE/'source-methods'/p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
    shutil.copyfile(PRIOR/'products.json.gz', HERE/'products.json.gz')
    p = load(HERE/'products.json.gz')
    prior = load(PRIOR/'hedge-consumer.json.gz')
    pending = prior['answer']['meaning_coverage']['selected_body_pending']
    graph = p['P1']['payload']['graph']
    raw = {u['id']:u for u in graph['units']}
    selected = {u['unit']:u for u in p['P2']['payload']['assembly']['units']}
    nodes = p['P3']['payload']['clauses']['nodes']
    rows = []
    for row in pending:
        key = row['unit']
        spans = [{'node':n['id'], **s, 'quote':selected[key]['text'][s['start']:s['end']]}
                 for n in nodes if n['effect']=='unknown' for s in n['spans'] if s['unit']==key]
        rows.append({'coverage':row, 'original':raw[key], 'selected':selected[key], 'unknown_spans':spans})
    assert len(rows)==77 and all(r['uncovered_characters']==0 for r in pending)
    save('pending-source-inventory.json', rows)
    doc = next(d for d in p['P1']['payload']['request']['bundle']['documents'] if d['id']=='basf-base-september-2022-exchange')
    assert file_hash(ROOT/doc['path'])==doc['sha256']
    pages = sorted({r['page'] for r in pending})
    images = [{'page':page, 'path':str((IMAGE_ROOT/('base-'+str(page)+'.png')).relative_to(ROOT)),
               'sha256':file_hash(IMAGE_ROOT/('base-'+str(page)+'.png'))} for page in pages]
    save('original-source.json', {'document':doc['id'],'path':doc['path'],'sha256':doc['sha256'],'images':images})
    process_ledger.create(HERE/'command-ledger.json',4,0,'Offline build,install,replay;one repair spare')
    return {'pending_units':len(rows),'unknown_spans':sum(len(r['unknown_spans']) for r in rows),
            'retained_original_pages':pages,'new_native_calls':0,'http_calls':0}


def main():
    assert sys.argv[1:]==['prepare']
    ad = bindings()
    folder = HERE/'invocations/prepare'
    folder.mkdir(parents=True,exist_ok=False)
    save('invocations/prepare/started.json', {'command':['.venv/bin/python','-m','scripts.prospectus_basf_body_source','prepare'],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic',
        'cpu_gpu':'CPU only;no framework imports'})
    tick = time.monotonic()
    def expire(signum,frame): raise TimeoutError('120-second source-stage bound')
    signal.signal(signal.SIGALRM,expire); signal.alarm(120)
    try:
        details=prepare();bindings()
        result={'status':'PASS','details':details,'wall_seconds':time.monotonic()-tick}
    except BaseException as error:
        save('invocations/prepare/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick})
        raise
    finally: signal.alarm(0)
    save('invocations/prepare/result.json',result);print(result)


if __name__=='__main__': main()
