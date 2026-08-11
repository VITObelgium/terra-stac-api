from typing import Any, Dict, List, Optional, Union

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
    async def get_aggregations(
        self, collection_id: str | None = None, **kwargs
    ) -> Dict[str, Any]:
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
        aggregate_request: EsAggregationExtensionPostRequest | None = None,
        collection_id: Annotated[str, Path(description="Collection ID")] | None = None,
        collections: list[str] | None = [],
        datetime: DateTimeType | None = None,
        intersects: str | None = None,
        filter_lang: str | None = None,
        filter_expr: str | None = None,
        aggregations: str | None = None,
        ids: list[str] | None = None,
        bbox: BBox | None = None,
        centroid_geohash_grid_frequency_precision: int | None = None,
        centroid_geohex_grid_frequency_precision: int | None = None,
        centroid_geotile_grid_frequency_precision: int | None = None,
        geometry_geohash_grid_frequency_precision: int | None = None,
        geometry_geotile_grid_frequency_precision: int | None = None,
        datetime_frequency_interval: str | None = None,
        **kwargs,
    ) -> dict | Exception:
        request: Request = kwargs["request"]
        if collection_id is not None:
            collections = [str(collection_id)]
        if collections is not None:
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
