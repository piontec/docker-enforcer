import unittest
from copy import copy
from unittest.mock import create_autospec

import docker

from dockerenforcer.config import Config
from dockerenforcer.docker_helper import Container, CheckSource, DockerHelper


class ContainerTests(unittest.TestCase):
    def test_create_without_name(self):
        container = Container("123", {"param1": 1}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("123", str(container))

    def test_create_with_name(self):
        container = Container("123", {"name": "container1"}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("container1", str(container))


class DockerHelperTests(unittest.TestCase):
    def setUp(self):
        self._config = Config()
        self._client = create_autospec(docker.APIClient)
        self._helper = DockerHelper(self._config, self._client)
        self._cid = "cont_id1"
        self._cid2 = "cont_id2"
        self._params = {"id": self._cid, "param1": "1"}
        self._params2 = {"id": self._cid2, "param1": "2"}

    def test_kill_container(self):
        c = Container(self._cid, params=self._params, metrics={}, position=0, check_source=CheckSource.Periodic)
        self._helper.kill_container(c)
        self._client.stop.assert_called_once_with(self._cid)

    def test_get_params_no_cache(self):
        self._client.inspect_container.return_value = self._params
        params = self._helper.get_params(self._cid)
        self._client.inspect_container.assert_called_once_with(self._cid)
        self.assertDictEqual(params, self._helper.rename_keys_to_lower(copy(self._params)))

    def test_get_params_fill_cache(self):
        self._config.cache_params = True
        self._client.inspect_container.return_value = self._params
        params = self._helper.get_params(self._cid)
        self._client.inspect_container.assert_called_once_with(self._cid)
        self.assertDictEqual(params, self._helper.rename_keys_to_lower(copy(self._params)))
        self.assertDictEqual(self._helper._params_cache[self._cid], self._helper.rename_keys_to_lower(copy(self._params)))

    def test_get_params_from_cache_and_remove(self):
        self._config.cache_params = True
        self._helper._params_cache[self._cid] = self._params
        params = self._helper.get_params(self._cid)
        self._client.inspect_container.assert_not_called()
        self.assertDictEqual(params, self._params)
        self.assertDictEqual(self._helper._params_cache[self._cid], self._params)
        # now try to remove cached params
        self._helper.remove_from_cache(self._cid)
        self.assertFalse(self._cid in self._helper._params_cache)

    def test_purge_cache(self):
        self._config.cache_params = True
        self._helper._params_cache[self._cid] = self._params
        self._helper._params_cache[self._cid2] = self._params2
        self._client.inspect_container.assert_not_called()
        self._helper.purge_cache([self._cid])
        self.assertFalse(self._cid2 in self._helper._params_cache)

    def test_check_containers(self):
        self._config.disable_metrics = True
        self._client.containers.return_value = [{'Id': self._cid}, {'Id': self._cid2}]
        self._client.inspect_container.side_effect = [self._params, self._params2]
        containers = list(self._helper.check_containers(CheckSource.Periodic))
        self._client.containers.assert_called_once_with(quiet=True)
        self._client.inspect_container.side_effect = [self._params, self._params2]
        self.assertEqual(len(containers), 2)
        self.assertEqual(containers[0].cid, self._cid)
        self.assertEqual(containers[0].check_source, CheckSource.Periodic)
        self.assertDictEqual(containers[0].params, self._helper.rename_keys_to_lower(copy(self._params)))
        self.assertEqual(containers[1].cid, self._cid2)
        self.assertEqual(containers[1].check_source, CheckSource.Periodic)
        self.assertDictEqual(containers[1].params, self._helper.rename_keys_to_lower(copy(self._params2)))

    def test_get_events(self):
        res = [
            {u'from': u'image/with:tag', u'id': self._cid, u'status': u'start', u'time': 1423339459},
            {u'from': u'image/with:tag', u'id': self._cid2, u'status': u'start', u'time': 1423339459}
            ]
        self._client.events.return_value = res
        events = list(self._helper.get_events_observable())
        self._client.events.assert_called_once_with(decode=True)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['id'], self._cid)
        self.assertEqual(events[1]['id'], self._cid2)

    def test_rename_keys_to_lower(self):
        params = {"Privileged": True, "CapAdd": ["SYS_ADMIN"], "HostConfig": {"MOUNTS": [{"TESTLIST0KEY": "..."}, {"TESTLIST1KEY": "..."}]}, "TEST2KEY": "TEST2VALUE"}
        params = self._helper.rename_keys_to_lower(params)

        self.assertTrue("privileged" in params)
        self.assertFalse("Privileged" in params)

        self.assertTrue("capadd" in params)
        self.assertFalse("CapAdd" in params)

        self.assertTrue("hostconfig" in params)
        self.assertFalse("HostConfig" in params)

        self.assertTrue("mounts" in params['hostconfig'])
        self.assertFalse("MOUNTS" in params['hostconfig'])

        self.assertTrue("testlist0key" in params['hostconfig']["mounts"][0])
        self.assertFalse("TESTLIST0KEY" in params['hostconfig']["mounts"][0])

        self.assertTrue("testlist1key" in params['hostconfig']["mounts"][1])
        self.assertFalse("TESTLIST1KEY" in params['hostconfig']["mounts"][1])
