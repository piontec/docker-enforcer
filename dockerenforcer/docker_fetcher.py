from docker import Client


class Container:
    def __init__(self, cid, params, metrics):
        super().__init__()
        self.metrics = metrics
        self.params = params
        self.cid = cid

    def __str__(self, *args, **kwargs):
        return self.params['Name'] if self.params['Name'] else self.cid


class DockerFetcher:
    def __init__(self, config, rules):
        super().__init__()
        self.__rules = rules
        self.__config = config
        self.__client = Client(base_url=config.docker_socket)

    def check_containers(self):
        res = []

        ids = [container['Id'] for container in self.__client.containers()]
        for container_id in ids:
            params = self.__client.inspect_container(container_id)
            metrics = self.__client.stats(container=container_id, decode=True, stream=False)
            res.append(Container(container_id, params, metrics))
        return res

    def should_be_killed(self, container):
        if not (container and container.params and container.metrics):
            return False

        for rule in self.__rules:
            if rule(container):
                return True
        return False

    def kill_container(self, container):
        self.__client.stop(container.params['Id'])
