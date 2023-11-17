from typing import List, Optional, Tuple, Generator
from httpx._models import Request, Response

from starlette.authentication import AuthCredentials, BaseUser
from starlette.requests import HTTPConnection
from terra_stac_api.auth import OIDC, GrantType, ROLE_ANONYMOUS
from starlette.authentication import UnauthenticatedUser, SimpleUser
import httpx

class MockAuthBackend(OIDC):
    def __init__(self, issuer: str, *, scheme_name: str | None = "OpenID Connect", allowed_grant_types: List[GrantType] = ..., jwt_decode_options: dict | None = None):
        pass

    async def authenticate(self, conn: HTTPConnection) -> Tuple[AuthCredentials, BaseUser] | None:
        # just read roles from Authorization header
        authz_header = conn.headers.get("Authorization")

        if not authz_header:
            return AuthCredentials([ROLE_ANONYMOUS]), UnauthenticatedUser()
        else:
            scopes = authz_header.split(",")
            scopes.append(ROLE_ANONYMOUS)
            return AuthCredentials(scopes), SimpleUser("test_user")


class MockAuth(httpx.Auth):
    def __init__(self, *roles: str) -> None:
        self.auth_header = ",".join(roles)
    
    def auth_flow(self, request: Request) -> Generator[Request, Response, None]:
        request.headers["Authorization"] = self.auth_header
        yield request
