
async def test_landing_page(client):
    response = await client.get("/")
    assert response.status_code == 200


