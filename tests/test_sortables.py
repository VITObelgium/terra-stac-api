from constants import ROLE_PROTECTED

from .constants import COLLECTION_PROTECTED, COLLECTION_S2_TOC_V2, ENDPOINT_COLLECTIONS
from .mock_auth import MockAuth


async def test_get_sortables(client):
    response = await client.get("/sortables")
    assert response.status_code == 200


async def test_get_collection_sortables_public(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "sortables")
    )
    assert response.status_code == 200
    assert "properties.sat:absolute_orbit" in response.json()["properties"]


async def test_get_protected_collection_sortables_unauthenticated(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "sortables")
    )
    assert response.status_code == 401


async def test_get_protected_collection_sortables_unauthorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "sortables"),
        auth=MockAuth("unsufficient"),
    )
    assert response.status_code == 403


async def test_get_protected_collection_sortables_authorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "sortables"),
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == 200
