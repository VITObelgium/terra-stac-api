import logging
import os
from contextlib import asynccontextmanager

from asgi_logger import AccessLoggerMiddleware
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI, Security
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.middleware import ProxyHeaderMiddleware
from stac_fastapi.api.models import (
    ItemCollectionUri,
    create_get_request_model,
    create_post_request_model,
    create_request_model,
)
from stac_fastapi.api.routes import Scope
from stac_fastapi.core.rate_limit import setup_rate_limit
from stac_fastapi.core.session import Session
from stac_fastapi.opensearch.config import OpensearchSettings
from stac_fastapi.opensearch.database_logic import (
    DatabaseLogic,
    create_collection_index,
    create_index_templates,
)
from stac_fastapi.sfeos_helpers.models.extensions import Extensions
from starlette.authentication import AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import SAFELISTED_HEADERS, CORSMiddleware

import terra_stac_api.config
from terra_stac_api.auth import OIDC, GrantType, NoAuth, on_auth_error
from terra_stac_api.core import (
    CoreClientAuth,
)
from terra_stac_api.db import DatabaseLogicAuth
from terra_stac_api.extensions import ExtensionsAuth
from terra_stac_api.serializer import CustomCollectionSerializer

logger = logging.getLogger(__name__)

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


def get_route_dependencies(
    auth: AuthenticationBackend, app_settings: terra_stac_api.config.Settings
) -> list:
    if isinstance(auth, NoAuth):
        return []
    elif isinstance(auth, OIDC):
        return [
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
                    Scope(path="/collections/{collection_id}", method="PATCH"),
                    Scope(
                        path="/collections/{collection_id}/items/{item_id}",
                        method="PUT",
                    ),
                    Scope(
                        path="/collections/{collection_id}/items/{item_id}",
                        method="PATCH",
                    ),
                    Scope(path="/collections/{collection_id}/items", method="POST"),
                    Scope(
                        path="/collections/{collection_id}/items/{item_id}",
                        method="DELETE",
                    ),
                    Scope(path="/collections/{collection_id}", method="DELETE"),
                    Scope(
                        path="/collections/{collections_id}/bulk_items", method="POST"
                    ),
                ],
                [Security(auth)],
            ),
        ]
    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize index templates and the collections index at startup."""
    await create_index_templates()
    await create_collection_index()
    yield


def _log_extension_flags(extensions_manager: Extensions):
    logger.info("Extension flags:")
    logger.info("Transactions: %s", extensions_manager.transactions_enabled)
    logger.info("Collections search: %s", extensions_manager.collections_search_enabled)
    logger.info(
        "Collections search route: %s",
        extensions_manager.collections_search_route_enabled,
    )
    logger.info("Catalogs: %s", extensions_manager.catalogs_enabled)
    logger.info("Hide alternate parents: %s", extensions_manager.hide_alternate_parents)


def instantiate_api(
    settings: OpensearchSettings | None = None,
    database_logic: DatabaseLogic | None = None,
    extensions_manager: Extensions | None = None,
):
    """
    Instantiate the OpenSearch-backed STAC API.
    """
    settings = settings or OpensearchSettings()
    session = Session.create_from_settings(settings)
    database_logic = database_logic or DatabaseLogic()

    if extensions_manager is None:
        extensions_manager = ExtensionsAuth(
            settings=settings,
            database_logic=database_logic,
            session=session,
        )
    _log_extension_flags(extensions_manager)

    application_extensions = [
        *extensions_manager.aggregation,
        *extensions_manager.search,
        *extensions_manager.collection_search,
        *extensions_manager.collections_search_route,
        *extensions_manager.catalogs,
        *extensions_manager.extra,
    ]
    database_logic.extensions = [type(ext).__name__ for ext in application_extensions]

    post_request_model = create_post_request_model(extensions_manager.search)
    get_request_model = create_get_request_model(extensions_manager.search)
    collections_get_request_model = extensions_manager.collections_get_request_model

    items_get_request_model = create_request_model(
        model_name="ItemCollectionUri",
        base_model=ItemCollectionUri,
        extensions=extensions_manager.item_collection,
    )

    optional_api_kwargs = {}
    if collections_get_request_model is not None:
        optional_api_kwargs[
            "collections_get_request_model"
        ] = collections_get_request_model

    stac_api = StacApi(
        title=app_settings.stac_title,
        description=app_settings.stac_description,
        stac_version=app_settings.stac_version,
        api_version=terra_stac_api.__version__,
        settings=settings,
        extensions=application_extensions,
        client=CoreClientAuth(
            database=database_logic,
            session=session,
            extensions=application_extensions,
            collection_serializer=CustomCollectionSerializer,
            title=app_settings.stac_title,
            description=app_settings.stac_description,
            post_request_model=post_request_model,
        ),
        search_get_request_model=get_request_model,
        search_post_request_model=post_request_model,
        items_get_request_model=items_get_request_model,
        route_dependencies=get_route_dependencies(auth, app_settings),
        app=FastAPI(
            title=app_settings.stac_title,
            description=app_settings.stac_description,
            version=terra_stac_api.__version__,
            openapi_url="/api",
            docs_url="/api.html",
            redoc_url=None,
            lifespan=lifespan,
        ),
        middlewares=[
            Middleware(BrotliMiddleware),
            Middleware(
                CORSMiddleware,
                allow_origins=app_settings.cors_allow_origins,
                allow_methods=app_settings.cors_allow_methods,
                allow_credentials=app_settings.cors_allow_credentials,
                allow_headers={"Authorization"} | SAFELISTED_HEADERS
                if app_settings.cors_allow_credentials
                else SAFELISTED_HEADERS,
            ),
            Middleware(ProxyHeaderMiddleware),
            Middleware(AuthenticationMiddleware, backend=auth, on_error=on_auth_error),
            Middleware(
                AccessLoggerMiddleware,
                format='%(t)s %(client_addr)s "%(request_line)s" %(s)s %(B)s %(M)s "%(a)s"',
                logger=logging.getLogger("terra_stac_api.access"),
            ),
        ],
        **optional_api_kwargs,
    )
    fastapi_app = stac_api.app
    fastapi_app.root_path = os.getenv("STAC_FASTAPI_ROOT_PATH", "")

    setup_rate_limit(fastapi_app, rate_limit=os.getenv("STAC_FASTAPI_RATE_LIMIT"))

    return stac_api


def create_app() -> FastAPI:
    """
    Create a FastAPI app instance using the factory pattern.

    This function is designed to be used with Uvicorn's --factory flag:
    uvicorn terra_stac_api.app:create_app --factory
    """

    api = instantiate_api(settings=settings, database_logic=database_logic)
    return api.app


def run():
    """Run app from command line using uvicorn if available"""
    try:
        import uvicorn

        uvicorn.run(
            "terra_stac_api.app:create_app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
