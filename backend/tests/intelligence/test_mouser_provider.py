import httpx
from httpx import AsyncClient as OriginalAsyncClient
import pytest

from backend.app.intelligence.enrichment.mouser import (
    MouserProvider,
)


def make_mouser_response():
    return {
        "Errors": [],
        "SearchResults": {
            "NumberOfResult": 1,
            "Parts": [
                {
                    "MouserPartNumber": "595-LM358DR",
                    "ManufacturerPartNumber": "LM358DR",
                    "Manufacturer": "Texas Instruments",
                    "Description": "Dual Operational Amplifier",
                    "Category": "Operational Amplifiers",
                    "DataSheetUrl": (
                        "https://example.com/lm358dr.pdf"
                    ),
                    "ProductDetailUrl": (
                        "https://example.com/lm358dr"
                    ),
                    "Packaging": "SOIC-8",
                    "Availability": "5000 In Stock",
                    "AvailabilityInStock": "5000",
                    "LifecycleStatus": "Active",
                }
            ],
        },
    }


def make_mouser_commercial_response():
    return {
        "Errors": [],
        "SearchResults": {
            "NumberOfResult": 1,
            "Parts": [
                {
                    "MouserPartNumber": "595-LM358DR",
                    "ManufacturerPartNumber": "LM358DR",
                    "Manufacturer": "Texas Instruments",
                    "AvailabilityInStock": "5000",
                    "Min": "10",
                    "Mult": "10",
                    "LeadTime": "2 Weeks",
                    "PriceBreaks": [
                        {
                            "Quantity": "1",
                            "Price": "$2.40",
                            "Currency": "USD",
                        },
                        {
                            "Quantity": "10",
                            "Price": "$2.10",
                            "Currency": "USD",
                        },
                        {
                            "Quantity": "100",
                            "Price": "$1.72",
                            "Currency": "USD",
                        },
                    ],
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_mouser_provider_enriches_component(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings.mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(request: httpx.Request):
        assert request.method == "POST"
        assert request.url.path.endswith(
            "/search/partnumber"
        )

        return httpx.Response(
            200,
            json=make_mouser_response(),
        )

    transport = httpx.MockTransport(mock_handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert result is not None
    assert result.source == "mouser"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"
    assert result.description == "Dual Operational Amplifier"
    assert result.category == "Operational Amplifiers"
    assert result.package == "SOIC-8"
    assert result.availability == 5000
    assert result.lifecycle_status == "Active"

    assert (
        result.datasheet_url
        == "https://example.com/lm358dr.pdf"
    )


@pytest.mark.asyncio
async def test_mouser_provider_returns_none_for_no_match(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings.mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "Errors": [],
                "SearchResults": {
                    "NumberOfResult": 0,
                    "Parts": [],
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="DOES-NOT-EXIST",
        manufacturer="Unknown",
    )

    assert result is None


@pytest.mark.asyncio
async def test_mouser_provider_returns_supplier_quote(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings."
        "mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        assert request.method == "POST"

        return httpx.Response(
            200,
            json=make_mouser_commercial_response(),
        )

    transport = httpx.MockTransport(
        mock_handler
    )

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.quote(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert result is not None

    assert result.supplier == "mouser"
    assert result.source == "mouser"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"

    assert result.unit_price == 1.72
    assert result.currency == "USD"

    assert result.quantity_available == 5000
    assert result.moq == 10
    assert result.order_multiple == 10
    assert result.lead_time_days == 14

    assert len(result.price_breaks) == 3

    assert result.price_breaks[0].min_quantity == 1
    assert result.price_breaks[0].unit_price == 2.40

    assert result.price_breaks[1].min_quantity == 10
    assert result.price_breaks[1].unit_price == 2.10

    assert result.price_breaks[2].min_quantity == 100
    assert result.price_breaks[2].unit_price == 1.72


@pytest.mark.asyncio
async def test_mouser_provider_selects_quantity_1_price(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings."
        "mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=make_mouser_commercial_response(),
        )

    transport = httpx.MockTransport(mock_handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.quote(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=1,
    )

    assert result is not None
    assert result.unit_price == 2.40
    assert result.currency == "USD"


@pytest.mark.asyncio
async def test_mouser_provider_selects_quantity_10_price(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings."
        "mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=make_mouser_commercial_response(),
        )

    transport = httpx.MockTransport(mock_handler)

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.quote(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=10,
    )

    assert result is not None
    assert result.unit_price == 2.10
    assert result.currency == "USD"

@pytest.mark.asyncio
async def test_mouser_provider_propagates_http_429(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings."
        "mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            429,
            request=request,
        )

    transport = httpx.MockTransport(
        mock_handler
    )

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )


@pytest.mark.asyncio
async def test_mouser_provider_propagates_timeout(
    monkeypatch,
):
    provider = MouserProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser.settings."
        "mouser_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        raise httpx.TimeoutException(
            "Mouser request timed out."
        )

    transport = httpx.MockTransport(
        mock_handler
    )

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.client = OriginalAsyncClient(
                transport=transport
            )

        async def __aenter__(self):
            return self.client

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            await self.client.aclose()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.mouser."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.TimeoutException):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )