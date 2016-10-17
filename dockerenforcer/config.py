from enum import Enum


class Mode(Enum):
    Warn = 1
    Kill = 2


class Config:
    interval_sec = 5
    docker_socket = 'unix:///var/run/docker.sock'
    white_list = [
        'docker_enforcer',
    ]
    mode = Mode.Warn
