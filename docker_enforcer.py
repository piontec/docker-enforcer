import inspect
import json
import logging
import signal
import sys
from base64 import b64decode
from logging import StreamHandler

from flask import Flask, Response, request
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.data import JsonLexer
from pygments.lexers.python import Python3Lexer
from rx import Observable
from rx.concurrency import NewThreadScheduler
from urllib import parse

from dockerenforcer.config import Config, ConfigEncoder, Mode
from dockerenforcer.docker_helper import DockerHelper, Container, CheckSource
from dockerenforcer.killer import Killer, Judge, TriggerHandler
from rules.rules import rules
from request_rules.request_rules import request_rules

config = Config()
docker_helper = DockerHelper(config)
judge = Judge(rules, "container", config)
requests_judge = Judge(request_rules, "request", config, run_whitelists=False)
jurek = Killer(docker_helper, config.mode)
trigger_handler = TriggerHandler()


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
    flask_app.logger.info("Starting docker-enforcer v{0} with docker socket {1}".format(config.version,
                                                                                        config.docker_socket))

    task_scheduler = NewThreadScheduler()
    # task_scheduler = ThreadPoolScheduler(multiprocessing.cpu_count())
    if config.run_start_events:
        events = Observable.from_iterable(docker_helper.get_events_observable()) \
            .observe_on(scheduler=task_scheduler) \
            .where(lambda e: is_configured_event(e)) \
            .map(lambda e: e['id']) \
            .map(lambda cid: docker_helper.check_container(cid, CheckSource.Event, remove_from_cache=True))

    if config.run_periodic:
        periodic = Observable.interval(config.interval_sec * 1000)

        if config.immediate_periodical_start:
            flask_app.logger.debug("Run periodic immediately")
            periodic = periodic.start_with(-1)

        periodic = periodic.observe_on(scheduler=task_scheduler) \
            .map(lambda _: docker_helper.check_containers(CheckSource.Periodic)) \
            .flat_map(lambda c: c)

    detections = Observable.empty()
    if config.run_start_events:
        detections = detections.merge(events)
    if config.run_periodic:
        detections = detections.merge(periodic)

    verdicts = detections \
        .map(lambda container: judge.should_be_killed(container)) \
        .where(lambda v: v.verdict)

    threaded_verdicts = verdicts \
        .retry() \
        .subscribe_on(task_scheduler) \
        .publish() \
        .auto_connect(2)

    if not config.run_start_events and not config.run_periodic:
        flask_app.logger.info("Neither start events or periodic checks are enabled. Docker Enforcer will be working in "
                              "authz plugin mode only.")
    else:
        killer_subs = threaded_verdicts.subscribe(jurek)
        trigger_subs = threaded_verdicts.subscribe(trigger_handler)

    def on_exit(sig, frame):
        flask_app.logger.info("Stopping docker monitoring")
        if config.run_start_events or config.run_periodic:
            killer_subs.dispose()
            trigger_subs.dispose()
        flask_app.logger.debug("Complete, ready to finish")
        quit()

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    return flask_app


app = create_app()


def is_configured_event(e):
    if e['Action'] == 'rename' and config.run_rename_events:
        return True
    if e['Action'] == 'update' and config.run_update_events:
        return True
    if e['Action'] == 'start' and config.run_start_events:
        return True
    return False


@app.route('/rules')
def show_rules():
    if request.accept_mimetypes.accept_html:
        with open("rules/rules.py", "r") as file:
            data = file.read()
            html = highlight(data, Python3Lexer(), HtmlFormatter(full=True, linenos='table'))
            return Response(html, content_type="text/html")
    rules_txt = [{"name": d["name"], "rule": inspect.getsource(d["rule"]).strip().split(':', 1)[1].strip()} for d in
                 rules]
    data = json.dumps(rules_txt, sort_keys=True, indent=4, separators=(',', ': '))
    return Response(data, content_type="application/json")


@app.route('/metrics')
def show_metrics():
    data = jurek.get_stats().to_prometheus_stats_format()
    return Response(data, content_type="text/plain; version=0.0.4")


