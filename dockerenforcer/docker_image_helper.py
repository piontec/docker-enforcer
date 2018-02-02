from functools import lru_cache
from typing import Any, Dict

from docker import APIClient

from dockerenforcer.config import Config


class DockerImageHelper:
    def __init__(self, config: Config, client: APIClient) -> None:
        super().__init__()
        self._config: Config = config
        self._client: APIClient = client

    @lru_cache(maxsize=1024)
    def get_image_uniq_tag_by_id(self, image_id):
        image_inspect_data: Dict = self._client.inspect_image(image_id)
        if 'RepoTags' in image_inspect_data and len(image_inspect_data['RepoTags']) > 0:
            return image_inspect_data['RepoTags'][0]
        else:
            return image_id
