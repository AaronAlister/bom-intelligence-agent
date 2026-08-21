import time
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.ingestion.normalizer import (
    manufacturers_match,          # <-- ADDED
    normalize_manufacturer,
    normalize_mpn,
    normalize_text,
)
from backend.app.intelligence.availability.supplier.base import (
    SupplierQuoteProvider,
)
from backend.app.intelligence.availability.supplier.models import (
    PriceBreak,
    SupplierQuote,
)
from backend.app.intelligence.availability.supplier.pricing import (
    select_price_break,
)
from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class DigiKeyProvider(
    ComponentEnrichmentProvider,
    SupplierQuoteProvider,
):
    """Digi-Key Product Information V4 provider."""

    # Refresh slightly before actual expiration.
    _TOKEN_EXPIRY_BUFFER_SECONDS = 30.0

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def name(self) -> str:
        return "digikey"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        """
        Retrieve Digi-Key product information for an MPN.
        """

        if not settings.digikey_client_id:
            raise RuntimeError(
                "Digi-Key client ID is not configured"
            )

        if not settings.digikey_client_secret:
            raise RuntimeError(
                "Digi-Key client secret is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Digi-Key enrichment"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        async with httpx.AsyncClient(
            timeout=settings.digikey_api_timeout_seconds
        ) as client:
            access_token = (
                await self._get_access_token(client)
            )

            # Step 1: Search by keyword to get exact match and product number
            search_product = await self._search_keyword(
                client=client,
                access_token=access_token,
                mpn=normalized_mpn,
                manufacturer=normalized_manufacturer,
            )

            if not search_product:
                return None

            # Step 2: Extract Digi-Key product number from search result
            product_number = (
                self._extract_digikey_product_number(
                    search_product
                )
            )

            if product_number is None:
                return None

            # Step 3: Get product details using the product number
            data = await self._get_product_details(
                client=client,
                access_token=access_token,
                product_number=product_number,
            )

        detailed_product = self._extract_product(data)

        if detailed_product is None:
            return None

        return self._to_enrichment_result(
            detailed_product
        )

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        """
        Retrieve normalized commercial information
        for a Digi-Key component.
        """

        if not settings.digikey_client_id:
            raise RuntimeError(
                "Digi-Key client ID is not configured"
            )

        if not settings.digikey_client_secret:
            raise RuntimeError(
                "Digi-Key client secret is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Digi-Key quote"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        async with httpx.AsyncClient(
            timeout=settings.digikey_api_timeout_seconds
        ) as client:
            access_token = (
                await self._get_access_token(client)
            )

            # Step 1: Search by keyword to get exact match and product number
            search_product = await self._search_keyword(
                client=client,
                access_token=access_token,
                mpn=normalized_mpn,
                manufacturer=normalized_manufacturer,
            )

            if not search_product:
                return None

            # Step 2: Extract Digi-Key product number
            product_number = (
                self._extract_digikey_product_number(
                    search_product
                )
            )

            if product_number is None:
                return None

            # Step 3: Get product details using the product number
            product_data = await self._get_product_details(
                client=client,
                access_token=access_token,
                product_number=product_number,
            )

            product = self._extract_product(
                product_data
            )

            if product is None:
                return None

            # Step 4: Get pricing using the product number
            pricing_data = await self._get_pricing(
                client=client,
                access_token=access_token,
                product_number=product_number,
            )

        return self._to_supplier_quote(
            product=product,
            pricing_data=pricing_data,
            quantity=quantity,
        )

    async def _get_access_token(
        self,
        client: httpx.AsyncClient,
    ) -> str:
        """
        Return a valid Digi-Key OAuth access token.

        Reuses the cached token while it remains valid.
        Requests a new token only when the cache is empty
        or expired.
        """

        now = time.monotonic()

        # Reuse cached token when still valid.
        if (
            self._access_token is not None
            and now < self._token_expires_at
        ):
            return self._access_token

        url = (
            f"{settings.digikey_api_base_url}"
            "/v1/oauth2/token"
        )

        response = await client.post(
            url,
            data={
                "client_id": settings.digikey_client_id,
                "client_secret": (
                    settings.digikey_client_secret
                ),
                "grant_type": "client_credentials",
            },
        )

        response.raise_for_status()

        data = response.json()

        access_token = data.get("access_token")

        if not access_token:
            raise RuntimeError(
                "Digi-Key OAuth response did not "
                "contain an access token"
            )

        expires_in = data.get(
            "expires_in",
            600,
        )

        try:
            expires_in_seconds = float(expires_in)
        except (TypeError, ValueError):
            expires_in_seconds = 600.0

        self._access_token = access_token

        self._token_expires_at = (
            now
            + max(
                0.0,
                expires_in_seconds
                - self._TOKEN_EXPIRY_BUFFER_SECONDS,
            )
        )

        return access_token

    async def _search_keyword(
        self,
        *,
        client: httpx.AsyncClient,
        access_token: str,
        mpn: str,
        manufacturer: str | None,
    ) -> dict[str, Any]:
        """Search Digi-Key by MPN and return matching products."""
        url = (
            f"{settings.digikey_api_base_url}"
            "/products/v4/search/keyword"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-DIGIKEY-Client-Id": (
                settings.digikey_client_id
            ),
            "X-DIGIKEY-Locale-Site": (
                settings.digikey_locale_site
            ),
            "X-DIGIKEY-Locale-Language": (
                settings.digikey_locale_language
            ),
            "X-DIGIKEY-Locale-Currency": (
                settings.digikey_locale_currency
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = await client.post(
            url,
            headers=headers,
            json={
                "Keywords": mpn,
                "Limit": 10,
                "Offset": 0,
            },
        )

        response.raise_for_status()

        data = response.json()

        product = self._select_exact_product(
            data=data,
            mpn=mpn,
            manufacturer=manufacturer,
        )

        if product is None:
            return {}

        return product

    @staticmethod
    def _select_exact_product(
        *,
        data: dict[str, Any],
        mpn: str,
        manufacturer: str | None,
    ) -> dict[str, Any] | None:
        """Select an exact MPN/manufacturer match."""
        candidates = data.get("ExactMatches")

        if not isinstance(candidates, list):
            candidates = data.get("Products")

        if not isinstance(candidates, list):
            return None

        normalized_target_mpn = normalize_mpn(mpn)

        if normalized_target_mpn is None:
            return None

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            candidate_mpn = normalize_mpn(
                candidate.get("ManufacturerProductNumber")
            )

            if candidate_mpn != normalized_target_mpn:
                continue

            if not DigiKeyProvider._manufacturer_matches(
                product=candidate,
                manufacturer=manufacturer,
            ):
                continue

            return candidate

        return None

    @staticmethod
    def _extract_digikey_product_number(
        product: dict[str, Any],
    ) -> str | None:
        """Extract a Digi-Key product number from a search result."""
        variations = product.get("ProductVariations")

        if not isinstance(variations, list):
            return None

        for variation in variations:
            if not isinstance(variation, dict):
                continue

            product_number = variation.get(
                "DigiKeyProductNumber"
            )

            if isinstance(product_number, str):
                normalized = normalize_text(
                    product_number
                )

                if normalized is not None:
                    return normalized

        return None

    async def _get_product_details(
        self,
        *,
        client: httpx.AsyncClient,
        access_token: str,
        product_number: str,
    ) -> dict[str, Any]:
        """Retrieve expanded product information using Digi-Key product number."""
        url = (
            f"{settings.digikey_api_base_url}"
            "/products/v4/search/"
            f"{product_number}/productdetails"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-DIGIKEY-Client-Id": (
                settings.digikey_client_id
            ),
            "X-DIGIKEY-Locale-Site": (
                settings.digikey_locale_site
            ),
            "X-DIGIKEY-Locale-Language": (
                settings.digikey_locale_language
            ),
            "X-DIGIKEY-Locale-Currency": (
                settings.digikey_locale_currency
            ),
            "Accept": "application/json",
        }

        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()

    async def _get_pricing(
        self,
        *,
        client: httpx.AsyncClient,
        access_token: str,
        product_number: str,
    ) -> dict[str, Any]:
        """Retrieve Digi-Key pricing information using Digi-Key product number."""
        url = (
            f"{settings.digikey_api_base_url}"
            "/products/v4/search/"
            f"{product_number}/pricing"
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-DIGIKEY-Client-Id": (
                settings.digikey_client_id
            ),
            "X-DIGIKEY-Locale-Site": (
                settings.digikey_locale_site
            ),
            "X-DIGIKEY-Locale-Language": (
                settings.digikey_locale_language
            ),
            "X-DIGIKEY-Locale-Currency": (
                settings.digikey_locale_currency
            ),
            "Accept": "application/json",
        }

        response = await client.get(
            url,
            headers=headers,
        )

        response.raise_for_status()

        return response.json()

    @staticmethod
    def _extract_product(
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Extract the product from Digi-Key's response.
        """
        product = data.get("Product")

        if isinstance(product, dict):
            return product

        products = data.get("Products")

        if isinstance(products, list) and products:
            first = products[0]

            if isinstance(first, dict):
                return first

        return None

    @staticmethod
    def _manufacturer_matches(
        *,
        product: dict[str, Any],
        manufacturer: str | None,
    ) -> bool:
        """Verify manufacturer when supplied by the BOM."""
        if manufacturer is None:
            return True

        manufacturer_data = product.get(
            "Manufacturer"
        )

        if isinstance(manufacturer_data, dict):
            product_manufacturer = (
                manufacturer_data.get("Name")
            )
        else:
            product_manufacturer = manufacturer_data

        product_manufacturer = normalize_manufacturer(
            product_manufacturer
        )

        if product_manufacturer is None:
            return False

        # Changed to fuzzy manufacturer matching
        return manufacturers_match(
            product_manufacturer,
            manufacturer,
        )

    @staticmethod
    def _to_enrichment_result(
        product: dict[str, Any],
    ) -> ComponentEnrichmentResult:
        """Convert Digi-Key data into our common result."""
        manufacturer_data = product.get(
            "Manufacturer"
        )

        if isinstance(manufacturer_data, dict):
            manufacturer = manufacturer_data.get(
                "Name"
            )
        else:
            manufacturer = manufacturer_data

        mpn = (
            product.get("ManufacturerProductNumber")
            or product.get("ManufacturerPartNumber")
        )

        description = (
            product.get("Description")
            or product.get("DetailedDescription")
        )

        category = product.get("Category")

        if isinstance(category, dict):
            category = (
                category.get("Name")
                or category.get("CategoryName")
            )

        package = (
            product.get("PackageType")
            or product.get("Packaging")
        )

        if isinstance(package, dict):
            package = (
                package.get("Name")
                or package.get("Description")
            )

        datasheet_url = (
            product.get("DatasheetUrl")
            or product.get("DatasheetURL")
        )

        manufacturer_part_url = (
            product.get("ProductUrl")
            or product.get("ProductDetailUrl")
        )

        availability = (
            product.get("QuantityAvailable")
            or product.get("Quantity")
        )

        # --- MODIFIED BLOCK START ---
        lifecycle_status = (
            product.get("ProductStatus")
            or product.get("LifecycleStatus")
        )

        if isinstance(lifecycle_status, dict):
            lifecycle_status = lifecycle_status.get("Status")
        # --- MODIFIED BLOCK END ---

        return ComponentEnrichmentResult(
            manufacturer=normalize_manufacturer(
                manufacturer
            ),
            mpn=normalize_mpn(mpn),
            description=normalize_text(
                description
            ),
            category=normalize_text(
                category
            ),
            package=normalize_text(
                package
            ),
            datasheet_url=normalize_text(
                datasheet_url
            ),
            manufacturer_part_url=normalize_text(
                manufacturer_part_url
            ),
            availability=(
                DigiKeyProvider._parse_quantity(
                    availability
                )
            ),
            lifecycle_status=normalize_text(
                lifecycle_status
            ),
            source="digikey",
        )

    @staticmethod
    def _to_supplier_quote(
        *,
        product: dict[str, Any],
        pricing_data: dict[str, Any],
        quantity: int | None = None,
    ) -> SupplierQuote:
        """Convert Digi-Key product and pricing data."""
        price_breaks = (
            DigiKeyProvider._extract_price_breaks(
                pricing_data
            )
        )

        selected_price_break = None

        if quantity is not None:
            selected_price_break = select_price_break(
                price_breaks,
                quantity,
            )

        if selected_price_break is not None:
            unit_price = selected_price_break.unit_price
            currency = selected_price_break.currency
        elif price_breaks:
            unit_price = price_breaks[0].unit_price
            currency = price_breaks[0].currency
        else:
            unit_price = None
            currency = None

        pricing_product = pricing_data.get("Product")

        if not isinstance(pricing_product, dict):
            pricing_product = {}

        manufacturer_data = product.get(
            "Manufacturer"
        )

        if isinstance(manufacturer_data, dict):
            manufacturer = manufacturer_data.get(
                "Name"
            )
        else:
            manufacturer = manufacturer_data

        mpn = (
            product.get("ManufacturerProductNumber")
            or product.get("ManufacturerPartNumber")
        )

        availability = (
            product.get("QuantityAvailable")
            or product.get("Quantity")
        )

        return SupplierQuote(
            supplier="digikey",
            manufacturer=normalize_manufacturer(
                manufacturer
            ),
            mpn=normalize_mpn(mpn) or "",
            unit_price=unit_price,
            currency=currency,
            quantity_available=(
                DigiKeyProvider._parse_quantity(
                    availability
                )
            ),
            moq=DigiKeyProvider._parse_quantity(
                pricing_product.get(
                    "MinimumOrderQuantity"
                )
            ),
            order_multiple=(
                DigiKeyProvider._parse_quantity(
                    pricing_product.get(
                        "OrderMultiple"
                    )
                )
            ),
            lead_time_days=(
                DigiKeyProvider._parse_quantity(
                    pricing_product.get(
                        "LeadTimeDays"
                    )
                )
            ),
            price_breaks=price_breaks,
            source="digikey",
        )

    @staticmethod
    def _extract_price_breaks(
        data: dict[str, Any],
    ) -> list[PriceBreak]:
        """Extract normalized Digi-Key price breaks."""
        product = data.get("Product")

        if not isinstance(product, dict):
            return []

        raw_breaks = product.get(
            "PriceBreaks"
        ) or []

        if not isinstance(raw_breaks, list):
            return []

        price_breaks: list[PriceBreak] = []

        for item in raw_breaks:
            if not isinstance(item, dict):
                continue

            min_quantity = (
                DigiKeyProvider._parse_quantity(
                    item.get("Quantity")
                )
            )

            unit_price = (
                DigiKeyProvider._parse_float(
                    item.get("UnitPrice")
                )
            )

            currency = normalize_text(
                item.get("Currency")
            )

            if min_quantity is None:
                continue

            if unit_price is None:
                continue

            if currency is None:
                continue

            price_breaks.append(
                PriceBreak(
                    min_quantity=min_quantity,
                    unit_price=unit_price,
                    currency=currency,
                )
            )

        return price_breaks

    @staticmethod
    def _parse_float(
        value: Any,
    ) -> float | None:
        """Normalize a numeric price."""
        if value is None:
            return None

        try:
            parsed = float(
                str(value)
                .replace(",", "")
                .strip()
            )
        except (TypeError, ValueError):
            return None

        if parsed < 0:
            return None

        return parsed

    @staticmethod
    def _parse_quantity(
        value: Any,
    ) -> int | None:
        """Normalize Digi-Key inventory quantity."""
        if value is None:
            return None

        try:
            return int(
                str(value)
                .replace(",", "")
                .strip()
            )
        except (TypeError, ValueError):
            return None