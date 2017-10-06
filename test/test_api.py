import json
import unittest

import re
from unittest import mock

from flask import Response

from docker_enforcer import app, judge, config, requests_judge, trigger_handler
from dockerenforcer.config import Mode
from test.test_helpers import ApiTestHelper, DefaultRulesHelper


class ApiContainerTest(unittest.TestCase):
    mem_rule = {"name": "must have memory limit", "rule": lambda c: c.params['HostConfig']['Memory'] == 0}
    cp_request_rule_regexp = re.compile("^/v1\.[23]\d/containers/test/archive$")
    cp_request_rule = {"name": "cp not allowed", "rule": lambda r, x=cp_request_rule_regexp:
    r['RequestMethod'] in ['GET', 'HEAD'] and x.match(r['ParsedUri'].path)}
    test_trigger_flag = False
    test_trigger = {"name": "set local flag", "trigger": lambda v: ApiContainerTest.set_trigger_flag()}
    forbid_privileged_rule = {
        "name": "can't use privileged or cap-add without being on the whitelist",
        "rule": lambda c: c.params["HostConfig"]["Privileged"] or c.params["HostConfig"]["CapAdd"] is not None
    }

    @staticmethod
    def set_trigger_flag():
        ApiContainerTest.test_trigger_flag = True

    @classmethod
    def setUpClass(cls):
        config.mode = Mode.Kill
        config.log_authz_requests = True
        cls.de = app
        cls.de.testing = True
        cls.app = cls.de.test_client()

    def setUp(self):
        judge._rules = []
        judge._global_whitelist = []
        judge._image_global_whitelist = []
        judge._per_rule_whitelist = {}
        judge._image_per_rule_whitelist = {}
        judge._custom_whitelist_rules = {}

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

    def test_request_rule_no_cp_to(self):
        requests_judge._rules = [self.cp_request_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_copy_to_cont)
        self._check_response(res, False, "cp not allowed")

    def test_trigger_when_rule_fails_run_with_mem_check(self):
        judge._rules = [self.mem_rule]
        trigger_handler._triggers = [self.test_trigger]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run)
        self._check_response(res, False, "must have memory limit")
        self.assertTrue(ApiContainerTest.test_trigger_flag)

    def test_logs_correctly(self):
        with mock.patch.object(app.logger, 'info') as mock_info:
            self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_run_with_tls)
            self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run)
            self.assertTrue(mock_info.called
                            and mock_info.call_count == 2
                            and mock_info.call_args_list[0][0][0] ==
                            '[AUTHZ_REQ] New auth request: user: client, method: GET, uri: /v1.27/containers/json'
                            and mock_info.call_args_list[1][0][0] ==
                            '[AUTHZ_REQ] New auth request: user: [unknown], method: POST, '
                            'uri: /v1.30/containers/create')

    def test_violates_rules_but_on_whitelist(self):
        judge._rules = [self.forbid_privileged_rule]
        judge._global_whitelist = [re.compile('^docker_enforcer$')]
        res = self.app.post('/AuthZPlugin.AuthZReq',
                            data=ApiTestHelper.authz_req_run_with_privileged_name_docker_enforcer)
        self._check_response(res, True)

    def test_violates_rules_but_on_image_whitelist(self):
        judge._rules = [self.forbid_privileged_rule]
        judge._image_global_whitelist = [re.compile('^alpine$')]
        res = self.app.post('/AuthZPlugin.AuthZReq',
                            data=ApiTestHelper.authz_req_run_with_privileged_name_test)
        self._check_response(res, True)

    def test_violates_rules_but_on_per_rule_regexp_whitelist(self):
        judge._rules = [self.forbid_privileged_rule]
        judge._per_rule_whitelist = {self.forbid_privileged_rule['name']: [re.compile('^docker_enf.*$')]}
        res = self.app.post('/AuthZPlugin.AuthZReq',
                            data=ApiTestHelper.authz_req_run_with_privileged_name_docker_enforcer)
        self._check_response(res, True)

    def test_violates_rules_but_on_per_rule_regexp_image_whitelist(self):
        judge._rules = [self.forbid_privileged_rule]
        judge._image_per_rule_whitelist = {self.forbid_privileged_rule['name']: [re.compile('^alp.*$')]}
        res = self.app.post('/AuthZPlugin.AuthZReq',
                            data=ApiTestHelper.authz_req_run_with_privileged_name_test)
        self._check_response(res, True)

    def test_violates_rules_but_on_custom_whitelist(self):
        judge._rules = [self.forbid_privileged_rule]
        judge._custom_whitelist_rules = [{
            "name": "name docker_enforcer and image alpine and rule forbid_privileged",
            "rule": lambda c, r: c.params['Name'] == 'docker_enforcer'
            and c.params['Image'] == 'alpine'
            and r == self.forbid_privileged_rule['name']
        }]
        res = self.app.post('/AuthZPlugin.AuthZReq',
                            data=ApiTestHelper.authz_req_run_with_privileged_name_docker_enforcer)
        self._check_response(res, True)

    def test_killed_check_api_log(self):
        judge._rules = [self.mem_rule]
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_plain_run_with_tls)
        self._check_response(res, False, "must have memory limit")
        log = self.app.get('/')
        int_json = json.loads(log.data.decode(log.charset))
        self.assertEqual(len(int_json["detections"]), 1)
        det = int_json["detections"][0]
        self.assertEqual(det["id"], "<unnamed_container>")
        self.assertEqual(det["name"], "<unnamed_container>")
        self.assertEqual(det["source"], "authz_plugin")
        self.assertEqual(det["violated_rule"], "must have memory limit")
        self.assertEqual(det["owner"], "client")

    def test_handles_empty_when_default_action_accept(self):
        config.default_allow = True
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_empty)
        self._check_response(res, True)

    def test_handles_empty_when_default_action_deny(self):
        config.default_allow = False
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_empty)
        self._check_response(res, False, "Denied as default action")

    def test_handles_malformed_when_default_action_accept(self):
        config.default_allow = True
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_malformed)
        self._check_response(res, True)

    def test_handles_malformed_when_default_action_deny(self):
        config.default_allow = False
        res = self.app.post('/AuthZPlugin.AuthZReq', data=ApiTestHelper.authz_req_malformed)
        self._check_response(res, False, "Denied as default action")


class ApiInfoTest(unittest.TestCase):
    def setUp(self):
        self.de = app
        self.de.testing = True
        self.app = self.de.test_client()

    def _check_rules_response(self, res: Response, mime_type: str, data: bytearray = None):
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, mime_type)
        if data is not None:
            self.assertEqual(res.data, data)

    def test_fetch_rules(self):
        res = self.app.get('/rules')
        self._check_rules_response(res, "application/json", DefaultRulesHelper.rules_json)

    def test_fetch_rules_html(self):
        res = self.app.get('/rules', headers={"Accept": "text/html"})
        self._check_rules_response(res, "text/html")

    def test_fetch_triggers(self):
        res = self.app.get('/triggers')
        self._check_rules_response(res, "application/json", DefaultRulesHelper.triggers_json)

    def test_fetch_triggers_html(self):
        res = self.app.get('/triggers', headers={"Accept": "text/html"})
        self._check_rules_response(res, "text/html")

    def test_fetch_request_rules(self):
        res = self.app.get('/request_rules')
        self._check_rules_response(res, "application/json", DefaultRulesHelper.request_rules)

    def test_fetch_request_rules_html(self):
        res = self.app.get('/request_rules', headers={"Accept": "text/html"})
        self._check_rules_response(res, "text/html")
