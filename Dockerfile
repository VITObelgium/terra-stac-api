FROM python:3.12-alpine

ARG PACKAGE_NAME
ARG USER=fastapi
ENV HOME=/home/$USER

RUN adduser -D $USER
USER $USER
WORKDIR $HOME
ENV PATH="$PATH:$HOME/.local/bin/"

COPY dist/$PACKAGE_NAME /src/$PACKAGE_NAME
COPY logging.conf /src/logging.conf

RUN pip install --no-cache-dir /src/$PACKAGE_NAME gunicorn==22.0.0

ENV WEB_CONCURRENCY=8

EXPOSE 8080

ENTRYPOINT [ \
    "gunicorn", \
    "terra_stac_api.app:app", \
    "--bind", "0.0.0.0:8080", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--log-config", "/src/logging.conf" \
]