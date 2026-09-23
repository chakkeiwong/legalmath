"""Retain the service's actual request models alongside generated domain schemas."""
import json
from pathlib import Path
import tempfile
from legalmath.api.app import create_app

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="legalmath-openapi-") as td:
    spec = create_app(td).openapi()
out = ROOT / "docs/specs/v0.1/openapi.json"
out.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
print(f"Wrote {len(spec['paths'])} API paths to {out.relative_to(ROOT)}")
