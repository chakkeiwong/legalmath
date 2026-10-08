import json
from pathlib import Path
import pytest
from legalmath.interpretation.semantics.clauses import propose
from legalmath.interpretation.semantics.records import Branch, Settings

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-1"

@pytest.fixture
def pilot_inputs():
    packet = json.loads((BASE / "packet.json").read_text())
    rows = json.loads((BASE / "overlay.json").read_text())["records"]
    settings = Settings(semantics="grounded", ordering="none", priorities=(), max_arguments=8,
                        max_extensions=256, timeout_seconds=5)
    return packet, {"query": "Conditional responsibility and demonstration duties"}, rows, settings

@pytest.fixture
def inventory(pilot_inputs):
    return propose(*pilot_inputs)

@pytest.fixture
def branches(inventory):
    return [Branch.model_validate_json(json.dumps(b)) for b in inventory["branches"]]
