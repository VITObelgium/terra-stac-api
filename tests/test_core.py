
def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200