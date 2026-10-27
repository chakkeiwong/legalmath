"""Inventory local evidence without publishing payloads or deleting original bytes."""
from pathlib import Path
import argparse
import collections
import gzip
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/implementation/legal-mission-control/checkpoint-2026-10-27'
LOCAL = ROOT / 'artifacts/legal-mission-control/2026-10-27/git-handoff'
NAMES = {'result.json', 'local-result.json', 'registration.json', 'authority.json',
         'finished.json', 'installed-verification.json', 'verification.json', 'README.md'}
FINAL = 'artifacts/legal-mission-control/2026-10-26/product-closure/followthrough/live-review-diagnostic/'
SELECTED = {FINAL + p for p in [
    'source-comparison-candidate/result.json', 'source-comparison-candidate/reviewed.patch',
    'final-local-dispositions/result.json', 'appendix-consumer-delivery/final-checkpoint/result.json',
    'closeout-audit/result.json', 'closeout-audit/reset-memo.md']}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def selected(name):
    p = Path(name)
    if not name.startswith(('artifacts/', '.localresources/', 'docs/testprospectus/')):
        return True
    if name in SELECTED:
        return True
    return (name.startswith('artifacts/legal-mission-control/2026-10-2')
            and len(p.parts) <= 5 and p.lstat().st_size < 131072
            and (p.suffix in {'.py', '.md'} or p.name in NAMES))

def inventory():
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    names = sorted(p for p in raw.decode().split('\0') if p)
    keep = [p for p in names if selected(p)]
    selected_set = set(keep)
    excluded = [p for p in names if p not in selected_set]
    (LOCAL / 'selected-paths.txt').write_text('\n'.join(keep) + '\n')
    (LOCAL / 'excluded-paths.txt').write_text('\n'.join(excluded) + '\n')
    target = OUT / 'local-evidence-inventory.jsonl.gz'
    if target.exists():
        raise ValueError('Inventory already retained; do not overwrite')
    counts, sizes, changed = collections.Counter(), collections.Counter(), []
    with target.open('xb') as rawout, gzip.GzipFile(filename='', fileobj=rawout, mode='wb', mtime=0) as out:
        for i, name in enumerate(excluded):
            path = ROOT / name
            before = path.lstat()
            row = {'path': name, 'bytes': before.st_size}
            if path.is_symlink():
                row.update(kind='symlink', target=os.readlink(path))
            elif path.is_dir():
                head = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                                      text=True, capture_output=True)
                row.update(kind='local-directory', git_head=head.stdout.strip() if head.returncode == 0 else None,
                           coverage='Directory retained locally; contents are not individually hashed by this inventory')
            else:
                row.update(kind='file', sha256=sha(path))
            after = path.lstat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                changed.append(name)
            group = '/'.join(Path(name).parts[:2])
            counts[group] += 1
            sizes[group] += before.st_size
            out.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
            if (i + 1) % 50000 == 0:
                print(json.dumps({'inventoried': i + 1}), flush=True)
    result = {'profile': 'local-only-evidence-inventory.v1', 'root': str(ROOT),
              'excluded_files': len(excluded), 'excluded_bytes': sum(sizes.values()),
              'selected_untracked_files': len(keep),
              'selected_bytes': sum((ROOT / p).lstat().st_size for p in keep),
              'groups': {p: {'files': counts[p], 'bytes': sizes[p]} for p in sorted(counts)},
              'inventory': str(target.relative_to(ROOT)), 'inventory_sha256': sha(target),
              'changed_during_inventory': changed, 'payloads_published': False,
              'original_files_deleted': False, 'remote_backup_complete': False}
    (OUT / 'retention.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if changed:
        raise ValueError('Local evidence changed while inventoried; review before claiming coherent retention')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inventory'])
    parser.parse_args()
    inventory()
