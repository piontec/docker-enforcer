import logging
import sched
import signal
import threading
import time
from logging import StreamHandler
from threading import Thread

import sys
from flask import Flask

keep_running = True
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

    scheduler = sched.scheduler(time.time, time.sleep)

    def on_exit(sig, frame):
        flask_app.logger.info("Stopping docker monitoring")
        global keep_running
        keep_running = False
        thread.join()
        flask_app.logger.debug("Threads complete, ready to finish")
        raise KeyboardInterrupt()

    def start_something():
        flask_app.logger.debug("Starting background thread")
        scheduler.enter(1, 1, do_something)
        scheduler.run()

    def do_something():
        if not keep_running:
            return
        flask_app.logger.debug("Working...")
        global counter
        with padlock:
            counter += 1
        # do your stuff
        scheduler.enter(1, 1, do_something)

    thread = Thread(target=start_something)
    thread.start()
    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    return flask_app

app = create_app()


@app.route('/')
def hello_world():
    with padlock:
        val = counter
    return 'Hello, World! {0}'.format(val)
