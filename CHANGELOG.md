## [1.3.0] - 2026-11-03

### 🚀 Features

- Upgrade to SFEOS v8.0.0
  - added collection-search extension
  - support for sub-catalogs (not enabled in terra-stac-api)
  - added stac-validator
  - added sortables extension
  - CQL2 text parsing switched from `pygeofilter` to `cql2` library
- Automatic migration of index templates and indices on startup: outdated templates are updated and outdated
  indices are reindexed. Can be disabled with `MIGRATE_ON_STARTUP=false`.
- Application factory pattern, use Uvicorn/Gunicorn `--factory` option to run the application.

### Migration guide
The automatic migration of index templates and indices on startup is enabled by default. 
Outdated templates are updated and outdated collection indices are reindexed.

To support the collection-search extension with the `sortby` parameter, it is recommended to add a keyword mapping for the _title_ field.
The default mapping in previous versions was text-only, which does not support sorting. The new mapping for the _title_ field is a multi-field mapping with both text and keyword sub-fields.

## [1.2.0] - 2025-12-09

### 🚀 Features

- Upgrade SFEOS to v6.7.6
  - added sort, query, filter and fields extension to item collection route
  - corrected result count fields to `numberReturned` and `numberMatched`
  - added collection search extension
  - removed listing of collections on landing page
  - added `previous` pagination links through Redis caching

## [1.1.0] - 2025-08-05

### 🚀 Features

- Upgrade SFEOS to v6.1.0