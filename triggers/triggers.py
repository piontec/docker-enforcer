import json
import threading

from flask import logging

logger = logging.getLogger("docker_enforcer")

triggers = [
    {
        "name": "additional log verdict",
        "trigger": lambda v: logger.debug("[{0}] Trigger: container {1} is detected to violate the rule \"{2}\"."
                                          .format(threading.current_thread().name, v.container, json.dumps(v.reasons)))
    }
]
