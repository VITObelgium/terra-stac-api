import json
import os
import typing
import urllib.parse
import urllib.request
from enum import Enum
from typing import Callable, Optional, List

from fastapi import Depends, Request, HTTPException
from fastapi.openapi.models import OAuthFlows, OAuthFlowPassword, OAuthFlowAuthorizationCode, \
    OAuthFlowClientCredentials, OAuthFlowImplicit, OAuth2
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, JWTError
from starlette.authentication import AuthenticationBackend, BaseUser, SimpleUser, AuthCredentials, AuthenticationError, \
    UnauthenticatedUser
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED


class GrantType(str, Enum):
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    IMPLICIT = "implicit"
    PASSWORD = "password"


ROLE_ANONYMOUS = "anonymous"


def fetch_well_known(issuer: str) -> dict:
    issuer = issuer if issuer.endswith("/") else issuer + '/'
    url = urllib.parse.urljoin(issuer, ".well-known/openid-configuration")
    with urllib.request.urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError("Failed to fetch OIDC well-known configuration")
        return json.load(response)


def fetch_jwks(well_known: dict) -> dict:
    url = well_known['jwks_uri']
    with urllib.request.urlopen(url) as response:
        if response.status != 200:
            raise RuntimeError("Failed to fetch OIDC JWKS")
        return json.load(response)


def on_auth_error(request: Request, exc: AuthenticationError):
    return JSONResponse(
        content={
            "detail": str(exc)
        },
        status_code=HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"}
    )


class OIDC(SecurityBase, AuthenticationBackend):
    def __init__(
            self,
            issuer: str,
            *,
            scheme_name: Optional[str] = "OpenID Connect",
            allowed_grant_types: List[GrantType] = list(GrantType),
            jwt_decode_options: Optional[dict] = None
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
                authorizationUrl=authz_endpoint,
                tokenUrl=token_endpoint
            )

        if GrantType.CLIENT_CREDENTIALS in grant_types:
            flows.clientCredentials = OAuthFlowClientCredentials(tokenUrl=token_endpoint)

        if GrantType.IMPLICIT in grant_types:
            flows.implicit = OAuthFlowImplicit(authorizationUrl=authz_endpoint)

        self.model = OAuth2(flows=flows)

    async def authenticate(self, conn: HTTPConnection) -> typing.Optional[typing.Tuple["AuthCredentials", "BaseUser"]]:
        """
        Get the user information and credentials for the request.
        :param conn:
        :return: AuthCredentials and User object if user is successfully authenticated, otherwise None
        """
        authz_header = conn.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authz_header)

        if not authz_header or scheme.lower() != "bearer":
            return AuthCredentials([ROLE_ANONYMOUS]), UnauthenticatedUser()

        try:
            claims = jwt.decode(param, self.jwks, options=self.jwt_decode_options)
            scopes = claims['realm_access']['roles']
            scopes.append(ROLE_ANONYMOUS)
        except JWTError:
            raise AuthenticationError("Invalid token")
        return AuthCredentials(scopes), SimpleUser(claims['preferred_username'])

    def require_any_role(self, *roles: str) -> Callable:
        async def _role_require(request: Request, authenticated=Depends(self)):
            if not any(role in request.auth.scopes for role in roles):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN
                )
        return _role_require

    async def __call__(self, request: Request):
        if not request.user.is_authenticated:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )


ROLE_ADMIN = os.getenv("ROLE_ADMIN")
ROLE_EDITOR = os.getenv("ROLE_EDITOR")
