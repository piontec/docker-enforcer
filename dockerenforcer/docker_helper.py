from docker import Client
from docker.errors import NotFound
from flask import logging
from requests import ReadTimeout
from requests.packages.urllib3.exceptions import ProtocolError

logger = logging.getLogger("docker_enforcer")


class Container:
    def __init__(self, cid, params, metrics, position):
        super().__init__()
        self.position = position
        self.metrics = metrics
        self.params = params
        self.cid = cid

    def __str__(self, *args, **kwargs):
        return self.params['Name'] if self.params['Name'] else self.cid


class DockerHelper:
    def __init__(self, config):
        super().__init__()
        self.__config = config
        self.__client = Client(base_url=config.docker_socket)
        self.__params_cache = {}

    def check_container(self, container_id):
        try:
            params = self.__client.inspect_container(container_id)
            metrics = self.__client.stats(container=container_id, decode=True, stream=False)
            logger.debug("Fetched data for container {0}".format(container_id))
        except NotFound as e:
            logger.warn("Container {0} not found.".format(e))
            return None
        except (ReadTimeout, ProtocolError) as e:
            logger.error("Error while trying to get list of containers from docker: {0}".format(e))
            return None
        return Container(container_id, params, metrics, 0)

    def check_containers(self):
        res = []

        try:
            containers = sorted(self.__client.containers(), key=lambda c: c["Created"])
            logger.debug("Fetched containers list from docker daemon")
        except (ReadTimeout, ProtocolError) as e:
            logger.error("Timeout while trying to get list of containers from docker: {0}".format(e))
            return res
        ids = [container['Id'] for container in containers]
        counter = 0
        for container_id in ids:
            container = self.check_container(container_id)
            if container is None:
                continue
            counter += 1
            res.append(container)
        return res

    def get_params(self, container_id):
        if not self.__config.cache_params:
            return self.__client.inspect_container(container_id)
        if container_id in self.__params_cache:
            return self.__params_cache[container_id]
        params = self.__client.inspect_container(container_id)
        self.__params_cache[container_id] = params
        return params

    def get_start_events_observable(self):
        return self.__client.events(filters={"event": "start"}, decode=True)

    def kill_container(self, container):
        self.__client.stop(container.params['Id'])
