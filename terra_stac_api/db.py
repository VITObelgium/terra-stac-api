import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type, Union

import attr
import orjson
from fastapi import HTTPException
from opensearchpy import Search
from overrides import overrides
from stac_fastapi.core.serializers import CollectionSerializer
from stac_fastapi.opensearch.database_logic import (
    COLLECTIONS_INDEX,
    ES_COLLECTIONS_MAPPINGS,
    DatabaseLogic,
)
from stac_fastapi.sfeos_helpers import filter as filter_module
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
        token: Optional[str],
        limit: int,
        request: Request,
        sort: Optional[List[Dict[str, Any]]] = None,
        bbox: Optional[List[float]] = None,
        q: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Dict[str, Any]]] = None,
        datetime: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[int]]:
        """
        Retrieve a list of collections from OpenSearch, supporting pagination.
        This custom implementation adds collection authorization filtering.

        Args:
            token (Optional[str]): The pagination token.
            limit (int): The number of results to return.
            request (Request): The FastAPI request object.
            sort (Optional[List[Dict[str, Any]]]): Optional sort parameter from the request.
            bbox (Optional[List[float]]): Bounding box to filter collections by spatial extent.
            q (Optional[List[str]]): Free text search terms.
            query (Optional[Dict[str, Dict[str, Any]]]): Query extension parameters.
            filter (Optional[Dict[str, Any]]): Structured query in CQL2 format.
            datetime (Optional[str]): Temporal filter.

        Returns:
            A tuple of (collections, next pagination token if any).

        Raises:
            HTTPException: If sorting is requested on a field that is not sortable.
        """
        # Define sortable fields based on the ES_COLLECTIONS_MAPPINGS
        sortable_fields = ["id", "extent.temporal.interval", "temporal"]

        # Format the sort parameter
        formatted_sort = []
        if sort:
            for item in sort:
                field = item.get("field")
                direction = item.get("direction", "asc")
                if field:
                    # Validate that the field is sortable
                    if field not in sortable_fields:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Field '{field}' is not sortable. Sortable fields are: {', '.join(sortable_fields)}. "
                            + "Text fields are not sortable by default in OpenSearch. "
                            + "To make a field sortable, update the mapping to use 'keyword' type or add a '.keyword' subfield. ",
                        )
                    formatted_sort.append({field: {"order": direction}})
            # Always include id as a secondary sort to ensure consistent pagination
            if not any("id" in item for item in formatted_sort):
                formatted_sort.append({"id": {"order": "asc"}})
        else:
            formatted_sort = [{"id": {"order": "asc"}}]

        body = {
            "sort": formatted_sort,
            "size": limit,
        }

        # Handle search_after token - split by '|' to get all sort values
        search_after = None
        if token:
            try:
                # The token should be a pipe-separated string of sort values
                # e.g., "2023-01-01T00:00:00Z|collection-1"
                search_after = token.split("|")
                # If the number of sort fields doesn't match token parts, ignore the token
                if len(search_after) != len(formatted_sort):
                    search_after = None
            except Exception:
                search_after = None

            if search_after is not None:
                body["search_after"] = search_after

        # Build the query part of the body
        query_parts = []

        # apply collection authorization filter
        authorizations = request.auth.scopes
        if settings.role_admin not in authorizations:
            query_parts.append({"terms": {"_auth.read": authorizations}})

        # Apply free text query if provided
        if q:
            # For collections, we want to search across all relevant fields
            should_clauses = []

            # For each search term
            for term in q:
                # Create a multi_match query for each term
                for field in [
                    "id",
                    "title",
                    "description",
                    "keywords",
                    "summaries.platform",
                    "summaries.constellation",
                    "providers.name",
                    "providers.url",
                ]:
                    should_clauses.append(
                        {
                            "wildcard": {
                                field: {"value": f"*{term}*", "case_insensitive": True}
                            }
                        }
                    )

            # Add the free text query to the query parts
            query_parts.append(
                {"bool": {"should": should_clauses, "minimum_should_match": 1}}
            )

        # Apply structured filter if provided
        if filter:
            # Convert string filter to dict if needed
            if isinstance(filter, str):
                filter = orjson.loads(filter)
            # Convert the filter to an OpenSearch query using the filter module
            es_query = filter_module.to_es(await self.get_queryables_mapping(), filter)
            query_parts.append(es_query)

        # Apply query extension if provided
        if query:
            try:
                # First create a search object to apply filters
                search = Search(index=COLLECTIONS_INDEX)

                # Process each field and operator in the query
                for field_name, expr in query.items():
                    for op, value in expr.items():
                        # For collections, we don't need to prefix with 'properties__'
                        field = field_name
                        # Apply the filter using apply_stacql_filter
                        search = self.apply_stacql_filter(
                            search=search, op=op, field=field, value=value
                        )

                # Convert the search object to a query dict and add it to query_parts
                search_dict = search.to_dict()
                if "query" in search_dict:
                    query_parts.append(search_dict["query"])

            except Exception as e:
                logger.error(f"Error converting query to OpenSearch: {e}")
                # If there's an error, add a query that matches nothing
                query_parts.append({"bool": {"must_not": {"match_all": {}}}})
                raise

        # Combine all query parts with AND logic if there are multiple
        datetime_filter = None
        if datetime:
            datetime_filter = self._apply_collection_datetime_filter(datetime)
            if datetime_filter:
                query_parts.append(datetime_filter)

        # Combine all query parts with AND logic
        if query_parts:
            body["query"] = (
                query_parts[0]
                if len(query_parts) == 1
                else {"bool": {"must": query_parts}}
            )

        # Create a copy of the body for count query (without pagination and sorting)
        count_body = body.copy()
        if "search_after" in count_body:
            del count_body["search_after"]
        count_body["size"] = 0

        # Create async tasks for both search and count
        search_task = asyncio.create_task(
            self.client.search(
                index=COLLECTIONS_INDEX,
                body=body,
            )
        )

        count_task = asyncio.create_task(
            self.client.count(
                index=COLLECTIONS_INDEX,
                body={"query": body.get("query", {"match_all": {}})},
            )
        )

        # Wait for search task to complete
        response = await search_task

        hits = response["hits"]["hits"]
        collections = [
            self.collection_serializer.db_to_stac(
                collection=hit["_source"], request=request, extensions=self.extensions
            )
            for hit in hits
        ]

        next_token = None
        if len(hits) == limit:
            next_token_values = hits[-1].get("sort")
            if next_token_values:
                # Join all sort values with '|' to create the token
                next_token = "|".join(str(val) for val in next_token_values)

        # Get the total count of collections
        matched = (
            response["hits"]["total"]["value"]
            if response["hits"]["total"]["relation"] == "eq"
            else None
        )

        # If count task is done, use its result
        if count_task.done():
            try:
                matched = count_task.result().get("count")
            except Exception as e:
                logger.error(f"Count task failed: {e}")

        return collections, next_token, matched

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
