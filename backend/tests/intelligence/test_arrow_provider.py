import httpx
import pytest

from httpx import AsyncClient as OriginalAsyncClient

from backend.app.intelligence.enrichment.arrow import (
    ArrowProvider,
)


def make_arrow_response():
    return {
        "itemserviceresult": {
            "serviceMetaData": [
                {
                    "version": "4.0.0",
                }
            ],
            "transactionArea": [
                {
                    "response": {
                        "returnCode": "0",
                        "returnMsg": "",
                        "success": True,
                    }
                }
            ],
            "data": [
                {
                    "PartList": [
                        {
                            "itemId": 123456,
                            "partNum": "LM358DR",
                            "manufacturer": {
                                "mfrCd": "TEXASI",
                                "mfrName": "Texas Instruments",
                            },
                            "desc": (
                                "Dual Operational Amplifier"
                            ),
                            "packageType": "SOIC-8",
                            "resources": [
                                {
                                    "type": (
                                        "cloud_part_detail"
                                    ),
                                    "uri": (
                                        "https://example.com/"
                                        "lm358dr"
                                    ),
                                }
                            ],
                            "InvOrg": {
                                "sources": [
                                    {
                                        "sourceCd": "ACNA",
                                        "displayName": (
                                            "Arrow North America"
                                        ),
                                        "sourceParts": [
                                            {
                                                "Availability": [
                                                    {
                                                        "fohQty": 3000,
                                                        "availabilityCd": (
                                                            "INSTK"
                                                        ),
                                                        "availabilityMessage": (
                                                            "In Stock"
                                                        ),
                                                    }
                                                ]
                                            }
                                        ],
                                    },
                                    {
                                        "sourceCd": "EUROPE",
                                        "displayName": (
                                            "Arrow Europe"
                                        ),
                                        "sourceParts": [
                                            {
                                                "Availability": [
                                                    {
                                                        "fohQty": 1200,
                                                        "availabilityCd": (
                                                            "INSTK"
                                                        ),
                                                        "availabilityMessage": (
                                                            "In Stock"
                                                        ),
                                                    }
                                                ]
                                            }
                                        ],
                                    },
                                ]
                            },
                            "hasDatasheet": True,
                        }
                    ]
                }
            ],
        }
    }


def make_arrow_commercial_response():
    return {
        "itemserviceresult": {
            "transactionArea": [
                {
                    "response": {
                        "returnCode": "0",
                        "returnMsg": "",
                        "success": True,
                    }
                }
            ],
            "data": [
                {
                    "PartList": [
                        {
                            "itemId": 123456,
                            "partNum": "LM358DR",
                            "manufacturer": {
                                "mfrCd": "TEXASI",
                                "mfrName": "Texas Instruments",
                            },
                            "desc": (
                                "Dual Operational Amplifier"
                            ),
                            "packageType": "SOIC-8",
                            "InvOrg": {
                                "sources": [
                                    {
                                        "sourceCd": "ACNA",
                                        "sourceParts": [
                                            {
                                                "Availability": [
                                                    {
                                                        "fohQty": 3000,
                                                    }
                                                ]
                                            }
                                        ],
                                    },
                                    {
                                        "sourceCd": "EUROPE",
                                        "sourceParts": [
                                            {
                                                "Availability": [
                                                    {
                                                        "fohQty": 1200,
                                                    }
                                                ]
                                            }
                                        ],
                                    },
                                ]
                            },
                            "minimumOrderQuantity": 10,
                            "packSize": 10,
                            "Prices": {
                                "resaleList": [
                                    {
                                        "currency": "USD",
                                        "price": 2.40,
                                        "minQty": 1,
                                        "maxQty": 9,
                                    },
                                    {
                                        "currency": "USD",
                                        "price": 2.10,
                                        "minQty": 10,
                                        "maxQty": 99,
                                    },
                                    {
                                        "currency": "USD",
                                        "price": 1.72,
                                        "minQty": 100,
                                    },
                                ]
                            },
                            "mfrLeadTime": 7,
                            "arrowLeadTime": 3,
                        }
                    ]
                }
            ],
        }
    }


