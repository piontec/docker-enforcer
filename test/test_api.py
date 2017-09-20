import json
import unittest
from docker_enforcer import app, judge, config
from dockerenforcer.config import Mode
from test.test_helpers import ApiTestHelper


class ApiRequestFilterTest(unittest.TestCase):
    mem_rule = {"name": "must have memory limit", "rule": lambda c: c.params['HostConfig']['Memory'] == 0}

    def setUp(self):
        config.mode = Mode.Kill
        self.de = app
        self.de.testing = True
        self.app = self.de.test_client()

    def _check_response(self, response, allow, msg=None, code=200):
        self.assertEqual(response.status_code, code)
        json_res = json.loads(response.data.decode(response.charset))
        self.assertEqual(json_res["Allow"], allow)
        if not allow:
            self.assertEqual(json_res["Msg"], msg)

    def test_fails_run_with_mem_check(self):
        judge._rules = [self.mem_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run)
        self._check_response(res, False, "must have memory limit")

    def test_ok_run_with_mem_check(self):
        judge._rules = [self.mem_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run_mem_limit)
        self._check_response(res, True)

