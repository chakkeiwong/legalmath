"""Isolated localhost authoring restoration; no real users or external messages."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
RESOURCE=ROOT/'.localresources/prospectus/closure-runtime/authoring-profile'
BASE=ROOT/'docs/implementation/prospectus-integration-closure/authoring-restoration'
APP=ROOT/'.venv/bin/python'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


WORKER='''import json,os,sys
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='-1'
root,profile,folder=map(Path,sys.argv[1:])
sys.path[:0]=[str(root/'src'),str(root)]
from scripts import prospectus_inception as server
from playwright.sync_api import sync_playwright
server.LOCAL=profile
server.OUT=folder
server.JAVA=profile/'java/bin/java'
original=json.loads((root/'docs/implementation/prospectus-inception/toolchain.json').read_text())
(folder/'toolchain.json').write_text(json.dumps(original))
with server.server(folder,guests=False) as (client,runtime):
    created=client.request('POST',server.API+'/projects',fields={'name':'closure-restored-synthetic','title':'Closure restored synthetic project'})
    identifier=created['body']['id']
    exported=client.request('GET',server.API+f'/projects/{identifier}/export.zip',name='project.zip')
    assert len(exported)>0
    credentials=json.loads((runtime/'connection.json').read_text())
    with sync_playwright() as engine:
        browser=engine.chromium.launch(executable_path=str(profile/'browser/chrome-headless-shell'),
            headless=True,args=['--disable-gpu','--disable-background-networking'])
        context=browser.new_context()
        context.route('**/*',lambda route: route.continue_() if route.request.url.startswith(client.base+'/') else route.abort())
        page=context.new_page()
        page.set_default_timeout(30000)
        page.goto(client.base+'/login.html')
        page.locator('input[name="username"]').fill(credentials['user'])
        page.locator('input[name="password"]').fill(credentials['password'])
        page.locator('button[type="submit"],input[type="submit"]').first.click()
        page.wait_for_load_state('networkidle')
        if page.locator('input[name="username"]').is_visible():
            raise ValueError('Restored browser login did not succeed')
        body=page.locator('body').inner_text()
        if 'INCEpTION' not in body:
            raise ValueError('Restored browser did not reach application')
        page.screenshot(path=str(folder/'authenticated.png'))
        browser_version=browser.version
        browser.close()
    (folder/'consumer.json').write_text(json.dumps({'project_created':identifier,'export_bytes':len(exported),
        'browser_login':True,'browser_version':browser_version,'synthetic_account':True,'independent_review':False}))
'''


def main():
    if sys.executable != str(APP) and sys.prefix != str(APP.parent.parent):
        os.execve(str(APP),[str(APP),'-m','scripts.prospectus_closure_authoring_restore'],{**os.environ,'CUDA_VISIBLE_DEVICES':'-1'})
    folder=BASE/f'attempt-{len(list(BASE.glob("attempt-*")))+1:03d}'
    folder.mkdir(parents=True)
    started=time.monotonic()
    method=sha(__file__)
    commands=[]
    env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
    env.update(CUDA_VISIBLE_DEVICES='-1',PYTHONNOUSERSITE='1',PIP_NO_INDEX='1')
    write(folder/'started.json',{'method_sha256':method,'timeout_seconds':600,'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1'})
    def expired(signum,frame):
        raise TimeoutError('600-second authoring restoration budget exhausted')
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(600)
    def run(name,argv):
        try:
            result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,
                                  timeout=max(1,min(360,600-(time.monotonic()-started))))
        except subprocess.TimeoutExpired as exc:
            (folder/(name+'.log')).write_bytes((exc.stdout or b'')+(exc.stderr or b''))
            raise
        (folder/(name+'.log')).write_bytes(result.stdout+result.stderr)
        commands.append({'name':name,'argv':list(map(str,argv)),'returncode':result.returncode})
        if result.returncode:
            raise ValueError(name+' failed; inspect preserved log')
    try:
        toolchain=json.loads((ROOT/'docs/implementation/prospectus-inception/toolchain.json').read_text())
        java=Path(toolchain['java']['path']).parent.parent
        jar=ROOT/'.localresources/prospectus-inception/inception-app-webapp-38.0-standalone.jar'
        browser=ROOT.parents[1]/'.localresources/browser/chromium_headless_shell-1208/chrome-headless-shell-linux64'
        if sha(java/'bin/java')!=toolchain['java']['sha256'] or sha(jar)!=toolchain['jar']['sha256']:
            raise ValueError('Historical Java/JAR identities changed')
        inventory={}
        for prefix,base in [('java',java),('browser',browser)]:
            for path in sorted(base.rglob('*')):
                if path.is_file():
                    if path.is_symlink() and not path.resolve().is_relative_to(base.resolve()):
                        raise ValueError('External runtime symlink requires review')
                    inventory[prefix+'/'+str(path.relative_to(base))]=path
        inventory[jar.name]=jar
        versions={}
        for name in ('playwright','pyee','greenlet','typing_extensions'):
            distribution=importlib.metadata.distribution(name)
            versions[name]=distribution.version
            for relative in distribution.files:
                if '..' in relative.parts or '__pycache__' in relative.parts or relative.suffix=='.pyc':
                    continue
                path=Path(distribution.locate_file(relative))
                if path.is_file():
                    inventory['packages/'+str(relative)]=path
        if not any(name.startswith('browser/') for name in inventory):
            raise ValueError('Browser profile missing')
        records={name:{'sha256':sha(path),'bytes':path.stat().st_size} for name,path in inventory.items()}
        if sum(r['bytes'] for r in records.values())>2_000_000_000:
            raise ValueError('Authoring profile exceeds budget')
        manifest=RESOURCE/'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text())['files']!=records:
                raise ValueError('Existing profile differs; preserve it and review a replacement')
        else:
            RESOURCE.mkdir(parents=True,exist_ok=True)
            for name,path in inventory.items():
                target=RESOURCE/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,target)
            write(manifest,{'files':records,'versions':versions,'scope':'Same-host restored binary profile'})
        for name,row in records.items():
            if not (RESOURCE/name).is_file() or sha(RESOURCE/name)!=row['sha256']:
                raise ValueError('Profile bytes missing or changed')
        shutil.copy2(manifest,folder/'profile-manifest.json')
        with tempfile.TemporaryDirectory(prefix='closure-authoring-restored-') as temporary:
            base=Path(temporary)
            worker=base/'worker.py'
            worker.write_text(WORKER)
            for trial in range(2):
                runtime=base/'runtime'
                profile=base/'profile'
                run(f'venv-{trial}',[APP,'-m','venv',runtime])
                site=runtime/'lib/python3.11/site-packages'
                for name,row in records.items():
                    target=site/name[len('packages/'):] if name.startswith('packages/') else profile/name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(RESOURCE/name,target)
                    if sha(target)!=row['sha256']:
                        raise ValueError('Restored runtime bytes differ')
                run(f'dependencies-{trial}',[runtime/'bin/python','-m','pip','check'])
                out=folder/f'run-{trial}'
                out.mkdir()
                run(f'live-{trial}',[runtime/'bin/python','-I',worker,ROOT,profile,out])
                if not json.loads((out/'server-stop.json').read_text())['stopped']:
                    raise ValueError('Isolated server not stopped')
                if trial==0:
                    shutil.rmtree(runtime)
                    shutil.rmtree(profile)
        if sha(__file__)!=method:
            raise ValueError('Restoration method changed')
        result={'status':'PASS','restorations':2,'live_browser_login':True,'project_export':True,
            'independent_review':False,'new_cross_document_ui':'NOT_TESTED','host_libraries':'UNCONFINED',
            'versions':versions,'source_toolchain_sha256':sha(ROOT/'docs/implementation/prospectus-inception/toolchain.json')}
    except (Exception,KeyboardInterrupt) as exc:
        result={'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
    finally:
        signal.alarm(0)
    result.update(method_sha256=method,commands=commands,wall_seconds=time.monotonic()-started,
        plan='docs/plans/prospectus-authoring-restoration-2026-10-09.md',python=sys.version,
        cpu_gpu='CPU; CUDA_VISIBLE_DEVICES=-1',seeds='Synthetic randomized credentials; no statistical ranking',
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    write(folder/'result.json',result)
    write(folder/'manifest.json',{'files':{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}})
    print(json.dumps({'directory':str(folder.relative_to(ROOT)),'status':result['status'],'error':result.get('error')}))
    if result['status']!='PASS':
        raise SystemExit(1)


if __name__=='__main__':
    main()
