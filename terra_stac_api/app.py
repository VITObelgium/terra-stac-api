import os

from fastapi import Security
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.api.routes import Scope
from stac_fastapi.elasticsearch.config import ElasticsearchSettings
from stac_fastapi.elasticsearch.core import (
    TransactionsClient,
    EsAsyncBaseFiltersClient,
    CoreClient,
    BulkTransactionsClient
)
from stac_fastapi.elasticsearch.database_logic import create_collection_index
from stac_fastapi.elasticsearch.session import Session
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    FilterExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from starlette.middleware.authentication import AuthenticationMiddleware

from terra_stac_api.auth import OIDC, on_auth_error, GrantType

settings = ElasticsearchSettings()
session = Session.create_from_settings(settings)

ROLE_ADMIN = os.getenv("ROLE_ADMIN")
ROLE_EDITOR = os.getenv("ROLE_EDITOR")

auth = OIDC(
    issuer=os.getenv("OIDC_ISSUER"),
    jwt_decode_options={"verify_aud": False},
    allowed_grant_types=[GrantType.AUTHORIZATION_CODE, GrantType.PASSWORD]
)

extensions = [
    TransactionExtension(client=TransactionsClient(session=session), settings=settings),
    BulkTransactionExtension(client=BulkTransactionsClient(session=session)),
    FieldsExtension(),
    FilterExtension(client=EsAsyncBaseFiltersClient()),
    SortExtension(),
    TokenPaginationExtension(),
    ContextExtension(),
]

get_request_model = create_get_request_model(extensions)
post_request_model = create_post_request_model(extensions)

api = StacApi(
    settings=settings,
    extensions=extensions,
    client=CoreClient(session=session, post_request_model=post_request_model),
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    route_dependencies=[
        ([Scope(path="/collections", method="POST")], [Security(auth.require_any_role(ROLE_ADMIN, ROLE_EDITOR))]),  # only allow editors or admins to create new collections
        ([
            Scope(path="/collections", method="PUT"),
            Scope(path="/collections/{collection_id}/items/{item_id}", method="PUT"),
            Scope(path="/collections/{collection_id}/items", method="POST"),
            Scope(path="/collections/{collection_id}/items/{item_id}", method="DELETE"),
            Scope(path="/collections/{collection_id}", method="DELETE"),
            Scope(path="/collections/{collections_id}/bulk_items", method="POST")
         ],
         [Security(auth)])
    ]
)
app = api.app
app.add_middleware(AuthenticationMiddleware, backend=auth, on_error=on_auth_error)


@app.on_event("startup")
async def _startup_event():
    await create_collection_index()


def run():
    """Run app from command line using uvicorn if available"""
    try:
        import uvicorn
        uvicorn.run(
            "terra_stac_api.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
