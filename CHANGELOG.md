# Changelog
## [1.3.0] - 2026-08-..

### 🚀 Features

- Upgrade to SFEOS v6.19.0
  - added collection-search extension
  - support for sub-catalogs (not enabled in terra-stac-api)
  - added stac-validator

### Migration guide
To support the collection-search extension with the `sortby` parameter, it is recommended to add a keyword mapping for the _title_ field.
The default mapping is text-only, which does not support sorting. You can add this mapping by running this application with the following environment variable:
```
STAC_FASTAPI_ES_COLLECTIONS_CUSTOM_MAPPINGS={"properties": {"title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}}}}
```

After the index template has been updated, you can reindex your collections to apply the new mapping.

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