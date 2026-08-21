import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.models.component import Component
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)


@pytest.mark.asyncio
async def test_finds_compatible_alternatives():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"SOURCE-{suffix}"
    alternative_mpn = f"ALTERNATIVE-{suffix}"

    category = f"Analog-{suffix}"
    package = f"PKG-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            category=category,
            package=package,
        )

        await session.commit()

        source_id = source.id
        alternative_id = alternative.id

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=category,
        package=package,
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        result = await AlternativeComponentService.find_alternatives(
            session,
            component_id=source_id,
            source_enrichment=source_enrichment,
        )

        assert result.source_mpn == source_mpn
        assert len(result.candidates) == 1

        assert (
            result.candidates[0].component.mpn
            == alternative_mpn
        )

        assert result.best_candidate is not None

        assert (
            result.best_candidate.component.mpn
            == alternative_mpn
        )

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [source_id, alternative_id]
                )
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_excludes_incompatible_components():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"SOURCE-{suffix}"
    wrong_category_mpn = f"WRONG-CATEGORY-{suffix}"
    wrong_package_mpn = f"WRONG-PACKAGE-{suffix}"

    category = f"Analog-{suffix}"
    package = f"PKG-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        wrong_category = await ComponentRepository.create(
            session,
            mpn=wrong_category_mpn,
            manufacturer="Texas Instruments",
            category=f"MCU-{suffix}",
            package=package,
        )

        wrong_package = await ComponentRepository.create(
            session,
            mpn=wrong_package_mpn,
            manufacturer="Texas Instruments",
            category=category,
            package=f"QFN-{suffix}",
        )

        await session.commit()

        source_id = source.id
        wrong_category_id = wrong_category.id
        wrong_package_id = wrong_package.id

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="Texas Instruments",
        category=category,
        package=package,
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        result = await AlternativeComponentService.find_alternatives(
            session,
            component_id=source_id,
            source_enrichment=source_enrichment,
        )

        assert result.candidates == []
        assert result.best_candidate is None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [
                        source_id,
                        wrong_category_id,
                        wrong_package_id,
                    ]
                )
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_limit_is_respected():
    suffix = uuid.uuid4().hex[:8]

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category="Analog IC",
            package="SOIC-8",
        )

        candidate_ids = []

        for index in range(5):
            candidate = await ComponentRepository.create(
                session,
                mpn=f"ALT-{suffix}-{index}",
                manufacturer="Texas Instruments",
                category="Analog IC",
                package="SOIC-8",
            )

            candidate_ids.append(candidate.id)

        await session.commit()

        source_id = source.id

    source_enrichment = ComponentEnrichmentResult(
        mpn=f"SOURCE-{suffix}",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        result = await AlternativeComponentService.find_alternatives(
            session,
            component_id=source_id,
            source_enrichment=source_enrichment,
            limit=2,
        )

        assert len(result.candidates) == 2

        assert result.best_candidate is not None

        assert (
            result.best_candidate
            == result.candidates[0]
        )

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id.in_(
                    [source_id, *candidate_ids]
                )
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_missing_component_raises_error():
    source_enrichment = ComponentEnrichmentResult(
        mpn="MISSING",
        manufacturer="Texas Instruments",
        category="Analog IC",
        package="SOIC-8",
        lifecycle_status="ACTIVE",
        availability=1000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        with pytest.raises(
            ValueError,
            match="Component 999999 not found",
        ):
            await AlternativeComponentService.find_alternatives(
                session,
                component_id=999999,
                source_enrichment=source_enrichment,
            )


@pytest.mark.asyncio
async def test_finds_review_alternative_with_different_package():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"STM32-SOURCE-{suffix}"
    alternative_mpn = f"STM32-ALTERNATIVE-{suffix}"

    source_id: int | None = None
    alternative_id: int | None = None

    try:
        async with AsyncSessionLocal() as session:
            source = await ComponentRepository.create(
                session,
                mpn=source_mpn,
                manufacturer="STMicroelectronics",
                category="ARM Microcontrollers - MCU",
                package="LQFP-100",
            )

            alternative = await ComponentRepository.create(
                session,
                mpn=alternative_mpn,
                manufacturer="STMicroelectronics",
                category="MCU",
                package="LQFP-48",
            )

            await session.commit()

            source_id = source.id
            alternative_id = alternative.id

        source_enrichment = ComponentEnrichmentResult(
            mpn=source_mpn,
            manufacturer="STMicroelectronics",
            category="ARM Microcontrollers - MCU",
            package="LQFP-100",
            lifecycle_status="ACTIVE",
            availability=5000,
            source="test",
        )

        async with AsyncSessionLocal() as session:
            result = (
                await AlternativeComponentService.find_alternatives(
                    session,
                    component_id=source_id,
                    source_enrichment=source_enrichment,
                )
            )

            assert len(result.candidates) == 1

            candidate = result.candidates[0]

            assert candidate.component.mpn == alternative_mpn
            assert candidate.category_match is False
            assert candidate.package_match is False
            assert candidate.manufacturer_match is True
            assert candidate.compatibility_status == "REVIEW"

            assert any(
                "Engineering review" in reason
                for reason in candidate.reasons
            )

    finally:
        if (
            source_id is not None
            and alternative_id is not None
        ):
            async with AsyncSessionLocal() as session:
                await session.execute(
                    delete(Component).where(
                        Component.id.in_(
                            [source_id, alternative_id]
                        )
                    )
                )
                await session.commit()