@pytest.mark.asyncio
async def test_arrow_provider_enriches_component(
    monkeypatch,
):
    provider = ArrowProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_login",
        "test-login",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        assert request.method == "GET"
        assert request.url.path.endswith(
            "/itemservice/v4/en/search/token"
        )

        assert (
            request.url.params["search_token"]
            == "LM358DR"
        )

        return httpx.Response(
            200,
            json=make_arrow_response(),
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
        "backend.app.intelligence.enrichment.arrow."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert result is not None
    assert result.source == "arrow"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"
    assert (
        result.description
        == "Dual Operational Amplifier"
    )
    assert result.package == "SOIC-8"

    assert result.availability == 4200

    assert (
        result.manufacturer_part_url
        == "https://example.com/lm358dr"
    )


@pytest.mark.asyncio
async def test_arrow_provider_returns_none_for_no_match(
    monkeypatch,
):
    provider = ArrowProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_login",
        "test-login",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        return httpx.Response(
            200,
            json={
                "itemserviceresult": {
                    "transactionArea": [
                        {
                            "response": {
                                "returnCode": "0",
                                "returnMsg": "",
                                "success": True,
                            }
                        }
                    ],
                    "data": [
                        {
                            "PartList": []
                        }
                    ],
                }
            },
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
        "backend.app.intelligence.enrichment.arrow."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.enrich(
        mpn="DOES-NOT-EXIST",
        manufacturer="Unknown",
    )

    assert result is None


@pytest.mark.asyncio
async def test_arrow_provider_returns_supplier_quote(
    monkeypatch,
):
    provider = ArrowProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_login",
        "test-login",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        assert request.method == "GET"

        return httpx.Response(
            200,
            json=make_arrow_commercial_response(),
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
        "backend.app.intelligence.enrichment.arrow."
        "httpx.AsyncClient",
        MockClient,
    )

    result = await provider.quote(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
        quantity=100,
    )

    assert result is not None

    assert result.supplier == "arrow"
    assert result.source == "arrow"
    assert result.mpn == "LM358DR"
    assert result.manufacturer == "Texas Instruments"

    assert result.unit_price == 1.72
    assert result.currency == "USD"

    assert result.quantity_available == 4200

    assert result.moq == 10
    assert result.order_multiple == 10

    assert result.lead_time_days == 10

    assert len(result.price_breaks) == 3

    assert result.price_breaks[0].min_quantity == 1
    assert result.price_breaks[0].unit_price == 2.40

    assert result.price_breaks[1].min_quantity == 10
    assert result.price_breaks[1].unit_price == 2.10

    assert result.price_breaks[2].min_quantity == 100
    assert result.price_breaks[2].unit_price == 1.72

@pytest.mark.asyncio
async def test_arrow_provider_propagates_http_429(
    monkeypatch,
):
    provider = ArrowProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_login",
        "test-login",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_key",
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
        "backend.app.intelligence.enrichment.arrow."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.HTTPStatusError):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )


@pytest.mark.asyncio
async def test_arrow_provider_propagates_timeout(
    monkeypatch,
):
    provider = ArrowProvider()

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_login",
        "test-login",
    )

    monkeypatch.setattr(
        "backend.app.intelligence.enrichment.arrow."
        "settings.arrow_api_key",
        "test-api-key",
    )

    async def mock_handler(
        request: httpx.Request,
    ):
        raise httpx.TimeoutException(
            "Arrow request timed out."
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
        "backend.app.intelligence.enrichment.arrow."
        "httpx.AsyncClient",
        MockClient,
    )

    with pytest.raises(httpx.TimeoutException):
        await provider.enrich(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
        )