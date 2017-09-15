# docker enforcer

## What for?
Docker enforcer audits containers running on a shared docker host. The aim of docker enforcer is to stop containers running on a single host, but not obeying rules configured by the host's administrator. These rules may restrict values used as container's parameters or values reported by container's performance metrics.
 
## How?
It's the easiest to run docker enforcer as a container. Before starting, pay attention to a few facts:
- Docker enforcer needs to be run as a privileged container and needs access to the docker socket.
- To keep the rule expressions as elastic as possible, they are directly stored as python code. This is a security risk, as any python code put into the rules file will be executed in a privileged container with access to the docker socket. Make sure that you rules file has restricted access and can be modified only by the root user.
- Docker enforcer can kill itself if you're not paying attention (when running as a container)! You can protect it from stopping itself by using the white list contains rules to never kill containers named 'docker-enforcer' or 'docker_enforcer'.
- You can always exclude some containers from being killed due to rules evaluation by including their name in the white list (see configuration options).
 
### Preparing rules file
Docker-enforcer works by checking a set of rules against the containers that are running on the docker host. Each of the rules is applied to data about each container. Rules indicate which container should be killed, so if any of the rules returns `True`, the container will be stopped (unless it's on the white list). 
The rules file must include a python list of dictionaries, where each of the dictionaries is a single rule. The rule includes its name and a lambda function, which contains evaluation logic. Container's data that can be checked by a rule includes the following properties:
- `position` - the sequence number of the container on the list of all containers, sorted by the start date,
- `params` - a dictionary of parameters used to start this container (for example with `docker run`),
- `metrics` - a dictionary of performance metrics reported by the docker daemon for the container.
 
The rules file is evaluated against all running containers each `CHECK_INTERVAL_S` seconds. Also, all rules are evaluated against a single container, when the container is being started.  
The very basic rules file, that doesn't stop any container looks like this (this is also the default list set):
```python
rules = [
    {
        "name": "always false",
        "rule": lambda c: False
    }
]
```
This creates just a single rule, which has name "always false" and matches no container (so, no container will be ever stopped because of this rule).

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

You can see an example of the full list of parameters available (except `position`) in the file [test_helpers.py](test_helpers.py).

### Running enforcer as a container
Put your `rules.py` file into a directory, for example `rules_dir`. Be sure to check your permissions on this file, the code inside will be executed inside the enforcer's container! Then, run (minimal command):
```bash
docker run -d --name docker_enforcer -p 8888:8888 --privileged -v /rules_dir:/opt/docker_enforcer/rules -v /var/run:/var/run tailoredcloud/docker-enforcer
```
After the successful run, a simple web API will be exposed to show current rules and status (see below). You can access `http://localhost:8888/rules` to see the list of rules configured. This should be in sync with the rules file you passed to the container.

#### Run modes
Currently, Docker Enforcer supports two different run modes. They can be used together, but at least one fo them must be enabled. The supported modes are:

##### Periodic mode
In this mode, Docker Enforcer has a configured time period. When it passes, the enforcer connects to docker daemon, fetches the list of all currently running containers and then runs all the rules against every container on the list. 

##### Events mode
In this mode, Docker Enforcer listens for container lifetime events from the docker daemon. Each time you run or modify your container, you pass it a set of configuration options. This situation is also reported by docker daemon for anyone willing to act on it. Docker enforcer listens for these events and then runs all rules against the single container related to the event signalled by the docker daemon.

#### Configuration options
All the configuration options are loaded from environment variables, which makes them pretty easy to configure when running as docker container (by passing to docker with `-e KEY=VAL` added to the run command above).
The following options are supported (values after '=' below are the defaults):
- "RUN_PERIODIC=True" - enables Periodic run mode,
- "RUN_START_EVENTS=False" - enables Events run mode,
- "CHECK_INTERVAL_S=600" - if RUN_PERIODIC is enabled, sets how often the periodic check of containers is started 
- "DOCKER_SOCKET=unix:///var/run/docker.sock" - path to the docker Unix socket, default should be OK in most cases; you can run against a remote host by passing a value like `10.20.30.40:2375`
- "DOCKER_REQ_TIMEOUT_S=30" - a timeout for communication between the enforcer and the docker daemon; when the docker daemon is heavily stressed, it might respond very slowly and it's better to fail and retry later, 
- "MODE=WARN" - by default docker enforcer runs in a 'WARN' mode, where violations of rules are logged, but the containers are never actually stopped; to enable containers stopping, set this to 'KILL'
- "CACHE_PARAMS=True" - by default docker-enforcer is caching indefinitely "params" section of container data in order to decrease the number of calls to docker daemon. Set this to "False" to always query the daemon.
- "LOG_LEVEL=INFO" - set python logging level for the software
- "DISABLE_PARAMS=False" - disable container's parameters fetching; this decreases the number of requests made to the docker daemon, but you can't use any rules that refer to `c.params` property
- "DISABLE_METRICS=False" - disable container's metrics fetching; this decreases the number of requests made to the docker daemon (metrics fetching is quite heavy), but you can't use any rules that refer to `c.metrics` property
- "IMMEDIATE_PERIODICAL_START=False" - normally, when the enforcer is started in Periodic mode, it waits CHECK_INTERVAL_S seconds and just then starts the first check; if you want the check to start immediately after daemon startup - set this to True,
- "STOP_ON_FIRST_VIOLATION=True" - normally, docker enforcer stops checking validation rules after it finds the first matching rules - this allows for a better performance; still, if you want to keep checking all the rules and have all the violations, not only the first one, logged - set this to True,
- "WHITE_LIST=docker-enforcer docker_enforcer" - comma separated white list of container names; containers on the won't be stopped even if they break the rules
 
### Accessing data about running docker enforcer container
Docker enforcer exposes a simple HTTP API on the port 8888. If the "Accept:" header in client's request includes HTML, a human-friendly JSON will be returned. Otherwise, plain text JSON is sent in response.  This currently includes the following endpoints:
- `/` - shows statistics about containers stopped by docker enforcer; shows all detections since starting the service
- `/recent` - shows statistics about containers stopped by docker enforcer in the most recent periodic run; makes sense only when "RUN_PERIODIC" is True
- `/metrics` - exposes the number of containers stopped since launch in the [prometheus](https://prometheus.io/) data format,
- `/config` - shows the current version and configuration options of the daemon
- `/rules` - allows you to view the configured set of rules.
  
Additionally, for `/` and `/recent` endpoints, you can append the following options in the URL (like: http://localhost:8888/?show_all_violated_rules=1&show_image_and_labels=1):
- show_all_violated_rules=1 - if STOP_ON_FIRST_VIOLATION is set to False, then enabling this option will show all violated rules; normally only the first one is reported,
- show_image_and_labels=1 - for any detected violation, show additionally image name used to start the container and all of its labels.

# TODO
- triggers