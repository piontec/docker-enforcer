import json
import threading
import logging

logger = logging.getLogger("docker_enforcer")

request_rules = [
    {
        "name": "always false",
        "rule": lambda request: False
    }
]
