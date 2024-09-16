import json
import typing
import urllib.parse
import urllib.request
from enum import Enum
from typing import Callable, List, Optional

import jsonpath_ng
from fastapi import Depends, HTTPException, Request
from fastapi.openapi.models import (
    OAuth2,
    OAuthFlowAuthorizationCode,
    OAuthFlowClientCredentials,
    OAuthFlowImplicit,
    OAuthFlowPassword,
    OAuthFlows,
)
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    BaseUser,
    SimpleUser,
    UnauthenticatedUser,
)
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from terra_stac_api.config import Settings

settings = Settings()


class GrantType(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    IMPLICIT = "implicit"
    PASSWORD = "password"


def fetch_well_known(issuer: str) -> dict:
    issuer = issuer if issuer.endswith("/") else issuer + "/"
    url = urllib.parse.urljoin(issuer, ".well-known/openid-configuration")
    with urllib.request.urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError("Failed to fetch OIDC well-known configuration")
        return json.load(response)


def fetch_jwks(well_known: dict) -> dict:
    url = well_known["jwks_uri"]
    with urllib.request.urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError("Failed to fetch OIDC JWKS")
        return json.load(response)


def on_auth_error(request: Request, exc: AuthenticationError):
    return JSONResponse(
        content={"detail": str(exc)},
        status_code=HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


class OIDC(SecurityBase, AuthenticationBackend):
    def __init__(
        self,
        issuer: str,
        *,
        scheme_name: Optional[str] = "OpenID Connect",
        allowed_grant_types: List[GrantType] = list(GrantType),
        jwt_decode_options: Optional[dict] = None,
    ):
        self.scheme_name = scheme_name
        self.jwt_decode_options = jwt_decode_options

        self.well_known = fetch_well_known(issuer)
        self.jwks = fetch_jwks(self.well_known)

        flows = OAuthFlows()
        grant_types = set(self.well_known["grant_types_supported"])
        grant_types = grant_types.intersection(allowed_grant_types)
        token_endpoint = self.well_known["token_endpoint"]
        authz_endpoint = self.well_known["authorization_endpoint"]

        if GrantType.PASSWORD in grant_types:
            flows.password = OAuthFlowPassword(tokenUrl=token_endpoint)

        if GrantType.AUTHORIZATION_CODE in grant_types:
            flows.authorizationCode = OAuthFlowAuthorizationCode(
                authorizationUrl=authz_endpoint, tokenUrl=token_endpoint
            )

        if GrantType.CLIENT_CREDENTIALS in grant_types:
            flows.clientCredentials = OAuthFlowClientCredentials(
                tokenUrl=token_endpoint
            )

        if GrantType.IMPLICIT in grant_types:
            flows.implicit = OAuthFlowImplicit(authorizationUrl=authz_endpoint)

        self.model = OAuth2(flows=flows)
        self._roles_claim_path = jsonpath_ng.parse(settings.oidc_roles_claim)

    async def authenticate(
        self, conn: HTTPConnection
    ) -> typing.Optional[typing.Tuple["AuthCredentials", "BaseUser"]]:
        """
        Get the user information and credentials for the request.
        :param conn:
        :return: AuthCredentials and User object if user is successfully authenticated, otherwise None
        """
        authz_header = conn.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authz_header)

        if not authz_header or scheme.lower() != "bearer":
            return AuthCredentials([settings.role_anonymous]), UnauthenticatedUser()

        try:
            claims = jwt.decode(param, self.jwks, options=self.jwt_decode_options)
            scopes = self._roles_claim_path.find(claims)[0].value
            scopes.append(settings.role_anonymous)
        except JWTError:
            raise AuthenticationError("Invalid token")
        return AuthCredentials(scopes), SimpleUser(claims["preferred_username"])

    def require_any_role(self, *roles: str) -> Callable:
        async def _role_require(request: Request, authenticated=Depends(self)):
            if not any(role in request.auth.scopes for role in roles):
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)

        return _role_require

    async def __call__(self, request: Request):
        if not request.user.is_authenticated:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )


class NoAuth(AuthenticationBackend):
    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        return AuthCredentials([settings.role_anonymous]), UnauthenticatedUser()
