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
