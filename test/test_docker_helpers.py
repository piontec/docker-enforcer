import unittest
from unittest.mock import create_autospec

import docker

from dockerenforcer.config import Config
from dockerenforcer.docker_helper import Container, CheckSource, DockerHelper


class ContainerTests(unittest.TestCase):
    def test_create_without_name(self):
        container = Container("123", {"param1": 1}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("123", str(container))

    def test_create_with_name(self):
        container = Container("123", {"Name": "container1"}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("container1", str(container))


class DockerHelperTests(unittest.TestCase):
    def setUp(self):
        self._config = Config()
        self._client = create_autospec(docker.APIClient)
        self._helper = DockerHelper(self._config, self._client)

    def test_kill_container(self):
        cid = "cont_id1"
        c = Container("cid1", {"Id": cid}, {}, 0, CheckSource.Periodic)
        self._helper.kill_container(c)
        self._client.stop.assert_called_once_with(cid)

    def test_get_params_no_cache(self):
        cid = "cont_id1"
        exp_params = {"param1": "1"}
        self._client.inspect_container.return_value = exp_params
        params = self._helper.get_params(cid)
        self._client.inspect_container.assert_called_once_with(cid)
        self.assertDictEqual(params, exp_params)
