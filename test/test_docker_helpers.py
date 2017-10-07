import unittest

from dockerenforcer.docker_helper import Container, CheckSource


class ContainerTests(unittest.TestCase):
    def test_create_without_name(self):
        container = Container("123", {"param1": 1}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("123", str(container))

    def test_create_with_name(self):
        container = Container("123", {"Name": "container1"}, {"cpu": 7}, 0, CheckSource.Periodic)
        self.assertEqual("container1", str(container))
