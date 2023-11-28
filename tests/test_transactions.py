from copy import deepcopy

from httpx import codes

from .constants import (
    COLLECTION_PROTECTED,
    COLLECTION_S2_TOC_V2,
    ENDPOINT_COLLECTIONS,
    ROLE_EDITOR,
    ROLE_PROTECTED,
    ROLE_SENTINEL2,
)
from .mock_auth import MockAuth


async def test_create_collection(client, extra_collection):
    response = await client.post(str(ENDPOINT_COLLECTIONS), json=extra_collection)
    assert response.status_code == codes.UNAUTHORIZED


async def test_create_collection_authenticated_no_editor(client, extra_collection):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS), json=extra_collection, auth=MockAuth(ROLE_PROTECTED)
    )
    assert response.status_code == codes.FORBIDDEN


async def test_create_collection_authorized(client, extra_collection):
    auth = MockAuth(ROLE_PROTECTED, ROLE_EDITOR)
    response = await client.post(
        str(ENDPOINT_COLLECTIONS), json=extra_collection, auth=auth
    )
    assert response.status_code == codes.OK

    response = await client.get(
        str(ENDPOINT_COLLECTIONS / extra_collection["id"]), auth=auth
    )
    assert response.status_code == codes.OK


async def test_update_collection(client, collections):
    protected = collections[COLLECTION_PROTECTED]
    response = await client.put(str(ENDPOINT_COLLECTIONS), json=protected)
    assert response.status_code == codes.UNAUTHORIZED


async def test_update_collection_no_write_permission(client, collections):
    protected = collections[COLLECTION_S2_TOC_V2]
    response = await client.put(
        str(ENDPOINT_COLLECTIONS), json=protected, auth=MockAuth(ROLE_PROTECTED)
    )
    assert response.status_code == codes.FORBIDDEN


async def test_update_collection_authorized(client, collections):
    collection = deepcopy(collections[COLLECTION_PROTECTED])
    description_updated = "Updated description"
    collection["description"] = description_updated
    auth = MockAuth(ROLE_SENTINEL2, ROLE_PROTECTED)

    response = await client.put(str(ENDPOINT_COLLECTIONS), json=collection, auth=auth)
    assert response.status_code == codes.OK

    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED), auth=auth
    )
    assert response.status_code == codes.OK
    assert response.json()["description"] == description_updated


async def test_delete_collection(client):
    response = await client.delete(str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2))
    assert response.status_code == codes.UNAUTHORIZED


async def test_delete_collection_unauthorized(client):
    response = await client.delete(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2), auth=MockAuth("unsufficient")
    )
    assert response.status_code == codes.FORBIDDEN


async def test_delete_collection_authorized(client, api):
    response = await client.delete(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2), auth=MockAuth(ROLE_SENTINEL2)
    )
    assert response.status_code == codes.NO_CONTENT
    await api.client.database._refresh()

    response = await client.get(str(ENDPOINT_COLLECTIONS))
    assert response.status_code == codes.OK
    assert COLLECTION_S2_TOC_V2 not in list(
        c["id"] for c in response.json()["collections"]
    )
