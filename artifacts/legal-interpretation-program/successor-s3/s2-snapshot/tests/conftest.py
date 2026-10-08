import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root():
    return ROOT


@pytest.fixture
def case():
    return json.loads((ROOT / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"][0]


@pytest.fixture
def db(tmp_path):
    from legalmath.storage import Database
    return Database(tmp_path / "db")
