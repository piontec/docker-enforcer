import threading
import datetime
from copy import deepcopy

from flask import logging
from rx import Observer

from dockerenforcer.config import Mode

logger = logging.getLogger("docker_enforcer")


class Stat:
    def __init__(self):
        super().__init__()
        self.counter = 1
        self.last_timestamp = datetime.datetime.utcnow()

    def __str__(self, *args, **kwargs):
        return "{0} - {1}".format(self.counter, self.last_timestamp)


class StatusDictionary:
    def __init__(self, killed_containers=None):
        super().__init__()
        self.__padlock = threading.Lock()
        self.__killed_containers = killed_containers if killed_containers else {}

    def register_killed(self, container):
        with self.__padlock:
            if container.cid in self.__killed_containers.keys():
                self.__killed_containers[container.cid].counter += 1
                self.__killed_containers[container.cid].last_timestamp = datetime.datetime.utcnow()
            else:
                self.__killed_containers[container.cid] = Stat()

    def copy(self):
        with self.__padlock:
            res = StatusDictionary(deepcopy(self.__killed_containers))
        return res

    def to_prometheus_stats_format(self):
        with self.__padlock:
            res = """# HELP containers_stopped_total The total number of docker containers stopped.
# TYPE containers_stopped_total counter
containers_stopped_total {0}
""".format(len(self.__killed_containers))
        return res

    def to_json_detail_stats(self):
        str_list = ""
        with self.__padlock:
            is_first = True
            for k, v in self.__killed_containers.items():
                if not is_first:
                    str_list += ",\n"
                else:
                    is_first = False
                str_list += "{{ \"id\": \"{0}\", \"count\": {1}, \"last_timestamp\": \"{2}\" }}"\
                    .format(k, v.counter, v.last_timestamp.isoformat())
            return "[{0}]".format(str_list)


class Killer(Observer):
    def __init__(self, manager, mode):
        super().__init__()
        self.__mode = mode
        self.__manager = manager
        self.__status = StatusDictionary()

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
