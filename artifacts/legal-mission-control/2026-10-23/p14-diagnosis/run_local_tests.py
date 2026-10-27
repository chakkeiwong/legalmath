"""CPU-only local P14 candidate checks; never invokes a live provider."""
import os
import sys
from pathlib import Path

ROOT = Path('/tmp/legalmath-p14-repair-20261023')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTHONPATH'] = str(ROOT/'src') + ':' + str(ROOT)
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
os.chdir(ROOT)
import legalmath
import pytest
assert Path(legalmath.__file__).is_relative_to(ROOT)

class RetainedReceiptLocation:
    """One production receipt test explicitly reads the original evidence root."""
    def pytest_runtest_setup(self, item):
        if item.nodeid.endswith('test_actual_slot_3591_is_authenticated_empty_timeout'):
            from scripts import legal_review_timeout_correction as correction
            self.previous_root = correction.ROOT
            correction.ROOT = Path('/home/chakwong/python/legalmath')

    def pytest_runtest_teardown(self, item):
        if item.nodeid.endswith('test_actual_slot_3591_is_authenticated_empty_timeout'):
            from scripts import legal_review_timeout_correction as correction
            correction.ROOT = self.previous_root

raise SystemExit(pytest.main(sys.argv[1:] or [
    '-q', 'tests/assurance/test_review_assignment_contract.py',
    'tests/assurance/test_service_prerequisite.py',
    'tests/assurance/test_source_review_repair.py',
    'tests/assurance/test_bounded_references.py',
    'tests/assurance/test_common_capacity.py',
    'tests/assurance/test_phased_phase.py',
    'tests/assurance/test_downstream_instructions.py',
    'tests/assurance/test_bounded_product.py',
    'tests/assurance/test_review_receipts.py',
    'tests/tooling/test_review_service_checkpoint.py',
    'tests/tooling/test_review_repair_registration.py',
    'tests/tooling/test_review_timeout_correction.py',
    'tests/tooling/test_legal_mission_execution.py',
    'tests/tooling/test_settled_recovery_registration.py',
    '--junitxml=/home/chakwong/python/legalmath/artifacts/legal-mission-control/2026-10-23/p14-diagnosis/local-tests.xml',
], plugins=[RetainedReceiptLocation()]))
