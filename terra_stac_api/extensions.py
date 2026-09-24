from stac_fastapi.core.extensions.aggregation import (
    EsAggregationExtensionGetRequest,
    EsAggregationExtensionPostRequest,
)
from stac_fastapi.extensions import (
    AggregationExtension,
    BulkTransactionExtension,
    TransactionExtension,
)
from stac_fastapi.sfeos_helpers.models.extensions import Extensions
from stac_fastapi.types.extension import ApiExtension

from terra_stac_api.aggregation_client import AggregationClientAuth
from terra_stac_api.core import BulkTransactionsClientAuth, TransactionsClientAuth


class ExtensionsAuth(Extensions):
    """Extension manager with support for authorization checks."""

    @property
    def aggregation(self) -> list[ApiExtension]:
        """
        Return the aggregation extension with authorization checks.
        """
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

    @property
    def transaction(self) -> list[ApiExtension]:
        """
        Return the transaction extension with authorization checks.
        """
        if not self.transactions_enabled:
            return []

        return [
            TransactionExtension(
                client=TransactionsClientAuth(
                    database=self.database_logic,
                    session=self.session,
                    settings=self.settings,
                ),
                settings=self.settings,
            ),
            BulkTransactionExtension(
                client=BulkTransactionsClientAuth(
                    database=self.database_logic,
                    session=self.session,
                    settings=self.settings,
                )
            ),
        ]
