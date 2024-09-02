import logging
from typing import Any, Dict, Iterable, List, Optional, Union

import stac_fastapi.opensearch.database_logic
from opensearchpy import Search, exceptions
from stac_fastapi.opensearch.config import AsyncOpensearchSettings
from stac_fastapi.opensearch.database_logic import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    DatabaseLogic,
    index_by_collection_id,
)
from stac_fastapi.types.errors import DatabaseError, NotFoundError
from stac_fastapi.types.stac import Collection

from terra_stac_api.config import ROLE_ADMIN

logger = logging.getLogger(__name__)

ES_COLLECTIONS_MAPPINGS["properties"]["_auth"] = {
    "type": "object",
    "properties": {"read": {"type": "keyword"}, "write": {"type": "keyword"}},
}


async def fix_delete_item_index(collection_id: str):
    """Delete the index for items in a collection.

    Args:
        collection_id (str): The ID of the collection whose items index will be deleted.
    """
    client = AsyncOpensearchSettings().create_client

    name = index_by_collection_id(collection_id)
    index_info = await client.indices.get(index=name)
    [index] = index_info.keys()
    index_info = index_info[index]

    if "aliases" in index_info and index_info["aliases"]:
        [alias] = index_info["aliases"].keys()
        await client.indices.delete_alias(index=index, name=alias)
        await client.indices.delete(index=index)
    else:
        await client.indices.delete(index=index)
    await client.close()


# fix backwards compatibility for Elasticsearch versions without resolve functionality
stac_fastapi.opensearch.database_logic.delete_item_index = fix_delete_item_index


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
            if ROLE_ADMIN in authorizations
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
        ignore_unavailable: Optional[bool] = True,
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
            ignore_unavailable,
        )
