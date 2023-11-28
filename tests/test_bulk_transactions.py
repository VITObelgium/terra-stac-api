from httpx import codes

from .constants import (
    COLLECTION_PROTECTED,
    COLLECTION_S2_TOC_V2,
    ENDPOINT_COLLECTIONS,
    ROLE_PROTECTED,
    ROLE_SENTINEL2,
)
from .mock_auth import MockAuth


async def test_bulk_create(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "bulk_items"),
        json={"items": {extra_item["id"]: extra_item}},
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_bulk_create_unauthorized(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "bulk_items"),
        json={"items": {extra_item["id"]: extra_item}},
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_bulk_create_authorized(client, extra_item):
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "bulk_items"),
        json={"items": {extra_item["id"]: extra_item}},
        auth=MockAuth(ROLE_SENTINEL2),
    )
    assert response.status_code == codes.OK


async def test_bulk_create_unmatching_collection(client, extra_item):
    # item collection doesn't match collection in URI
    response = await client.post(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "bulk_items"),
        json={"items": {extra_item["id"]: extra_item}},
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.BAD_REQUEST
