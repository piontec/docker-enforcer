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
        self.__client = APIClient(base_url=config.docker_socket, timeout=config.docker_req_timeout_sec)
        self.__params_cache = {}
        self.last_check_containers_run_end_timestamp = datetime.datetime.min
        self.last_check_containers_run_start_timestamp = datetime.datetime.min
        self.last_check_containers_run_time = datetime.timedelta.min
        self.last_periodic_run_ok = False

    def check_container(self, container_id):
        try:
            if not self.__config.disable_params:
                params = self.get_params(container_id)
            else:
                params = {}
            if not self.__config.disable_metrics:
                logger.debug("[{0}] Starting to fetch metrics for {1}".format(threading.current_thread().name,
                                                                              container_id))
                metrics = self.__client.stats(container=container_id, decode=True, stream=False)
            else:
                metrics = {}
            logger.debug("[{0}] Fetched data for container {1}".format(threading.current_thread().name, container_id))
        except NotFound as e:
            logger.warning("Container {0} not found - {1}.".format(container_id, e))
            return None
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Communication error when fetching info about container {0}: {1}".format(container_id, e))
            return None
        except Exception as e:
            logger.error("Unexpected error when fetching info about container {0}: {1}".format(container_id, e))
            return None
        return Container(container_id, params, metrics, 0)

    def check_containers(self):
        with self.__padlock:
            if self.__check_in_progress:
                logger.warning("Previous check did not yet complete, consider increasing CHECK_INTERVAL_S")
                return
            self.__check_in_progress = True
        logger.debug("Periodic check start: connecting to get the list of containers")
        self.last_check_containers_run_start_timestamp = datetime.datetime.utcnow()
        try:
            containers = self.__client.containers(quiet=True)
            logger.debug("[{0}] Fetched containers list from docker daemon".format(threading.current_thread().name))
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
        for container_id in ids:
            container = self.check_container(container_id)
            if container is None:
                continue
            yield container
        logger.debug("Containers checked")
        if self.__config.cache_params:
            logger.debug("Purging cache")
            self.purge_cache(ids)
        self.last_periodic_run_ok = True
        self.last_check_containers_run_end_timestamp = datetime.datetime.utcnow()
        self.last_check_containers_run_time = self.last_check_containers_run_end_timestamp \
            - self.last_check_containers_run_start_timestamp
        logger.debug("Periodic check done")
        with self.__padlock:
            self.__check_in_progress = False

    def get_params(self, container_id):
        if self.__config.cache_params and container_id in self.__params_cache:
            logger.debug("Returning cached params for container {0}".format(container_id))
            return self.__params_cache[container_id]

        logger.debug("[{0}] Starting to fetch params for {1}".format(threading.current_thread().name, container_id))
        try:
            params = self.__client.inspect_container(container_id)
        except NotFound as e:
            logger.warning("Container {0} not found - {1}.".format(container_id, e))
            return None
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Communication error when fetching params for container {0}: {1}".format(container_id, e))
            return {}
        except Exception as e:
            logger.error("Unexpected error when fetching params for container {0}: {1}".format(container_id, e))
            return {}
        logger.debug("[{0}] Params fetched for {1}".format(threading.current_thread().name, container_id))
        if not self.__config.cache_params:
            return params

        logger.debug("[{0}] Storing params of {1} in cache".format(threading.current_thread().name, container_id))
        self.__params_cache[container_id] = params
        return params

    def purge_cache(self, running_container_ids):
        diff = [c for c in self.__params_cache.keys() if c not in running_container_ids]
        for cid in diff:
            self.__params_cache.pop(cid, None)

    def remove_from_cache(self, container_id):
        self.__params_cache.pop(container_id, None)

    def __get_events_observable(self, event_type):
        successful = False
        ev = None
        while not successful:
            try:
                ev = self.__client.events(filters={"event": event_type}, decode=True)
            except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
                logger.error("Communication error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            except Exception as e:
                logger.error("Unexpected error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            successful = True
        return ev

    def get_start_events_observable(self):
        return self.__get_events_observable("start")

    def get_update_events_observable(self):
        return self.__get_events_observable("update")

    def kill_container(self, container):
        try:
            self.__client.stop(container.params['Id'])
        except (ReadTimeout, ProtocolError) as e:
            logger.error("Communication error when stopping container {0}: {1}".format(container.cid, e))
        except Exception as e:
            logger.error("Unexpected error when stopping container {0}: {1}".format(container.cid, e))
