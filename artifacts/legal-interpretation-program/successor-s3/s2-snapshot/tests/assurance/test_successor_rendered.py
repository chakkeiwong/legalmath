from pathlib import Path
import pytest
from legalmath.canonical import raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.rendered_provider import RenderedSourceProvider
from .test_successor_grants import grant


def test_rendered_source_is_explicitly_attached_and_bound(tmp_path):
    allowance,_=grant(tmp_path)
    image=tmp_path/'source.png';image.write_bytes(b'public source image fixture')
    p=RenderedSourceProvider(allowance=allowance,image=image,sha256=raw_digest(image.read_bytes()))
    command=p.command(tmp_path,tmp_path/'schema.json',tmp_path/'out.json')
    assert command[-4:]==['--image',str(image),'--','-']
    assert allowance.verify()['used']==0
    image.write_bytes(b'changed page')
    with pytest.raises(LegalMathError) as caught:p.command(tmp_path,Path('schema'),Path('out'))
    assert caught.value.code=='E_INTEGRITY'


def test_ungranted_image_route_rejected_before_io(tmp_path):
    with pytest.raises(LegalMathError) as caught:
        RenderedSourceProvider(allowance=None,image=tmp_path/'absent.png',sha256='0'*64)
    assert caught.value.code=='E_AUTHORITY'
