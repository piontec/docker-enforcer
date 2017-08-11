import json
import threading

from flask import logging

logger = logging.getLogger("docker_enforcer")

request_rules = [
    {
        "name": "always false",
        "rule": lambda r: False
    }
]
