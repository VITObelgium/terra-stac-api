import json

from httpx import codes

from .constants import (
    COLLECTION_PROTECTED,
    COLLECTION_S2_TOC_V2,
    ENDPOINT_AGGREGATE,
    ENDPOINT_COLLECTIONS,
    ROLE_PROTECTED,
)
from .mock_auth import MockAuth


async def test_get_protected_collection_aggregations(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregations")
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_get_protected_collection_unauthorized_aggregations(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregations"),
        auth=MockAuth("unsufficient"),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_get_protected_collection_authorized_aggregations(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregations"),
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK


async def test_get_protected_collection_aggregate(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregate"),
        params={"aggregations": "total_count"},
    )
    assert response.status_code == codes.UNAUTHORIZED


async def test_get_protected_collection_unauthorized_aggregate(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregate"),
        params={"aggregations": "total_count"},
        auth=MockAuth("unsufficient"),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_get_protected_collection_authorized_aggregate(client):
    response = await client.get(
        str(ENDPOINT_COLLECTIONS / COLLECTION_PROTECTED / "aggregate"),
        params={"aggregations": "total_count"},
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK
    [agg] = response.json()["aggregations"]
    assert agg["name"] == "total_count"


async def test_get_aggregate(client):
    response = await client.get(
        str(ENDPOINT_AGGREGATE),
        params={"aggregations": "total_count,collection_frequency"},
    )
    assert response.status_code == codes.OK
    rj = response.json()
    print(json.dumps(rj, indent=4))
    [agg] = [agg for agg in rj["aggregations"] if agg["name"] == "collection_frequency"]
    [bucket] = agg["buckets"]
    assert bucket["key"] == COLLECTION_S2_TOC_V2


async def test_get_unauthorized_aggregate(client):
    response = await client.get(
        str(ENDPOINT_AGGREGATE),
        params={
            "collections": f"{COLLECTION_S2_TOC_V2},{COLLECTION_PROTECTED}",
            "aggregations": "total_count,collection_frequency",
        },
        auth=MockAuth("unsufficient"),
    )
    assert response.status_code == codes.FORBIDDEN


async def test_get_authorized_aggregate(client):
    response = await client.get(
        str(ENDPOINT_AGGREGATE),
        params={
            "collections": f"{COLLECTION_S2_TOC_V2},{COLLECTION_PROTECTED}",
            "aggregations": "total_count,collection_frequency",
        },
        auth=MockAuth(ROLE_PROTECTED),
    )
    assert response.status_code == codes.OK
    aggs = response.json()["aggregations"]
    assert aggs[0]["name"] == "total_count"
    assert aggs[1]["name"] == "collection_frequency"
    buckets_collections = {b["key"] for b in aggs[1]["buckets"]}
    assert buckets_collections == {COLLECTION_S2_TOC_V2, COLLECTION_PROTECTED}
