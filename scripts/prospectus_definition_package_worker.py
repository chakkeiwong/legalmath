"""Isolated installed-wheel checks; no source-checkout production imports."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.dont_write_bytecode=True


def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)


def write(path,value):
    data=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(data,mtime=0) if path.suffix=='.gz' else data)


def main():
    root,attempt,target=[Path(p).resolve() for p in sys.argv[1:4]]
    stage=sys.argv[4]
    assert sys.flags.isolated and stage in ('baseline','consume','control')
    assert target.is_relative_to(attempt)
    sys.path.insert(0,str(target))
    import legalmath
    package=target/'legalmath'
    assert Path(legalmath.__file__).resolve()==package/'__init__.py'
    expected=read(attempt/'package-files.json')
    installed={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    missing={n for n in expected if n.endswith('.json.gz')}
    assert len(missing)==2
    assert installed=={k:v for k,v in expected.items() if stage!='baseline' or k not in missing}
    forbidden={'subprocess.Popen','os.system','os.fork','os.forkpty','os.exec','os.posix_spawn','os.spawn'}
    def audit(event,args):
        if event.startswith('socket.') or event in forbidden:
            raise RuntimeError('Installed definition check forbids network/process execution')
    sys.addaudithook(audit)
    started=time.monotonic()
    from legalmath.prospectus.successor import service,definition_scopes,definition_applications
    from legalmath.prospectus.successor.contracts import digest
    result={'status':'PASS','stage':stage}
    if stage=='baseline':
        receipts=[]
        for module,name in ((definition_scopes,'definition_scopes_spec.json.gz'),
                            (definition_applications,'definition_applications_spec.json.gz')):
            try:
                module.specification()
            except FileNotFoundError as exc:
                assert Path(exc.filename).resolve()==package/'prospectus/successor'/name
                receipts.append({'module':module.__name__,'type':type(exc).__name__,'filename':str(exc.filename)})
            else:
                raise ValueError('Expected baseline package omission not reproduced')
        result['missing_profile_failures']=receipts
    else:
        p=read(attempt/'complete-products.json.gz')
        original=read(attempt/'complete-inputs.json')
        assert digest(p)==original['products_sha256']
        if stage=='consume':
            actual=service.consume(p,root,mode='frozen')
            write(attempt/'installed-answer.json.gz',actual)
            expected_answer=read(attempt/'complete-expected-answer.json.gz')
            assert digest(expected_answer)==original['answer_sha256']
            assert actual==expected_answer and digest(actual)==digest(expected_answer),'Installed complete answer differs'
            result.update(complete_answer_equal=True,actual_answer_sha256=digest(actual))
        else:
            semantic=deepcopy(p['P3']['payload'])
            rows={r['id']:r for r in semantic['definition_sources']['application_supplement']['applications']}
            rows['amount:21547']['meaning']=deepcopy(rows['amount:21403']['meaning'])
            forged=dict(p)
            bundle=p['P1']['payload']['request']['bundle']
            for key in ('P3','P4','P5'):
                inputs=dict(p[key]['inputs'])
                if key!='P3':
                    inputs['P3']=forged['P3']['sha256']
                forged[key]=service.seal(key,bundle,inputs,semantic if key=='P3' else p[key]['payload'])
                service.verify(forged[key],key,bundle,inputs)
            assert digest(forged)!=digest(p)
            write(attempt/'installed-forged-products.json.gz',forged)
            try:
                service.consume(forged,root,mode='frozen')
            except ValueError as exc:
                frames=[]
                tb=exc.__traceback__
                while tb:
                    frames.append({'module':tb.tb_frame.f_globals.get('__name__'),
                                   'function':tb.tb_frame.f_code.co_name})
                    tb=tb.tb_next
                assert str(exc)=='Consumed definition source differs from reconstruction'
                assert frames[-1]=={'module':'legalmath.prospectus.successor.definition_scopes','function':'verify_consumed'}
                result.update(actual_consumer_refusals=1,validly_resealed=True,
                              error=str(exc),origin=frames[-1],forged_products_sha256=digest(forged))
            else:
                raise ValueError('Installed consumer accepted changed make-whole meaning')
    modules={}
    for name,module in dict(sys.modules).items():
        if name=='legalmath' or name.startswith('legalmath.'):
            file=getattr(module,'__file__',None)
            if file:
                path=Path(file).resolve()
                assert path.is_relative_to(package),('Production import escaped installed package',name,str(path))
                relative=str(path.relative_to(package))
                assert hashlib.sha256(path.read_bytes()).hexdigest()==expected[relative]
                modules[name]=relative
    result.update(isolated=True,production_modules=modules,python=sys.executable,
                  cpu_gpu='CPU; GPU intentionally hidden',wall_seconds=time.monotonic()-started)
    write(attempt/('installed-'+stage+'-result.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k in
        ('status','stage','complete_answer_equal','actual_consumer_refusals','wall_seconds')}))


if __name__=='__main__':
    main()
