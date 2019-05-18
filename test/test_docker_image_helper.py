import types
import unittest
from unittest.mock import create_autospec

import docker
from docker.errors import NotFound

from dockerenforcer.config import Config
from dockerenforcer.docker_image_helper import DockerImageHelper


class DockerHelperTests(unittest.TestCase):
    def setUp(self):
        self._config = Config()
        self._client = create_autospec(docker.APIClient)
        self._helper = DockerImageHelper(self._config, self._client)
        self._image_id = 'sha256:7f6f52e2942811a77591960a62e9e88c2249c976b3fb83bf73aa1e9e570dfc51'
        self._image_name1 = 'test1:latest'
        self._image_name2 = 'test2:latest'

    def test_get_image_uniq_tag_by_id__when_empty_inspect(self):
        self._client.inspect_image.return_value = {}
        image_tag = self._helper.get_image_uniq_tag_by_id(self._image_id)
        self._client.inspect_image.assert_called_once_with(self._image_id)
        self.assertEqual(self._image_id, image_tag)

    def test_get_image_uniq_tag_by_id__when_empty_repo_tags(self):
        self._client.inspect_image.return_value = {'RepoTags': []}
        image_tag = self._helper.get_image_uniq_tag_by_id(self._image_id)
        self._client.inspect_image.assert_called_once_with(self._image_id)
        self.assertEqual(self._image_id, image_tag)

    def test_get_image_uniq_tag_by_id__image_not_found(self):
        self._client.inspect_image.side_effect = NotFound('Image not found')
        image_tag = self._helper.get_image_uniq_tag_by_id(self._image_id)
        self.assertEqual(self._image_id, image_tag)

    def test_get_image_uniq_tag_by_id__when_single_repo_tag(self):
        self._client.inspect_image.return_value = {'RepoTags': [self._image_name1]}
        image_tag = self._helper.get_image_uniq_tag_by_id(self._image_id)
        self.assertEqual(self._image_name1, image_tag)

    def test_get_image_uniq_tag_by_id__when_many_repo_tags(self):
        self._client.inspect_image.return_value = {'RepoTags': [self._image_name2, self._image_name1]}
        image_tag = self._helper.get_image_uniq_tag_by_id(self._image_id)
        self.assertEqual(self._image_name2, image_tag)

    def test_merge_container_and_image_labels(self):
        image_labels = {'label1': 'label1_image_value', 'label2': 'label2_image_value'}
        container_labels = {'label2': 'label2_container_value', 'label3': 'label3_container_value'}

        self._client.inspect_image.return_value = {'Config': {'Labels': image_labels}}

        container = types.SimpleNamespace()
        container.params = {'image': 'test', 'config': {'labels': container_labels}}

        final_labels = self._helper.merge_container_and_image_labels(container=container)

        self.assertIn('label1', final_labels)
        self.assertEquals('label1_image_value', final_labels['label1'])

        self.assertIn('label2', final_labels)
        self.assertEquals('label2_container_value', final_labels['label2'])

        self.assertIn('label3', final_labels)
        self.assertEquals('label3_container_value', final_labels['label3'])

