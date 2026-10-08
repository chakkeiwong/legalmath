"""Extend current recovery catalogues; keep all old rows and original products."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import subprocess

root=Path(__file__).resolve().parents[4]
base=root/'docs/implementation/prospectus-adoption'
out=Path(__file__).resolve().parent
out.mkdir(exist_ok=True)

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def pack(path,directory):
    identity=sha(path)
    directory.mkdir(exist_ok=True)
    packed=directory/(identity+'.gz')
    if not packed.exists():
        with path.open('rb') as source,packed.open('wb') as target:
            with gzip.GzipFile(filename='',fileobj=target,mode='wb',mtime=0) as encoded:
                shutil.copyfileobj(source,encoded)
    with gzip.open(packed,'rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==identity
    assert sha(path)==identity
    return packed

changes=[]
catalogue=base/'checkpoint/manifest.json'
original=catalogue.read_bytes()
with (out/'checkpoint-manifest-before.json').open('xb') as stream:
    stream.write(original)
manifest=json.loads(original)
known={r['path'] for r in manifest['files']}
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
additions=[]
for name in untracked:
    if not name: continue
    path=root/name
    if (not path.is_relative_to(base) and not path.is_relative_to(out.parent)) or name in known or path.stat().st_size<manifest['threshold_bytes']: continue
    packed=pack(path,base/'checkpoint')
    additions.append({'path':name,'sha256':sha(path),'bytes':path.stat().st_size,
        'archive':str(packed.relative_to(root)),'archive_sha256':sha(packed),'archive_bytes':packed.stat().st_size})
manifest['files'].extend(additions)
save(catalogue,manifest)
ignore=root/'.gitignore'
old_ignore=ignore.read_text()
new_lines=['/'+r['path'] for r in additions if '/'+r['path'] not in old_ignore.splitlines()]
if new_lines:
    ignore.write_text(old_ignore.rstrip()+'\n\n# BASF reference repair: exact large products retained in adoption checkpoint/manifest.json.\n'+'\n'.join(new_lines)+'\n')
changes.append({'catalogue':str(catalogue.relative_to(root)),'before_sha256':hashlib.sha256(original).hexdigest(),
    'after_sha256':sha(catalogue),'added':additions})

catalogue=base/'snapshot-manifest.json'
original=catalogue.read_bytes()
with (out/'snapshot-manifest-before.json').open('xb') as stream:
    stream.write(original)
manifest=json.loads(original)
known={r['sha256'] for r in manifest['files']}
sources={}
for record in (base/'phases').glob('*/attempt-*/read-context.json'):
    for row in json.loads(record.read_text())['records']:
        if row['kind'] in ('file','external-file') and row['sha256']:
            sources.setdefault(row['sha256'],set()).add(row['name'])
additions=[]
for path in sorted((base/'snapshots').iterdir()):
    if path.name.startswith('.') or path.name in known:continue
    identity=sha(path)
    assert identity==path.name
    candidates=sorted(sources.get(identity,[]))
    usable=[name for name in candidates if not Path(name).is_absolute() and (root/name).is_file() and sha(root/name)==identity]
    row={'snapshot':str(path.relative_to(root)),'sha256':identity,'bytes':path.stat().st_size,'observed_sources':candidates}
    if usable:
        row.update(kind='retained-file',source=usable[0])
    else:
        packed=pack(path,base/'snapshot-archive')
        row.update(kind='archived',archive=str(packed.relative_to(root)),archive_sha256=sha(packed))
    additions.append(row)
manifest['files'].extend(additions)
# A previously retained source may have changed in this continuation. Keep its
# snapshot identity and old row in the before-copy, and archive its exact bytes.
rebound=[]
for row in manifest['files']:
    if row['kind']=='retained-file':
        source=root/row['source']
        if not source.is_file() or sha(source)!=row['sha256']:
            snapshot=root/row['snapshot']
            if sha(snapshot)!=row['sha256']:raise ValueError('Changed historical snapshot')
            packed=pack(snapshot,base/'snapshot-archive')
            rebound.append({'before':dict(row),'archive':str(packed.relative_to(root))})
            row.pop('source')
            row.update(kind='archived',archive=str(packed.relative_to(root)),archive_sha256=sha(packed))
# Check recovery sources themselves, not only currently present snapshots.
for row in manifest['files']:
    if row['kind']=='archived':
        packed=root/row['archive']
        assert sha(packed)==row['archive_sha256']
        with gzip.open(packed,'rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
    else:
        source=Path(row['source'])
        if not source.is_absolute():source=root/source
        assert sha(source)==row['sha256']
save(catalogue,manifest)
save(out/'rebound-snapshot-sources.json',rebound)
changes.append({'catalogue':str(catalogue.relative_to(root)),'before_sha256':hashlib.sha256(original).hexdigest(),
    'after_sha256':sha(catalogue),'added':additions})
save(out/'receipt.json',{'status':'PASS','originals':'PRESERVED','historical_rows':'PRESERVED; old catalogues copied here',
    'changes':changes,'restore_commands':['python3 -m scripts.archive_prospectus_successor_checkpoint restore --campaign adoption',
        'python3 -m scripts.archive_prospectus_successor_checkpoint restore-snapshots --campaign adoption']})
print(json.dumps({'status':'PASS','added_large_products':len(changes[0]['added']),'added_snapshots':len(changes[1]['added']),'archived_changed_historical_sources':len(rebound)}))
