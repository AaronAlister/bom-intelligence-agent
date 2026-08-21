from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
    SupplierQuote,
)


def test_price_break_stores_quantity_range_and_price():
    price_break = PriceBreak(
        min_quantity=100,
        max_quantity=999,
        unit_price=1.75,
        currency="USD",
    )

    assert price_break.min_quantity == 100
    assert price_break.max_quantity == 999
    assert price_break.unit_price == 1.75
    assert price_break.currency == "USD"


def test_price_break_supports_open_ended_range():
    price_break = PriceBreak(
        min_quantity=1000,
        unit_price=1.25,
        currency="USD",
    )

    assert price_break.min_quantity == 1000
    assert price_break.max_quantity is None


def test_supplier_quote_stores_commercial_data():
    quote = SupplierQuote(
        supplier="mouser",
        manufacturer="Texas Instruments",
        mpn="LM358DR",
        unit_price=2.10,
        currency="USD",
        quantity_available=5000,
        moq=10,
        order_multiple=10,
        lead_time_days=7,
        price_breaks=[
            PriceBreak(
                min_quantity=1,
                max_quantity=9,
                unit_price=2.40,
                currency="USD",
            ),
            PriceBreak(
                min_quantity=10,
                max_quantity=99,
                unit_price=2.10,
                currency="USD",
            ),
        ],
        source="mouser",
    )

    assert quote.supplier == "mouser"
    assert quote.mpn == "LM358DR"
    assert quote.unit_price == 2.10
    assert quote.currency == "USD"
    assert quote.quantity_available == 5000
    assert quote.moq == 10
    assert quote.order_multiple == 10
    assert quote.lead_time_days == 7
    assert len(quote.price_breaks) == 2