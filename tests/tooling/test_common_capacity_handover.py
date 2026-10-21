import unittest
from scripts.legal_common_capacity_handover import guards


class HandoverGuards(unittest.TestCase):
    def test_settled_failed_owners_are_safe(self):
        self.assertTrue(guards({'tasks': {'a': {'status': 'FAILED'}}},
            [{'calls': {'x': {'status': 'FAILED'}}}], [{'status': 'COMPLETED'}])[0])

    def test_running_owner_blocks(self):
        self.assertFalse(guards({'tasks': {'a': {'status': 'RUNNING'}}}, [], [])[0])

    def test_uncertain_dispatch_blocks(self):
        self.assertFalse(guards({'tasks': {}},
            [{'calls': {'x': {'status': 'RESERVED'}}}], [])[0])

    def test_uncertain_native_operation_blocks(self):
        self.assertFalse(guards({'tasks': {}}, [], [{'status': 'RESERVED'}])[0])
