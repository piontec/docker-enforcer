from enum import Enum
from json import JSONEncoder
import os
import copy
from typing import Dict

version = "0.8.15"


class Mode(Enum):
    Warn = 1
    Kill = 2


class Config:
    def __init__(self) -> None:
        super().__init__()
        self.interval_sec: int = int(os.getenv('CHECK_INTERVAL_S', '600'))
        self.docker_req_timeout_sec: int = int(os.getenv('DOCKER_REQ_TIMEOUT_S', '30'))
        self.docker_socket: str = os.getenv('DOCKER_SOCKET', 'unix:///var/run/docker.sock')
        self.white_list: str = os.getenv('WHITE_LIST', 'docker-enforcer,docker_enforcer').split(",")
        self.image_white_list: str = os.getenv('IMAGE_WHITE_LIST', '').split(",")
        self.mode: Mode = Mode[os.getenv('MODE', 'WARN').lower().capitalize()]
        self.cache_params: bool = bool(os.getenv('CACHE_PARAMS', 'True') == 'True')
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.disable_params: bool = bool(os.getenv('DISABLE_PARAMS', 'False') == 'True')
        self.disable_metrics: bool = bool(os.getenv('DISABLE_METRICS', 'False') == 'True')
        self.run_start_events: bool = bool(os.getenv('RUN_START_EVENTS', 'False') == 'True')
        self.run_update_events: bool = bool(os.getenv('RUN_UPDATE_EVENTS', 'False') == 'True')
        self.run_rename_events: bool = bool(os.getenv('RUN_RENAME_EVENTS', 'False') == 'True')
        self.run_periodic: bool = bool(os.getenv('RUN_PERIODIC', 'True') == 'True')
        self.immediate_periodical_start: bool = bool(os.getenv('IMMEDIATE_PERIODICAL_START', 'False') == 'True')
        self.stop_on_first_violation: bool = bool(os.getenv('STOP_ON_FIRST_VIOLATION', 'True') == 'True')
        self.log_authz_requests: bool = bool(os.getenv('LOG_AUTHZ_REQUESTS', 'False') == 'True')
        self.default_allow: bool = bool(os.getenv('DEFAULT_ACTION_ALLOW', 'True') == 'True')
        self.version: str = version
        self.white_list_separator: str = "|"


class ConfigEncoder(JSONEncoder):
    def default(self, o: Config) -> Dict[str, str]:
        out_dict = copy.deepcopy(o).__dict__
        mode = out_dict.pop("mode")
        out_dict["mode"] = mode.__str__()
        out_dict["version"] = version
        return out_dict
