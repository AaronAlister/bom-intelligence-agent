import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from backend.app.db.repositories import ComponentRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.alternative import AlternativeRecord
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_alternative_analysis_api_persists_record():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"API-PERSIST-SOURCE-{suffix}"
    alternative_mpn = f"API-PERSIST-ALT-{suffix}"

    category = f"API-Analog-{suffix}"
    package = f"API-PKG-{suffix}"

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

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                f"/api/v1/components/"
                f"{source_id}/alternatives/analyze"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["source_mpn"] == source_mpn

        assert len(data["candidates"]) == 1

        candidate = data["candidates"][0]

        assert (
            candidate["component"]["mpn"]
            == alternative_mpn
        )

        assert (
            candidate["compatibility_score"]
            == 65.0
        )

        assert candidate["category_match"] is True
        assert candidate["package_match"] is True
        assert candidate["manufacturer_match"] is False

        assert (
            data["best_candidate"]["component"]["mpn"]
            == alternative_mpn
        )

        assert data["persisted_count"] == 1

    finally:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AlternativeRecord).where(
                    AlternativeRecord.source_component_id
                    == source_id
                )
            )

            records = list(result.scalars().all())

            assert len(records) == 1

            record = records[0]

            assert (
                record.source_component_id
                == source_id
            )

            assert (
                record.alternative_component_id
                == alternative_id
            )

            assert (
                record.compatibility_score
                == 65.0
            )

            await session.execute(
                delete(Component).where(
                    Component.id.in_(
                        [source_id, alternative_id]
                    )
                )
            )

            await session.commit()