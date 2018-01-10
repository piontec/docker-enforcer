import unittest
from dockerenforcer.config import Config
from .test_helpers import RulesTestHelper


class TestsWithVerdicts(unittest.TestCase):
    def assert_verdicts(self, expected, verdicts):
        index = 0
        for exp in expected:
            for i in range(index, index + exp[0]):
                self.assertTrue(verdicts[i].verdict == exp[1])
            index += exp[0]


class ParamsRulesTests(TestsWithVerdicts):
    def test_not_violates_count_rule(self):
        rules = [{"name": "no more than 10", "rule": lambda c: c.position > 10}]
        self.assertFalse(RulesTestHelper(rules).get_verdicts()[0].verdict)

    def test_violates_no_containers(self):
        rules = [{"name": "no containers", "rule": lambda c: True}]
        self.assertTrue(RulesTestHelper(rules).get_verdicts()[0].verdict)

    def test_count_limit(self):
        rules = [{"name": "no more than 3", "rule": lambda c: c.position >= 3}]
        verdicts = RulesTestHelper(rules, container_count=5).get_verdicts()
        self.assert_verdicts([(3, False), (2, True)], verdicts)

    def test_must_have_memory_limit(self):
        rules = [{"name": "must have memory limit", "rule": lambda c: c.params['hostconfig']['memory'] == 0}]
        self.assertFalse(RulesTestHelper(rules, mem_limit=1024).get_verdicts()[0].verdict)
        self.assertTrue(RulesTestHelper(rules, mem_limit=0).get_verdicts()[0].verdict)

    def test_must_have_cpu_quota(self):
        rules = [{"name": "must have CPU limit",
                  "rule": lambda c: c.params['hostconfig']['cpuquota'] == 0
                  and c.params['hostconfig']['cpuperiod'] == 0}]
        self.assertFalse(RulesTestHelper(rules, cpu_period=50000, cpu_quota=50000).get_verdicts()[0].verdict)
        self.assertTrue(RulesTestHelper(rules, cpu_period=0, cpu_quota=0).get_verdicts()[0].verdict)


class MetricsRulesTests(TestsWithVerdicts):
    def test_uses_too_much_ram(self):
        rules = [{"name": "uses over 1GB of RAM", "rule": lambda c: c.metrics['memory_stats']['usage'] > 1 * 1024 ** 3}]
        self.assertFalse(RulesTestHelper(rules, mem_usage=1024 ** 2).get_verdicts()[0].verdict)
        self.assertTrue(RulesTestHelper(rules, mem_usage=10 * 1024 ** 3).get_verdicts()[0].verdict)


class WhitelistTests(TestsWithVerdicts):
    def setUp(self):
        self.wl_config = Config()
        self.rules = [{"name": "must have CPU limit",
                       "rule": lambda c: c.params['HostConfig']['CpuQuota'] == 0
                       and c.params['HostConfig']['CpuPeriod'] == 0}]

    def test_killed_without_whitelist(self):
        self.assertTrue(RulesTestHelper(self.rules, cpu_period=0, cpu_quota=0).get_verdicts()[0].verdict)

    def test_not_killed_on_whitelist_full_name_periodic(self):
        self.wl_config.white_list = ["testing_vro"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_whitelist_name_regex_periodic(self):
        self.wl_config.white_list = ["testing_.*"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_whitelist_full_name_and_rule_periodic(self):
        self.wl_config.white_list = ["testing_vro|must have CPU limit"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_whitelist_name_regex_and_rule_periodic(self):
        self.wl_config.white_list = ["testing.*|must have CPU limit"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_image_whitelist_name_periodic(self):
        self.wl_config.image_white_list = ["busybox"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_image_whitelist_name_regex_periodic(self):
        self.wl_config.image_white_list = ["busy.*"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_image_whitelist_full_name_and_rule_periodic(self):
        self.wl_config.image_white_list = ["busybox|must have CPU limit"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)

    def test_not_killed_on_image_whitelist_name_regex_and_rule_periodic(self):
        self.wl_config.image_white_list = ["busy.*|must have CPU limit"]
        self.assertFalse(RulesTestHelper(self.rules, config=self.wl_config, cpu_period=0, cpu_quota=0)
                         .get_verdicts()[0].verdict)
