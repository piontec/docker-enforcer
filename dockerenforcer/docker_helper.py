import datetime
import threading
from json import JSONDecodeError

import time
from typing import Dict, Any, Iterable, Optional

from docker import APIClient
from docker.errors import NotFound
from flask import logging
from requests import ReadTimeout
from requests.packages.urllib3.exceptions import ProtocolError

from dockerenforcer.config import Config

logger = logging.getLogger("docker_enforcer")


class CheckSource:
    AuthzPlugin: str = "authz_plugin"
    Periodic: str = "periodic"
    Event: str = "event"


class Container:
    def __init__(self, cid: str, params: Dict[str, Any], metrics: Dict[str, Any], position: int,
                 check_source: CheckSource, owner: str="[unknown]") -> None:
        super().__init__()
        self.params: Dict[str, Any] = params
        self.check_source: CheckSource = check_source
        self.position: int = position
        self.metrics: Dict[str, Any] = metrics
        self.cid: str = cid
        self.owner: str = owner

    def __str__(self, *args, **kwargs) -> str:
        return self.params.get('Name', self.cid)


class DockerHelper:
    def __init__(self, config: Config, client: APIClient) -> None:
        super().__init__()
        self._padlock = threading.Lock()
        self._check_in_progress: bool = False
        self._config: Config = config
        self._client: APIClient = client
        self._params_cache: Dict[str, Any] = {}
        self.last_check_containers_run_end_timestamp: datetime.datetime = datetime.datetime.min
        self.last_check_containers_run_start_timestamp: datetime.datetime = datetime.datetime.min
        self.last_check_containers_run_time: datetime.timedelta = datetime.timedelta.min
        self.last_periodic_run_ok: bool = False

    def check_container(self, container_id: str, check_source: CheckSource, remove_from_cache: bool=False) \
            -> Optional[Container]:
        try:
            if remove_from_cache:
                self.remove_from_cache(container_id)

            if not self._config.disable_params:
                params = self.get_params(container_id)
            else:
                params = {}
            if not self._config.disable_metrics:
                logger.debug("[{0}] Starting to fetch metrics for {1}".format(threading.current_thread().name,
                                                                              container_id))
                metrics = self._client.stats(container=container_id, decode=True, stream=False)
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
        if params is None or metrics is None:
            logger.warning("Params or metrics were not fetched for container {}. Not returning container."
                           .format(container_id))
            return None
        return Container(container_id, params, metrics, 0, check_source)

    def check_containers(self, check_source: CheckSource) -> Iterable[Container]:
        with self._padlock:
            if self._check_in_progress:
                logger.warning("[{0}] Previous check did not yet complete, consider increasing CHECK_INTERVAL_S"
                               .format(threading.current_thread().name))
                return
            self._check_in_progress = True
        logger.debug("Periodic check start: connecting to get the list of containers")
        self.last_check_containers_run_start_timestamp = datetime.datetime.utcnow()
        try:
            containers = self._client.containers(quiet=True)
            logger.debug("[{0}] Fetched containers list from docker daemon".format(threading.current_thread().name))
        except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
            logger.error("Timeout while trying to get list of containers from docker: {0}".format(e))
            with self._padlock:
                self._check_in_progress = False
            self.last_periodic_run_ok = False
            return
        except Exception as e:
            logger.error("Unexpected error while trying to get list of containers from docker: {0}".format(e))
            with self._padlock:
                self._check_in_progress = False
            self.last_periodic_run_ok = False
            return
        ids = [container['Id'] for container in containers]
        for container_id in ids:
            container = self.check_container(container_id, check_source)
            if container is None:
                continue
            yield container
        logger.debug("Containers checked")
        if self._config.cache_params:
            logger.debug("Purging cache")
            self.purge_cache(ids)
        self.last_periodic_run_ok = True
        self.last_check_containers_run_end_timestamp = datetime.datetime.utcnow()
        self.last_check_containers_run_time = self.last_check_containers_run_end_timestamp \
            - self.last_check_containers_run_start_timestamp
        logger.debug("Periodic check done")
        with self._padlock:
            self._check_in_progress = False

    def get_params(self, container_id: str) -> Optional[Dict[str, Any]]:
        if self._config.cache_params and container_id in self._params_cache:
            logger.debug("Returning cached params for container {0}".format(container_id))
            return self._params_cache[container_id]

        logger.debug("[{0}] Starting to fetch params for {1}".format(threading.current_thread().name, container_id))
        try:
            params = self._client.inspect_container(container_id)
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

        params = self.rename_keys_to_lower(params)
        if not self._config.cache_params:
            return params

        logger.debug("[{0}] Storing params of {1} in cache".format(threading.current_thread().name, container_id))
        self._params_cache[container_id] = params
        return params

    def purge_cache(self, running_container_ids) -> None:
        diff = [c for c in self._params_cache.keys() if c not in running_container_ids]
        for cid in diff:
            self._params_cache.pop(cid, None)

    def remove_from_cache(self, container_id: str) -> None:
        self._params_cache.pop(container_id, None)

    def rename_keys_to_lower(self, iterable):
        new = None
        if type(iterable) is dict:
            new = {}
            for key in iterable.keys():
                lower_key = key.lower()
                if type(iterable[key]) is dict or type(iterable[key]) is list:
                    new[lower_key] = self.rename_keys_to_lower(iterable[key])
                else:
                    new[lower_key] = iterable[key]
        elif type(iterable) is list:
            new = []
            for item in iterable:
                new.append(self.rename_keys_to_lower(item))
        else:
            new = iterable
        return new

    def get_events_observable(self) -> Iterable[Any]:
        successful = False
        ev = None
        while not successful:
            try:
                ev = self._client.events(decode=True)
            except (ReadTimeout, ProtocolError, JSONDecodeError) as e:
                logger.error("Communication error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            except Exception as e:
                logger.error("Unexpected error when subscribing for container events, retrying in 5s: {0}".format(e))
                time.sleep(5)
            successful = True
        return ev

    def kill_container(self, container: Container) -> None:
        try:
            self._client.stop(container.params['id'])
        except (ReadTimeout, ProtocolError) as e:
            logger.error("Communication error when stopping container {0}: {1}".format(container.cid, e))
        except Exception as e:
            logger.error("Unexpected error when stopping container {0}: {1}".format(container.cid, e))
