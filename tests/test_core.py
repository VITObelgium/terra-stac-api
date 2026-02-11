import json

from httpx import codes

from terra_stac_api.core import AccessType, _auth

from .constants import (
    COLLECTION_PROTECTED,
    COLLECTION_S2_TOC_V2,
    ENDPOINT_COLLECTIONS,
    ENDPOINT_SEARCH,
    ROLE_ADMIN,
    ROLE_ANONYMOUS,
    ROLE_PROTECTED,
)
from .mock_auth import MockAuth


def check_collections(roles, collections_response, collections_all):
    for c in collections_all:
        if any(role in c[_auth][AccessType.READ.value] for role in roles):
            assert c["id"] in collections_response
        else:
            assert c["id"] not in collections_response


async def test_landing_page(client, collections):
    response = await client.get("/")
    assert response.status_code == codes.OK
    response_collections = {
        link["href"].split("/collections/", 1)[1]
        for link in response.json()["links"]
        if link["rel"] == "child"
    }
    assert len(response_collections) == 0


async def test_landing_page_authenticated(client, collections):
    response = await client.get("/", auth=MockAuth(ROLE_PROTECTED))
    assert response.status_code == codes.OK
    response_collections = {
        link["href"].split("/collections/", 1)[1]
        for link in response.json()["links"]
        if link["rel"] == "child"
    }
    assert len(response_collections) == 0


async def test_collections(client, collections):
    response = await client.get(str(ENDPOINT_COLLECTIONS))
    assert response.status_code == codes.OK
    response_collections = {c["id"] for c in response.json()["collections"]}
    check_collections((ROLE_ANONYMOUS,), response_collections, collections.values())


async def test_collections_authenticated(client, collections):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS), auth=MockAuth(ROLE_PROTECTED)
    )
    assert response.status_code == codes.OK
    response_collections = {c["id"] for c in response.json()["collections"]}
    check_collections(
        (ROLE_ANONYMOUS, ROLE_PROTECTED), response_collections, collections.values()
    )
    for c in response.json()["collections"]:
        assert "_auth" not in c  # check if auth permissions are not leaked in response


async def test_get_collection(client):
    response = await client.get(str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2))
    assert response.status_code == codes.OK


async def test_get_protected_collection(client):
    response = await client.get(str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED))
    assert response.status_code == codes.UNAUTHORIZED


async def test_get_protected_collection_unauthorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED), auth=MockAuth("unsufficient")
    )
    assert response.status_code == codes.FORBIDDEN


async def test_get_protected_collection_authorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED), auth=MockAuth(ROLE_PROTECTED)
    )
    assert response.status_code == codes.OK


async def test_get_protected_collection_admin(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED), auth=MockAuth(ROLE_ADMIN)
    )
    assert response.status_code == codes.OK


async def test_get_collection_items(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "items")
    )
    assert response.status_code == codes.OK
    assert len(response.json()["features"]) == 4


async def test_get_protected_collection_items_unauthorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "items")
    )
    assert response.status_code == codes.UNAUTHORIZED
    assert "features" not in response.json()


async def test_get_protected_collection_items_authorized(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "items"),
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK
    assert len(response.json()["features"]) == 2


async def test_search(client):
    response = await client.get(str(ENDPOINT_SEARCH), params={"limit": 100})
    assert response.status_code == codes.OK
    rj = response.json()
    assert len(rj["features"]) == 4
    for item in rj["features"]:
        assert item["collection"] == COLLECTION_S2_TOC_V2


async def test_search_protected(client):
    response = await client.get(
        str(ENDPOINT_SEARCH),
        params={
            "collections": f"{COLLECTION_S2_TOC_V2},{COLLECTION_PROTECTED}",
            "limit": 100,
        },
    )
    assert response.status_code == codes.UNAUTHORIZED
    assert "features" not in response.json()


async def test_search_protected_authorized(client):
    response = await client.post(
        str(ENDPOINT_SEARCH),
        json={
            "collections": [COLLECTION_S2_TOC_V2, COLLECTION_PROTECTED],
            "limit": 100,
        },
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK
    rj = response.json()
    assert len(rj["features"]) == 6


async def test_search_protected_fields(client):
    response = await client.get(
        str(ENDPOINT_SEARCH),
        params={
            "collections": [COLLECTION_PROTECTED],
            "fields": "properties.eo:cloud_cover",
        },
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK
    rj = response.json()
    assert len(rj["features"]) == 2
    for item in rj["features"]:
        assert (
            "eo:cloud_cover" not in item["properties"]
        )  # eo:cloudcover field is not specified in Items


async def test_search_admin(client, items):
    response = await client.post(
        str(ENDPOINT_SEARCH), json={"limit": 100}, auth=MockAuth(ROLE_ADMIN)
    )
    assert response.status_code == codes.OK
    rj = response.json()
    response_item_ids = {i["id"] for i in rj["features"]}
    for collection, collection_items in items.items():
        for item in collection_items:
            assert item["id"] in response_item_ids


async def test_filter_items_collections_cql2_text(client):
    item_endpoint = str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "items")

    response = await client.get(item_endpoint + f"?filter=id='UNKNOWN_ID'")
    assert len(response.json().get("features", [])) == 0

    response = await client.get(item_endpoint)
    assert len(response.json().get("features", [])) > 1

    for item in response.json().get("features", []):
        response = await client.get(item_endpoint + f"?filter=id='{item['id']}'")
        assert len(response.json().get("features", [])) == 1
        assert response.json().get("features", [])[0]["id"] == item["id"]


async def test_filter_items_collections_collections_cql2_json(client):
    item_endpoint = str(ENDPOINT_COLLECTIONS / COLLECTION_S2_TOC_V2 / "items")
    def filter_param(id):
        return [("filter", json.dumps({"op": "=", "args": [{"property": "id"}, id]})), ("filter-lang", "cql2-json")]

    response = await client.get(item_endpoint,params=filter_param("UNKNOWN_ID"))
    assert len(response.json().get("features", [])) == 0

    response = await client.get(item_endpoint)
    assert len(response.json().get("features", [])) > 1

    for item in response.json().get("features", []):
        response = await client.get(item_endpoint, params=filter_param(item["id"]))
        assert len(response.json().get("features", [])) == 1
        assert response.json().get("features", [])[0]["id"] == item["id"]