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
    assert response.status_code == codes.CREATED

    response = await client.get(
        str(ENDPOINT_COLLECTIONS / extra_collection["id"]), auth=auth
    )
    assert response.status_code == codes.OK


async def test_update_collection(client, collections):
    protected = collections[COLLECTION_PROTECTED]
    response = await client.put(
        str(ENDPOINT_COLLECTIONS / protected["id"]), json=protected
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_update_collection_no_write_permission(client, collections):
    protected = collections[COLLECTION_S2_TOC_V2]
    response = await client.put(
        str(ENDPOINT_COLLECTIONS / protected["id"]),
        json=protected,
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_update_collection_authorized(client, collections):
    collection = deepcopy(collections[COLLECTION_PROTECTED])
    description_updated = "Updated description"
    collection["description"] = description_updated
    auth = MockAuth(ROLE_SENTINEL2, ROLE_PROTECTED)

    response = await client.put(
        str(ENDPOINT_COLLECTIONS / collection["id"]), json=collection, auth=auth
    )
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


async def test_create_item(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / extra_item["collection"] / "items"),
        json=extra_item,
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_create_item_unauthorized(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / extra_item["collection"] / "items"),
        json=extra_item,
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_create_item_authorized(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / extra_item["collection"] / "items"),
        json=extra_item,
        auth=MockAuth(ROLE_SENTINEL2),
    )
    assert response.status_code == codes.CREATED


async def test_update_item(client, items):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.put(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]), json=item
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_update_item_unauthorized(client, items):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.put(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]),
        json=item,
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_update_item_authorized(client, items):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.put(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]),
        json=item,
        auth=MockAuth(ROLE_SENTINEL2),
    )
    assert response.status_code == codes.OK


async def test_delete_item(client, items):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.delete(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]),
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_delete_item_unauthorized(client, items):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.delete(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]),
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_delete_item_authorized(client, items, api):
    item = next(iter(items[COLLECTION_S2_TOC_V2]))
    response = await client.delete(
        str(ENDPOINT_COLLECTIONS / item["collection"] / "items" / item["id"]),
        auth=MockAuth(ROLE_SENTINEL2),
    )
    assert response.status_code == codes.NO_CONTENT

    await api.client.database._refresh()

    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "items")
    )
    assert response.status_code == codes.OK
    assert item["id"] not in list(i["id"] for i in response.json()["features"])
