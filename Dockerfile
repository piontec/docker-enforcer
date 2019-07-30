FROM python:3-alpine
MAINTAINER Łukasz Piątkowski <piontec@gmail.com>

COPY Pipfile* /opt/docker_enforcer/
WORKDIR /opt/docker_enforcer/
RUN pip install pipenv
RUN pipenv install --deploy --ignore-pipfile --system
COPY . /opt/docker_enforcer/

ENTRYPOINT ["gunicorn"]
CMD ["-w", "1", "--threads", "16", "-b", "0.0.0.0:8888", "--access-logfile", "/var/log/docker_enforcer.log", "--error-logfile", "-", "--log-level", "info", "--timeout", "120", "docker_enforcer:app"]
