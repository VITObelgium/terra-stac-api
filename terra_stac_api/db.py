from typing import Any, Dict, Iterable, List, Union

import stac_fastapi.elasticsearch.database_logic
from stac_fastapi.elasticsearch.config import AsyncElasticsearchSettings
from stac_fastapi.elasticsearch.database_logic import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    DatabaseLogic,
    index_by_collection_id,
)
from stac_fastapi.types.errors import NotFoundError
from stac_fastapi.types.stac import Collection

from elasticsearch import exceptions
from terra_stac_api.auth import ROLE_ADMIN

ES_COLLECTIONS_MAPPINGS["properties"]["_auth"] = {
    "type": "object",
    "properties": {"read": {"type": "keyword"}, "write": {"type": "keyword"}},
}


async def fix_delete_item_index(collection_id: str):
    """Delete the index for items in a collection.

    Args:
        collection_id (str): The ID of the collection whose items index will be deleted.
    """
    client = AsyncElasticsearchSettings().create_client

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
stac_fastapi.elasticsearch.database_logic.delete_item_index = fix_delete_item_index


class DatabaseLogicAuth(DatabaseLogic):
    async def get_all_authorized_collections(
        self,
        authorizations: List[str],
        _source: Union[List[str], str, bool, None] = None,
    ) -> Iterable[Dict[str, Any]]:
        # TODO: should be paginated
        # TODO: implement caching?
        # https://github.com/stac-utils/stac-fastapi-elasticsearch/issues/65
        query = (
            None
            if ROLE_ADMIN in authorizations
            else {"bool": {"must": [{"terms": {"_auth.read": authorizations}}]}}
        )
        collections = await self.client.search(
            index=COLLECTIONS_INDEX, query=query, size=1000, _source=_source
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
