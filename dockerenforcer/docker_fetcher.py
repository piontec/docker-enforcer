from docker import Client


class DockerFetcher:
    def __init__(self, config):
        super().__init__()
        self.__config = config
        self.__client = Client(base_url=config.docker_socket)

    def check_containers(self):
        ids = [container['Id'] for container in self.__client.containers()]
        pass
