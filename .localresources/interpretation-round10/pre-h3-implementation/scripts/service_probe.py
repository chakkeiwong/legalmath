"""Bounded startup diagnostic for the HTTP test transport, without network I/O."""
import faulthandler
from tempfile import TemporaryDirectory
from fastapi.testclient import TestClient
from legalmath.api.app import create_app

faulthandler.dump_traceback_later(8)
with TemporaryDirectory() as directory:
    app = create_app(directory)
    with TestClient(app) as client:
        response = client.get("/")
        if response.status_code != 200:
            raise SystemExit(response.text)
        print("Service startup and first HTTP request passed.")
faulthandler.cancel_dump_traceback_later()
