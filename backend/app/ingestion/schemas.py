from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BOMComponent(BaseModel):
    """
    Normalized representation of a single BOM component.
    """

    mpn: str = Field(
        ...,
        description="Manufacturer Part Number",
    )

    manufacturer: Optional[str] = None

    description: Optional[str] = None

    category: Optional[str] = None

    package: Optional[str] = None

    quantity: int = Field(
        default=1,
        ge=1,
    )

    reference_designators: list[str] = Field(
        default_factory=list,
    )


class BOMMetadata(BaseModel):
    """
    Metadata describing the uploaded BOM.
    """

    bom_id: str

    # Internal database identifier, populated after persistence
    bom_database_id: int | None = None

    product: Optional[str] = None

    revision: Optional[str] = None

    source_file: str

    source_format: str

    ingested_at: datetime


class ValidationIssue(BaseModel):
    """
    Validation issue associated with an input BOM row.
    """

    row_number: int

    field: str

    message: str

    severity: str


class IngestionResult(BaseModel):
    """
    Complete result produced by the BOM ingestion pipeline.
    """

    bom_id: str

    # Internal database identifier, populated after persistence
    bom_database_id: int | None = None

    source_file: str

    source_format: str

    metadata: BOMMetadata

    total_rows: int

    valid_rows: int

    invalid_rows: int

    components: list[BOMComponent]

    validation_issues: list[ValidationIssue] = Field(
        default_factory=list,
    )


class CanonicalBOM(BaseModel):
    """
    Canonical representation produced by the
    BOM ingestion pipeline.
    """

    metadata: BOMMetadata

    components: list[BOMComponent]

    component_count: int = 0