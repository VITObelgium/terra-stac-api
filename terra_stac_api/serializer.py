from stac_fastapi.core.serializers import CollectionSerializer
from stac_fastapi.types import stac as stac_types


class CustomCollectionSerializer(CollectionSerializer):
    """
    Custom serializer for Collection objects, hiding fields starting with an underscore.
    """

    @classmethod
    def db_to_stac(cls, collection: dict, base_url: str) -> stac_types.Collection:
        c = super().db_to_stac(collection, base_url)
        hidden_keys = {k for k in c.keys() if k.startswith("_")}
        for key in hidden_keys:
            c.pop(key)
        return c
