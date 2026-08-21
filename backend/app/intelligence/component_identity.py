from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.component_repository import (
    ComponentRepository,
)
from backend.app.models.component import Component
from backend.app.ingestion.normalizer import (
    normalize_mpn,
    normalize_manufacturer,
)



def normalize_component_identity(
    *,
    mpn: Any,
    manufacturer: Any,
) -> dict[str, str | None]:
    """
    Normalize the identity fields used to resolve a component.

    Uses the existing Phase 2 normalization rules so that
    component identity remains consistent across the system.
    """

    return {
        "normalized_mpn": normalize_mpn(mpn),
        "normalized_manufacturer": normalize_manufacturer(
            manufacturer
        ),
    }


def component_identity_key(
    *,
    mpn: Any,
    manufacturer: Any,
) -> tuple[str | None, str | None]:
    """
    Build a deterministic identity key for a component.
    """

    identity = normalize_component_identity(
        mpn=mpn,
        manufacturer=manufacturer,
    )

    return (
        identity["normalized_mpn"],
        identity["normalized_manufacturer"],
    )


class ComponentIdentityResolver:
    """Resolve incoming component data to an existing or new Component."""

    @staticmethod
    async def resolve(
        session: AsyncSession,
        *,
        mpn: Any,
        manufacturer: Any = None,
        description: Any = None,
        category: Any = None,
        package: Any = None,
    ) -> Component:
        identity = normalize_component_identity(
            mpn=mpn,
            manufacturer=manufacturer,
        )

        normalized_mpn = identity["normalized_mpn"]

        if normalized_mpn is None:
            raise ValueError("MPN is required for component identity resolution")

        existing = await ComponentRepository.get_by_normalized_mpn(
            session,
            normalized_mpn,
        )

        if existing is not None:
            return existing

        component = await ComponentRepository.create(
            session,
            mpn=normalized_mpn,
            manufacturer=identity["normalized_manufacturer"],
            description=description,
            category=category,
            package=package,
        )

        component.normalized_mpn = normalized_mpn
        component.normalized_manufacturer = identity[
            "normalized_manufacturer"
        ]

        return component