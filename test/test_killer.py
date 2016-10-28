import unittest
from test.test_helpers import RulesTestHelper


class RulesTests(unittest.TestCase):

    def test_count_rule(self):
        rules = [{"name": "no more than 10", "rule": lambda c: c.position > 10}]
        self.assertFalse(RulesTestHelper(rules).get_verdicts()[0].verdict)

    def test_no_containers(self):
        rules = [{"name": "no containers", "rule": lambda c: True}]
        self.assertTrue(RulesTestHelper(rules).get_verdicts()[0].verdict)

    def test_count_limit(self):
        rules = [{"name": "no more than 3", "rule": lambda c: c.position > 3}]
        verdicts = RulesTestHelper(rules, container_count=5).get_verdicts()
        for v in verdicts[0:3]:
            self.assertFalse(v.verdict)
        for v in verdicts[4:5]:
            self.assertTrue(v.verdict)
