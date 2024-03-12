import os

ROLE_ADMIN = os.getenv("ROLE_ADMIN", "stac-admin")
ROLE_EDITOR = os.getenv("ROLE_EDITOR", "stac-editor")
ROLE_ANONYMOUS = "anonymous"
EDITOR_PUBLIC_COLLECTIONS = (
    os.getenv("EDITOR_PUBLIC_COLLECTIONS", "false").lower() == "true"
)

OIDC_ISSUER = os.getenv("OIDC_ISSUER")

STAC_ID = os.getenv("STAC_ID", "terra-stac-api")
STAC_TITLE = os.getenv("STAC_TITLE", "terra-stac-api")
STAC_DESCRIPTION = os.getenv("STAC_DESCRIPTION", "STAC API")
