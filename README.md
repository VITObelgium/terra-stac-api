# `terra-stac-api`

## Configuration

The application can be configured via environment variables. Here is an overview of the most important settings:

| Environment variable      | Description                              | Default value |
|---------------------------|------------------------------------------|---------------|
| `ES_HOST`                 | Elasticsearch host                       |               | 
| `ES_PORT`                 | Elasticsearch port                       |               |
| `STAC_COLLECTIONS_INDEX`  | Collection index in Elasticsearch        | collections   |
| `STAC_ITEMS_INDEX_PREFIX` | Prefix for Item indices in Elasticsearch | items_        |
