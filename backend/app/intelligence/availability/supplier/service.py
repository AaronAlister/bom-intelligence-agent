from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)


class SupplierQuoteService:
    """
    Coordinates commercial quote retrieval across
    all configured supplier providers.
    """

    def __init__(
        self,
        providers: list[SupplierQuoteProvider],
    ) -> None:
        if not providers:
            raise ValueError(
                "At least one supplier quote provider is required"
            )

        self._providers = providers

    async def quote_all(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> list[SupplierQuote]:
        """
        Query every supplier and return successful quotes.

        A supplier failure must not prevent the remaining
        suppliers from being queried.
        """

        results: list[SupplierQuote] = []

        for provider in self._providers:
            try:
                result = await provider.quote(
                    mpn=mpn,
                    manufacturer=manufacturer,
                    quantity=quantity,
                )

            except Exception:
                # One supplier failure must not prevent
                # other suppliers from being evaluated.
                continue

            if result is None:
                continue

            results.append(result)

        return results

    @property
    def providers(
        self,
    ) -> tuple[SupplierQuoteProvider, ...]:
        """Return configured suppliers in order."""

        return tuple(self._providers)