"""Bounded ZIP member retrieval using recorded, edition-bound HTTP ranges."""
import io
from pathlib import Path
import re
from zipfile import ZipFile
import httpx

from ...canonical import raw_digest,loads
from ...errors import LegalMathError
from .diversity import save
from .evidence_identity import checked_url


class RangeReader(io.RawIOBase):
    def __init__(self,url,client,directory,*,maximum_bytes=32_000_000):
        self.url=checked_url(url);self.client=client;self.directory=Path(directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        head=client.head(url,headers={'Accept-Encoding':'identity'},follow_redirects=False)
        head.raise_for_status()
        self.size=int(head.headers['content-length']);self.etag=head.headers.get('etag')
        if not self.etag or self.etag.startswith('W/') or head.status_code!=200:
            raise LegalMathError('E_INTEGRITY',details='Archive lacks a strong edition binding')
        self.position=0;self.used=0;self.maximum=maximum_bytes;self.ranges=[]
        self.head={'url':url,'size':self.size,'etag':self.etag,
                   'last_modified':head.headers.get('last-modified'),'server_date':head.headers.get('date')}
        save(self.directory/'head.json',self.head)
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        pos=offset if whence==0 else self.position+offset if whence==1 else self.size+offset if whence==2 else -1
        if not 0<=pos<=self.size:raise LegalMathError('E_REFERENCE')
        self.position=pos;return pos
    def read(self,n=-1):
        n=self.size-self.position if n<0 else min(n,self.size-self.position)
        if not n:return b''
        if n>16_000_000 or self.used+n>self.maximum or len(self.ranges)>=64:
            raise LegalMathError('E_RESOURCE_LIMIT',details='Archive range budget exhausted')
        start=self.position;end=start+n-1
        with self.client.stream('GET',self.url,headers={'Accept-Encoding':'identity',
                'Range':f'bytes={start}-{end}','If-Match':self.etag},follow_redirects=False) as response:
            response.raise_for_status()
            if (response.status_code!=206 or response.headers.get('etag')!=self.etag or
                response.headers.get('content-range')!=f'bytes {start}-{end}/{self.size}'):
                raise LegalMathError('E_INTEGRITY',details='Server did not supply the requested archive edition/range')
            data=bytearray()
            for block in response.iter_bytes(65536):
                data.extend(block)
                if len(data)>n:raise LegalMathError('E_INTEGRITY')
        if len(data)!=n:raise LegalMathError('E_INTEGRITY')
        path=self.directory/f'range-{len(self.ranges):03}.bin';path.write_bytes(data)
        self.ranges.append({'start':start,'end':end,'file':path.name,'sha256':raw_digest(data)})
        save(self.directory/'ranges.json',self.ranges)
        self.used+=n;self.position+=n
        return bytes(data)


def chapter(url,directory,number=571):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'result.json').exists():
        value=loads((directory/'result.json').read_bytes())
        for item in value['members']:
            if raw_digest((directory/item['file']).read_bytes())!=item['sha256']:raise LegalMathError('E_INTEGRITY')
        for item in loads((directory/'ranges/ranges.json').read_bytes()):
            if raw_digest((directory/'ranges'/item['file']).read_bytes())!=item['sha256']:raise LegalMathError('E_INTEGRITY')
        return value
    members=[]
    with httpx.Client(timeout=30) as client:
        remote=RangeReader(url,client,directory/'ranges')
        with ZipFile(remote) as archive:
            names=archive.namelist();save(directory/'members.json',names)
            selected=[n for n in names if re.search(r'(?:^|[/_\-])(?:cap[ _\-]?)?0*'+str(number)+r'(?:[._/\-]|$)',n,re.I)]
            for index,name in enumerate(selected):
                info=archive.getinfo(name)
                if info.is_dir():continue
                if info.file_size>50_000_000:raise LegalMathError('E_RESOURCE_LIMIT')
                data=archive.read(name)  # ZIP CRC is checked by the standard library.
                output=f'chapter-{index:02d}{Path(name).suffix}'
                (directory/output).write_bytes(data)
                members.append({'member':name,'file':output,'sha256':raw_digest(data),'bytes':len(data),'crc32':str(info.CRC)})
    result={'status':'CHAPTER_BYTES_RETAINED' if members else 'CHAPTER_NOT_LOCATED',
        'archive_edition':remote.head,'downloaded_range_bytes':remote.used,'members':members,
        'qualification':'Full selected members, ZIP CRC, strong HTTP ETag and retained byte ranges; no whole-archive hash or trusted chronology.',
        'temporal_applicability':'NOT_ESTABLISHED','legal_conclusions':[]}
    save(directory/'result.json',result);return result
