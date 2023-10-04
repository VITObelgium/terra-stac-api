FROM python:3.10-alpine

ARG PACKAGE_NAME
COPY dist/$PACKAGE_NAME /tmp/$PACKAGE_NAME

RUN pip install /tmp/$PACKAGE_NAME

ENTRYPOINT uvicorn terra_stac_api.app:app