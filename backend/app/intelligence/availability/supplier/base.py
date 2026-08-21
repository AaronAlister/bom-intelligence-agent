from abc import ABC, abstractmethod

from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)


class SupplierQuoteProvider(ABC):
    """Interface implemented by supplier quote providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the supplier name."""
        raise NotImplementedError

    @abstractmethod
    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        """
        Retrieve normalized commercial information
        for a component.

        Returns None when the supplier cannot provide
        a quote for the requested component.
        """
        raise NotImplementedError