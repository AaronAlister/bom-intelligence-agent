from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .deduplicator import deduplicate_components
from .detector import detect_columns
from .metadata import extract_metadata
from .normalizer import normalize_component
from .parsers import get_parser
from .schemas import (
    BOMComponent,
    BOMMetadata,
    IngestionResult,
    ValidationIssue,
)
from .validator import (
    validate_bom_structure,
    validate_component,
)


def ingest_bom(
    file_path: Path,
    product: str | None = None,
    revision: str | None = None,
) -> IngestionResult:
    """
    Execute the complete BOM ingestion pipeline.

    Pipeline:
        Parse
        -> Detect
        -> Extract Metadata
        -> Normalize
        -> Validate
        -> Deduplicate
    """

    extension = file_path.suffix.lower()

    parser = get_parser(extension)

    raw_records = parser.parse(
        file_path
    )

    # Generate the BOM ID once so that the same ID is used
    # by both IngestionResult and BOMMetadata.
    bom_id = str(uuid4())

    # Extract metadata using:
    # 1. Explicit API values
    # 2. Structured file metadata
    # 3. Filename inference
    # 4. None
    detected_product, detected_revision = (
        extract_metadata(
            file_path=file_path,
            records=raw_records,
            product=product,
            revision=revision,
        )
    )

    metadata = BOMMetadata(
        bom_id=bom_id,
        product=detected_product,
        revision=detected_revision,
        source_file=file_path.name,
        source_format=extension.lstrip("."),
        ingested_at=datetime.now(timezone.utc),
    )

    # Handle empty BOM files.
    if not raw_records:
        return IngestionResult(
            bom_id=bom_id,
            source_file=file_path.name,
            source_format=extension.lstrip("."),
            metadata=metadata,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            components=[],
            validation_issues=[],
        )

    columns = list(
        raw_records[0].keys()
    )

    column_mapping = detect_columns(
        columns
    )

    validation_issues: list[ValidationIssue] = []

    structure_errors = validate_bom_structure(
        columns
    )

    if structure_errors:

        for error in structure_errors:

            validation_issues.append(
                ValidationIssue(
                    row_number=0,
                    field=error.field,
                    message=error.message,
                    severity=error.severity,
                )
            )

        return IngestionResult(
            bom_id=bom_id,
            source_file=file_path.name,
            source_format=extension.lstrip("."),
            metadata=metadata,
            total_rows=len(raw_records),
            valid_rows=0,
            invalid_rows=len(raw_records),
            components=[],
            validation_issues=validation_issues,
        )

    normalized_components: list[dict[str, Any]] = []

    for row_number, raw_record in enumerate(
        raw_records,
        start=2,
    ):

        component = normalize_component(
            raw_record,
            column_mapping,
        )

        errors = validate_component(
            component
        )

        for error in errors:

            validation_issues.append(
                ValidationIssue(
                    row_number=row_number,
                    field=error.field,
                    message=error.message,
                    severity=error.severity,
                )
            )

        has_errors = any(
            error.severity == "error"
            for error in errors
        )

        if not has_errors:
            normalized_components.append(
                component
            )

    deduplicated_components = (
        deduplicate_components(
            normalized_components
        )
    )

    canonical_components = [
        BOMComponent.model_validate(
            component
        )
        for component in deduplicated_components
    ]

    total_rows = len(
        raw_records
    )

    invalid_row_numbers = {
        issue.row_number
        for issue in validation_issues
        if issue.severity == "error"
    }

    invalid_rows = len(
        invalid_row_numbers
    )

    valid_rows = (
        total_rows - invalid_rows
    )

    return IngestionResult(
        bom_id=bom_id,
        source_file=file_path.name,
        source_format=extension.lstrip("."),
        metadata=metadata,
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        components=canonical_components,
        validation_issues=validation_issues,
    )