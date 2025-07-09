from typing import Dict, List, Optional, Union, Any

from fastapi import Path
from overrides import overrides
from stac_fastapi.core.extensions.aggregation import (
    EsAggregationExtensionPostRequest,
)
from stac_fastapi.sfeos_helpers.aggregation import EsAsyncBaseAggregationClient

from stac_fastapi.types.rfc3339 import DateTimeType
from stac_pydantic.shared import BBox
from typing_extensions import Annotated

from terra_stac_api.core import AccessType, ensure_authorized_for_collection
from terra_stac_api.db import DatabaseLogicAuth


class AggregationClientAuth(EsAsyncBaseAggregationClient):
    database: DatabaseLogicAuth

    @overrides
    async def get_aggregations(self, collection_id: Optional[str] = None, **kwargs)\
            -> Dict[str, Any]:
        request = kwargs["request"]
        if collection_id is not None:
            await ensure_authorized_for_collection(
                self.database,
                request.user,
                request.auth.scopes,
                collection_id,
                AccessType.READ,
            )
        return await super().get_aggregations(collection_id, **kwargs)

    @overrides
    async def aggregate(
        self,
        aggregate_request: Optional[EsAggregationExtensionPostRequest] = None,
        collection_id: Optional[
            Annotated[str, Path(description="Collection ID")]
        ] = None,
        collections: Optional[List[str]] = [],
        datetime: Optional[DateTimeType] = None,
        intersects: Optional[str] = None,
        filter_lang: Optional[str] = None,
        filter_expr: Optional[str] = None,
        aggregations: Optional[str] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[BBox] = None,
        centroid_geohash_grid_frequency_precision: Optional[int] = None,
        centroid_geohex_grid_frequency_precision: Optional[int] = None,
        centroid_geotile_grid_frequency_precision: Optional[int] = None,
        geometry_geohash_grid_frequency_precision: Optional[int] = None,
        geometry_geotile_grid_frequency_precision: Optional[int] = None,
        datetime_frequency_interval: Optional[str] = None,
        **kwargs,
    ) -> Union[Dict, Exception]:
        request = kwargs["request"]
        if collection_id is not None:
            await ensure_authorized_for_collection(
                self.database,
                request.user,
                request.auth.scopes,
                collection_id,
                AccessType.READ,
            )
        elif collections is not None:
            for c in collections:
                await ensure_authorized_for_collection(
                    self.database,
                    request.user,
                    request.auth.scopes,
                    c,
                    AccessType.READ,
                )
        else:
            # set collections to authorized collections
            collections = {
                c["id"]
                for c in await self.database.get_all_authorized_collections(
                    request.auth.scopes, _source=["id"]
                )
            }

        return await super().aggregate(
            aggregate_request,
            collection_id,
            collections,
            datetime,
            intersects,
            filter_lang,
            filter_expr,
            aggregations,
            ids,
            bbox,
            centroid_geohash_grid_frequency_precision,
            centroid_geohex_grid_frequency_precision,
            centroid_geotile_grid_frequency_precision,
            geometry_geohash_grid_frequency_precision,
            geometry_geotile_grid_frequency_precision,
            datetime_frequency_interval,
            **kwargs,
        )
