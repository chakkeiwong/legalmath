import pytest
from legalmath.sources.fetch import validate_url, fetch
from legalmath.errors import LegalMathError


def resolve(ip): return lambda *a, **kw: [(2, 1, 6, "", (ip, 443))]


@pytest.mark.parametrize("url", ["http://apps.sfc.hk/x", "https://apps.sfc.hk.evil.test/x", "https://user:pass@apps.sfc.hk/x", "https://127.0.0.1/x", "file:///etc/passwd", "https://apps.sfc.hk:8000/x"])
def test_official_url_boundary(url):
    with pytest.raises(LegalMathError): validate_url(url, resolve("8.8.8.8"))


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "192.168.0.1"])
def test_public_host_private_dns_rejected(ip):
    with pytest.raises(LegalMathError): validate_url("https://apps.sfc.hk/x", resolve(ip))


class Response:
    status = 302
    def getheader(self, key, default=None): return "https://127.0.0.1/secret" if key == "Location" else default


class Connection:
    sock = None
    def __init__(self, *args): pass
    def request(self, *args, **kwargs): pass
    def getresponse(self): return Response()
    def close(self): pass


def test_redirect_checked_before_connection():
    with pytest.raises(LegalMathError): fetch("https://apps.sfc.hk/x", resolver=resolve("8.8.8.8"), connection_factory=Connection)


def test_oversize_and_wrong_pdf_magic():
    class BadResponse:
        status = 200
        def __init__(self, oversized): self.oversized = oversized
        def getheader(self, key, default=None):
            return {"Content-Type": "application/pdf", "Content-Length": "100" if self.oversized else "5"}.get(key, default)
        def read(self, count): return b"<html>"
    class BadConnection(Connection):
        oversized = True
        def getresponse(self): return BadResponse(self.oversized)
    with pytest.raises(LegalMathError) as e: fetch("https://apps.sfc.hk/pdf", max_bytes=8, resolver=resolve("8.8.8.8"), connection_factory=BadConnection)
    assert e.value.code == "E_RESOURCE_LIMIT"
    class FakePDF(Connection):
        def getresponse(self):
            class R(BadResponse):
                sent = False
                def read(self, count):
                    if self.sent: return b""
                    self.sent = True
                    return b"<html>"
            return R(False)
    with pytest.raises(LegalMathError) as e: fetch("https://apps.sfc.hk/pdf", resolver=resolve("8.8.8.8"), connection_factory=FakePDF)
    assert e.value.code == "E_FETCH"
