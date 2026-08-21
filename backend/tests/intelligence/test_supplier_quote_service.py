import pytest

from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.service import (
    SupplierQuoteService,
)


class MockSupplier(
    SupplierQuoteProvider,
):
    def __init__(
        self,
        supplier_name: str,
        result: SupplierQuote | None = None,
        error: Exception | None = None,
    ) -> None:
        self._name = supplier_name
        self._result = result
        self._error = error
        self.calls = 0
        self.received_quantity = None

    @property
    def name(self) -> str:
        return self._name

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        self.calls += 1
        self.received_quantity = quantity

        if self._error is not None:
            raise self._error

        return self._result


@pytest.mark.asyncio
async def test_quote_all_queries_every_supplier():
    mouser = MockSupplier(
        "mouser",
        SupplierQuote(
            supplier="mouser",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.72,
            currency="USD",
            quantity_available=5000,
            moq=10,
            order_multiple=10,
            lead_time_days=14,
            source="mouser",
        ),
    )

    arrow = MockSupplier(
        "arrow",
        SupplierQuote(
            supplier="arrow",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.75,
            currency="USD",
            quantity_available=4200,
            moq=10,
            order_multiple=10,
            lead_time_days=10,
            source="arrow",
        ),
    )

    digikey = MockSupplier(
        "digikey",
        SupplierQuote(
            supplier="digikey",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.80,
            currency="USD",
            quantity_available=8100,
            moq=10,
            order_multiple=10,
            lead_time_days=5,
            source="digikey",
        ),
    )

    service = SupplierQuoteService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.quote_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert len(results) == 3

    assert [
        result.supplier
        for result in results
    ] == [
        "mouser",
        "arrow",
        "digikey",
    ]

    assert [
        result.unit_price
        for result in results
    ] == [
        1.72,
        1.75,
        1.80,
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1

    assert mouser.received_quantity == 100
    assert arrow.received_quantity == 100
    assert digikey.received_quantity == 100


@pytest.mark.asyncio
async def test_quote_all_ignores_supplier_not_found():
    mouser = MockSupplier(
        "mouser",
        None,
    )

    arrow = MockSupplier(
        "arrow",
        SupplierQuote(
            supplier="arrow",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.75,
            currency="USD",
            source="arrow",
        ),
    )

    digikey = MockSupplier(
        "digikey",
        None,
    )

    service = SupplierQuoteService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.quote_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert len(results) == 1
    assert results[0].supplier == "arrow"

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_quote_all_continues_after_supplier_failure():
    mouser = MockSupplier(
        "mouser",
        error=RuntimeError(
            "Mouser unavailable"
        ),
    )

    arrow = MockSupplier(
        "arrow",
        SupplierQuote(
            supplier="arrow",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.75,
            currency="USD",
            source="arrow",
        ),
    )

    digikey = MockSupplier(
        "digikey",
        SupplierQuote(
            supplier="digikey",
            manufacturer="Texas Instruments",
            mpn="LM358DR",
            unit_price=1.80,
            currency="USD",
            source="digikey",
        ),
    )

    service = SupplierQuoteService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.quote_all(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert len(results) == 2

    assert [
        result.supplier
        for result in results
    ] == [
        "arrow",
        "digikey",
    ]

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


@pytest.mark.asyncio
async def test_quote_all_returns_empty_when_no_supplier_succeeds():
    mouser = MockSupplier(
        "mouser",
        None,
    )

    arrow = MockSupplier(
        "arrow",
        error=RuntimeError(
            "Arrow unavailable"
        ),
    )

    digikey = MockSupplier(
        "digikey",
        None,
    )

    service = SupplierQuoteService(
        [
            mouser,
            arrow,
            digikey,
        ]
    )

    results = await service.quote_all(
        mpn="UNKNOWN",
        manufacturer="Unknown",
        quantity=100,
    )

    assert results == []

    assert mouser.calls == 1
    assert arrow.calls == 1
    assert digikey.calls == 1


def test_supplier_quote_service_requires_provider():
    with pytest.raises(
        ValueError,
        match="At least one supplier quote provider",
    ):
        SupplierQuoteService([])