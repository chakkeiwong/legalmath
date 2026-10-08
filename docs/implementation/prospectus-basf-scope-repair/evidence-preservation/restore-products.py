"""Restore byte-identical BASF products from their verified adoption archive."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent

for row in json.loads((HERE / "product-aliases.json").read_text())["files"]:
    archive = (ROOT / row["archive"]).resolve()
    destination = (ROOT / row["path"]).resolve()
    if not archive.is_relative_to(ROOT) or not destination.is_relative_to(HERE.parent):
        raise ValueError("Recovery path outside declared scope")
    packed = archive.read_bytes()
    if hashlib.sha256(packed).hexdigest() != row["archive_sha256"]:
        raise ValueError("Changed recovery archive")
    raw = gzip.decompress(packed)
    if hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("Changed recovery product")
    if destination.exists():
        if destination.read_bytes() != raw:
            raise ValueError("Existing product differs; refusing overwrite")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(raw)
print(json.dumps({"status": "PASS", "originals": "PRESERVED"}))
