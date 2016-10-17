import threading
import datetime
from copy import deepcopy

from flask import logging
from rx import Observer

from dockerenforcer.config import Mode

logger = logging.getLogger("docker_enforcer")


class Status:
    def __init__(self, counter=0, killed_containers=None, last_killing_timestamp=None):
        super().__init__()
        self.__padlock = threading.Lock()
        self.__counter = counter
        self.__killed_containers = killed_containers if killed_containers else []
        self.__last_killing_timestamp = last_killing_timestamp

    def register_killed(self, container):
        with self.__padlock:
            self.__counter += 1
            self.__killed_containers.append(container)
            self.__last_killing_timestamp = datetime.datetime.utcnow()

    def copy(self):
        with self.__padlock:
            res = Status(self.__counter, deepcopy(self.__killed_containers), self.__last_killing_timestamp)
        return res

    def to_prometheus_stats_format(self):
        with self.__padlock:
            res = """
# HELP containers_stopped_total The total number of docker containers stopped.
# TYPE containers_stopped_total counter
containers_stopped_total {0}

# HELP containers_stopped_last_timestamp The timestamp of last event of stopping a container
# TYPE containers_stopped_last_timestamp gauge
containers_stopped_last_timestamp {1}
""".format(self.__counter, self.__last_killing_timestamp)
        return res


class Killer(Observer):
    def __init__(self, manager, mode):
        super().__init__()
        self.__mode = mode
        self.__manager = manager
        self.__status = Status()

    def on_next(self, container):
        # TODO: needs to be more explaining, why killing is performed
        # TODO: logging doesn't work
        logger.info("Container {0} is detected to violate one of the rules. {1} the container [{2} mode]"
                    .format(container, "Not stopping" if self.__mode == Mode.Warn else "Stopping", self.__mode))
        self.__status.register_killed(container)
        if self.__mode == Mode.Kill:
            self.__manager.kill_container(container)

    def on_error(self, e):
        logger.warn("An error occurred while trying to check running containers")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")

    def get_stats(self):
        return self.__status.copy()
