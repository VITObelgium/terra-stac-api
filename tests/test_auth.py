from httpx import codes

# public endpoints
unprotected_routes = {
    "/api": ["GET", "HEAD"],
    "/api.html": ["GET", "HEAD"],
    "/docs/oauth2-redirect": ["GET", "HEAD"],
    "/": ["GET"],
    "/conformance": ["GET"],
    "/collections/{collection_id}/items/{item_id}": ["GET"],
    "/search": ["POST", "GET"],
    "/collections": ["GET"],
    "/collections/{collection_id}": ["GET"],
    "/collections/{collection_id}/items": ["GET"],
    "/aggregations": ["GET", "POST"],
    "/collections/{collection_id}/aggregations": ["GET", "POST"],
    "/aggregate": ["GET", "POST"],
    "/collections/{collection_id}/aggregate": ["GET", "POST"],
    "/queryables": ["GET"],
    "/collections/{collection_id}/queryables": ["GET"],
    "/_mgmt/ping": ["GET"],
}

# CRUD endpoints
crud_routes = {
    "/collections/{collection_id}/items": ["POST"],
    "/collections/{collection_id}/items/{item_id}": ["PUT", "DELETE"],
    "/collections": ["POST"],
    "/collections/{collection_id}": ["PUT", "DELETE"],
    "/collections/{collection_id}/bulk_items": ["POST"],
}


async def test_route_status(client, api):
    """
    Check all available routes and assume it is either a public route or a route protected with a route dependency.
    This can make us aware of newly introduced routes that may need extra implementation work to enforce authorization.
    """
    for route in api.app.routes:
        for method in route.methods:
            url = route.path.format_map(
                dict(collection_id="test-collection", item_id="test-item")
            )
            r = await client.request(method=method, url=url)
            if r.status_code == codes.OK:
                assert route.path in unprotected_routes
                assert method in unprotected_routes[route.path]
            elif r.status_code == codes.UNAUTHORIZED:
                assert route.path in crud_routes
                assert method in crud_routes[route.path]
            else:
                assert r.status_code in (400, 404)
                assert route.path in unprotected_routes
                assert method in unprotected_routes[route.path]


async def test_route_dependencies(client, api):
    """
    Check if there is a route dependency defined for known CRUD endpoints.
    """
    for route, methods in crud_routes.items():
        for method in methods:
            [api_route] = [
                r for r in api.app.routes if r.path == route and method in r.methods
            ]
            assert len(api_route.dependencies) >= 1
