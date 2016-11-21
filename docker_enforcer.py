import inspect
import json
import logging
import signal
import sys
from logging import StreamHandler

from flask import Flask
from flask import Response
from rx import Observable
from rx.concurrency import NewThreadScheduler

from dockerenforcer.config import Config
from dockerenforcer.docker_helper import DockerHelper
from dockerenforcer.killer import Killer, Judge
from rules.rules import rules

version = "0.3.2"
config = Config()
docker_helper = DockerHelper(config)
judge = Judge(rules)
jurek = Killer(docker_helper, config.mode)


def create_app():
    def setup_logging():
        handler = StreamHandler(stream=sys.stdout)
        handler.setLevel(config.log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        flask_app.logger.addHandler(handler)
        flask_app.logger.setLevel(config.log_level)
        flask_app.logger.name = "docker_enforcer"

    flask_app = Flask(__name__)
    if not flask_app.debug:
        setup_logging()

    flask_app.logger.info("Starting docker-enforcer v{0} with docker socket {1}".format(version, config.docker_socket))
    if not (config.run_start_events or config.run_periodic):
        raise ValueError("Either RUN_START_EVENTS or RUN_PERIODIC must be set to True")

    if config.run_start_events:
        start_events = Observable.from_iterable(docker_helper.get_start_events_observable()) \
            .observe_on(scheduler=NewThreadScheduler()) \
            .map(lambda e: e['id']) \
            .map(lambda cid: docker_helper.check_container(cid))

    if config.run_periodic:
        periodic = Observable.interval(config.interval_sec * 1000) \
            .start_with(-1) \
            .map(lambda _: docker_helper.check_containers()) \
            .flat_map(lambda c: c)

    if config.run_start_events and not config.run_periodic:
        detections = start_events
    elif not config.run_start_events and config.run_periodic:
        detections = periodic
    else:
        detections = start_events.merge(periodic)

    verdicts = detections \
        .where(lambda c: not_on_white_list(c)) \
        .map(lambda container: judge.should_be_killed(container)) \
        .where(lambda v: v.verdict)

    subscription = verdicts \
        .retry() \
        .subscribe_on(NewThreadScheduler()) \
        .subscribe(jurek)

    def on_exit(sig, frame):
        flask_app.logger.info("Stopping docker monitoring")
        subscription.dispose()
        flask_app.logger.debug("Complete, ready to finish")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    return flask_app


app = create_app()


def not_on_white_list(container):
    not_on_list = container.params and container.params['Name'] \
           and container.params['Name'][1:] not in config.white_list
    if not not_on_list:
        app.logger.debug("Container {0} is on white list".format(container.params['Name'][1:]))
    return not_on_list


@app.route('/rules')
def show_rules():
    rules_txt = [{"name": d["name"], "rule": inspect.getsource(d["rule"]).strip().split(':', 1)[1].strip()} for d in
                 rules]
    data = json.dumps(rules_txt)
    return Response(data, content_type="application/json")


@app.route('/metrics')
def show_metrics():
    data = jurek.get_stats().to_prometheus_stats_format()
    return Response(data, content_type="text/plain; version=0.0.4")


@app.route('/')
def show_stats():
    data = jurek.get_stats().to_json_detail_stats()
    return Response(data, content_type="application/json")
