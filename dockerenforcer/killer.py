import json
import threading
import datetime
import re
from copy import deepcopy

import itertools
from flask import logging
from rx import Observer

from .config import Mode
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
        self.owner = None

    def record_new(self, reasons, image, labels, source, owner):
        self.counter += 1
        self.last_timestamp = datetime.datetime.utcnow()
        self.reasons = reasons
        self.image = image
        self.labels = labels
        self.source = source
        self.owner = owner

    def __str__(self, *args, **kwargs):
        return "{0} - {1}".format(self.counter, self.last_timestamp)


class StatusDictionary:
    def __init__(self, killed_containers=None):
        super().__init__()
        self._padlock = threading.Lock()
        self._killed_containers = killed_containers if killed_containers else {}

    def register_killed(self, verdict):
        subject = verdict.subject
        reasons = verdict.reasons
        user = "[unknown]" if not hasattr(verdict.subject, "owner") else verdict.subject.owner
        with self._padlock:
            name = subject.params["Name"]
            image = subject.params["Config"]["Image"] \
                if "Config" in subject.params and "Image" in subject.params["Config"] \
                else subject.params["Image"]
            labels = subject.params["Config"]["Labels"] if "Config" in subject.params \
                else subject.params["Labels"]
            self._killed_containers.setdefault(subject.cid, Stat(name))\
                .record_new(reasons, image, labels, subject.check_source, user)

    def copy(self):
        with self._padlock:
            res = StatusDictionary(deepcopy(self._killed_containers))
        return res

    def to_prometheus_stats_format(self):
        with self._padlock:
            res = """# HELP containers_stopped_total The total number of docker containers stopped.
# TYPE containers_stopped_total counter
containers_stopped_total {0}
""".format(len(self._killed_containers))
        return res

    def to_json_detail_stats(self, output_filter, show_all_violated_rules, show_image_and_labels):
        str_list = ""
        with self._padlock:
            is_first = True
            for k, v in self._killed_containers.items():
                if not output_filter(v):
                    continue
                if not is_first:
                    str_list += ",\n"
                else:
                    is_first = False

                violated_rule = '"%s"' % v.reasons[0]
                if show_all_violated_rules:
                    violated_rule = json.dumps(v.reasons)

                str_list += "    {{\"id\": \"{0}\", \"name\": \"{1}\", \"violated_rule\": {2}, \"owner\": \"{6}\", " \
                            "\"source\": \"{3}\", \"count\": {4}, \"last_timestamp\": \"{5}\""\
                    .format(k, v.name, violated_rule, v.source, v.counter, v.last_timestamp.isoformat(), v.owner)

                if show_image_and_labels:
                    str_list += ', "image": "{0}", "labels": {1}'.format(v.image, json.dumps(v.labels))
                str_list += " }"
            return "[\n{0}\n]".format(str_list)

    def get_items(self):
        return self._killed_containers.items()


class Verdict:
    def __init__(self, verdict, container, reasons):
        super().__init__()
        self.reasons = reasons
        self.subject = container
        self.verdict = verdict


