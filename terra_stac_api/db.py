import logging
from typing import Any, Dict, Iterable, List, Optional, Union

from opensearchpy import Search, exceptions
from stac_fastapi.opensearch.database_logic import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    DatabaseLogic,
)
from stac_fastapi.types.errors import DatabaseError, NotFoundError
from stac_fastapi.types.stac import Collection

from terra_stac_api.config import Settings

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


class DatabaseLogicAuth(DatabaseLogic):
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

    def sync_find_collection(self, collection_id: str) -> Collection:
        try:
            collection = self.sync_client.get(index=COLLECTIONS_INDEX, id=collection_id)
        except exceptions.NotFoundError:
            raise NotFoundError(f"Collection {collection_id} not found")

        return collection["_source"]

    async def _refresh(self):
        await self.client.indices.refresh()

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
