import logging
import signal
import sys
import threading
from logging import StreamHandler

from flask import Flask
from rx import Observable
from rx.linq.observable.interval import interval
from rx.testing.dump import dump

from dockerenforcer.config import Config
from dockerenforcer.docker_fetcher import DockerFetcher
from dockerenforcer.rules import rules
from dockerenforcer.killer import Killer


config = Config()
fetcher = DockerFetcher(config, rules)
jurek = Killer(fetcher, config.mode)


def not_on_white_list(container):
    return container.params and container.params['Name'] \
        and container.params['Name'] not in config.white_list


def create_app():
    flask_app = Flask(__name__)

    if not flask_app.debug:
        handler = StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        flask_app.logger.addHandler(handler)
        flask_app.logger.setLevel(logging.DEBUG)

    detections = Observable.interval(config.interval_sec * 1000) \
        .map(lambda _: fetcher.check_containers()) \
        .dump(name="1") \
        .flat_map(lambda c: c) \
        .dump(name="2") \
        .where(lambda container: fetcher.should_be_killed(container)) \
        .where(lambda container: not_on_white_list(container))

    # remove self
    subscription = detections.subscribe(jurek)

    def on_exit(sig, frame):
        flask_app.logger.info("Stopping docker monitoring")
        subscription.dispose()
        flask_app.logger.debug("Complete, ready to finish")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    return flask_app


app = create_app()


@app.route('/')
def hello_world():
    return 'Hello, World! '
