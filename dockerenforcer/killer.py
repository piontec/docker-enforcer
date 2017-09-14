import json
import threading
import datetime
from copy import deepcopy

from flask import logging
from rx import Observer

from dockerenforcer.config import Mode
from triggers.triggers import triggers

logger = logging.getLogger("docker_enforcer")


class Stat:
    def __init__(self, name):
        super().__init__()
        self.counter = 0
        self.name = name
        self.last_timestamp = None
        self.reasons = None
        self.image = None
        self.labels = None
        self.source = None

    def record_new(self, reasons, image, labels, source):
        self.counter += 1
        self.last_timestamp = datetime.datetime.utcnow()
        self.reasons = reasons
        self.image = image
        self.labels = labels
        self.source = source

    def __str__(self, *args, **kwargs):
        return "{0} - {1}".format(self.counter, self.last_timestamp)


class StatusDictionary:
    def __init__(self, killed_containers=None):
        super().__init__()
        self.__padlock = threading.Lock()
        self.__killed_containers = killed_containers if killed_containers else {}

    def register_killed(self, container, reasons):
        with self.__padlock:
            name = container.params["Name"]
            image = container.params["Config"]["Image"] \
                if "Config" in container.params and "Image" in container.params["Config"] \
                else container.params["Image"]
            labels = container.params["Config"]["Labels"] if "Config" in container.params else container.params["Labels"]
            self.__killed_containers.setdefault(container.cid, Stat(name))\
                .record_new(reasons, image, labels, container.check_source)

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

    def to_json_detail_stats(self, output_filter, show_all_violated_rules, show_image_and_labels):
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

                violated_rule = '"%s"' % v.reasons[0]
                if show_all_violated_rules:
                    violated_rule = json.dumps(v.reasons)

                str_list += "    {{\"id\": \"{0}\", \"name\": \"{1}\", \"violated_rule\": {2}, " \
                            "\"source\": \"{3}\", \"count\": {4}, \"last_timestamp\": \"{5}\""\
                    .format(k, v.name, violated_rule, v.source, v.counter, v.last_timestamp.isoformat())

                if show_image_and_labels:
                    str_list += ', "image": "{0}", "labels": {1}'.format(v.image, json.dumps(v.labels))
                str_list += " }"
            return "[\n{0}\n]".format(str_list)

    def get_items(self):
        return self.__killed_containers.items()


class Verdict:
    def __init__(self, verdict, container, reasons):
        super().__init__()
        self.reasons = reasons
        self.container = container
        self.verdict = verdict


class Judge:
    def __init__(self, rules, config):
        super().__init__()
        self.__rules = rules
        self.__config = config
        self.__global_whitelist = []
        self.__per_rule_whitelist = {}
        self.__whitelist_separator = ":"
        self._load_whitelist_from_config()

    def _on_global_white_list(self, container):
        has_name = container.params and 'Name' in container.params
        on_list = has_name and container.params['Name'][1:] in self.__global_whitelist

        if on_list:
            name = container.params['Name'][1:] if has_name else container.cid
            logger.debug("Container {0} is on white list".format(name))
        return on_list

    def _on_per_rule_whitelist(self, container, rule_name):
        has_name = container.params and 'Name' in container.params
        on_list = has_name and rule_name in self.__per_rule_whitelist \
            and container.params['Name'][1:] in self.__per_rule_whitelist[rule_name]

        if on_list:
            name = container.params['Name'][1:] if has_name else container.cid
            logger.debug("Container {0} is on white list for rule '{1}'".format(name, rule_name))
        return on_list

    def should_be_killed(self, container):
        if not container:
            logger.warning("No container details, skipping checks")
            return Verdict(False, container, None)
        if self._on_global_white_list(container):
            return Verdict(False, container, None)

        reasons = []
        for rule in self.__rules:
            if self._on_per_rule_whitelist(container, rule['name']):
                continue
            try:
                if rule['rule'](container):
                    reasons.append(rule['name'])
                    if self.__config.stop_on_first_violation:
                        break
            except Exception as e:
                reasons.append("Exception - rule: {0}, class: {1}, val: {2}"
                               .format(rule['name'], e.__class__.__name__, str(e)))
        if len(reasons) > 0:
            return Verdict(True, container, reasons)
        else:
            return Verdict(False, container, None)

    def _load_whitelist_from_config(self):
        self.__global_whitelist = [r for r in self.__config.white_list if r.find(self.__whitelist_separator) == -1]
        self.__per_rule_whitelist = {n: r for (r, n) in
                                     [s.split(self.__whitelist_separator, 1) for s in self.__config.white_list
                                     if s.find(self.__whitelist_separator) > -1]}


class Killer(Observer):
    def __init__(self, manager, mode):
        super().__init__()
        self.__mode = mode
        self.__manager = manager
        self.__status = StatusDictionary()

    def on_next(self, verdict):
        logger.info("Container {0} is detected to violate the rule \"{1}\". {2} the container [{3} mode]"
                    .format(verdict.container, json.dumps(verdict.reasons),
                            "Not stopping" if self.__mode == Mode.Warn else "Stopping", self.__mode))
        self.register_kill(verdict)
        if self.__mode == Mode.Kill:
            self.__manager.kill_container(verdict.container)

    def on_error(self, e):
        logger.warning("An error occurred while trying to check running containers")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")

    def get_stats(self):
        return self.__status.copy()

    def register_kill(self, verdict):
        self.__status.register_killed(verdict.container, verdict.reasons)


class TriggerHandler(Observer):
    def __init__(self):
        super().__init__()
        self.__triggers = triggers

    def on_next(self, verdict):
        for trigger in self.__triggers:
            try:
                trigger["trigger"](verdict)
            except Exception as e:
                logger.error("During execution of trigger {0} exception was raised: {1}".format(trigger, e))

    def on_error(self, e):
        logger.warning("An error occurred while waiting for detections")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")
