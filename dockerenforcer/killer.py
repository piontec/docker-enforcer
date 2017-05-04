import threading
import datetime
from copy import deepcopy

from flask import logging
from rx import Observer

from dockerenforcer.config import Mode

logger = logging.getLogger("docker_enforcer")


class Stat:
    def __init__(self, name, reason):
        super().__init__()
        self.counter = 1
        self.last_timestamp = datetime.datetime.utcnow()
        self.name = name
        self.reason = reason

    def record_new(self, reason):
        self.counter += 1
        self.last_timestamp = datetime.datetime.utcnow()
        self.reason = reason

    def __str__(self, *args, **kwargs):
        return "{0} - {1}".format(self.counter, self.last_timestamp)


class StatusDictionary:
    def __init__(self, killed_containers=None):
        super().__init__()
        self.__padlock = threading.Lock()
        self.__killed_containers = killed_containers if killed_containers else {}

    def register_killed(self, container, reason):
        with self.__padlock:
            if container.cid in self.__killed_containers.keys():
                self.__killed_containers[container.cid].record_new(reason)
            else:
                self.__killed_containers[container.cid] = Stat(container.params['Name'], reason)

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

    def to_json_detail_stats(self, output_filter):
        str_list = ""
        with self.__padlock:
            is_first = True
            for k, v in self.__killed_containers.items():
                if not output_filter(v):
                    continue
                if not is_first:
                    str_list += ",\n"
                else:
                    is_first = False
                str_list += "    {{\"id\": \"{0}\", \"name\": \"{1}\", \"violated_rule\": \"{2}\", " \
                            "\"count\": {3}, \"last_timestamp\": \"{4}\" }}"\
                    .format(k, v.name, v.reason, v.counter, v.last_timestamp.isoformat())
            return "[\n{0}\n]".format(str_list)


class Verdict:
    def __init__(self, verdict, container, reason):
        super().__init__()
        self.reason = reason
        self.container = container
        self.verdict = verdict


class Judge:
    def __init__(self, rules):
        super().__init__()
        self.__rules = rules

    def should_be_killed(self, container):
        if not container:
            logger.warning("No container details, skipping checks")
            return Verdict(False, container, None)

        for rule in self.__rules:
            try:
                if rule['rule'](container):
                    return Verdict(True, container, rule['name'])
            except Exception as e:
                logger.error("During execution of rule {0} exception was raised: {1}".format(rule['name'], e))
        return Verdict(False, container, None)


class Killer(Observer):
    def __init__(self, manager, mode):
        super().__init__()
        self.__mode = mode
        self.__manager = manager
        self.__status = StatusDictionary()

    def on_next(self, verdict):
        logger.info("Container {0} is detected to violate the rule \"{1}\". {2} the container [{3} mode]"
                    .format(verdict.container, verdict.reason,
                            "Not stopping" if self.__mode == Mode.Warn else "Stopping", self.__mode))
        self.__status.register_killed(verdict.container, verdict.reason)
        if self.__mode == Mode.Kill:
            self.__manager.kill_container(verdict.container)

    def on_error(self, e):
        logger.warning("An error occurred while trying to check running containers")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")

    def get_stats(self):
        return self.__status.copy()
