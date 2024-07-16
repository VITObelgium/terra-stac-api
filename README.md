# `terra-stac-api`

![Architecture of terra-stac-api](assets/architecture.svg)

## Configuration

The application can be configured via environment variables. Here is an overview of the most important settings:

| Environment variable        | Description                                                              | Default value |
|-----------------------------|--------------------------------------------------------------------------|---------------|
| `ES_HOST`                   | Elasticsearch host                                                       |               |
| `ES_PORT`                   | Elasticsearch port                                                       |               |
| `ES_USE_SSL`                | Use SSL to connect to Elasticsearch                                      | true          |
| `ES_VERIFY_CERTS`           | Verify certificates for Elasticsearch                                    | true          |
| `CURL_CA_BUNDLE`            | CA certificates for Elasticsearch                                        |               |
| `STAC_COLLECTIONS_INDEX`    | Collection index in Elasticsearch                                        | collections   |
| `STAC_ITEMS_INDEX_PREFIX`   | Prefix for Item indices in Elasticsearch                                 | items_        |
| `OIDC_ISSUER`               | OIDC token issuer. When not provided, auth integration will be disabled. |               |
| `ROLE_ADMIN`                | Role for admin users                                                     | stac-admin    |
| `ROLE_EDITOR`               | Role for editors                                                         | stac-editor   |
| `EDITOR_PUBLIC_COLLECTIONS` | Indicates whether editors can create public collections                  | false         |


## Dependencies
The `terra-stac-api` application relies on a **OpenSearch** / **Elasticsearch** database to store the STAC Collections and Items.
The necessary indices will be created automatically by the application on application start-up (collections index) or when creating new collections (item index). 

> [!IMPORTANT]
> If you want to run multiple instances of the `terra-stac-api` with same OpenSearch / Elasticsearch instance, 
> make sure to properly configure the `STAC_COLLECTIONS_INDEX` and `STAC_ITEMS_INDEX_PREFIX` to be unique and prefix-free.

## Collection authorization

Specific authorizations on collections can be configured in the STAC collection document. You can grant read and write
access to specific roles with the `_auth` field.
A special 'role' is dedicated to unauthenticated users: **anonymous**. Only users with role `$ROLE_ADMIN` can create
collections open to the public.
For example:

```json
{
  "_auth": {
    "read": [
      "anonymous"
    ],
    "write": [
      "stac-admin",
      "stac-editor"
    ]
  }
}
```

If you don't want to store the collection authorizations in your STAC document, you can also send these details as HTTP
query parameters when creating the collection. These parameters are `_auth_read` and `_auth_write`. Multiple roles can
be provided by specifying the query parameter multiple times.

```http
POST /collections?_auth_read=anonymous&_auth_write=stac-admin&_auth_write=stac-editor
```

## Development

To start developing on this project, you should install all needed dependencies for running and testing the code:

```shell
$ pip install -e .[dev]
```

This will also install linting and formatting tools, which are automatically executed when you commit using Git.
To set up pre-commit as a Git hook, run

```shell
$ pre-commit install
```

## Testing

Running the tests requires an active Elasticsearch cluster. By default, it will look for an Elasticsearch cluster on the
local host, port 9200.

In the Jenkins pipeline, we will run an Elasticsearch process in the test container.
If you want to run the tests locally, you can use the Docker compose file `elasticsearch/docker-compose.yml`.