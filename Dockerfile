FROM python:3.10-alpine

ARG PACKAGE_NAME
COPY dist/$PACKAGE_NAME /src/$PACKAGE_NAME
COPY logging.yaml /src/logging.yaml

RUN pip install --no-cache-dir /src/$PACKAGE_NAME

EXPOSE 8080
ENTRYPOINT ["uvicorn", "terra_stac_api.app:app", "--host", "0.0.0.0", "--port", "8080", "--log-config", "/src/logging.yaml"]