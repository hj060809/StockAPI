FROM python:3.12-slim
WORKDIR /app

COPY shared/requirements.txt ./shared-requirements.txt
COPY app/requirements.txt ./api-requirements.txt

RUN pip install --no-cache-dir -r shared-requirements.txt \
    && pip install --no-cache-dir -r api-requirements.txt

COPY shared/ ./shared/
COPY app/ ./app/

RUN pip install --no-cache-dir -e ./shared --no-deps

ENV PYTHONPATH=/app:/app/shared
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]