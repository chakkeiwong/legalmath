"""Focused CPU-only installed regression for exact account continuation."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys
import pytest
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
tests = [
    'tests/tooling/test_account_service_continuation.py',
    'tests/tooling/test_synthesis_continuation_scope.py',
    'tests/tooling/test_synthesis_correction_scope.py',
    'tests/tooling/test_synthesis_edit_scope.py',
    'tests/tooling/test_repair_execution.py',
    'tests/tooling/test_repair_plan_projection.py',
    'tests/tooling/test_outage_refresh_continuation.py',
    'tests/assurance/test_initial_checkpoint.py',
    'tests/assurance/test_bounded_terminal_recovery.py',
    'tests/assurance/test_completed_account_receipt.py',
    'tests/assurance/test_account_recovery_lineage.py',
    'tests/assurance/test_downstream_replay_order.py',
    'tests/assurance/test_phased_product.py',
]
raise SystemExit(pytest.main(['-q', *tests, '--junitxml=' + str(Path(__file__).with_name('tests.xml'))]))
