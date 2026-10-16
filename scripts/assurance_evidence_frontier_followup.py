"""Restore the matched validated test baseline before independent-frontier testing."""
import shutil
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_frontier_recovery as candidate
report = candidate.report


def repair(root):
    active = run.verify(root)
    if run.Allowance(root).verify()['used'] != 90:
        c.fail('E_AUTHORITY', 'Matched-baseline repair is bound to the 90-call checkpoint')
    name = 'tests/assurance/test_assurance_evidence_continuation.py'
    shutil.copyfile(root/active['frozen_root']/name, root/name)
    return candidate.repair(root)
