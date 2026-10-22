"""Execute one finite component from an exact installed wheel target."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True


def identity(package, expected, modules):
    result = {}
    for name,module in modules.items():
        if name != 'legalmath' and not name.startswith('legalmath.'):
            continue
        raw = getattr(module,'__file__',None)
        if not raw: continue
        path = Path(raw).resolve()
        if not path.is_relative_to(package):
            raise ValueError('Production import outside installed target: '+name)
        rel = str(path.relative_to(package)); value = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected.get(rel) != value:
            raise ValueError('Loaded production bytes differ: '+name)
        result[name] = {'path':str(path),'sha256':value}
    if not result: raise ValueError('No installed production imports')
    return result


def main():
    root, attempt, target = [Path(p).resolve() for p in sys.argv[1:4]]
    kind = sys.argv[4]
    expected = json.loads((attempt/'source-package.json').read_text())
    package = target/'legalmath'
    actual = {str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != expected or not sys.flags.isolated:
        raise ValueError('Isolated exact installed package required')
    sys.path.insert(0,str(target))
    import legalmath
    identity(package,expected,sys.modules)
    sys.path.insert(0,str(root))  # validation scripts only; legalmath is already bound
    from scripts.prospectus_component_evidence import evaluate, load
    packet_path = attempt/'controls-packet.json.gz'
    packet = load(packet_path) if packet_path.exists() else None
    guard = {'starts':0,'blocked':0}
    def audit(event,args):
        if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.fork','os.forkpty','os.exec','os.posix_spawn','os.spawn','pty.spawn'}:
            guard['blocked'] += 1
            raise RuntimeError('Installed component forbids process/network actions')
    sys.addaudithook(audit)
    start = time.monotonic(); result = evaluate(root,kind,packet)
    # A retained financial helper also pins its own command's source path.
    # legalmath's package path stayed installed; verify all loaded modules below.
    sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() != root/'src']
    proof = {'isolated':sys.flags.isolated,'python':sys.executable,'prefix':sys.prefix,'sys_path':sys.path,
        'modules':identity(package,expected,dict(sys.modules)),'package_files':len(expected),'process_guard':guard}
    if guard != {'starts':0,'blocked':0}: raise ValueError('Unexpected installed action')
    for name,value in [('installed-checks.json',result),('installed-proof.json',proof),
                       ('installed-result.json',{'status':'PASS','wall_seconds':time.monotonic()-start,'kind':kind})]:
        with (attempt/name).open('x') as stream: json.dump(value,stream,sort_keys=True,indent=2)
    print(json.dumps({'installed':kind,'status':'PASS','package_files':len(expected)}))


if __name__ == '__main__': main()
