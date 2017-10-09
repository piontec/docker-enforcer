# docker enforcer 
[![Build Status](https://travis-ci.org/piontec/docker-enforcer.png?branch=develop)](https://travis-ci.org/piontec/docker-enforcer)
[![Coverage Status](https://coveralls.io/repos/github/piontec/docker-enforcer/badge.svg?branch=develop)](https://coveralls.io/github/piontec/docker-enforcer?branch=develop)

## Why?
Docker enforcer audits containers running on a shared docker host. The aim of docker enforcer is to
stop containers running on a single host, but not obeying rules configured by the host's administrator. These rules may restrict values used as container's parameters or values reported by container's performance metrics.

## Index
* [How - Configuring and Running](#how-configuring-and-running)
  * [Preparing the rules file](#preparing-the-rules-file)
  * [Configuration options](#configuration-options)
  * [Running custom code for whitelist evaluation](running-custom-code-for-whitelist-evaluation)
  * [Running additional actions when a rule violation is detected](#running-additional-actions-when-a-rule-violation-is-detected)
  * [Filtering docker API requests](#filtering-docker-api-requests)
  * [Run modes](#run-modes)
  * [Recommended mode setup for production hosts](#recommended-mode-setup-for-production-hosts)
  * [Running enforcer as a container](#running-enforcer-as-a-container)
  * [Running enforcer as a system service with systemd](#running-enforcer-as-a-system-service-with-systemd)
* [Accessing data about running docker enforcer container](#accessing-data-about-running-docker-enforcer-container)

## How - Configuring and Running
It's the easiest to run docker enforcer as a container. Before starting, pay attention to a few facts:
- Docker enforcer needs to be run as a privileged container and needs access to the docker socket.
- To keep the rule expressions as elastic as possible, they are directly stored as python code. This
is a security risk, as any python code put into the rules file will be executed in a privileged
container with access to the docker socket. Make sure that you rules file has restricted access and
can be modified only by the root user.
- Docker enforcer can kill itself if you're not paying attention (when running as a container)! You
can protect it from stopping itself by using the white list contains rules to never kill containers
named 'docker-enforcer' or 'docker_enforcer'.
- You can always exclude some containers from being killed due to rules evaluation by including their
name in the white list (see configuration options).
 
### Preparing the rules file
Docker-enforcer works by checking a set of rules against the containers that are running on the docker
host. Each of the rules is applied to data about each container. Rules indicate which container should
be killed, so if any of the rules returns `True`, the container will be stopped (unless it's on the
white list).
The rules file must include a python list of dictionaries, where each of the dictionaries is a single
rule. The rule includes its name and a lambda function, which contains evaluation logic. Container's
data that can be checked by a rule includes the following properties:
- `position` - the sequence number of the container on the list of all containers, sorted by the start
date,
- `params` - a dictionary of parameters used to start this container (for example with `docker run`),
- `metrics` - a dictionary of performance metrics reported by the docker daemon for the container.
 
The rules file is evaluated against all running containers each `CHECK_INTERVAL_S` seconds. Also, all
rules are evaluated against a single container, when the container is being started.
The very basic rules file, that doesn't stop any container looks like this (this is also the default
list set):
```python
rules = [
    {
        "name": "always false",
        "rule": lambda c: False
    }
]
```
This creates just a single rule, which has name "always false" and matches no container (so, no container
will be ever stopped because of this rule).

#### Sample rules - using container's configuration parameters (static)
1. All containers must have memory limits set:
```python
    {
        "name": "must have memory limit", 
        "rule": lambda c: c.params['HostConfig']['Memory'] == 0
    }
```
2. Must have CPU quota set:
```python
    {
        "name": "must have CPU limit",
        "rule": lambda c: c.params['HostConfig']['CpuQuota'] == 0
    }
```
3. Limit the number of containers running on the host:
```python
    {
        "name": "no more than 3",
        "rule": lambda c: c.position >= 3
    }
```
4. Can use host mapped volumes only from `/opt/mnt1` or `/opt/mnt2` on the host:
```python
    {
        "name": "uses valid dirs for volumes",
        "rule": lambda c: False if c.params['HostConfig']['Binds'] is None else not all([b.startswith("/opt/mnt1") or b.startswith("/opt/mnt2") for b in c.params['HostConfig']['Binds']])
    }
```


#### Sample rules - using container's usage metrics (dynamic)
1.
```python
rules = [
    {
        "name": "can't use over 1GB of RAM",
        "rule": lambda c: c.metrics['memory_stats']['usage'] > 1 * 1024 ** 3
    }
]
```

You can see an example of the full list of parameters available (except `position`) in the file
[test_helpers.py](test_helpers.py).

### Configuration options
All the configuration options are loaded from environment variables, which makes them pretty easy to
configure when running as docker container (by passing to docker with `-e KEY=VAL` added to the run
command above).
The following options are supported (values after '=' below are the defaults):
- "RUN_PERIODIC=True" - enables Periodic run mode,
- "RUN_START_EVENTS=False" - enables Events run mode,
- "CHECK_INTERVAL_S=600" - if RUN_PERIODIC is enabled, sets how often the periodic check of containers
is started
- "DOCKER_SOCKET=unix:///var/run/docker.sock" - path to the docker Unix socket, default should be OK in
most cases; you can run against a remote host by passing a value like `10.20.30.40:2375`
- "DOCKER_REQ_TIMEOUT_S=30" - a timeout for communication between the enforcer and the docker daemon;
when the docker daemon is heavily stressed, it might respond very slowly and it's better to fail and
retry later,
- "MODE=WARN" - by default docker enforcer runs in a 'WARN' mode, where violations of rules are logged,
but the containers are never actually stopped; to enable containers stopping, set this to 'KILL'
- "CACHE_PARAMS=True" - by default docker-enforcer is caching indefinitely "params" section of container
data in order to decrease the number of calls to docker daemon. Set this to "False" to always query the
daemon.
- "LOG_LEVEL=INFO" - set python logging level for the software
- "DISABLE_PARAMS=False" - disable container's parameters fetching; this decreases the number of
requests made to the docker daemon, but you can't use any rules that refer to `c.params` property
- "DISABLE_METRICS=False" - disable container's metrics fetching; this decreases the number of requests
made to the docker daemon (metrics fetching is quite heavy), but you can't use any rules that refer to
`c.metrics` property when this is disabled; using metrics based rules requires running in
[periodic mode](#periodic-mode)
- "IMMEDIATE_PERIODICAL_START=False" - normally, when the enforcer is started in Periodic mode, it waits
CHECK_INTERVAL_S seconds and just then starts the first check; if you want the check to start
immediately after daemon startup - set this to True,
- "STOP_ON_FIRST_VIOLATION=True" - normally, docker enforcer stops checking validation rules after it
finds the first matching rules - this allows for a better performance; still, if you want to keep
checking all the rules and have all the violations, not only the first one, logged - set this to True,
- "LOG_AUTHZ_REQUESTS=False" - log all incoming docker API requests received in Authz mode. This logs
username (if available - only when TLS auth is used), HTTP method and URI for each received authorization
request. Of course, works only in Authz plugin mode.
- "DEFAULT_ACTION_ALLOW=True" - if any request is malformed and can't be parsed and evaluated, docker
enforcer allows this request if set to `True` and denies when `False`
- "WHITE_LIST=docker-enforcer,docker_enforcer" - pipe ('|') separated list of container name based white
list definitions, which allow to define a whitelist based on a container name. Each definition can be
(like in a sample value: "docker.\*,docker-enforcer|steal socket,docker.\*|steal socket"):
  - container name, like "docker-enforcer": this makes container named exactly "docker-enforcer" to be
  excluded from checks of all rules
  - container name regexp, like "docker.\*": this makes any container which name matches regex "docker.\*"
  to be excluded from checks of all rules
  - container and rule name, like "docker-enforcer|steal socket": this makes container named exactly
  "docker-enforcer" to be excluded from checking against the rule named "steal socket"
  - container name regexp and rule name, like "docker.\*|steal socket": this makes any container which
  name matches regex "docker.\*" to be excluded from checking against the rule named "steal socket"
- "IMAGE_WHITE_LIST=''" - pipe ('|') separated list of container image white list definitions, which allow to
define a whitelist based on a name of docker image used to create the container. Each definition
(like in a: "alpine.\*,alpine|steal socket, alpine.\*|steal socket") has the same syntax as in "WHITE_LIST"
above.

### Running custom code for whitelist evaluation
If the above usage of `WHITE_LIST` and `IMAGE_WHITE_LIST` is still not elastic enough for your needs, you
can implement your custom evaluation rules for the whitelist, like for [rules](#preparing-the-rules-file).
This time, the evaluation lambda takes 2 arguments: `lambda container, violated_rule_name` and it must
return `bool`. `container` is a full container info, like in `Rules[]`, while the 2nd argument provides
the name of the violated rule. If any of custom whitelist lambdas returns `True`, the container won't be
stopped.


### Running additional actions when a rule violation is detected
When a violation is detected, docker enforcer logs information about it and stops the container (only
in Kill mode). If you want to run some additional logic on this event, you can use a similar mechanism
as with the rules file. You can overwrite the file `triggers/triggers.py` and inject your own logic that
will be triggered on violation detection event. You can see an example trigger that does additional
logging in the default [triggers/triggers.py](triggers/triggers.py) file.

### Filtering docker API requests
*This feature is available only when running in [Authz plugin mode](#authz-plugin-mode).*
When running in Authz plugin mode, Docker Enforcer receives information from docker about all API calls
made by users to docker daemon. Normally, only requests creating or changing containers are processed
and passed for validation with `rules.py` rules file. However, you can also use Docker Enforcer to
authorize any API call made to docker. To use this, you need to implement another set of python lambdas
working as validation rules triggered for each request. You can see the default
[request_rules/request_rules.py](request_rules/request_rules.py) file for the default "always OK" rule,
but you can override it and include some custom ones. For example, the one below (included in
[tests](test/test_api.py)) forbids any `docker cp` commands to containers with name starting with "test":
```python
    cp_request_rule_regexp = re.compile("^/v1\.[23]\d/containers/test[a-zA-Z0-9_]*/archive$")
    cp_request_rule = {"name": "cp not allowed", "rule": lambda r, x=cp_request_rule_regexp:
                       r['RequestMethod'] in ['GET', 'HEAD'] and x.match(r['ParsedUri'].path)}
```

### Run modes
Docker Enforcer supports different run modes. In general, the modes above can be mixed, but you shouldn't
run "Events mode" and "Authz plugin mode" together. The supported modes are:

#### Periodic mode
In this mode, Docker Enforcer has a configured time period. When it passes, the enforcer connects to
docker daemon, fetches the list of all currently running containers and then runs all the rules against
every container on the list.

#### Events mode
In this mode, Docker Enforcer listens for container lifetime events from the docker daemon. Each time you
run or modify your container, you pass it a set of configuration options. This situation is also reported
by docker daemon for anyone willing to act on it. Docker enforcer listens for these events and then runs
all rules against the single container related to the event signalled by the docker daemon.

#### Authz plugin mode
In this mode, Docker Enforcer runs as
[docker authorization plugin](https://docs.docker.com/engine/extend/plugins_authorization/). As a result,
your users won't even be able to complete an API call that has parameters that don't validate with your
rules. In that case, an error message is returned to the user and the call is not executed by docker. This
mode additionally allows you to use [request rules](#filtering-docker-api-requests) for low level auditing
of API calls. This requires additional configuration of docker daemon, as below:
* You need to register your valid endpoint as docker plugin. To do this, create a file
`/etc/docker/plugins/enforcer.spec` with this single line:
```
tcp://127.0.0.1:5000
```
* You need to let know docker to use this plugin. The simplest way is to create (or add to your existing
one) docker configuration file in `/etc/docker/daemon.json` and be sure it includes the following JSON line:
```
{
"authorization-plugins": ["enforcer"]
}
```
* Using this creates a cyclic dependency between docker and docker enforcer running as a container (docker
needs docker enforcer to authorize any API call, but docker enforcer needs docker to start as a container).
To solve this problem, you need to
[run Docker Enforcer as a system service](#running-enforcer-as-a-system-service-with-systemd), not docker
container.

### Recommended mode setup for production hosts
In production, you might want a setup, that allows you to test new compliance rules on a production system,
but without hurting anybody by mistake, while enforcing your battle tested rules at the same time. The
solution is to run 2 docker enforcers at the same time:
- 1st - main Docker Enforcer: configured in Kill mode, running either in "Event+Periodic" or "Authz plugin"
mode; here you run your stable and tested compliance rules
- 2nd - auditing Docker Enforcer: configured in Warn mode only and running in "Event+Periodic" mode or just
one of them. Here you can test and audit your new rules, so that even if they don't work exactly as you
expected, no container is stopped, only logged.

### Running enforcer as a container
Put your `rules.py` file into a directory, for example `rules_dir`. Be sure to check your permissions on
this file, the code inside will be executed inside the enforcer's container! Then, run (minimal command):
```bash
docker run -d --name docker_enforcer \
  -p 8888:8888 \
  --privileged \
  -v /rules_dir:/opt/docker_enforcer/rules \
  -v /var/run:/var/run \
  tailoredcloud/docker-enforcer
```
After the successful run, a simple web API will be exposed to show current rules and status (see below).
You can access `http://localhost:8888/rules` to see the list of rules configured. This should be in sync
with the rules file you passed to the container.

### Running enforcer as a system service with systemd
Please follow the following steps:
* python at least 3.6+ is required
* download docker enforcer from [the release page](https://github.com/piontec/docker-enforcer/releases)
* extract it to some directory accessible only by system/docker admin (let's suppose `/opt/de`)
* (optional, but recommended) create a python virtual environment for running the service
* install python dependencies with `pip install -r requirements-prod.txt`
* overwrite default `rules.py`, `triggers.py` and `request_rules.py` files with your custom rules
* in the directory `/opt/de`, create a file named `environment.conf` and put there any required
[configuration options](#configuration-options) formatted one option per line as `OPTION=value`
* create service file for systemd as `/etc/systemd/system/docker_enforcer.service` using
[this template](systemd/docker_enforcer.service). Be sure to adjust `DE_PATH` to your service location
(`/opt/de` in our example) and `GUNICORN_PATH` to the place where `pip` installed `gunicorn` for you.
* (recommended) let `docker.service` in systemd know, that now docker-enforcer is "wanted" to be
running before docker starts. Create a directory `/etc/systemd/system/docker.service.d/` and a file
`docker.conf` in it. Put this into `docker.conf` file:
```
[Unit]
Wants=docker_enforcer.service
```
* reload service configuration in systemd
```
systemctl daemon-reload
```
* start docker enforcer
```
systemctl start docker_enforcer
```
* restart docker
```
systemctl restart docker
```

## Accessing data about running docker enforcer container
Docker enforcer exposes a simple HTTP API on the port 8888. If the "Accept:" header in client's request
includes HTML, a human-friendly JSON will be returned. Otherwise, plain text JSON is sent in response.
This currently includes the following endpoints:
- `/` - shows statistics about containers stopped by docker enforcer; shows all detections since starting
the service
- `/recent` - shows statistics about containers stopped by docker enforcer in the most recent periodic
run; makes sense only when "RUN_PERIODIC" is True
- `/metrics` - exposes the number of containers stopped since launch in the
[prometheus](https://prometheus.io/) data format,
- `/config` - shows the current version and configuration options of the daemon
- `/rules` - allows you to view the configured set of rules,
- `/request_rules` - allows you to view the configured set of request rules,
- `/triggers` - allows you to view the configured set of triggers.
  
Additionally, for `/` and `/recent` endpoints, you can append the following options in the URL (like:
`http://localhost:8888/?show_all_violated_rules=1&show_image_and_labels=1`):
- show_all_violated_rules=1 - if STOP_ON_FIRST_VIOLATION is set to False, then enabling this option will
show all violated rules; normally only the first one is reported,
- show_image_and_labels=1 - for any detected violation, show additionally image name used to start the
container and all of its labels.

