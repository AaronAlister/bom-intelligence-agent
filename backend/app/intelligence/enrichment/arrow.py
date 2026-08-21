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


class ArrowProvider(
    ComponentEnrichmentProvider,
    SupplierQuoteProvider,
):
    """Arrow Electronics Pricing & Availability provider."""

    @property
    def name(self) -> str:
        return "arrow"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        """
        Search Arrow for an exact manufacturer part number.

        Arrow's Search By Token endpoint can return prefix matches,
        so the adapter performs exact MPN matching locally.
        """

        if not settings.arrow_api_login:
            raise RuntimeError(
                "Arrow API login is not configured"
            )

        if not settings.arrow_api_key:
            raise RuntimeError(
                "Arrow API key is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Arrow enrichment"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        url = (
            f"{settings.arrow_api_base_url}"
            "/itemservice/v4/en/search/token"
        )

        params = {
            "login": settings.arrow_api_login,
            "apikey": settings.arrow_api_key,
            "search_token": normalized_mpn,
            "rows": 25,
            "fmt": "json",
        }

        async with httpx.AsyncClient(
            timeout=settings.arrow_api_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        self._raise_for_arrow_error(data)

        parts = self._extract_parts(data)

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
        for an Arrow component.
        """

        if not settings.arrow_api_login:
            raise RuntimeError(
                "Arrow API login is not configured"
            )

        if not settings.arrow_api_key:
            raise RuntimeError(
                "Arrow API key is not configured"
            )

        normalized_mpn = normalize_mpn(mpn)

        if normalized_mpn is None:
            raise ValueError(
                "MPN is required for Arrow quote"
            )

        normalized_manufacturer = normalize_manufacturer(
            manufacturer
        )

        url = (
            f"{settings.arrow_api_base_url}"
            "/itemservice/v4/en/search/token"
        )

        params = {
            "login": settings.arrow_api_login,
            "apikey": settings.arrow_api_key,
            "search_token": normalized_mpn,
            "rows": 25,
            "fmt": "json",
        }

        async with httpx.AsyncClient(
            timeout=settings.arrow_api_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params=params,
            )

        response.raise_for_status()

        data = response.json()

        self._raise_for_arrow_error(data)

        parts = self._extract_parts(data)

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
    def _raise_for_arrow_error(
        data: dict[str, Any],
    ) -> None:
        """Validate Arrow's application-level response status."""

        result = data.get("itemserviceresult") or {}

        transaction_area = (
            result.get("transactionArea") or []
        )

        if not transaction_area:
            raise RuntimeError(
                "Arrow API returned an invalid response"
            )

        response = (
            transaction_area[0].get("response") or {}
        )

        success = response.get("success")

        return_code = str(
            response.get("returnCode", "")
        )

        if success is False or (
            return_code
            and return_code != "0"
        ):
            message = response.get(
                "returnMsg",
                "Unknown Arrow API error",
            )

            raise RuntimeError(
                f"Arrow API error "
                f"({return_code}): {message}"
            )

    @staticmethod
    def _extract_parts(
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract PartList from Arrow's nested response."""

        result = data.get("itemserviceresult") or {}

        data_blocks = result.get("data") or []

        parts: list[dict[str, Any]] = []

        for block in data_blocks:
            parts.extend(
                block.get("PartList") or []
            )

        return parts

    @staticmethod
    def _select_matching_part(
        *,
        parts: list[dict[str, Any]],
        mpn: str,
        manufacturer: str | None,
    ) -> dict[str, Any] | None:
        """
        Select an exact MPN and manufacturer match.

        Arrow's search-token endpoint can return multiple
        possible matches, so never accept a prefix match.
        """

        normalized_target_mpn = normalize_mpn(mpn)

        if normalized_target_mpn is None:
            return None

        for part in parts:
            part_mpn = normalize_mpn(
                part.get("partNum")
            )

            if part_mpn != normalized_target_mpn:
                continue

            if manufacturer is None:
                return part

            manufacturer_data = (
                part.get("manufacturer") or {}
            )

            part_manufacturer = normalize_manufacturer(
                manufacturer_data.get("mfrName")
            )

            # Changed to fuzzy manufacturer matching
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
        """Convert Arrow data to our provider-neutral result."""

        manufacturer_data = (
            part.get("manufacturer") or {}
        )

        return ComponentEnrichmentResult(
            manufacturer=normalize_manufacturer(
                manufacturer_data.get("mfrName")
            ),
            mpn=normalize_mpn(
                part.get("partNum")
            ),
            description=normalize_text(
                part.get("desc")
            ),
            package=normalize_text(
                part.get("packageType")
            ),
            datasheet_url=None,
            manufacturer_part_url=(
                ArrowProvider._extract_product_url(part)
            ),
            availability=(
                ArrowProvider._extract_availability(part)
            ),
            lifecycle_status=None,
            source="arrow",
        )

    @staticmethod
    def _to_supplier_quote(
        part: dict[str, Any],
        *,
        quantity: int | None = None,
    ) -> SupplierQuote:
        """Convert Arrow commercial data into SupplierQuote."""

        price_breaks = ArrowProvider._extract_price_breaks(part)

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

        return SupplierQuote(
            supplier="arrow",
            manufacturer=normalize_manufacturer(
                (part.get("manufacturer") or {}).get(
                    "mfrName"
                )
            ),
            mpn=normalize_mpn(
                part.get("partNum")
            )
            or "",
            unit_price=unit_price,
            currency=currency,
            quantity_available=(
                ArrowProvider._extract_availability(part)
            ),
            moq=ArrowProvider._parse_integer(
                part.get("minimumOrderQuantity")
            ),
            order_multiple=ArrowProvider._parse_integer(
                part.get("packSize")
            ),
            lead_time_days=(
                ArrowProvider._extract_lead_time(part)
            ),
            price_breaks=price_breaks,
            source="arrow",
        )

    @staticmethod
    def _extract_price_breaks(
        part: dict[str, Any],
    ) -> list[PriceBreak]:
        """Extract Arrow quantity-based resale pricing."""

        prices = part.get("Prices") or {}

        resale_list = prices.get("resaleList") or []

        if not isinstance(resale_list, list):
            return []

        price_breaks: list[PriceBreak] = []

        for item in resale_list:
            if not isinstance(item, dict):
                continue

            min_quantity = ArrowProvider._parse_integer(
                item.get("minQty")
            )

            unit_price = ArrowProvider._parse_float(
                item.get("price")
            )

            currency = normalize_text(
                item.get("currency")
            )

            max_quantity = ArrowProvider._parse_integer(
                item.get("maxQty")
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
                    max_quantity=max_quantity,
                    unit_price=unit_price,
                    currency=currency,
                )
            )

        return price_breaks

    @staticmethod
    def _extract_product_url(
        part: dict[str, Any],
    ) -> str | None:
        """Extract Arrow's product-detail URL."""

        resources = part.get("resources") or []

        for resource in resources:
            if resource.get("type") in {
                "cloud_part_detail",
                "part_detail",
            }:
                url = normalize_text(
                    resource.get("uri")
                )

                if url:
                    return url

        return None

    @staticmethod
    def _extract_availability(
        part: dict[str, Any],
    ) -> int | None:
        """
        Aggregate free-on-hand inventory across Arrow sources.

        Arrow exposes inventory as:
            InvOrg → sources → sourceParts → Availability → fohQty
        """

        inventory = part.get("InvOrg") or {}
        sources = inventory.get("sources") or []

        total_available = 0

        found_inventory = False

        for source in sources:
            source_parts = (
                source.get("sourceParts") or []
            )

            for source_part in source_parts:
                availability_list = (
                    source_part.get("Availability")
                    or []
                )

                for availability in availability_list:
                    quantity = availability.get(
                        "fohQty"
                    )

                    if quantity is None:
                        continue

                    try:
                        total_available += int(
                            quantity
                        )
                        found_inventory = True
                    except (TypeError, ValueError):
                        continue

        if not found_inventory:
            return None

        return total_available

    @staticmethod
    def _extract_lead_time(
        part: dict[str, Any],
    ) -> int | None:
        """Calculate total Arrow procurement lead time."""

        manufacturer_lead = ArrowProvider._parse_integer(
            part.get("mfrLeadTime")
        )

        arrow_lead = ArrowProvider._parse_integer(
            part.get("arrowLeadTime")
        )

        if manufacturer_lead is None and arrow_lead is None:
            return None

        return (manufacturer_lead or 0) + (arrow_lead or 0)

    @staticmethod
    def _parse_integer(
        value: Any,
    ) -> int | None:
        """Parse a non-negative integer."""

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
    def _parse_float(
        value: Any,
    ) -> float | None:
        """Parse a non-negative floating-point number."""

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