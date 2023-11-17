from terra_stac_api.auth import ROLE_ANONYMOUS
from terra_stac_api.core import _auth, AccessType
from tests.mock_auth import MockAuth

ROLE_PROTECTED = "protected"


async def test_landing_page(client, collections):
    response = await client.get("/")
    assert response.status_code == 200
    response_collections = {l['href'].split("/collections/", 1)[1] for l in response.json()['links'] if l['rel'] == "child"}
    for collection in collections:
        if ROLE_ANONYMOUS in collection[_auth][AccessType.READ.value]:
            assert collection['id'] in response_collections
        else:
            assert collection['id'] not in response_collections

async def test_landing_page_authenticated(client, collections):
    response = await client.get("/", auth=MockAuth(ROLE_PROTECTED))
    assert response.status_code == 200
    response_collections = {l['href'].split("/collections/", 1)[1] for l in response.json()['links'] if l['rel'] == "child"}
    for collection in collections:
        if any(role in collection[_auth][AccessType.READ.value] for role in (ROLE_ANONYMOUS, ROLE_PROTECTED)):
            assert collection['id'] in response_collections
        else:
            assert collection['id'] not in response_collections

async def test_public_collections(client, collections):
    response = await client.get("/collections")
    assert response.status_code == 200
    response_collections = {c['id'] for c in response.json()['collections']}

    for c in collections:
        if ROLE_ANONYMOUS in c[_auth][AccessType.READ.value]:
            assert c['id'] in response_collections
        else:
            assert c['id'] not in response_collections

async def test_collections_authenticated(client, collections):
    pass


async def test_get_protected_collection_anon(client):
    pass