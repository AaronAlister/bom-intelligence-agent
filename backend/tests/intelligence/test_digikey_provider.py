import httpx
import pytest

from httpx import AsyncClient as OriginalAsyncClient

from backend.app.intelligence.enrichment.digikey import (
    DigiKeyProvider,
)


def make_token_response():
    return {
        "access_token": "test-access-token",
        "expires_in": 600,
        "token_type": "Bearer",
    }


def make_product_response():
    return {
        "Product": {
            "Manufacturer": {
                "Name": "Texas Instruments",
            },
            "ManufacturerProductNumber": "LM358DR",
            "Description": "Dual Operational Amplifier",
            "Category": {
                "Name": "Operational Amplifiers",
            },
            "PackageType": {
                "Name": "SOIC-8",
            },
            "DatasheetUrl": (
                "https://example.com/lm358dr.pdf"
            ),
            "ProductUrl": (
                "https://example.com/lm358dr"
            ),
            "QuantityAvailable": 8100,
            "ProductStatus": "Active",
        }
    }


def make_keyword_search_response():
    return {
        "Products": [
            {
                "Manufacturer": {
                    "Name": "Texas Instruments",
                },
                "ManufacturerProductNumber": "LM358DR",
                "ProductVariations": [
                    {
                        "DigiKeyProductNumber": "LM358DR-ND",
                    }
                ],
            }
        ]
    }


def make_pricing_response():
    return {
        "Product": {
            "Manufacturer": {
                "Name": "Texas Instruments",
            },
            "ManufacturerProductNumber": "LM358DR",
            "QuantityAvailable": 8100,
            "PriceBreaks": [
                {
                    "Quantity": 1,
                    "UnitPrice": 2.40,
                    "Currency": "USD",
                },
                {
                    "Quantity": 10,
                    "UnitPrice": 2.10,
                    "Currency": "USD",
                },
                {
                    "Quantity": 100,
                    "UnitPrice": 1.72,
                    "Currency": "USD",
                },
            ],
            "MinimumOrderQuantity": 10,
            "OrderMultiple": 10,
            "LeadTimeDays": 5,
        }
    }


@pytest.mark.asyncio
async def test_digikey_provider_enriches_component(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            assert request.method == "POST"
            return httpx.Response(
                200,
                json=make_token_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/keyword"
        ):
            assert request.method == "POST"
            return httpx.Response(
                200,
                json=make_keyword_search_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/LM358DR-ND/productdetails"
        ):
            assert request.method == "GET"
            assert (
                request.headers["Authorization"]
                == "Bearer test-access-token"
            )
            assert (
                request.headers["X-DIGIKEY-Client-Id"]
                == "test-client-id"
            )
            return httpx.Response(
                200,
                json=make_product_response(),
            )

        raise AssertionError(
            f"Unexpected Digi-Key request: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert result is not None
    assert result.source == "digikey"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"

    assert (
        result.description
        == "Dual Operational Amplifier"
    )

    assert result.category == "Operational Amplifiers"
    assert result.package == "SOIC-8"

    assert result.availability == 8100

    assert (
        result.datasheet_url
        == "https://example.com/lm358dr.pdf"
    )

    assert (
        result.manufacturer_part_url
        == "https://example.com/lm358dr"
    )

    assert result.lifecycle_status == "Active"


@pytest.mark.asyncio
async def test_digikey_provider_returns_none_for_no_match(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json=make_token_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/keyword"
        ):
            # Return empty search results (no match)
            return httpx.Response(
                200,
                json={"Products": []},
            )

        raise AssertionError(
            f"Unexpected Digi-Key request: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="DOES-NOT-EXIST",
        manufacturer="Unknown",
    )

    assert result is None


@pytest.mark.asyncio
async def test_digikey_provider_reuses_cached_token(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    oauth_calls = 0

    async def mock_handler(
        request: httpx.Request,
    ):
        nonlocal oauth_calls

        if request.url.path == "/v1/oauth2/token":
            oauth_calls += 1
            return httpx.Response(
                200,
                json={
                    "access_token": "cached-token",
                    "expires_in": 600,
                },
            )

        if request.url.path.endswith(
            "/products/v4/search/keyword"
        ):
            return httpx.Response(
                200,
                json=make_keyword_search_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/LM358DR-ND/productdetails"
        ):
            return httpx.Response(
                200,
                json=make_product_response(),
            )

        raise AssertionError(
            f"Unexpected Digi-Key request: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    first_result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    second_result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert first_result is not None
    assert second_result is not None

    assert oauth_calls == 1


@pytest.mark.asyncio
async def test_digikey_provider_refreshes_expired_token(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    oauth_calls = 0

    async def mock_handler(
        request: httpx.Request,
    ):
        nonlocal oauth_calls

        if request.url.path == "/v1/oauth2/token":
            oauth_calls += 1
            return httpx.Response(
                200,
                json={
                    "access_token": (
                        f"token-{oauth_calls}"
                    ),
                    "expires_in": 600,
                },
            )

        if request.url.path.endswith(
            "/products/v4/search/keyword"
        ):
            return httpx.Response(
                200,
                json=make_keyword_search_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/LM358DR-ND/productdetails"
        ):
            return httpx.Response(
                200,
                json=make_product_response(),
            )

        raise AssertionError(
            f"Unexpected Digi-Key request: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    first_result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert first_result is not None

    # Force the cached token to expire.
    provider._token_expires_at = 0.0

    second_result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert second_result is not None

    assert oauth_calls == 2


@pytest.mark.asyncio
async def test_digikey_provider_returns_supplier_quote(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                200,
                json=make_token_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/keyword"
        ):
            return httpx.Response(
                200,
                json=make_keyword_search_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/LM358DR-ND/productdetails"
        ):
            return httpx.Response(
                200,
                json=make_product_response(),
            )

        if request.url.path.endswith(
            "/products/v4/search/LM358DR-ND/pricing"
        ):
            return httpx.Response(
                200,
                json=make_pricing_response(),
            )

        raise AssertionError(
            f"Unexpected Digi-Key request: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.quote(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert result is not None

    assert result.supplier == "digikey"
    assert result.source == "digikey"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"

    assert result.unit_price == 1.72
    assert result.currency == "USD"

    assert result.quantity_available == 8100

    assert result.moq == 10
    assert result.order_multiple == 10

    assert result.lead_time_days == 5

    assert len(result.price_breaks) == 3

    assert result.price_breaks[0].min_quantity == 1
    assert result.price_breaks[0].unit_price == 2.40

    assert result.price_breaks[1].min_quantity == 10
    assert result.price_breaks[1].unit_price == 2.10

    assert result.price_breaks[2].min_quantity == 100
    assert result.price_breaks[2].unit_price == 1.72


@pytest.mark.asyncio
async def test_digikey_provider_propagates_http_429(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(
                429,
                request=request,
            )

        raise AssertionError(
            f"Unexpected request after OAuth: "
            f"{request.method} {request.url.path}"
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )


@pytest.mark.asyncio
async def test_digikey_provider_propagates_timeout(
    monkeypatch,
):
    provider = DigiKeyProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_id",
        "test-client-id",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.digikey."
        "settings.digikey_client_secret",
        "test-client-secret",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        raise httpx.TimeoutException(
            "Digi-Key request timed out."
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
        "backend.app.intelligence.enrichment.digikey."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.TimeoutException):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )