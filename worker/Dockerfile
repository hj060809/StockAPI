FROM python:3.12-slim
WORKDIR /app

COPY shared/requirements.txt ./shared-requirements.txt
COPY worker/requirements.txt ./worker-requirements.txt

RUN pip install --no-cache-dir -r shared-requirements.txt \
    && pip install --no-cache-dir -r worker-requirements.txt

COPY shared/ ./shared/
COPY worker/ ./worker/

RUN pip install --no-cache-dir -e ./shared --no-deps

ENV PYTHONPATH=/app:/app/shared

CMD ["python", "-m", "worker.worker"]
