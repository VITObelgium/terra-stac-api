## [1.3.1] - 2026-11-03

### 🚀 Features

- Upgrade to [SFEOS v8.0.0](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v800---2026-10-23)
  - added sortables endpoints for item and collection search, including authorization support
  - collection titles are sortable through automatic remapping to keyword sub-fields
  - bulk insert responses now contain structured `received`, `success`, `skipped` and `errors` fields
  - CQL2 text parsing switched from `pygeofilter` to `cql2`, adding support for more temporal and array expressions
- Automatic migration of index templates and indices on startup: outdated templates are updated and outdated
  indices are reindexed. Can be disabled with `MIGRATE_ON_STARTUP=false`.

### 🔧 Maintenance
- Require Python 3.14 or newer.
- Application factory pattern, use Uvicorn/Gunicorn `--factory` option to run the application.

### ⚠️ Changes

#### Deployment
- **Startup now modifies the database by default.** Outdated templates are updated and collection indices may be reindexed before startup completes. Ensure the database account has template, reindex and alias-management permissions, and allow time for migration. Set `MIGRATE_ON_STARTUP=false` to manage migrations separately.

#### End-users and API clients

- **Bulk insert response format changed.** Responses are now structured objects with `received`, `success`, `skipped` and `errors` fields instead of an unstructured string message. If you parsed this string message, update your code to parse the new structured response.
- **CQL2 operator precedence changed.** `a OR b AND c` now means `a OR (b AND c)`. Use explicit parentheses to retain the previous `(a OR b) AND c` behavior.
- **Item `PUT` no longer creates missing items.** It returns `404`; use `POST` to create items. With delayed index refresh, a newly created item must be searchable before it can be updated.
- **Updates can no longer rename resources.** Item and collection body IDs must match the URL; item collection IDs must also match. Mismatches return `400`.


## [1.3.0] - 2026-08-18

### 🚀 Features

- Upgrade to [SFEOS v6.19.0](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v6190---2026-06-23)
  - added configurable index mappings and wildcard field selection
  - added configurable root queryables, queryables caching and optional filter-field validation
  - improved free-text search with configurable fields, field boosting and typo tolerance
  - added optional STAC schema and geometry validation on ingestion
  - added upstream support for hierarchical catalogs and catalog-scoped search (not enabled in `terra-stac-api`)
  - fixed CQL2 `LIKE` filtering and pagination for items with time intervals
- Added collection-search conformance.
- Added configurable STAC version.
- Improved authorization filtering and aggregation endpoint behavior.

### ⚠️ Changes

#### Deployment
- Redis is now required when datetime-based indexing is enabled (`ENABLE_DATETIME_INDEX_FILTERING=true`).
SFEOS also adds an optional Redis queue for asynchronous item ingestion (`ENABLE_REDIS_QUEUE=true`).

## [1.2.2] - 2026-05-28

### 🚀 Features

- Added the requesting client's user agent to STAC request logs.

## [1.2.1] - 2026-02-11

### 🚀 Features

- Added filtering to `GET /collections/{collection_id}/items`.

## [1.2.0] - 2025-12-09

### 🚀 Features

- Upgrade to [SFEOS v6.7.6](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v676---2025-12-04)
  - added sort, query, filter and fields extension to item collection route
  - added collection search with spatial, datetime, free-text, CQL2, sorting and field-selection support
  - added optional datetime-based index partitioning and automatic rollover for large collections
  - improved asset indexing to avoid mapping explosion
  - improved datetime precision and consistency between GET and POST searches
  - removed listing of collections on landing page

### 🐛 Fixes
- Corrected result count fields to `numberReturned` and `numberMatched`

## [1.1.0] - 2025-08-05

### 🚀 Features

- Upgrade to [SFEOS v6.1.0](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v610---2025-07-24)
  - added JSON Patch and JSON Merge Patch support for items and collections
  - added dynamically generated queryables from index mappings
  - added CQL2 spatial operators `S_CONTAINS`, `S_WITHIN` and `S_DISJOINT`
  - extended datetime searches to items described by `start_datetime` / `end_datetime` intervals
  - improved search across large numbers of collection indices
  - added configurable bulk-insert error handling (`RAISE_ON_BULK_ERROR`) and index refresh behavior (`DATABASE_REFRESH`)

## [1.0.6] - 2025-06-16

### 🐛 Fixes

- Prevented collection summaries from being indexed.

## [1.0.5] - 2025-01-09

### 🔧 Maintenance

- Upgrade to [SFEOS v3.2.2](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v322---2024-12-15)
  - changed pagination tokens to base64-encoded JSON sort keys instead of comma-separated values
  - fixed aggregation total counts

## [1.0.4] - 2024-11-28

### 🐛 Fixes

- Prevented the collection `renders` field from being indexed.

## [1.0.3] - 2024-10-31

### 🐛 Fixes

- Allowed the `Authorization` header in CORS when credentials are enabled.

## [1.0.2] - 2024-10-15

### 🚀 Features

- Upgrade to [SFEOS v3.2.0](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v320---2024-10-09)
  - added the `datetime_frequency_interval` parameter to control datetime aggregation buckets
  - corrected collection and aggregation self links

## [1.0.1] - 2024-09-16

### 🚀 Features

- Made the roles claim path configurable for authorization.

## [1.0.0] - 2024-09-04

### 🚀 Features

- Introduced OIDC-based authorization, including collection checks for search and aggregation; deployments can also run without authentication.
- Added CORS support and upgraded to `stac-fastapi` v3.0.
- Upgrade to [SFEOS v3.1.0](https://github.com/stac-utils/stac-fastapi-elasticsearch-opensearch/blob/main/CHANGELOG.md#v310---2024-09-02)
