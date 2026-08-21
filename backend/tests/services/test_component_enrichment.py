import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.component import Component
from backend.app.services.component_enrichment import (
    ComponentEnrichmentService,
)

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)


@pytest.mark.asyncio
async def test_backfill_normalized_identity():
    suffix = uuid.uuid4().hex[:8]

    mpn = f"BACKFILL-MPN-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"  {mpn}  ",
            manufacturer=" Texas   Instruments ",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        updated_count = (
            await ComponentEnrichmentService.backfill_normalized_identity(
                session
            )
        )

        await session.commit()

        assert updated_count >= 1

    async with AsyncSessionLocal() as session:
        result = await session.get(
            Component,
            component_id,
        )

        assert result is not None
        assert result.normalized_mpn == mpn
        assert result.normalized_manufacturer == "Texas Instruments"

        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()

@pytest.mark.asyncio
async def test_enrich_component_populates_normalized_fields():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"ENRICH-COMPONENT-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=f"  {mpn}  ",
            manufacturer=" Texas   Instruments ",
            category="  Analog IC  ",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        component = await session.get(
            Component,
            component_id,
        )

        assert component is not None
        assert component.enrichment_status == "PENDING"

        enriched = await ComponentEnrichmentService.enrich_component(
            session,
            component,
        )

        await session.commit()

        assert enriched.normalized_mpn == mpn
        assert enriched.normalized_manufacturer == "Texas Instruments"
        assert enriched.normalized_category == "Analog IC"
        assert enriched.enrichment_status == "ENRICHED"
        assert enriched.enriched_at is not None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()

class MockEnrichmentProvider(ComponentEnrichmentProvider):
    @property
    def name(self) -> str:
        return "mock"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            description="Enriched component",
            category="Analog IC",
            package="SOIC-8",
            datasheet_url="https://example.com/datasheet.pdf",
            manufacturer_part_url="https://example.com/part",
            source=self.name,
        )

@pytest.mark.asyncio
async def test_enrich_component_with_provider():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"PROVIDER-ENRICH-{suffix}"

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        component = await session.get(
            Component,
            component_id,
        )

        assert component is not None
        assert component.enrichment_status == "PENDING"

        enriched = (
            await ComponentEnrichmentService.enrich_with_provider(
                session,
                component,
                MockEnrichmentProvider(),
            )
        )

        await session.commit()

        assert enriched.enrichment_status == "ENRICHED"
        assert enriched.normalized_mpn == mpn
        assert enriched.normalized_manufacturer == "Test Manufacturer"
        assert enriched.description == "Enriched component"
        assert enriched.normalized_category == "Analog IC"
        assert enriched.package == "SOIC-8"
        assert (
            enriched.datasheet_url
            == "https://example.com/datasheet.pdf"
        )
        assert (
            enriched.manufacturer_part_url
            == "https://example.com/part"
        )
        assert enriched.enriched_at is not None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(Component.id == component_id)
        )
        await session.commit()


class NotFoundEnrichmentProvider(
    ComponentEnrichmentProvider,
):
    @property
    def name(self) -> str:
        return "not-found"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return None


class FallbackEnrichmentProvider(
    ComponentEnrichmentProvider,
):
    @property
    def name(self) -> str:
        return "fallback"

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        return ComponentEnrichmentResult(
            mpn=mpn,
            manufacturer=manufacturer,
            description="Fallback enriched component",
            category="Analog IC",
            package="SOIC-8",
            datasheet_url="https://example.com/fallback.pdf",
            manufacturer_part_url="https://example.com/fallback",
            source="fallback",
        )


@pytest.mark.asyncio
async def test_enrich_component_with_orchestrator():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"ORCHESTRATOR-ENRICH-{suffix}"

    orchestrator = EnrichmentOrchestrator(
        [
            NotFoundEnrichmentProvider(),
            FallbackEnrichmentProvider(),
        ]
    )

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="Test Manufacturer",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        component = await session.get(
            Component,
            component_id,
        )

        assert component is not None
        assert component.enrichment_status == "PENDING"

        enriched = (
            await ComponentEnrichmentService
            .enrich_with_orchestrator(
                session,
                component,
                orchestrator,
            )
        )

        await session.commit()

        assert enriched.enrichment_status == "ENRICHED"
        assert enriched.normalized_mpn == mpn
        assert (
            enriched.normalized_manufacturer
            == "Test Manufacturer"
        )
        assert (
            enriched.description
            == "Fallback enriched component"
        )
        assert enriched.normalized_category == "Analog IC"
        assert enriched.package == "SOIC-8"
        assert (
            enriched.datasheet_url
            == "https://example.com/fallback.pdf"
        )
        assert (
            enriched.manufacturer_part_url
            == "https://example.com/fallback"
        )
        assert enriched.enriched_at is not None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_enrich_component_with_orchestrator_not_found():
    suffix = uuid.uuid4().hex[:8]
    mpn = f"ORCHESTRATOR-NOT-FOUND-{suffix}"

    orchestrator = EnrichmentOrchestrator(
        [
            NotFoundEnrichmentProvider(),
            NotFoundEnrichmentProvider(),
        ]
    )

    async with AsyncSessionLocal() as session:
        component = await ComponentRepository.create(
            session,
            mpn=mpn,
            manufacturer="Unknown Manufacturer",
        )

        await session.commit()

        component_id = component.id

    async with AsyncSessionLocal() as session:
        component = await session.get(
            Component,
            component_id,
        )

        assert component is not None

        result = (
            await ComponentEnrichmentService
            .enrich_with_orchestrator(
                session,
                component,
                orchestrator,
            )
        )

        await session.commit()

        assert result.enrichment_status == "NOT_FOUND"
        assert result.enriched_at is None

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(Component).where(
                Component.id == component_id
            )
        )
        await session.commit()