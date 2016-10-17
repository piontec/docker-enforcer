class Config:
    interval_sec = 5
    docker_socket = 'unix:///var/run/docker.sock'
    white_list = [
        'docker_enforcer',
    ]
