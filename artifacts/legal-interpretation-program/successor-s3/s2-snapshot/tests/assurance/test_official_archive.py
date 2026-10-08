from io import BytesIO
from zipfile import ZipFile
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.official_archive import RangeReader


class Response:
    def __init__(self,status,headers,data=b''):self.status_code=status;self.headers=headers;self.data=data
    def raise_for_status(self):pass
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def iter_bytes(self,n):yield self.data


class Client:
    def __init__(self,data,defect=None):self.data=data;self.defect=defect
    def head(self,*a,**k):return Response(200,{'content-length':str(len(self.data)),'etag':'"edition"'})
    def stream(self,*a,headers,**k):
        start,end=map(int,headers['Range'][6:].split('-'))
        return Response(200 if self.defect=='whole' else 206,
            {'etag':'"changed"' if self.defect=='edition' else '"edition"',
             'content-range':f'bytes {start}-{end}/{len(self.data)}'},self.data[start:end+1])


def archive():
    out=BytesIO()
    with ZipFile(out,'w') as z:z.writestr('EN/CAP_571.xml','Complete selected chapter')
    return out.getvalue()


def test_range_reader_yields_whole_member_and_records_every_range(tmp_path):
    data=archive();reader=RangeReader('https://resource.data.one.gov.hk/doj/test.zip',Client(data),tmp_path)
    with ZipFile(reader) as z:assert z.read('EN/CAP_571.xml')==b'Complete selected chapter'
    assert reader.ranges and all((tmp_path/r['file']).exists() for r in reader.ranges)


@pytest.mark.parametrize('defect',['whole','edition'])
def test_changed_edition_or_whole_response_is_not_accepted(tmp_path,defect):
    reader=RangeReader('https://resource.data.one.gov.hk/doj/test.zip',Client(archive(),defect),tmp_path)
    with pytest.raises(LegalMathError):reader.read(8)
