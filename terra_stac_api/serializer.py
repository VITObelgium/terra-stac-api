from typing import List, Optional

from overrides import overrides
from stac_fastapi.core.serializers import CollectionSerializer
from stac_fastapi.types import stac as stac_types
from starlette.requests import Request


class CustomCollectionSerializer(CollectionSerializer):
    """
    Custom serializer for Collection objects, hiding fields starting with an underscore.
    """

    @classmethod
    @overrides
    def db_to_stac(
        cls, collection: dict, request: Request, extensions: Optional[List[str]] = []
    ) -> stac_types.Collection:
        c = super().db_to_stac(collection, request=request, extensions=extensions)
        hidden_keys = {k for k in c.keys() if k.startswith("_")}
        for key in hidden_keys:
            c.pop(key)
        return c
