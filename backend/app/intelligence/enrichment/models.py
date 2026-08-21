from dataclasses import dataclass


@dataclass(slots=True)
class ComponentEnrichmentResult:
    """Normalized enrichment data returned by an external provider."""

    manufacturer: str | None = None
    mpn: str | None = None
    description: str | None = None
    category: str | None = None
    package: str | None = None

    datasheet_url: str | None = None
    manufacturer_part_url: str | None = None

    availability: int | None = None
    lifecycle_status: str | None = None

    source: str = "unknown"