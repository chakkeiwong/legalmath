"""Isolated existing-wheel solver trial; no package or network changes."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True

def main():
    root, target, fixture, attempt = map(lambda p: Path(p).resolve(), sys.argv[1:5])
    expected = json.loads((attempt / 'source-package.json').read_text())
    package = target / 'legalmath'
    actual = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if actual != expected or not sys.flags.isolated:
        raise ValueError('Exact isolated installed package required')
    sys.path.insert(0, str(target))
    import legalmath
    sys.path.insert(0, str(root))
    from scripts.prospectus_component_installed_worker import identity
    from scripts.prospectus_solver_corpus import run, check_record
    identity(package, expected, sys.modules)
    guard = {'blocked': 0}
    def audit(event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.spawn', 'pty.spawn'}:
            guard['blocked'] += 1
            raise RuntimeError('No subprocess/network actions in installed solver trial')
    sys.addaudithook(audit)
    start = time.monotonic()
    record = run(root, fixture)
    checked = check_record(record)
    proof = {'isolated': sys.flags.isolated, 'python': sys.executable, 'prefix': sys.prefix,
        'modules': identity(package, expected, dict(sys.modules)), 'package_files': len(expected),
        'guard': guard, 'z3_version': record['z3_version']}
    import z3
    proof['z3_module'] = {'path': str(Path(z3.__file__).resolve()),
        'sha256': hashlib.sha256(Path(z3.__file__).read_bytes()).hexdigest()}
    if guard['blocked']:
        raise ValueError('Unexpected installed activity')
    with (attempt / 'installed-record.json.gz').open('xb') as stream:
        stream.write(gzip.compress(json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False).encode(), mtime=0))
    for name, value in [('installed-proof.json', proof), ('installed-checks.json', checked),
                        ('installed-result.json', {'status': 'PASS', 'seconds': time.monotonic()-start})]:
        with (attempt / name).open('x') as stream:
            json.dump(value, stream, sort_keys=True, indent=2)
    print(json.dumps({'status': 'PASS', 'installed': True, **checked}))

if __name__ == '__main__':
    main()