@app.route('/')
def show_stats():
    return show_filtered_stats(lambda _: True)


@app.route('/recent')
def show_recent_stats():
    return show_filtered_stats(lambda c: c.last_timestamp > docker_helper.last_check_containers_run_start_timestamp)


@app.route('/config')
def show_config():
    data = json.dumps(config, cls=ConfigEncoder, sort_keys=True, indent=4, separators=(',', ': '))
    return to_formatted_json(data)


def show_filtered_stats(stats_filter):
    show_all_violated_rules = request.args.get('show_all_violated_rules') == '1'
    show_image_and_labels = request.args.get('show_image_and_labels') == '1'

    data = '{{\n"last_full_check_run_timestamp_start": "{0}",\n' \
           '"last_full_check_run_timestamp_end": "{1}",\n' \
           '"last_full_check_run_time": "{2}",\n' \
           '"detections":\n{3}\n}}'.format(
        docker_helper.last_check_containers_run_start_timestamp,
        docker_helper.last_check_containers_run_end_timestamp,
        docker_helper.last_check_containers_run_time,
        jurek.get_stats().to_json_detail_stats(stats_filter, show_all_violated_rules, show_image_and_labels))
    return to_formatted_json(data)


def to_formatted_json(data):
    if request.accept_mimetypes.accept_html:
        html = highlight(data, JsonLexer(), HtmlFormatter(full=True, linenos='table'))
        return Response(html, content_type="text/html")
    return Response(data, content_type="application/json")


@app.route("/Plugin.Activate", methods=['POST'])
def activate():
    return to_formatted_json(json.dumps({'Implements': ['authz']}))


@app.route("/AuthZPlugin.AuthZRes", methods=['POST'])
def authz_response():
    return to_formatted_json(json.dumps({"Allow": True}))


@app.route("/AuthZPlugin.AuthZReq", methods=['POST'])
def authz_request():
    app.logger.debug("New AuthZ Request: {}".format(request.data))
    json_data = json.loads(request.data.decode(request.charset))
    url = parse.urlparse(json_data["RequestUri"])
    json_data["ParsedUri"] = url
    verdict = requests_judge.should_be_killed(json_data)
    if verdict.verdict:
        return process_positive_verdict(verdict, json_data, register=False)
    operation = url.path.split("/")[-1]
    if operation == "create" and "RequestBody" in json_data:
        int_bytes = b64decode(json_data["RequestBody"])
        int_json = json.loads(int_bytes.decode(request.charset))
        container = make_container_periodic_check_compatible(int_json, url)
        verdict = judge.should_be_killed(container)
        if verdict.verdict:
            return process_positive_verdict(verdict, json_data)
    return to_formatted_json(json.dumps({"Allow": True}))


def make_container_periodic_check_compatible(cont_json, url):
    url_params = parse.parse_qs(url.query)
    cont_json["Name"] = "<unnamed_container>" if "name" not in url_params else url_params["name"][0]
    cont_json["Config"] = {}
    cont_json["Config"]["Labels"] = cont_json["Labels"]
    return Container(cont_json["Name"], params=cont_json, metrics={}, position=0,
                     check_source=CheckSource.AuthzPlugin)


def process_positive_verdict(verdict, req, register=True):
    enhanced_info = "." if not hasattr(verdict.subject, "params") else " on container {}.".format(
        verdict.subject.params["Name"])
    if config.mode == Mode.Warn:
        app.logger.info("Authorization plugin detected rules violation for operation {}{}"
                        "Running in WARN mode, so the request is allowed anyway. Broken rules: {}"
                        .format(req["RequestUri"], enhanced_info, ", ".join(verdict.reasons)))
        reply = {"Allow": True}
    else:
        app.logger.info("Authorization plugin denied operation {}{} Broken rules: {}"
                        .format(req["RequestUri"], enhanced_info, ", ".join(verdict.reasons)))
        reply = {"Allow": False, "Msg": ", ".join(verdict.reasons)}

    trigger_handler.on_next(verdict)
    if register:
        jurek.register_kill(verdict)
    return to_formatted_json(json.dumps(reply))
