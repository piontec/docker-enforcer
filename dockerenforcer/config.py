from enum import Enum
from json import JSONEncoder
import os
import copy
import docker_enforcer


class Mode(Enum):
    Warn = 1
    Kill = 2


class Config:

    def __init__(self):
        super().__init__()
        self.interval_sec = int(os.getenv('CHECK_INTERVAL_S', '600'))
        self.docker_req_timeout_sec = int(os.getenv('DOCKER_REQ_TIMEOUT_S', '30'))
        self.docker_socket = os.getenv('DOCKER_SOCKET', 'unix:///var/run/docker.sock')
        self.white_list = os.getenv('WHITE_LIST', 'docker-enforcer docker_enforcer').split()
        self.mode = Mode[os.getenv('MODE', 'WARN').lower().capitalize()]
        self.cache_params = bool(os.getenv('CACHE_PARAMS', 'True') == 'True')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.disable_params = bool(os.getenv('DISABLE_PARAMS', 'False') == 'True')
        self.disable_metrics = bool(os.getenv('DISABLE_METRICS', 'False') == 'True')
        self.run_start_events = bool(os.getenv('RUN_START_EVENTS', 'False') == 'True')
        self.run_periodic = bool(os.getenv('RUN_PERIODIC', 'True') == 'True')


class ConfigEncoder(JSONEncoder):
    def default(self, o):
        out_dict = copy.deepcopy(o).__dict__
        mode = out_dict.pop("mode")
        out_dict["mode"] = mode.__str__()
        out_dict["version"] = docker_enforcer.version
        return out_dict
