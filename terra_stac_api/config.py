from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    role_admin: str = "stac-admin"
    role_editor: str = "stac-editor"
    role_anonymous: str = "anonymous"
    editor_public_collections: bool = False
    oidc_issuer: Optional[str] = None
    oidc_roles_claim: str = "realm_access.roles"
    stac_id: str = "terra-stac-api"
    stac_title: str = "terra-stac-api"
    stac_description: str = "STAC API"
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_methods: List[str] = Field(
        default_factory=lambda: ["OPTIONS", "GET", "POST"]
    )
    cors_allow_credentials: bool = True
