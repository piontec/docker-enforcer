from functools import lru_cache
from typing import Any, Dict

from docker import APIClient
from docker.errors import NotFound
from flask import logging

from dockerenforcer.config import Config

logger = logging.getLogger("docker_enforcer")


class DockerImageHelper:
    def __init__(self, config: Config, client: APIClient) -> None:
        super().__init__()
        self._config: Config = config
        self._client: APIClient = client

    @lru_cache(maxsize=1024)
    def get_image_uniq_tag_by_id(self, image_id):
        try:
            image_inspect_data: Dict = self._client.inspect_image(image_id)
        except NotFound as e:
            logger.warning("Image {0} not found".format(image_id, e))
            return image_id

        if 'RepoTags' in image_inspect_data and len(image_inspect_data['RepoTags']) > 0:
            return image_inspect_data['RepoTags'][0]
        else:
            return image_id

    def merge_container_and_image_labels(self, container):
        image = container.params['image']
        image_params = {}
        try:
            image_params = self._client.inspect_image(image)
        except NotFound as e:
            logger.debug("Image {0} not found - {1}.".format(image, e))
        image_labels = {}
        if 'Config' in image_params and 'Labels' in image_params['Config']:
            image_labels = image_params['Config']['Labels']
        final_labels = self.merge_dicts(image_labels, container.params["config"]["labels"])
        return final_labels

    def merge_dicts(self, image_labels, container_labels):
        if image_labels is None and container_labels is None:
            return None

        if not image_labels:
            return container_labels

        if not container_labels:
            return image_labels

        return {**image_labels, **container_labels}
