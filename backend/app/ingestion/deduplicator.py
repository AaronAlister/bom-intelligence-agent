from typing import Any


def deduplicate_components(
    components: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge BOM components with the same MPN.

    Quantities are summed and reference designators
    are combined without duplicates.
    """

    grouped: dict[str, dict[str, Any]] = {}

    for component in components:

        mpn = component.get("mpn")

        if not mpn:
            # Invalid components should be handled by
            # validation, not silently merged here.
            continue

        key = str(mpn).strip()

        if key not in grouped:

            grouped[key] = {
                **component,
                "quantity": component.get("quantity") or 0,
                "reference_designators": list(
                    component.get(
                        "reference_designators",
                        []
                    )
                ),
            }

            continue

        existing = grouped[key]

        existing["quantity"] += (
            component.get("quantity") or 0
        )

        existing_references = set(
            existing.get(
                "reference_designators",
                []
            )
        )

        for reference in component.get(
            "reference_designators",
            []
        ):

            if reference not in existing_references:
                existing["reference_designators"].append(
                    reference
                )

                existing_references.add(reference)

        for field in (
            "manufacturer",
            "description",
            "category",
            "package",
        ):

            if (
                not existing.get(field)
                and component.get(field)
            ):
                existing[field] = component[field]

    return list(grouped.values())