import json
import unittest

import re

from docker_enforcer import app, judge, config, requests_judge
from dockerenforcer.config import Mode
from test.test_helpers import ApiTestHelper


class ApiRequestFilterTest(unittest.TestCase):
    mem_rule = {"name": "must have memory limit", "rule": lambda c: c.params['HostConfig']['Memory'] == 0}
    cp_request_rule_regexp = re.compile("^/v1\.30/containers/test/archive$")
    cp_request_rule = {"name": "cp not allowed", "rule": lambda r, x=cp_request_rule_regexp: r['RequestMethod'] == 'GET'
        and x.match(r['ParsedUri'].path)}

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

    def test_rule_fails_run_with_mem_check(self):
        judge._rules = [self.mem_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run)
        self._check_response(res, False, "must have memory limit")

    def test_rule_ok_run_with_mem_check(self):
        judge._rules = [self.mem_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run_mem_limit)
        self._check_response(res, True)

    def test_request_rule_no_cp_from(self):
        requests_judge._rules = [self.cp_request_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_copy_from_cont)
        self._check_response(res, False, "cp not allowed")
