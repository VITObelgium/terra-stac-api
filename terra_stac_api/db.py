from typing import Iterable, Dict, Any, List, Union, Optional

from stac_fastapi.elasticsearch.database_logic import DatabaseLogic, COLLECTIONS_INDEX, ES_COLLECTIONS_MAPPINGS

from terra_stac_api.auth import ROLE_ADMIN

ES_COLLECTIONS_MAPPINGS["properties"]["_auth"] = {
    "type": "object",
    "properties": {
        "read": {"type": "keyword"},
        "write": {"type": "keyword"}
    }
}


class DatabaseLogicAuth(DatabaseLogic):

    async def get_all_authorized_collections(
            self,
            authorizations: List[str],
            _source: Union[List[str], str, bool, None] = None
    ) -> Iterable[Dict[str, Any]]:
        # TODO: should be paginated
        # TODO: implement caching?
        # https://github.com/stac-utils/stac-fastapi-elasticsearch/issues/65
        query = None if ROLE_ADMIN in authorizations else {
                "bool": {
                    "must": [
                        {
                            "terms": {
                                "_auth.read": authorizations
                            }
                        }
                    ]
                }
            }
        collections = await self.client.search(
            index=COLLECTIONS_INDEX,
            query=query,
            size=1000,
            _source=_source
        )
        return (c["_source"] for c in collections["hits"]["hits"])