class Judge:
    def __init__(self, rules, subject_type, config, run_whitelists=True):
        super().__init__()
        self._run_whitelists = run_whitelists
        self._subject_type = subject_type
        self._rules = rules
        self._config = config
        self._whitelist_separator = ":"
        self._load_whitelists_from_config()

    @staticmethod
    def _get_name_info(container):
        has_name = container.params and 'Name' in container.params
        if has_name:
            name = container.params['Name'][1:] if container.params['Name'].startswith('/') \
                else container.params['Name']
        else:
            name = container.cid
        return has_name, name

    def _on_global_whitelist(self, container):
        has_name, name = self._get_name_info(container)
        on_list = has_name and any(rn.match(name) for rn in self._global_whitelist)
        if on_list:
            logger.debug("Container {0} is on global white list (for all rules)".format(name))
            return True

        image_name = container.params['Image']
        on_list = any(rn.match(image_name) for rn in self._image_global_whitelist)
        if on_list:
            logger.debug("Container {0} is on global image white list (for all rules)".format(name))
            return True
        return False

    def _on_per_rule_whitelist(self, container, rule_name):
        has_name, name = self._get_name_info(container)
        on_list = has_name and rule_name in self._per_rule_whitelist \
            and any(rn.match(name) for rn in self._per_rule_whitelist[rule_name])
        if on_list:
            logger.debug("Container {} is on per rule white list for rule '{}'".format(name, rule_name))
            return True

        image_name = container.params['Image']
        on_list = rule_name in self._image_per_rule_whitelist \
            and any(rn.match(image_name) for rn in self._image_per_rule_whitelist[rule_name])
        if on_list:
            logger.debug("Container {} is on image per rule white list for rule '{}'".format(name, rule_name))
            return True
        return False

    def should_be_killed(self, subject):
        if not subject:
            logger.warning("No {} details, skipping checks".format(self._subject_type))
            return Verdict(False, subject, None)
        if self._run_whitelists and self._on_global_whitelist(subject):
            return Verdict(False, subject, None)

        reasons = []
        for rule in self._rules:
            if self._run_whitelists and self._on_per_rule_whitelist(subject, rule['name']):
                continue
            try:
                if rule['rule'](subject):
                    reasons.append(rule['name'])
                    if self._config.stop_on_first_violation:
                        break
            except Exception as e:
                reasons.append("Exception - rule: {0}, class: {1}, val: {2}"
                               .format(rule['name'], e.__class__.__name__, str(e)))
        if len(reasons) > 0:
            return Verdict(True, subject, reasons)
        else:
            return Verdict(False, subject, None)

    def _load_whitelists_from_config(self):
        self._global_whitelist, self._per_rule_whitelist = self._load_lists_pair_from_config(self._config.white_list)
        self._image_global_whitelist, self._image_per_rule_whitelist = self._load_lists_pair_from_config(
            self._config.image_white_list)

    def _load_lists_pair_from_config(self, whitelist: str):
        global_whitelist = [re.compile("^{0}$".format(r)) for r in whitelist
                            if r.find(self._whitelist_separator) == -1]
        per_rule = [s.split(self._whitelist_separator, 1) for s in whitelist
                    if s.find(self._whitelist_separator) > -1]
        grouped = itertools.groupby(sorted(per_rule, key=lambda p: p[1]), key=lambda p: p[1])
        per_rule_whitelist = {}
        for pair in grouped:
            rule_name = pair[0]
            containers_names = [re.compile("^{0}$".format(n[0])) for n in list(pair[1])]
            per_rule_whitelist[rule_name] = containers_names
        return global_whitelist, per_rule_whitelist


class Killer(Observer):
    def __init__(self, manager, mode):
        super().__init__()
        self._mode = mode
        self._manager = manager
        self._status = StatusDictionary()

    def on_next(self, verdict):
        logger.info("Container {0} is detected to violate the rule \"{1}\". {2} the container [{3} mode]"
                    .format(verdict.subject, json.dumps(verdict.reasons),
                            "Not stopping" if self._mode == Mode.Warn else "Stopping", self._mode))
        self.register_kill(verdict)
        if self._mode == Mode.Kill:
            self._manager.kill_container(verdict.subject)

    def on_error(self, e):
        logger.warning("An error occurred while trying to check running containers")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")

    def get_stats(self):
        return self._status.copy()

    def register_kill(self, verdict):
        self._status.register_killed(verdict)


class TriggerHandler(Observer):
    def __init__(self):
        super().__init__()
        self._triggers = triggers

    def on_next(self, verdict):
        for trigger in self._triggers:
            try:
                trigger["trigger"](verdict)
            except Exception as e:
                logger.error("During execution of trigger {0} exception was raised: {1}".format(trigger, e))

    def on_error(self, e):
        logger.warning("An error occurred while waiting for detections")
        logger.exception(e)

    def on_completed(self):
        logger.error("This should never happen. Please contact the dev")
