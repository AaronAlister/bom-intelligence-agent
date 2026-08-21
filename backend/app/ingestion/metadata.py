import re
from pathlib import Path
from typing import Any


PRODUCT_KEYS = {
    "product",
    "product_name",
    "product_name",
    "board_name",
    "assembly",
    "project",
}

REVISION_KEYS = {
    "revision",
    "rev",
    "revision_number",
    "version",
    "bom_revision",
}


def _normalize_key(value: str) -> str:
    """
    Normalize a metadata key for comparison.
    """

    return re.sub(
        r"[^a-z0-9]",
        "",
        value.lower(),
    )


def _find_metadata_value(
    records: list[dict[str, Any]],
    keys: set[str],
) -> str | None:
    """
    Search component records for a metadata value.

    This supports files where metadata is represented
    as ordinary columns.
    """

    normalized_keys = {
        _normalize_key(key)
        for key in keys
    }

    for record in records:

        for key, value in record.items():

            if _normalize_key(str(key)) not in normalized_keys:
                continue

            if value is None:
                continue

            value_str = str(value).strip()

            if value_str:
                return value_str

    return None


def infer_from_filename(
    file_path: Path,
) -> tuple[str | None, str | None]:
    """
    Infer product and revision from a BOM filename.

    Examples:

        power_control_board_RevA.xlsx
        main_controller_rev_2.xlsx
        motor_driver_v3.xlsx
    """

    filename = file_path.stem

    revision: str | None = None
    product: str | None = None

    revision_patterns = [
        r"(?i)(?:^|[_\-\s])rev(?:ision)?[_\-\s]*([A-Za-z0-9.]+)",
        r"(?i)(?:^|[_\-\s])v(?:ersion)?[_\-\s]*([0-9]+(?:\.[0-9]+)*)",
    ]

    for pattern in revision_patterns:

        match = re.search(
            pattern,
            filename,
        )

        if match:
            revision = match.group(1)
            break

    product_name = filename

    if revision is not None:

        product_name = re.sub(
            revision_patterns[0],
            "",
            product_name,
        )

        product_name = re.sub(
            revision_patterns[1],
            "",
            product_name,
        )

    product_name = re.sub(
        r"[_\-]+",
        " ",
        product_name,
    )

    product_name = re.sub(
        r"\s+",
        " ",
        product_name,
    ).strip()

    if product_name:
        product = product_name

    return product, revision


def extract_metadata(
    file_path: Path,
    records: list[dict[str, Any]],
    product: str | None = None,
    revision: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Extract BOM metadata using the following priority:

        1. Explicit API metadata
        2. Structured metadata in records
        3. Filename inference
        4. None
    """

    detected_product = _find_metadata_value(
        records,
        PRODUCT_KEYS,
    )

    detected_revision = _find_metadata_value(
        records,
        REVISION_KEYS,
    )

    filename_product, filename_revision = (
        infer_from_filename(file_path)
    )

    final_product = (
        product
        or detected_product
        or filename_product
    )

    final_revision = (
        revision
        or detected_revision
        or filename_revision
    )

    return (
        final_product,
        final_revision,
    )