"""Bounded official-host HTTPS, connecting only to validated public addresses."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin

from ..errors import LegalMathError

HOSTS = frozenset({"apps.sfc.hk", "www.sfc.hk", "www.hkma.gov.hk"})


def validate_url(url, resolver=socket.getaddrinfo):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443) or p.fragment:
        raise LegalMathError("E_FETCH")
    addresses = sorted({item[4][0] for item in resolver(p.hostname, 443, type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise LegalMathError("E_FETCH")
    return p, addresses


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), timeout=self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch(url, *, max_bytes=20 * 1024 * 1024, timeout=30, resolver=socket.getaddrinfo, connection_factory=PinnedHTTPS, json_body=None):
    deadline = time.monotonic() + timeout
    try:
        for _ in range(6):
            parsed, addresses = validate_url(url, resolver)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LegalMathError("E_FETCH")
            con = connection_factory(parsed.hostname, addresses[0], remaining)
            try:
                path = parsed.path or "/"
                if parsed.query: path += "?" + parsed.query
                headers = {"Host": parsed.hostname, "Accept-Encoding": "identity", "User-Agent": "LegalMath-public-prototype/0.1"}
                body = None
                if json_body is not None:
                    from ..canonical import canonical
                    if parsed.hostname != "apps.sfc.hk" or parsed.path != "/edistributionWeb/api/circular/search":
                        raise LegalMathError("E_FETCH")
                    body = canonical(json_body)
                    headers["Content-Type"] = "application/json"
                con.request("POST" if body else "GET", path, body=body, headers=headers)
                response = con.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location:
                        raise LegalMathError("E_FETCH")
                    url = urljoin(url, location)
                    continue
                if response.status != 200 or response.getheader("Content-Encoding", "identity") != "identity":
                    raise LegalMathError("E_FETCH")
                length = response.getheader("Content-Length")
                if length is not None and int(length) > max_bytes:
                    raise LegalMathError("E_RESOURCE_LIMIT")
                media = response.getheader("Content-Type", "").split(";")[0].strip().lower()
                if media not in ("application/json", "application/pdf", "text/plain", "text/html"):
                    raise LegalMathError("E_FETCH")
                chunks, size = [], 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0: raise LegalMathError("E_FETCH")
                    if con.sock: con.sock.settimeout(remaining)
                    block = response.read(min(65536, max_bytes - size + 1))
                    if not block: break
                    size += len(block)
                    if size > max_bytes: raise LegalMathError("E_RESOURCE_LIMIT")
                    chunks.append(block)
                data = b"".join(chunks)
                if media == "application/pdf" and not data.startswith(b"%PDF-"):
                    raise LegalMathError("E_FETCH")
                if media == "application/json":
                    from ..canonical import loads
                    loads(data)
                return {"url": url, "media_type": media, "data": data}
            finally:
                con.close()
        raise LegalMathError("E_FETCH")
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise LegalMathError("E_FETCH") from exc
