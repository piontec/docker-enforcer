from enum import Enum
import os


class Mode(Enum):
    Warn = 1
    Kill = 2


class Config:

    def __init__(self):
        super().__init__()
        self.interval_sec = int(os.getenv('CHECK_INTERVAL_S', '60'))
        self.docker_socket = os.getenv('DOCKER_SOCKET', 'unix:///var/run/docker.sock')
        self.white_list = os.getenv('WHITE_LIST', 'docker-enforcer docker_enforcer').split()
        self.mode = Mode[os.getenv('MODE', 'WARN').lower().capitalize()]
        self.cache_params = bool(os.getenv('CACHE_PARAMS', 'True'))
