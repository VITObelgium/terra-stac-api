from typing import Any

import attr
from overrides import overrides
from stac_fastapi.sfeos_helpers.sort import EsAsyncBaseSortablesClient
from starlette.requests import Request

from terra_stac_api.core import ensure_authorized_for_collection, AccessType


@attr.s
class SortablesClientAuth(EsAsyncBaseSortablesClient):
    @overrides
    async def get_collection_sortables(self, collection_id: str, request: Request | None = None, **kwargs: Any) -> dict[
        str, Any]:
        await ensure_authorized_for_collection(
            self.database,
            request.user,
            request.auth.scopes,
            collection_id,
            AccessType.READ,
        )

        return await super().get_collection_sortables(collection_id, request, **kwargs)
