import logging
import os
from contextlib import asynccontextmanager

from asgi_logger import AccessLoggerMiddleware
from fastapi import FastAPI, Security
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.api.routes import Scope
from stac_fastapi.core.core import EsAsyncBaseFiltersClient
from stac_fastapi.core.extensions import QueryExtension
from stac_fastapi.core.session import Session
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    FilterExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.opensearch.config import OpensearchSettings
from stac_fastapi.opensearch.database_logic import create_collection_index
from starlette.middleware.authentication import AuthenticationMiddleware

from terra_stac_api.auth import OIDC, ROLE_ADMIN, ROLE_EDITOR, GrantType, on_auth_error
from terra_stac_api.core import (
    BulkTransactionsClientAuth,
    CoreClientAuth,
    TransactionsClientAuth,
)
from terra_stac_api.db import DatabaseLogicAuth
from terra_stac_api.serializer import CustomCollectionSerializer

settings = OpensearchSettings()
session = Session.create_from_settings(settings)
database_logic = DatabaseLogicAuth()

auth = OIDC(
    issuer=os.getenv("OIDC_ISSUER"),
    jwt_decode_options={"verify_aud": False},
    allowed_grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.PASSWORD],
)

extensions = [
    TransactionExtension(
        client=TransactionsClientAuth(
            database=database_logic, session=session, settings=settings
        ),
        settings=settings,
    ),
    BulkTransactionExtension(
        client=BulkTransactionsClientAuth(
            database=database_logic, session=session, settings=settings
        )
    ),
    FieldsExtension(),
    FilterExtension(client=EsAsyncBaseFiltersClient()),
    QueryExtension(),
    SortExtension(),
    TokenPaginationExtension(),
    ContextExtension(),
]

get_request_model = create_get_request_model(extensions)
post_request_model = create_post_request_model(extensions)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_collection_index()
    yield


api = StacApi(
    settings=settings,
    extensions=extensions,
    client=CoreClientAuth(
        database=database_logic,
        session=session,
        post_request_model=post_request_model,
        collection_serializer=CustomCollectionSerializer,
    ),
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    route_dependencies=[
        (
            [Scope(path="/collections", method="POST")],
            [Security(auth.require_any_role(ROLE_ADMIN, ROLE_EDITOR))],
        ),  # only allow editors or admins to create new collections
        (
            [
                Scope(path="/collections", method="PUT"),
                Scope(
                    path="/collections/{collection_id}/items/{item_id}", method="PUT"
                ),
                Scope(path="/collections/{collection_id}/items", method="POST"),
                Scope(
                    path="/collections/{collection_id}/items/{item_id}", method="DELETE"
                ),
                Scope(path="/collections/{collection_id}", method="DELETE"),
                Scope(path="/collections/{collections_id}/bulk_items", method="POST"),
            ],
            [Security(auth)],
        ),
    ],
    title="terra-stac-api",
    description="Terrascope STAC API",
)
app = api.app
app.add_middleware(AuthenticationMiddleware, backend=auth, on_error=on_auth_error)
app.add_middleware(
    AccessLoggerMiddleware,
    format='%(t)s %(client_addr)s "%(request_line)s" %(s)s %(B)s %(M)s',
    logger=logging.getLogger("terra_stac_api.access"),
)
app.router.lifespan_context = lifespan


def run():
    """Run app from command line using uvicorn if available"""
    try:
        import uvicorn

        uvicorn.run(
            "terra_stac_api.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
