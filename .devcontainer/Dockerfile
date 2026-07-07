FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

WORKDIR /workspace

COPY app/requirements.txt /tmp/pip-tmp/api-requirements.txt
COPY apscheduler/requirements.txt /tmp/pip-tmp/worker-requirements.txt
COPY shared/requirements.txt /tmp/pip-tmp/shared-requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/pip-tmp/shared-requirements.txt \
    && pip install --no-cache-dir -r /tmp/pip-tmp/api-requirements.txt \
    && pip install --no-cache-dir -r /tmp/pip-tmp/worker-requirements.txt \
    && rm -rf /tmp/pip-tmp