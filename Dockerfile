FROM python:3.10-alpine

ARG PACKAGE_NAME
COPY dist/$PACKAGE_NAME /tmp/$PACKAGE_NAME

RUN pip install --no-cache-dir /tmp/$PACKAGE_NAME

EXPOSE 8080
ENTRYPOINT ["uvicorn", "terra_stac_api.app:app", "--host", "0.0.0.0", "--port", "8080"]