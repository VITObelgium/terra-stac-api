from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.elasticsearch.config import ElasticsearchSettings
from stac_fastapi.elasticsearch.session import Session

from stac_fastapi.elasticsearch.database_logic import create_collection_index
from stac_fastapi.elasticsearch.core import TransactionsClient, EsAsyncBaseFiltersClient, CoreClient, BulkTransactionsClient
from stac_fastapi.extensions.core import ContextExtension, FieldsExtension, FilterExtension, SortExtension, TokenPaginationExtension, TransactionExtension
from stac_fastapi.extensions.third_party import BulkTransactionExtension


settings = ElasticsearchSettings()
session = Session.create_from_settings(settings)

extensions = [
    TransactionExtension(client=TransactionsClient(session=session), settings=settings),
    BulkTransactionExtension(client=BulkTransactionsClient(session=session)),
    FieldsExtension(),
    FilterExtension(client=EsAsyncBaseFiltersClient()),
    SortExtension(),
    TokenPaginationExtension(),
    ContextExtension(),
    FilterExtension()
]

get_request_model = create_get_request_model(extensions)
post_request_model = create_post_request_model(extensions)

api = StacApi(
    settings=settings,
    extensions=extensions,
    client=CoreClient(session=session, post_request_model=post_request_model),
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
)
app = api.app


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
