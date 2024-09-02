from yarl import URL

ROLE_PROTECTED = "protected"
ROLE_ADMIN = "stac-admin"
ROLE_EDITOR = "stac-editor"
ROLE_SENTINEL2 = "sentinel2"

ENDPOINT_COLLECTIONS = URL("/collections")
ENDPOINT_SEARCH = URL("/search")
ENDPOINT_AGGREGATE = URL("/aggregate")
COLLECTION_PROTECTED = "protected"
COLLECTION_S2_TOC_V2 = "terrascope_s2_toc_v2"
