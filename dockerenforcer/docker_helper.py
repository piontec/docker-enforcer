from docker import Client


class Container:
    def __init__(self, cid, params, metrics, position):
        super().__init__()
        self.position = position
        self.metrics = metrics
        self.params = params
        self.cid = cid

    def __str__(self, *args, **kwargs):
        return self.params['Name'] if self.params['Name'] else self.cid


class DockerHelper:
    def __init__(self, config):
        super().__init__()
        self.__config = config
        self.__client = Client(base_url=config.docker_socket)

    def check_containers(self):
        res = []

        containers = sorted(self.__client.containers(), key=lambda c: c["Created"])
        ids = [container['Id'] for container in containers]
        counter = 0
        for container_id in ids:
            params = self.__client.inspect_container(container_id)
            metrics = self.__client.stats(container=container_id, decode=True, stream=False)
            counter += 1
            res.append(Container(container_id, params, metrics, counter))
        return res

    def get_start_events_observable(self):
        return self.__client.events(filters={"event": "start"}, decode=True)

    def check_container(self, container_id):
        params = self.__client.inspect_container(container_id)
        metrics = self.__client.stats(container=container_id, decode=True, stream=False)
        return Container(container_id, params, metrics, 0)

    def kill_container(self, container):
        self.__client.stop(container.params['Id'])
