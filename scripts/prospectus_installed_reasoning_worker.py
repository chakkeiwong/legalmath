"""One isolated installed reasoning stage; no model or native subprocesses."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True


def main():
    root, attempt, target = (Path(p).resolve() for p in sys.argv[1:4])
    stage = sys.argv[4]
    expected = json.loads((attempt / 'source-package.json').read_text())
    package = target / 'legalmath'
    actual = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if not sys.flags.isolated or actual != expected:
        raise ValueError('Exact installed package and isolated Python required')
    guard = {'blocked': 0}
    def audit(event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty',
                'os.exec', 'os.posix_spawn', 'os.spawn', 'pty.spawn'}:
            guard['blocked'] += 1
            raise RuntimeError('Installed reasoning forbids process/network activity')
    sys.addaudithook(audit)
    sys.path.insert(0, str(target))
    import legalmath
    sys.path.insert(0, str(root))
    from scripts.prospectus_component_installed_worker import identity
    from scripts.prospectus_installed_reasoning_evidence import evaluate
    sys.path[:] = [p for p in sys.path if Path(p or '.').resolve() != root / 'src']
    identity(package, expected, dict(sys.modules))
    tick = time.monotonic()
    details = evaluate(root, attempt / 'installed-results', stage)
    if guard['blocked']:
        raise ValueError('Forbidden installed action attempted')
    proof = {'stage': stage, 'isolated': sys.flags.isolated, 'python': sys.executable,
             'prefix': sys.prefix, 'sys_path': sys.path, 'guard': guard,
             'modules': identity(package, expected, dict(sys.modules)), 'package_files': len(expected),
             'seconds': time.monotonic() - tick, 'details': details}
    with (attempt / 'stages' / stage / 'installed-proof.json').open('x') as stream:
        json.dump(proof, stream, sort_keys=True, indent=2)
    print(json.dumps({'stage': stage, 'status': 'PASS', 'package_files': len(expected)}))


if __name__ == '__main__':
    main()
