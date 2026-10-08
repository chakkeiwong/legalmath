"""Portable, bounded native packages verified against an external commitment."""
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from ...canonical import canonical, digest, loads, raw_digest
from ...sources.anchors import verify_span
from .contracts import fail
from .runtime import verify_build

MAX_BYTES = 32_000_000


def safe_name(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or p.is_absolute() or any(x in ('..', '.') for x in name.split('/')):
        fail('E_INTEGRITY', 'Unsafe package name')
    return p


def source_check(task, blobs):
    for unit in task['packet']['units']:
        span = unit['span']
        if span is None:
            if task['packet']['authority'] != 'SYNTHETIC_FIXTURE':
                fail('E_REFERENCE', 'Retained sources require byte commitments')
            continue
        try:
            text = blobs[span['text_sha256']].decode('utf-8')
            quote = verify_span(span, blobs[span['raw_sha256']], text)
        except (KeyError, UnicodeError):
            fail('E_REFERENCE', 'Missing retained source bytes')
        if quote != unit['text']:
            fail('E_REFERENCE', 'Source unit differs from its retained span')


def prepare(directory, destination, cases, report, *, sources=()):
    task, candidate, manifest = verify_build(directory)
    if report['build_hash'] != digest(manifest) or report['cases_hash'] != digest(cases):
        fail('E_INTEGRITY')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    blobs = {raw_digest(data): data for data in sources}
    source_check(task, blobs)
    names = ['build.json','task.json','candidate.json','plain.jar','instrumented.jar']
    names += list(manifest.get('dependencies', {}).get('interpreter_plugins', {}))
    for name in names:
        safe_name(name)
        p = destination / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((Path(directory) / name).read_bytes())
    for sha, data in blobs.items():
        p = destination / 'sources' / (sha + '.bin'); p.parent.mkdir(exist_ok=True); p.write_bytes(data)
    (destination / 'cases.json').write_bytes(canonical(cases))
    (destination / 'verification.json').write_bytes(canonical(report))
    review = {'build_hash':digest(manifest), 'task_hash':digest(task), 'candidate_hash':digest(candidate),
              'source_packet_hash':digest(task['packet']), 'interface_hash':digest({k:task[k] for k in ('types','inputs','outputs')}),
              'semantics_hash':manifest.get('semantics_hash'), 'verification_hash':digest(report),
              'cases_hash':digest(cases), 'source_blobs':sorted(blobs)}
    (destination / 'review.json').write_bytes(canonical(review))
    inventory = {p.relative_to(destination).as_posix():raw_digest(p.read_bytes()) for p in sorted(destination.rglob('*')) if p.is_file()}
    package = {'record_type':'NativeCatalaPackage','version':1,'files':inventory,'review_hash':digest(review)}
    (destination / 'package.json').write_bytes(canonical(package))
    verify(destination, expected_hash=digest(package))
    return digest(package)


def verify(directory, *, expected_hash):
    directory = Path(directory)
    if directory.is_symlink() or (directory/'package.json').is_symlink(): fail('E_INTEGRITY')
    if (directory/'package.json').stat().st_size>1_000_000: fail('E_RESOURCE_LIMIT')
    value = loads((directory / 'package.json').read_bytes())
    if set(value)!={'record_type','version','files','review_hash'} or value['record_type']!='NativeCatalaPackage' or value['version']!=1:
        fail('E_SCHEMA')
    if digest(value) != expected_hash:
        fail('E_HASH_MISMATCH', 'Package approval')
    files = value['files']
    if len(files)>256 or any(p.is_symlink() for p in directory.rglob('*')):
        fail('E_RESOURCE_LIMIT')
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != set(files) | {'package.json'}:
        fail('E_INTEGRITY', 'Package inventory')
    total = 0
    for name, sha in files.items():
        safe_name(name); total += (directory / name).stat().st_size
        if total>MAX_BYTES: fail('E_RESOURCE_LIMIT')
        data = (directory / name).read_bytes()
        if raw_digest(data)!=sha: fail('E_HASH_MISMATCH', 'Package file: '+name)
    review=loads((directory/'review.json').read_bytes())
    if digest(review)!=value['review_hash']: fail('E_INTEGRITY')
    task,candidate,manifest=verify_build(directory,expected_hash=review['build_hash'])
    if any(len(s)!=64 or any(c not in '0123456789abcdef' for c in s) for s in review['source_blobs']):fail('E_INTEGRITY')
    blobs={sha:(directory/'sources'/(sha+'.bin')).read_bytes() for sha in review['source_blobs']}
    derived={'build_hash':digest(manifest),'task_hash':digest(task),'candidate_hash':digest(candidate),
             'source_packet_hash':digest(task['packet']),'interface_hash':digest({k:task[k] for k in ('types','inputs','outputs')}),
             'semantics_hash':manifest.get('semantics_hash')}
    if any(review.get(k)!=v for k,v in derived.items()):fail('E_INTEGRITY','Review commitments')
    if any(raw_digest(data)!=sha for sha,data in blobs.items()):fail('E_INTEGRITY','Source blob commitment')
    source_check(task,blobs)
    report=loads((directory/'verification.json').read_bytes());cases=loads((directory/'cases.json').read_bytes())
    if (digest(report)!=review['verification_hash'] or digest(cases)!=review['cases_hash']
            or report['cases_hash']!=digest(cases) or report['build_hash']!=digest(manifest)
            or report['report_hash']!=digest({k:v for k,v in report.items() if k!='report_hash'})
            or not cases or report['passed']!=len(cases)):
        fail('E_INTEGRITY', 'Package verification')
    return review


def export(directory, archive, *, expected_hash):
    verify(directory,expected_hash=expected_hash)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
        for p in sorted(Path(directory).rglob('*')):
            if p.is_file(): z.writestr(p.relative_to(directory).as_posix(),p.read_bytes())


def install(archive, store, *, expected_hash):
    store=Path(store);store.mkdir(parents=True,exist_ok=True)
    # Validate commitment format before using it in a destination pathname.
    if len(expected_hash)!=64 or any(c not in '0123456789abcdef' for c in expected_hash):fail('E_SCHEMA')
    destination=store/expected_hash
    if destination.exists():
        verify(destination,expected_hash=expected_hash);return destination
    with tempfile.TemporaryDirectory(prefix='.install-',dir=store) as temp:
        stage=Path(temp)/'package';stage.mkdir()
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if len(infos)>256 or sum(i.file_size for i in infos)>MAX_BYTES:fail('E_RESOURCE_LIMIT')
            if len({i.filename for i in infos})!=len(infos):fail('E_INTEGRITY')
            for i in infos:
                safe_name(i.filename)
                if i.is_dir() or (i.external_attr>>16)&0o170000==0o120000:fail('E_INTEGRITY')
                p=stage/i.filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(i))
        verify(stage,expected_hash=expected_hash)
        stage.rename(destination)
    return destination
