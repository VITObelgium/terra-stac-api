FROM python:3.10-alpine

ARG PACKAGE_NAME
COPY dist/$PACKAGE_NAME /src/$PACKAGE_NAME
COPY logging.conf /src/logging.conf

RUN pip install --no-cache-dir /src/$PACKAGE_NAME gunicorn==21.2.0

ENV WEB_CONCURRENCY=8

EXPOSE 8080

ENTRYPOINT [ \
    "gunicorn", \
    "terra_stac_api.app:app", \
    "--bind", "0.0.0.0:8080", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--log-config", "/src/logging.conf" \
]