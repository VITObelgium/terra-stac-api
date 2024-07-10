import asyncio
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from stac_fastapi.opensearch.database_logic import ITEM_INDICES

import terra_stac_api.auth

from .mock_auth import MockAuthBackend

terra_stac_api.auth.OIDC = MockAuthBackend

import terra_stac_api.app  # noqa

RESOURCES = Path(__file__).parent / "resources"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def api():
    return terra_stac_api.app.api


@pytest_asyncio.fixture(scope="session")
async def app(api):
    try:
        # clear Elasticsearch on test startup to remove residues of previously failed or aborted tests
        # these indices might not exist, so put in try block
        await api.client.database.delete_items()
        await api.client.database.delete_collections()
    finally:
        return api.app


@pytest_asyncio.fixture(scope="session")
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as tc:
        yield tc


@pytest.fixture(scope="session")
def collections():
    collections = {}
    collection_resources = RESOURCES / "collections"
    for c_path in collection_resources.glob("*.json"):
        with open(c_path) as f:
            collection = json.load(f)
        collections[collection["id"]] = collection
    return collections


@pytest.fixture(scope="session")
def items():
    items = dict()
    item_resources = RESOURCES / "items"
    for p_path in item_resources.glob("*.json"):
        with open(p_path) as f:
            item = json.load(f)
        if item["collection"] not in items:
            items[item["collection"]] = []
        items[item["collection"]].append(item)
    return items


@pytest.fixture(scope="session")
def extra_collection():
    with open(RESOURCES / "collections/extra/extra_collection.json") as f:
        collection = json.load(f)
    return collection


@pytest.fixture(scope="session")
def extra_item():
    with open(RESOURCES / "items/extra/S2A_20230220T093031_36VVR_TOC_V210.json") as f:
        item = json.load(f)
    return item


@pytest_asyncio.fixture(autouse=True)
async def setup_es(api, collections, items):
    # setup
    for collection in collections.values():
        await api.client.database.create_collection(collection, refresh=True)
    for collection, c_items in items.items():
        for item in c_items:
            await api.client.database.create_item(item, refresh=True)
    yield
    # teardown
    await api.client.database._refresh()
    await api.client.database.client.indices.delete(
        index=ITEM_INDICES
    )  # , expand_wildcards="all")
    await api.client.database.delete_collections()
    # await api.client.database.client.indices.delete(index=COLLECTIONS_INDEX)
    await api.client.database._refresh()

    # for collection in await api.client.database.get_all_collections(token=None, limit=100):
    #     await api.client.database.delete_collection(collection['id'])
    # await api.client.database._refresh()
    # await api.client.database.delete_collections()
    # await api.client.database.client.indices.delete(index=ITEM_INDICES)
