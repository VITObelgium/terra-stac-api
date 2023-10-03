FROM python:3.10-slim

ARG PACKAGE_NAME
COPY dist/$PACKAGE_NAME /tmp/$PACKAGE_NAME

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


RUN pip install /tmp/$PACKAGE_NAME

ENTRYPOINT uvicorn terra_stac_api.app:app