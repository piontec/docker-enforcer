import logging
import signal
import sys
import threading
from logging import StreamHandler

from flask import Flask
from rx import Observable


padlock = threading.Lock()
counter = 0


def create_app():
    flask_app = Flask(__name__)

    if not flask_app.debug:
        handler = StreamHandler(stream=sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        flask_app.logger.addHandler(handler)
        flask_app.logger.setLevel(logging.DEBUG)

    def run_detection(_1, _2):
        flask_app.logger.debug("Starting checks of docker containers")
        global counter
        with padlock:
            counter += 1

    detections = Observable.interval(1000).map(run_detection)
    subscription = detections.subscribe(print)

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
    with padlock:
        val = counter
    return 'Hello, World! {0}'.format(val)
