import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from backend.app.db.repositories import (ComponentRepository, AlternativeRepository,)
from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.component import Component


@pytest.mark.asyncio
async def test_alternative_api_returns_ranked_candidates():
    suffix = uuid.uuid4().hex[:8]

    source_mpn = f"API-SOURCE-{suffix}"
    alternative_mpn = f"API-ALT-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=source_mpn,
            manufacturer="Texas Instruments",
            category=f"Analog-{suffix}",
            package=f"PKG-{suffix}",
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=alternative_mpn,
            manufacturer="Texas Instruments",
            category=f"Analog-{suffix}",
            package=f"PKG-{suffix}",
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
            response = await client.get(
                f"/api/v1/components/{source_id}/alternatives"
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

        assert candidate["compatibility_score"] == 75.0
        assert candidate["category_match"] is True
        assert candidate["package_match"] is True
        assert candidate["manufacturer_match"] is True

        assert data["best_candidate"] is not None
        assert (
            data["best_candidate"]["component"]["mpn"]
            == alternative_mpn
        )

    finally:
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
async def test_alternative_api_respects_limit():
    suffix = uuid.uuid4().hex[:8]

    category = f"Analog-{suffix}"
    package = f"PKG-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"API-LIMIT-SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        candidate_ids = []

        for index in range(5):
            candidate = await ComponentRepository.create(
                session,
                mpn=f"API-LIMIT-ALT-{suffix}-{index}",
                manufacturer="Texas Instruments",
                category=category,
                package=package,
            )

            candidate_ids.append(candidate.id)

        await session.commit()

        source_id = source.id

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/api/v1/components/{source_id}/alternatives",
                params={"limit": 2},
            )

        assert response.status_code == 200

        data = response.json()

        assert len(data["candidates"]) == 2
        assert data["best_candidate"] is not None

    finally:
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
async def test_alternative_api_missing_component():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/components/999999/alternatives"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Component 999999 not found."
    )


@pytest.mark.asyncio
async def test_alternative_api_invalid_limit():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/components/1/alternatives",
            params={"limit": 0},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_alternative_analyze_api_missing_component():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/components/999999/alternatives/analyze"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Component 999999 not found."
    )


@pytest.mark.asyncio
async def test_alternative_analyze_api_persists_results():
    suffix = uuid.uuid4().hex[:8]

    category = f"Persist-{suffix}"
    package = f"PKG-{suffix}"

    async with AsyncSessionLocal() as session:
        source = await ComponentRepository.create(
            session,
            mpn=f"API-PERSIST-SOURCE-{suffix}",
            manufacturer="Texas Instruments",
            category=category,
            package=package,
        )

        alternative = await ComponentRepository.create(
            session,
            mpn=f"API-PERSIST-ALT-{suffix}",
            manufacturer="Texas Instruments",
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

        assert data["source_mpn"] == (
            f"API-PERSIST-SOURCE-{suffix}"
        )

        assert len(data["candidates"]) == 1

        assert data["best_candidate"] is not None

        assert (
            data["best_candidate"]["component"]["mpn"]
            == f"API-PERSIST-ALT-{suffix}"
        )

        assert data["persisted_count"] == 1

        async with AsyncSessionLocal() as session:
            history = await AlternativeRepository.list_for_source_component(
                session,
                source_id,
            )

            assert len(history) == 1

            assert (
                history[0].alternative_component_id
                == alternative_id
            )

    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(Component).where(
                    Component.id.in_(
                        [source_id, alternative_id]
                    )
                )
            )

            await session.commit()