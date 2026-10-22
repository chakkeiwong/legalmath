"""Isolated actual repair consumers; selected target must match every production byte."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES']='-1';sys.dont_write_bytecode=True

def main():
    root,attempt,target=map(lambda p:Path(p).resolve(),sys.argv[1:4]);mode=sys.argv[4]
    if mode not in {'source','installed'} or not sys.flags.isolated:raise ValueError('Explicit isolated mode required')
    config=json.loads((attempt/'config.json').read_text());package=target/'legalmath'
    expected=config['package']
    actual={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    if actual!=expected:raise ValueError('Complete package inventory differs')
    sys.path.insert(0,str(target));import legalmath
    sys.path.insert(0,str(root))
    from scripts.prospectus_component_installed_worker import identity
    from scripts.prospectus_input_repair_evidence import evaluate,validate_record,digest
    identity(package,expected,dict(sys.modules))
    guard={'blocked':0}
    def audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.exec','os.posix_spawn','os.spawn','pty.spawn'}:
            guard['blocked']+=1;raise RuntimeError('Repair evaluation forbids network/process actions')
    sys.addaudithook(audit);start=time.monotonic()
    record=evaluate(root,config);counts=validate_record(record)
    proof={'mode':mode,'isolated':sys.flags.isolated,'python':sys.executable,'prefix':sys.prefix,
        'target':str(target),'sys_path':sys.path,'modules':identity(package,expected,dict(sys.modules)),
        'package_files':len(expected),'guard':guard,'record_sha256':digest(record)}
    if guard['blocked']:raise ValueError('Unexpected guarded action')
    if mode=='installed' and str(root/'src') in sys.path:raise ValueError('Checkout source in installed search path')
    with (attempt/(mode+'-record.json.gz')).open('xb') as f:
        f.write(gzip.compress(json.dumps(record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
    for name,value in [('proof',proof),('result',{'status':'PASS','seconds':time.monotonic()-start,'counts':counts})]:
        with (attempt/(mode+'-'+name+'.json')).open('x') as f:json.dump(value,f,indent=2,sort_keys=True)
    print(json.dumps({'mode':mode,'status':'PASS','record_sha256':digest(record),'counts':counts}))

if __name__=='__main__':main()
