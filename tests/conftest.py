import asyncio
from httpx import AsyncClient
import pytest
import pytest_asyncio
import json
from pathlib import Path
from fastapi.testclient import TestClient

import terra_stac_api.auth
from tests.mock_auth import MockAuthBackend
terra_stac_api.auth.OIDC = MockAuthBackend

import terra_stac_api.app

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
    # clear Elasticsearch on test startup to remove residues of previously failed or aborted tests
    await api.client.database.delete_items()
    await api.client.database.delete_collections()
    return api.app


@pytest_asyncio.fixture(scope="session")
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as tc:
        yield tc

@pytest.fixture(scope="session")
def collections():
    collections = []
    collection_resources = RESOURCES / "collections"
    for c_path in collection_resources.iterdir():
        with open(c_path) as f:
            collection = json.load(f)
        collections.append(collection)
    return collections

@pytest.fixture(scope="session")
def items():
    items = dict()
    item_resources = RESOURCES / "items"
    for p_path in item_resources.iterdir():
        with open(p_path) as f:
            item = json.load(f)
        if item['collection'] not in items:
            items[item['collection']] = []
        items[item['collection']].append(item)
    return items


@pytest_asyncio.fixture(autouse=True)
async def setup_es(api, collections, items):
    # setup
    for collection in collections:
        await api.client.database.create_collection(collection, refresh=True)
    for collection, c_items in items.items():
        for item in c_items:
            await api.client.database.create_item(item, refresh=True)
    yield
    # teardown
    await api.client.database.delete_items()
    await api.client.database.delete_collections()