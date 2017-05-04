import datetime
import threading
from json import JSONDecodeError

import time

from docker import APIClient
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
        self.__padlock = threading.Lock()
        self.__check_in_progress = False
        self.__config = config
        self.__client = APIClient(base_url=config.docker_socket)
        self.__params_cache = {}
        self.last_check_containers_run_end_timestamp = datetime.datetime.min
        self.last_check_containers_run_start_timestamp = datetime.datetime.min
        self.last_periodic_run_ok = False

    def check_container(self, container_id):
        try:
            if not self.__config.disable_params:
                params = self.get_params(container_id)
            else:
                params = {}
            if not self.__config.disable_metrics:
                logger.debug("Starting to fetch metrics for {0}".format(container_id))
                metrics = self.__client.stats(container=container_id, decode=True, stream=False)
                logger.debug("Metrics fetched for {0}".format(container_id))
            else:
                metrics = {}
            logger.debug("Fetched data for container {0}".format(container_id))
        except NotFound as e:
            logger.warning("Container {0} not found - error {1}.".format(container_id, e))
            return None
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Communication error when fetching info about container {0}: {1}".format(container_id, e))
            return None
        except Exception as e:
            logger.error("Unexpected error when fetching info about container {0}: {1}".format(container_id, e))
            return None
        return Container(container_id, params, metrics, 0)

    def check_containers(self):
        logger.debug("Connecting to get the list of containers")
        self.last_check_containers_run_start_timestamp = datetime.datetime.utcnow()
        with self.__padlock:
            if self.__check_in_progress:
                logger.warning("Previous check did not yet complete, consider increasing CHECK_INTERVAL_S")
                return
            self.__check_in_progress = True
        try:
            containers = sorted(self.__client.containers(), key=lambda c: c["Created"])
            logger.debug("Fetched containers list from docker daemon")
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Timeout while trying to get list of containers from docker: {0}".format(e))
            with self.__padlock:
                self.__check_in_progress = False
            self.last_periodic_run_ok = False
            return
        except Exception as e:
            logger.error("Unexpected error while trying to get list of containers from docker: {0}".format(e))
            with self.__padlock:
                self.__check_in_progress = False
            self.last_periodic_run_ok = False
            return
        ids = [container['Id'] for container in containers]
        counter = 0
        for container_id in ids:
            container = self.check_container(container_id)
            if container is None:
                continue
            counter += 1
            yield container
        if self.__config.cache_params:
            self.purge_cache(ids)
        with self.__padlock:
            self.__check_in_progress = False
        self.last_periodic_run_ok = True
        self.last_check_containers_run_end_timestamp = datetime.datetime.utcnow()
        logger.debug("Periodic check done")

    def get_params(self, container_id):
        if self.__config.cache_params and container_id in self.__params_cache:
            logger.debug("Returning cached params for container {0}".format(container_id))
            return self.__params_cache[container_id]

        logger.debug("Starting to fetch params for {0}".format(container_id))
        try:
            params = self.__client.inspect_container(container_id)
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Communication error when fetching params for container {0}: {1}".format(container_id, e))
            return {}
        except Exception as e:
            logger.error("Unexpected error when fetching params for container {0}: {1}".format(container_id, e))
            return {}
        logger.debug("Params fetched for {0}".format(container_id))
        if not self.__config.cache_params:
            return params

        logger.debug("Storing params of {0} in cache".format(container_id))
        self.__params_cache[container_id] = params
        return params

    def purge_cache(self, running_container_ids):
        diff = [c for c in self.__params_cache.keys() if c not in running_container_ids]
        for cid in diff:
            self.__params_cache.pop(cid, None)

    def get_start_events_observable(self):
        successful = False
        ev = None
        while not successful:
            try:
                ev = self.__client.events(filters={"event": "start"}, decode=True)
            except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
                logger.error("Communication error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            except Exception as e:
                logger.error("Unexpected error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            successful = True
        return ev

    def kill_container(self, container):
        try:
            self.__client.stop(container.params['Id'])
        except (ReadTimeout, ProtocolError) as e:
            logger.error("Communication error when stopping container {0}: {1}".format(container.cid, e))
        except Exception as e:
            logger.error("Unexpected error when stopping container {0}: {1}".format(container.cid, e))
