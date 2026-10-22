"""Run inside the fresh installation; changes only private adverse fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus import native_profile as product
from legalmath.prospectus.successor import process_ledger


def main():
    base = Path(sys.argv[1]).resolve()
    environment = Path(sys.executable).parent.parent.resolve()
    assert Path(product.__file__).resolve().is_relative_to(environment)
    target = base / 'installed-controls'
    target.mkdir()
    root = Path(tempfile.mkdtemp(prefix='adverse-', dir=environment.parent))
    current = base / 'profile'
    pin = product.read(current / 'capture-result.json')['profile_sha256']
    rows = []
    tick = time.monotonic()
    def refuses(name, action):
        before = len(process_ledger.checked(base / 'native-ledger.json')['reservations'])
        try:
            action()
        except (ValueError, FileNotFoundError, FileExistsError) as error:
            rows.append({'case':name,'refused':True,'error':type(error).__name__+': '+str(error)})
        else:
            raise ValueError('Adverse installed input accepted: ' + name)
        assert len(process_ledger.checked(base / 'native-ledger.json')['reservations']) == before
    with process_ledger.observe(base / 'native-ledger.json'):
        refuses('wrong-profile-pin',lambda:product.load_profile(current,'0'*64))
        original = product.read(current / 'profile.json')
        for label in ('blob-changed','blob-missing','manifest-changed','method-changed','runtime-changed'):
            trial = root / label
            trial.mkdir()
            shutil.copyfile(current / 'profile.json',trial / 'profile.json')
            shutil.copytree(current / 'snapshot',trial / 'snapshot',copy_function=os.link)
            manifest = product.read(trial / 'snapshot/manifest.json')
            blob = trial / 'snapshot/blobs' / manifest['files'][0]['sha256']
            expected = pin
            if label.startswith('blob-'):
                blob.unlink()  # Unlink private hardlink before mutation.
                if label == 'blob-changed':
                    blob.write_bytes(b'changed private bytes')
            elif label == 'manifest-changed':
                path = trial / 'snapshot/manifest.json'
                path.unlink()
                manifest['directories'].append('/different')
                product.write(path,manifest)
            else:
                value = deepcopy(original)
                if label == 'method-changed':
                    value['methods']['prospectus/native_profile.py'] = '0'*64
                else:
                    value['trusted_runtime']['kernel_release'] = 'changed'
                (trial / 'profile.json').unlink()
                product.write(trial / 'profile.json',value)
                expected = product.digest(value)
            refuses(label,lambda trial=trial,expected=expected:product.load_profile(trial,expected))
        profile, manifest = product.load_profile(current,pin)
        request = product.read(base / 'fresh-request.json')
        request['bundle']['documents'][0]['sha256'] = '0'*64
        refuses('wrong-request-source',lambda:product.preflight(request,profile,manifest))
        refuses('duplicate-source-stage',lambda:product.stage(base/'fresh','source',
            lambda:(_ for _ in ()).throw(AssertionError('Duplicate ran')),new=True))
        failed = root / 'failed-predecessor'
        (failed/'stages/source').mkdir(parents=True)
        product.write(failed/'stages/source/result.json',{'status':'FAIL','files':{'P1.json.gz':'0'*64}})
        refuses('failed-predecessor',lambda:product.construct(failed))
        forged = root / 'forged-answer'
        shutil.copytree(base/'fresh',forged,copy_function=os.link)
        answer = product.read(forged/'answer.json.gz')
        answer['questions']['Q1']['status'] = 'FORGED'
        answer['report_sha256'] = product.digest({k:v for k,v in answer.items() if k!='report_sha256'})
        (forged/'answer.json.gz').unlink();product.write(forged/'answer.json.gz',answer)
        finish = product.read(forged/'stages/finish/result.json')
        finish['files']['answer.json.gz'] = product.file_hash(forged/'answer.json.gz')
        (forged/'stages/finish/result.json').unlink();product.write(forged/'stages/finish/result.json',finish)
        refuses('rehashed-forged-answer',lambda:product.verify(forged))
        missing = root / 'missing-stream'
        shutil.copytree(base/'retained',missing,copy_function=os.link)
        (missing/'native/1/stdout').unlink()
        refuses('missing-native-stream',lambda:product.verify(missing))
    product.write(target/'result.json',{'status':'PASS','cases':rows,'native_starts':0,
        'module_path':str(Path(product.__file__).resolve()),'python':sys.executable,
        'methods':product.methods(),'wall_seconds':time.monotonic()-tick,'private_fixtures':str(root)})
    print(json.dumps({'status':'PASS','controls':len(rows),'native_starts':0}))


if __name__ == '__main__':
    main()
