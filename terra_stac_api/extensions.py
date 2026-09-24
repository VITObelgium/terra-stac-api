from stac_fastapi.core.extensions.aggregation import (
    EsAggregationExtensionGetRequest,
    EsAggregationExtensionPostRequest,
)
from stac_fastapi.extensions import AggregationExtension
from stac_fastapi.sfeos_helpers.models.extensions import Extensions
from stac_fastapi.types.extension import ApiExtension

from terra_stac_api.aggregation_client import AggregationClientAuth


class ExtensionsAuth(Extensions):
    """Extension manager with support for authorization checks."""

    @property
    def aggregation(self) -> list[ApiExtension]:
        aggregation_extension = AggregationExtension(
            client=AggregationClientAuth(
                database=self.database_logic,
                session=self.session,
                settings=self.settings,
            ),
        )
        aggregation_extension.GET = EsAggregationExtensionGetRequest
        aggregation_extension.POST = EsAggregationExtensionPostRequest

        return [aggregation_extension]
