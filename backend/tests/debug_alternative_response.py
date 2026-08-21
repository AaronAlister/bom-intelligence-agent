import uuid

import pytest

from backend.app.api.component_schemas import (
    AlternativeCandidateResponse,
    AlternativeComponentResponse,
    AlternativeResponse,
)
from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.services.alternative_component import (
    AlternativeComponentService,
)


@pytest.mark.asyncio
async def test_debug_fastapi_response_model() -> None:
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"DEBUG-SOURCE-{suffix}"
    alternative_mpn = f"DEBUG-ALTERNATIVE-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="STMicroelectronics",
            description=(
                "ARM Microcontrollers - MCU "
                "ARM M4 1024 FLASH 168 Mhz 192kB SRAM"
            ),
            category="ARM Microcontrollers - MCU",
            package="LQFP-100",
        )

        await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="STMicroelectronics",
            description="ARM Cortex-M4 microcontroller",
            category="MCU",
            package="LQFP-48",
        )

        await session.commit()

        source_id = source.id

    source_enrichment = ComponentEnrichmentResult(
        mpn=source_mpn,
        manufacturer="STMicroelectronics",
        description=(
            "ARM Microcontrollers - MCU "
            "ARM M4 1024 FLASH 168 Mhz 192kB SRAM"
        ),
        category="ARM Microcontrollers - MCU",
        package="LQFP-100",
        lifecycle_status="ACTIVE",
        availability=5000,
        source="test",
    )

    async with AsyncSessionLocal() as session:
        analysis = (
            await AlternativeComponentService.find_alternatives(
                session,
                component_id=source_id,
                source_enrichment=source_enrichment,
                limit=10,
            )
        )

    assert analysis.candidates

    candidate = analysis.candidates[0]

    component_response = AlternativeComponentResponse(
        mpn=candidate.component.mpn or "",
        manufacturer=candidate.component.manufacturer,
        description=candidate.component.description,
        category=candidate.component.category,
        package=candidate.component.package,
    )

    candidate_response = AlternativeCandidateResponse(
        component=component_response,
        compatibility_score=candidate.compatibility_score,
        compatibility_status=candidate.compatibility_status,
        category_match=candidate.category_match,
        package_match=candidate.package_match,
        manufacturer_match=candidate.manufacturer_match,
        lifecycle_score=candidate.lifecycle_score,
        availability_score=candidate.availability_score,
        reasons=candidate.reasons,
    )

    response = AlternativeResponse(
        source_mpn=analysis.source_mpn,
        candidates=[candidate_response],
        best_candidate=candidate_response,
    )

    model_dump = response.model_dump()
    model_json = response.model_dump_json()

    print("\n=== MODEL DUMP ===")
    print(model_dump)

    print("\n=== MODEL JSON ===")
    print(model_json)

    assert (
        "ARM Cortex-M4 microcontroller"
        in model_json
    )

    assert (
        "Component belongs to the same category family as the source."
        in model_json
    )

    assert (
        "Candidate has no reported distributor availability."
        in model_json
    )