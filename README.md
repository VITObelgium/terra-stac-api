# `terra-stac-api`

## Configuration

The application can be configured via environment variables. Here is an overview of the most important settings:

| Environment variable      | Description                              | Default value |
| ------------------------- | ---------------------------------------- | ------------- |
| `ES_HOST`                 | Elasticsearch host                       |               |
| `ES_PORT`                 | Elasticsearch port                       |               |
| `ES_USE_SSL`              | Use SSL to connect to Elasticsearch      | true          |
| `ES_VERIFY_CERTS`         | Verify certificates for Elasticsearch    | true          |
| `CURL_CA_BUNDLE`          | CA certificates for Elasticsearch        |
| `STAC_COLLECTIONS_INDEX`  | Collection index in Elasticsearch        | collections   |
| `STAC_ITEMS_INDEX_PREFIX` | Prefix for Item indices in Elasticsearch | items_        |
| `OIDC_ISSUER`             | OIDC token issuer                        |               |
| `ROLE_ADMIN`              | Role for admin users                     |               |
| `ROLE_EDITOR`             | Role for editors                         |               |