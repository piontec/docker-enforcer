import logging
import signal
import sys
from logging import StreamHandler

from flask import Flask
from flask import Response
from rx import Observable

from dockerenforcer.config import Config
from dockerenforcer.docker_helper import DockerHelper
from dockerenforcer.rules import rules
from dockerenforcer.killer import Killer, Judge

config = Config()
fetcher = DockerHelper(config)
judge = Judge(rules)
jurek = Killer(fetcher, config.mode)


def not_on_white_list(container):
    return container.params and container.params['Name'] \
        and container.params['Name'] not in config.white_list


def create_app():

    def setup_logging():
        handler = StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        flask_app.logger.addHandler(handler)
        flask_app.logger.setLevel(logging.DEBUG)
        flask_app.logger.name = "docker_enforcer"

    flask_app = Flask(__name__)
    if not flask_app.debug:
        setup_logging()

    detections = Observable.interval(config.interval_sec * 1000) \
        .map(lambda _: fetcher.check_containers()) \
        .flat_map(lambda c: c) \
        .map(lambda container: judge.should_be_killed(container)) \
        .where(lambda v: v.verdict) \
        .where(lambda v: not_on_white_list(v.container))
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


@app.route('/metrics')
def show_metrics():
    data = jurek.get_stats().to_prometheus_stats_format()
    return Response(data, content_type="text/plain; version=0.0.4")


@app.route('/')
def show_stats():
    data = jurek.get_stats().to_json_detail_stats()
    return Response(data, content_type="application/json")
