import logging
from contextlib import asynccontextmanager

from asgi_logger import AccessLoggerMiddleware
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI, Security
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.middleware import ProxyHeaderMiddleware
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.api.routes import Scope
from stac_fastapi.core.core import EsAsyncBaseFiltersClient
from stac_fastapi.core.extensions import QueryExtension
from stac_fastapi.core.extensions.aggregation import (
    EsAggregationExtensionGetRequest,
    EsAggregationExtensionPostRequest,
)
from stac_fastapi.core.session import Session
from stac_fastapi.extensions.core import (
    AggregationExtension,
    FieldsExtension,
    FilterExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.opensearch.config import OpensearchSettings
from stac_fastapi.opensearch.database_logic import (
    create_collection_index,
    create_index_templates,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import SAFELISTED_HEADERS, CORSMiddleware

import terra_stac_api.config
from terra_stac_api.aggregation_client import AggregationClientAuth
from terra_stac_api.auth import OIDC, GrantType, NoAuth, on_auth_error
from terra_stac_api.core import (
    BulkTransactionsClientAuth,
    CoreClientAuth,
    TransactionsClientAuth,
)
from terra_stac_api.db import DatabaseLogicAuth
from terra_stac_api.serializer import CustomCollectionSerializer

app_settings = terra_stac_api.config.Settings()
settings = OpensearchSettings()
session = Session.create_from_settings(settings)
database_logic = DatabaseLogicAuth()

auth = (
    OIDC(
        issuer=app_settings.oidc_issuer,
        jwt_decode_options={"verify_aud": False},
        allowed_grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.PASSWORD],
    )
    if app_settings.oidc_issuer
    else NoAuth()
)

aggregation_extension = AggregationExtension(
    client=AggregationClientAuth(
        database=database_logic, session=session, settings=settings
    )
)
aggregation_extension.POST = EsAggregationExtensionPostRequest
aggregation_extension.GET = EsAggregationExtensionGetRequest

search_extensions = [
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
]

extensions = [aggregation_extension] + search_extensions
database_logic.extensions = [type(ext).__name__ for ext in extensions]

get_request_model = create_get_request_model(search_extensions)
post_request_model = create_post_request_model(search_extensions)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_index_templates()
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
            [
                Security(
                    auth.require_any_role(
                        app_settings.role_admin, app_settings.role_editor
                    )
                )
            ],
        ),  # only allow editors or admins to create new collections
        (
            [
                Scope(path="/collections/{collection_id}", method="PUT"),
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
    ]
    if not isinstance(auth, NoAuth)
    else [],
    title=app_settings.stac_title,
    description=app_settings.stac_description,
    api_version=terra_stac_api.__version__,
    middlewares=[
        Middleware(BrotliMiddleware),
        Middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_allow_origins,
            allow_methods=app_settings.cors_allow_methods,
            allow_credentials=app_settings.cors_allow_credentials,
            allow_headers=SAFELISTED_HEADERS,
        ),
        Middleware(ProxyHeaderMiddleware),
        Middleware(AuthenticationMiddleware, backend=auth, on_error=on_auth_error),
        Middleware(
            AccessLoggerMiddleware,
            format='%(t)s %(client_addr)s "%(request_line)s" %(s)s %(B)s %(M)s',
            logger=logging.getLogger("terra_stac_api.access"),
        ),
    ],
)
app = api.app
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
