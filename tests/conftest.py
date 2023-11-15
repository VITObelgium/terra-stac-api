import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import terra_stac_api.auth
from tests.mock_oidc import MockAuth
terra_stac_api.auth.OIDC = MockAuth

import terra_stac_api.app




@pytest.fixture(scope="session")
def app():
    return terra_stac_api.app.api.app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as tc:
        yield tc