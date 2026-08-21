from typing import Any

from pydantic import BaseModel

class ValidationError(BaseModel):
    field: str
    message: str
    severity: str = "error"


def validate_component(
    component: dict[str, Any],
) -> list[ValidationError]:
    """
    Validate a normalized BOM component.

    Returns all validation issues instead of stopping
    at the first error.
    """

    errors: list[ValidationError] = []

    mpn = component.get("mpn")

    if mpn is None or not str(mpn).strip():

        errors.append(
            ValidationError(
                field="mpn",
                message="Manufacturer Part Number is required.",
                severity="error",
            )
        )

    quantity = component.get("quantity")

    if quantity is None:

        errors.append(
            ValidationError(
                field="quantity",
                message="Quantity is required.",
                severity="error",
            )
        )

    elif not isinstance(quantity, int):

        errors.append(
            ValidationError(
                field="quantity",
                message="Quantity must be an integer.",
                severity="error",
            )
        )

    elif quantity < 1:

        errors.append(
            ValidationError(
                field="quantity",
                message="Quantity must be greater than or equal to 1.",
                severity="error",
            )
        )

    manufacturer = component.get("manufacturer")

    if manufacturer is None or not str(manufacturer).strip():

        errors.append(
            ValidationError(
                field="manufacturer",
                message="Manufacturer is missing.",
                severity="warning",
            )
        )

    return errors

def validate_bom_structure(
    columns: list[str],
) -> list[ValidationError]:
    """
    Validate the structural requirements of a BOM.

    Required fields:
        - MPN
        - Quantity

    Optional fields:
        - Manufacturer
        - Description
        - Category
        - Package
        - Reference Designators

    Required fields must have exactly one
    sufficiently confident column match.
    """

    from .detector import (
        detect_columns_with_confidence,
    )

    detections = detect_columns_with_confidence(
        columns
    )

    errors: list[ValidationError] = []

    required_fields = (
        "mpn",
        "quantity",
    )

    for field in required_fields:

        detection = detections[field]

        if detection.column is None:

            if detection.ambiguous:

                candidate_columns = ", ".join(
                    candidate.column
                    for candidate in detection.candidates
                )

                errors.append(
                    ValidationError(
                        field=field,
                        message=(
                            f"Required BOM column "
                            f"'{field}' is ambiguous. "
                            f"Possible columns: "
                            f"{candidate_columns}."
                        ),
                        severity="error",
                    )
                )

            else:

                errors.append(
                    ValidationError(
                        field=field,
                        message=(
                            f"Required BOM column "
                            f"'{field}' could not be detected."
                        ),
                        severity="error",
                    )
                )

            continue

        if detection.ambiguous:

            candidate_columns = ", ".join(
                candidate.column
                for candidate in detection.candidates
            )

            errors.append(
                ValidationError(
                    field=field,
                    message=(
                        f"Required BOM column "
                        f"'{field}' is ambiguous. "
                        f"Possible columns: "
                        f"{candidate_columns}."
                    ),
                    severity="error",
                )
            )

    return errors