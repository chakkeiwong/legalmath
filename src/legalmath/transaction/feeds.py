"""Acquire and validate fixed official OFAC list endpoints before activation."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile

from ..canonical import canonical
from .evidence import sha
from .sanctions import parse

ENDPOINT = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/"
FEEDS = (("ofac-sdn", "SDN", "sdn.xml", "SDN.XML"),
         ("ofac-consolidated", "CONSOLIDATED", "consolidated.xml", "CONSOLIDATED.XML"))


def retain(root, *, download=False):
    directory = Path(root) / "docs/compliance/feeds"
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, family, filename, remote in FEEDS:
        path = directory / filename
        if download:
            # Stage and validate first. Failed requests cannot replace a good list.
            with tempfile.TemporaryDirectory(prefix="legalmath-ofac-") as temp:
                candidate = Path(temp) / filename
                subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                    "--max-time", "240", "--output", str(candidate), ENDPOINT + remote], check=True, timeout=250)
                data = candidate.read_bytes()
                parse(data, list_kind=family)
                historical = directory / "history" / (sha(data) + ".xml")
                historical.parent.mkdir(exist_ok=True)
                if path.exists():
                    old = path.read_bytes()
                    (historical.parent / (sha(old) + ".xml")).write_bytes(old)
                path.write_bytes(data)
        data = path.read_bytes()
        parsed = parse(data, list_kind=family)
        rows.append({"id": key, "list_kind": family, "url": ENDPOINT + remote,
            "path": str(path.relative_to(root)), "sha256": sha(data),
            "retrieved_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "published_date": parsed["published_date"], "records": parsed["record_count"],
            "status": "PARSED_COMPLETE_DECLARED_RECORD_COUNT", "legal_currentness": "NOT_ESTABLISHED"})
    result = {"sources": rows, "acquisition": "Official fixed HTTPS endpoints; original bytes retained",
              "limitations": "A list snapshot and exact-name candidates do not establish identity, ownership or absence of all sanctions."}
    (directory / "manifest.json").write_bytes(canonical(result))
    return result
