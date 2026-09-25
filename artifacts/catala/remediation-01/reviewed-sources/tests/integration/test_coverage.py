import json
import pytest
from legalmath.sources.intake import import_spi
from legalmath.review.coverage import coverage_report
from legalmath.errors import LegalMathError


def test_full_actual_circular_disposition(db, root):
    import_spi(db, root)
    bundle = json.loads((root / "examples/java-dry-run/spec/spi-control.bundle.json").read_text())
    rows = json.loads((root / "examples/java-dry-run/spec/circular-disposition.json").read_text())["numbered_provisions"]
    with db.connect() as con:
        report = coverage_report(db, con, bundle, rows)
        assert len(report["provisions"]) == 51 and report["issues"]
        assert not report["coverage_is_legal_approval"]
        with pytest.raises(LegalMathError): coverage_report(db, con, bundle, rows[:1])


def test_transitive_definition_dependency_blocks_release(db, root):
    from legalmath.sources.dependencies import record_dependency, closure
    imported = import_spi(db, root)
    with db.transaction() as con:
        dep = {"from_revision_id": imported[1]["revision_id"], "target_revision_id": imported[2]["revision_id"],
            "locator": "synthetic definition chain", "relation": "defines", "resolution_status": "resolved", "resolution_note": "test"}
        record_dependency(db, con, dep)
        dep = {**dep, "from_revision_id": imported[2]["revision_id"], "target_revision_id": None,
            "locator": "missing imported definition", "resolution_status": "unresolved"}
        record_dependency(db, con, dep)
        result = closure(db, con, [imported[1]["revision_id"]])
        assert result["unresolved"] and imported[2]["revision_id"] in result["revision_ids"]
