"""Local byte identity and bounded official-source acquisition, without trust claims."""
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import hashlib
import sys
import time
from urllib.parse import urljoin, urlsplit

from ...canonical import digest, loads, raw_digest
from ...errors import LegalMathError
from .diversity import save

PROFILE = 'legalmath.local-dependency-identity.v1'
OFFICIAL_HOSTS = frozenset(('apps.sfc.hk','www.sfc.hk','www.elegislation.gov.hk',
                          'data.gov.hk','resource.data.one.gov.hk'))


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def dependency_identity(names):
    if not names or len(set(names))!=len(names):raise LegalMathError('E_SCHEMA')
    records=[]
    for name in sorted(names):
        try:dist=metadata.distribution(name)
        except metadata.PackageNotFoundError:
            records.append({'name':name,'status':'NOT_INSTALLED'});continue
        files=[]
        for item in sorted(dist.files or [],key=str):
            # Bytecode caches are not stable source/package identity.
            if str(item).endswith('.pyc'):continue
            path=Path(dist.locate_file(item)).resolve()
            files.append({'record_path':str(item),'resolved_path':str(path),
                'sha256':file_hash(path) if path.is_file() else None,
                'outside_environment':not path.is_relative_to(Path(sys.prefix).resolve())})
        records.append({'name':name,'version':dist.version,'files':files,
                        'status':'FILES_HASHED' if files and all(f['sha256'] for f in files) else 'INCOMPLETE'})
    return {'profile':PROFILE,'environment':str(Path(sys.prefix).resolve()),
        'python':{'path':str(Path(sys.executable).resolve()),'sha256':file_hash(sys.executable)},
        'distributions':records,'remote_execution_attested':False,
        'dependency_correctness_established':False,'transitive_closure_established':False}


def verify_dependencies(value):
    expected=dependency_identity([r['name'] for r in value['distributions']])
    if value!=expected:raise LegalMathError('E_INTEGRITY',details='Installed dependency bytes changed')
    return {'status':'LOCAL_FILES_RECHECKED','identity_hash':digest(value)}


def checked_url(url):
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.hostname not in OFFICIAL_HOSTS or
        parsed.username or parsed.password or parsed.port not in (None,443) or parsed.fragment):
        raise LegalMathError('E_AUTHORITY',details='Source acquisition requires a registered official HTTPS host')
    return url


def acquire(url,directory,*,expected_media,maximum_bytes=20_000_000,maximum_seconds=180):
    """Retain every attempt; redirect targets are checked before contacting them."""
    import httpx
    checked_url(url)
    if type(maximum_bytes)is not int or not 1<=maximum_bytes<=600_000_000:raise LegalMathError('E_SCHEMA')
    if type(maximum_seconds)is not int or not 1<=maximum_seconds<=600:raise LegalMathError('E_SCHEMA')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    existing=directory/'receipt.json'
    if existing.exists():return verify_acquisition(directory)
    partial=directory/'response.bin'; started=time.monotonic()
    row={'url':url,'expected_media':expected_media,'maximum_bytes':maximum_bytes,
         'maximum_seconds':maximum_seconds,'retrieved_at':datetime.now(timezone.utc).isoformat(),
         'requests':[],'status':'STARTED','authenticity':'HTTPS_HOST_ONLY',
         'legal_current_force':'NOT_ESTABLISHED','timestamp_attestation':'LOCAL_CLOCK_ONLY'}
    save(existing,row)
    try:
        with httpx.Client(follow_redirects=False,timeout=30) as client:
            target=url
            for _ in range(6):
                checked_url(target)
                with client.stream('GET',target,headers={'Accept-Encoding':'identity'}) as response:
                    headers={k:v for k,v in response.headers.items() if k.lower() in
                             ('content-type','content-length','etag','last-modified','date','location')}
                    row['requests'].append({'url':target,'status':response.status_code,'headers':headers})
                    save(existing,row)
                    if response.status_code in (301,302,303,307,308):
                        target=checked_url(urljoin(target,response.headers['location']));continue
                    response.raise_for_status()
                    if int(response.headers.get('content-length','0'))>maximum_bytes:
                        raise LegalMathError('E_RESOURCE_LIMIT',details='Declared source body exceeds acquisition limit')
                    total=0
                    with partial.open('wb') as stream:
                        for block in response.iter_bytes(1024*1024):
                            total+=len(block)
                            if total>maximum_bytes or time.monotonic()-started>maximum_seconds:
                                raise LegalMathError('E_RESOURCE_LIMIT',details='Bounded source acquisition exhausted')
                            stream.write(block)
                    media=response.headers.get('content-type','').split(';')[0].lower()
                    row.update(final_url=target,media_type=media,bytes=total,sha256=file_hash(partial))
                    if media not in expected_media:
                        row.update(status='UNEXPECTED_MEDIA',qualification='Returned bytes are not the requested source format')
                    else:row['status']='ACQUIRED'
                    break
            else:raise LegalMathError('E_RESOURCE_LIMIT',details='Redirect limit exhausted')
    except Exception as exc:
        row.update(status='FAILED',error=type(exc).__name__,details=str(exc)[:1000])
        if partial.exists():row.update(bytes=partial.stat().st_size,sha256=file_hash(partial))
    row['elapsed_seconds']=str(time.monotonic()-started);save(existing,row)
    return row


def verify_acquisition(directory):
    directory=Path(directory);row=loads((directory/'receipt.json').read_bytes())
    checked_url(row['url'])
    for request in row['requests']:checked_url(request['url'])
    if row.get('sha256') and (file_hash(directory/'response.bin')!=row['sha256'] or
                            (directory/'response.bin').stat().st_size!=row['bytes']):
        raise LegalMathError('E_INTEGRITY',details='Retained authority bytes changed')
    if row['status']=='STARTED':raise LegalMathError('E_JOB_STATE',details='Incomplete retrieval retained; use a new bounded attempt')
    return row
