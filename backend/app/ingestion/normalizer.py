import re
from typing import Any, Optional


def normalize_text(value: Any) -> Optional[str]:
    """
    Normalize a text value.

    Converts blank values to None and removes
    unnecessary leading/trailing whitespace.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def normalize_mpn(value: Any) -> Optional[str]:
    """
    Normalize a Manufacturer Part Number.

    MPNs are kept case-sensitive because some manufacturers
    distinguish part variants using case.
    """

    value = normalize_text(value)

    if value is None:
        return None

    return value


def normalize_manufacturer(value: Any) -> Optional[str]:
    """
    Normalize manufacturer name whitespace.
    """

    value = normalize_text(value)

    if value is None:
        return None

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def normalize_manufacturer_for_matching(
    value: Any,
) -> Optional[str]:
    """
    Normalize a manufacturer name for external-provider matching.

    This is intentionally separate from normalize_manufacturer()
    because provider APIs may include legal suffixes or minor
    naming variations that should not affect identity matching.

    Examples:
        "Microchip Technology"
            -> "microchip technology"

        "Microchip Technology Inc."
            -> "microchip technology"

        "Texas Instruments, Inc."
            -> "texas instruments"
    """

    value = normalize_manufacturer(value)

    if value is None:
        return None

    normalized = value.lower()

    normalized = re.sub(
        r"[.,]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\b(incorporated|inc|corp|corporation|"
        r"co|company|ltd|limited|llc|plc)\b",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    return normalized


def manufacturers_match(
    left: Any,
    right: Any,
) -> bool:
    """
    Determine whether two manufacturer names represent
    the same manufacturer for external-provider matching.

    Matching is case-insensitive and ignores common
    corporate suffixes.
    """

    normalized_left = normalize_manufacturer_for_matching(
        left
    )

    normalized_right = normalize_manufacturer_for_matching(
        right
    )

    if normalized_left is None or normalized_right is None:
        return normalized_left == normalized_right

    return normalized_left == normalized_right


def normalize_quantity(value: Any) -> Optional[int]:
    """
    Convert common quantity representations into integers.

    Examples:
        "4"      -> 4
        "4.0"    -> 4
        4        -> 4
        4.0      -> 4
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        numeric_value = float(str(value).strip())

    except (TypeError, ValueError):
        return None

    if not numeric_value.is_integer():
        return None

    return int(numeric_value)


def normalize_reference_designators(
    value: Any,
) -> list[str]:
    """
    Convert reference designators into a normalized list.

    Supports common separators such as:
        U1,U2,U3
        U1;U2;U3
        U1 U2 U3
        U1, U2; U3
    """

    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    parts = re.split(
        r"[,;|\n]+",
        text,
    )

    normalized = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        normalized.append(part)

    return normalized


def normalize_component(
    raw_record: dict[str, Any],
    column_mapping: dict[str, Optional[str]],
) -> dict[str, Any]:
    """
    Convert a raw BOM record into the canonical component
    field representation.

    `column_mapping` maps canonical field names to the
    original source column names.
    """

    def get_value(field: str) -> Any:
        source_column = column_mapping.get(field)

        if source_column is None:
            return None

        return raw_record.get(source_column)

    return {
        "mpn": normalize_mpn(
            get_value("mpn")
        ),

        "manufacturer": normalize_manufacturer(
            get_value("manufacturer")
        ),

        "description": normalize_text(
            get_value("description")
        ),

        "category": normalize_text(
            get_value("category")
        ),

        "package": normalize_text(
            get_value("package")
        ),

        "quantity": normalize_quantity(
            get_value("quantity")
        ),

        "reference_designators":
            normalize_reference_designators(
                get_value("reference_designators")
            ),
    }