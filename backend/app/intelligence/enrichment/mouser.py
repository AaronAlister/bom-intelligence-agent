import re
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


class MouserProvider(
    ComponentEnrichmentProvider,
    SupplierQuoteProvider,
):
    """Mouser Search API enrichment provider."""

    @property
    def name(self) -> str:
        return "mouser"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        """
        Search Mouser for a manufacturer part number.

        Returns:
            Normalized enrichment result when a matching part
            is found, otherwise None.
        """

        if not settings.mouser_api_key:
            raise RuntimeError(
                "Mouser API key is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Mouser enrichment"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        url = (
            f"{settings.mouser_api_base_url}"
            "/search/partnumber"
        )

        params = {
            "apiKey": settings.mouser_api_key,
        }

        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": normalized_mpn,
                "partSearchOptions": "Exact",
            }
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=settings.mouser_api_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params=params,
                json=payload,
                headers=headers,
            )

        response.raise_for_status()

        data = response.json()

        errors = data.get("Errors") or []

        if errors:
            raise RuntimeError(
                f"Mouser API returned errors: {errors}"
            )

        search_results = data.get("SearchResults")

        if not search_results:
            return None

        parts = search_results.get("Parts") or []

        if not parts:
            return None

        part = self._select_matching_part(
            parts=parts,
            mpn=normalized_mpn,
            manufacturer=normalized_manufacturer,
        )

        if part is None:
            return None

        return self._to_enrichment_result(part)

    async def quote(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
        quantity: int | None = None,
    ) -> SupplierQuote | None:
        """
        Retrieve normalized commercial information
        for a Mouser component.

        The same Mouser Search API response used for
        component enrichment also contains commercial
        procurement information.
        """

        if not settings.mouser_api_key:
            raise RuntimeError(
                "Mouser API key is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Mouser quote"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        url = (
            f"{settings.mouser_api_base_url}"
            "/search/partnumber"
        )

        params = {
            "apiKey": settings.mouser_api_key,
        }

        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": normalized_mpn,
                "partSearchOptions": "Exact",
            }
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=settings.mouser_api_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params=params,
                json=payload,
                headers=headers,
            )

        response.raise_for_status()

        data = response.json()

        errors = data.get("Errors") or []

        if errors:
            raise RuntimeError(
                f"Mouser API returned errors: {errors}"
            )

        search_results = data.get("SearchResults")

        if not search_results:
            return None

        parts = search_results.get("Parts") or []

        if not parts:
            return None

        part = self._select_matching_part(
            parts=parts,
            mpn=normalized_mpn,
            manufacturer=normalized_manufacturer,
        )

        if part is None:
            return None

        return self._to_supplier_quote(
            part,
            quantity=quantity,
        )

    @staticmethod
    def _select_matching_part(
        *,
        parts: list[dict[str, Any]],
        mpn: str,
        manufacturer: str | None,
    ) -> dict[str, Any] | None:
        """Select the best exact MPN match from Mouser results."""

        normalized_target_mpn = normalize_mpn(mpn)

        if normalized_target_mpn is None:
            return None

        for part in parts:
            part_mpn = normalize_mpn(
                part.get("ManufacturerPartNumber")
            )

            if part_mpn != normalized_target_mpn:
                continue

            if manufacturer is None:
                return part

            part_manufacturer = normalize_manufacturer(
                part.get("Manufacturer")
            )

            # Use the new matching function
            if manufacturers_match(
                part_manufacturer,
                manufacturer,
            ):
                return part

        return None

    @staticmethod
    def _to_enrichment_result(
        part: dict[str, Any],
    ) -> ComponentEnrichmentResult:
        """Convert Mouser response data to our internal model."""

        availability = MouserProvider._parse_availability(
            part.get("AvailabilityInStock")
        )

        return ComponentEnrichmentResult(
            manufacturer=normalize_manufacturer(
                part.get("Manufacturer")
            ),
            mpn=normalize_mpn(
                part.get("ManufacturerPartNumber")
            ),
            description=normalize_text(
                part.get("Description")
            ),
            category=normalize_text(
                part.get("Category")
            ),
            package=normalize_text(
                part.get("Packaging")
            ),
            datasheet_url=normalize_text(
                part.get("DataSheetUrl")
            ),
            manufacturer_part_url=normalize_text(
                part.get("ProductDetailUrl")
            ),
            availability=availability,
            lifecycle_status=normalize_text(
                part.get("LifecycleStatus")
            ),
            source="mouser",
        )

    @staticmethod
    def _to_supplier_quote(
        part: dict[str, Any],
        *,
        quantity: int | None = None,
    ) -> SupplierQuote:
        """Convert Mouser commercial data into SupplierQuote."""

        price_breaks = (
            MouserProvider._parse_price_breaks(
                part.get("PriceBreaks")
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
            unit_price = MouserProvider._parse_price(
                part.get("Price")
            )
            currency = MouserProvider._parse_currency(
                part.get("Price")
            )

        return SupplierQuote(
            supplier="mouser",
            manufacturer=normalize_manufacturer(
                part.get("Manufacturer")
            ),
            mpn=normalize_mpn(
                part.get("ManufacturerPartNumber")
            )
            or "",
            unit_price=unit_price,
            currency=currency,
            quantity_available=(
                MouserProvider._parse_availability(
                    part.get("AvailabilityInStock")
                )
            ),
            moq=MouserProvider._parse_integer(
                part.get("Min")
            ),
            order_multiple=MouserProvider._parse_integer(
                part.get("Mult")
            ),
            lead_time_days=MouserProvider._parse_lead_time(
                part.get("LeadTime")
            ),
            price_breaks=price_breaks,
            source="mouser",
        )

    @staticmethod
    def _parse_price_breaks(
        value: Any,
    ) -> list[PriceBreak]:
        """Normalize Mouser quantity-based pricing."""

        if not isinstance(value, list):
            return []

        price_breaks: list[PriceBreak] = []

        for item in value:
            if not isinstance(item, dict):
                continue

            quantity = MouserProvider._parse_integer(
                item.get("Quantity")
            )

            price = MouserProvider._parse_price(
                item.get("Price")
            )

            currency = MouserProvider._parse_currency(
                item.get("Currency")
            )

            if quantity is None:
                continue

            if price is None:
                continue

            if currency is None:
                continue

            price_breaks.append(
                PriceBreak(
                    min_quantity=quantity,
                    unit_price=price,
                    currency=currency,
                )
            )

        return price_breaks

    @staticmethod
    def _parse_integer(
        value: Any,
    ) -> int | None:
        """Parse a positive integer from API data."""

        if value is None:
            return None

        try:
            parsed = int(
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
    def _parse_price(
        value: Any,
    ) -> float | None:
        """Parse a numeric unit price."""

        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()

        if not text:
            return None

        match = re.search(
            r"\d+(?:\.\d+)?",
            text.replace(",", ""),
        )

        if match is None:
            return None

        try:
            return float(match.group())
        except ValueError:
            return None

    @staticmethod
    def _parse_currency(
        value: Any,
    ) -> str | None:
        """Extract a three-letter currency code."""

        if value is None:
            return None

        text = str(value).strip()

        match = re.search(
            r"\b([A-Z]{3})\b",
            text.upper(),
        )

        if match is None:
            return None

        return match.group(1)

    @staticmethod
    def _parse_lead_time(
        value: Any,
    ) -> int | None:
        """
        Convert Mouser lead-time text into days.

        Examples:
            "7 Days"   -> 7
            "2 Weeks"  -> 14
            "1 Week"   -> 7
        """

        if value is None:
            return None

        text = str(value).strip().lower()

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*"
            r"(day|days|week|weeks)",
            text,
        )

        if match is None:
            return None

        amount = float(match.group(1))
        unit = match.group(2)

        if unit.startswith("week"):
            amount *= 7

        return int(amount)

    @staticmethod
    def _parse_availability(
        value: Any,
    ) -> int | None:
        """Convert Mouser's stock value to an integer."""

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