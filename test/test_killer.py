import unittest
from test.test_helpers import RulesTestHelper


class RulesTests(unittest.TestCase):

    def test_count_rule(self):
        rules = [{"name": "no more than 10", "rule": lambda c: c.position > 10}]
        self.assertFalse(RulesTestHelper(rules).get_verdict().verdict)

    def test_no_containers(self):
        rules = [{"name": "no containers", "rule": lambda c: True}]
        self.assertTrue(RulesTestHelper(rules).get_verdict().verdict)
