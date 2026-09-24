import logging
from typing import Any, Dict, Iterable, List, Optional, Type, Union

import attr
from opensearchpy import Search
from overrides import overrides
from stac_fastapi.core.serializers import CollectionSerializer
from stac_fastapi.opensearch.database_logic import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    DatabaseLogic,
)
from stac_fastapi.types.errors import DatabaseError
from starlette.requests import Request

from terra_stac_api.config import Settings
from terra_stac_api.serializer import CustomCollectionSerializer

settings = Settings()
logger = logging.getLogger(__name__)

ES_COLLECTIONS_MAPPINGS["properties"]["_auth"] = {
    "type": "object",
    "properties": {"read": {"type": "keyword"}, "write": {"type": "keyword"}},
}
ES_COLLECTIONS_MAPPINGS["properties"]["renders"] = {
    "type": "object",
    "enabled": False,
}
ES_COLLECTIONS_MAPPINGS["properties"]["summaries"] = {
    "type": "object",
    "enabled": False,
}


@attr.s
class DatabaseLogicAuth(DatabaseLogic):
    collection_serializer: Type[CollectionSerializer] = attr.ib(
        default=CustomCollectionSerializer
    )

    async def get_all_authorized_collections(
        self,
        authorizations: List[str],
        _source: Union[List[str], str, bool, None] = None,
    ) -> Iterable[Dict[str, Any]]:
        # TODO: should be paginated
        # TODO: implement caching?
        # https://github.com/stac-utils/stac-fastapi-elasticsearch/issues/65
        body = (
            {}
            if settings.role_admin in authorizations
            else {
                "query": {"bool": {"must": [{"terms": {"_auth.read": authorizations}}]}}
            }
        )
        collections = await self.client.search(
            body=body, index=COLLECTIONS_INDEX, size=1000, _source=_source
        )
        return (c["_source"] for c in collections["hits"]["hits"])

    @overrides
    async def get_all_collections(
        self,
        token: str | None,
        limit: int,
        request: Request,
        sort: list[dict[str, Any]] | None = None,
        bbox: list[float] | None = None,
        q: list[str] | None = None,
        filter: dict[str, Any] | None = None,
        query: dict[str, dict[str, Any]] | None = None,
        datetime: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, int | None]:
        # apply collection authorization filter
        authorizations = request.auth.scopes
        if settings.role_admin not in authorizations:
            if not query:
                query = {}
            query["_auth.read"] = {"in": authorizations}
            # query_parts.append({"terms": {"_auth.read": authorizations}})
        return await super().get_all_collections(
            token=token,
            limit=limit,
            request=request,
            sort=sort,
            bbox=bbox,
            q=q,
            filter=filter,
            query=query,
            datetime=datetime,
        )

    async def _refresh(self):
        await self.client.indices.refresh()

    @overrides
    async def aggregate(
        self,
        collection_ids: Optional[List[str]],
        aggregations: List[str],
        search: Search,
        centroid_geohash_grid_precision: int,
        centroid_geohex_grid_precision: int,
        centroid_geotile_grid_precision: int,
        geometry_geohash_grid_precision: int,
        geometry_geotile_grid_precision: int,
        datetime_frequency_interval: str,
        datetime_search,
        ignore_unavailable: Optional[bool] = True,
        **kwargs,
    ):
        if collection_ids is None or len(collection_ids) == 0:
            raise DatabaseError()
        return await super().aggregate(
            collection_ids,
            aggregations,
            search,
            centroid_geohash_grid_precision,
            centroid_geohex_grid_precision,
            centroid_geotile_grid_precision,
            geometry_geohash_grid_precision,
            geometry_geotile_grid_precision,
            datetime_frequency_interval,
            ignore_unavailable,
        )
