"""Keep the hash-bound comparison test intact while declaring its local inputs."""
from pathlib import Path

import pytest


def pytest_collection_modifyitems(items):
    test_file = Path(__file__).with_name("test_legal_tool_program.py")
    root = Path(__file__).resolve().parents[2]
    archive_dirs = (
        root / ".localresources/legal-tool-comparison",
        root / "artifacts/legal-interpretation-program",
    )
    missing = [str(path.relative_to(root)) for path in archive_dirs if not path.is_dir()]
    if not missing:
        return
    for item in items:
        if (item.path == test_file
                and item.name == "test_terminal_review_preserves_incomplete_evidence"):
            item.add_marker(pytest.mark.skip(
                reason="Requires local comparison archive: " + ", ".join(missing)
                + "; see docs/implementation/legal-tool-comparison/commit-scope.md"
            ))
