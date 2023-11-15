import asyncio
import pytest
import pytest_asyncio

import terra_stac_api.auth
from tests.mock_oidc import MockAuth
terra_stac_api.auth.OIDC = MockAuth

import terra_stac_api.app



@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def app():
    return terra_stac_api.app.api.app