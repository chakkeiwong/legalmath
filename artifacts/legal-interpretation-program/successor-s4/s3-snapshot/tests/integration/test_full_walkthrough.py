from pathlib import Path
from legalmath.demo import walkthrough


def test_complete_spi_walkthrough(root, tmp_path):
    report = walkthrough(root, tmp_path / "walkthrough", root / ".localresources/java-toolchain/jdk-17.0.20.1+1")
    assert report["status"] == "OFFLINE_WALKTHROUGH_PASSED"
    assert report["decision_cases"] == 32 and report["event_cases"] == 8
    assert report["coverage_provisions"] == 51 and report["pilot_sources"] == 5
    assert report["withdrawal_outcome"] == "FALSE" and report["original_replay_equal"]
    assert report["authority"] == "LOCAL_SYNTHETIC"
    assert Path(report["java"]["directory"], "policy.jar").is_file()
