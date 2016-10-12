import sched
import signal
import threading
import time
from threading import Thread
from flask import Flask

keep_running = True
padlock = threading.Lock()
counter = 0


def create_app():
    flask_app = Flask(__name__)
    # thread = None
    s = sched.scheduler(time.time, time.sleep)

    def on_exit(sig, frame):
        print("stopping")
        global keep_running
        keep_running = False
        thread.join()
        print("Threads complete, ready to finish")
        raise KeyboardInterrupt()

    def start_something():
        print("stuff start")
        s.enter(1, 1, do_something)
        s.run()

    def do_something():
        if not keep_running:
            return
        print("Doing stuff...")
        global counter
        with padlock:
            counter += 1
        # do your stuff
        s.enter(1, 1, do_something)

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
