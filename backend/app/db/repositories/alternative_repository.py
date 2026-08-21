import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.alternative import AlternativeRecord


class AlternativeRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        record_id: int,
    ) -> AlternativeRecord | None:
        result = await session.execute(
            select(AlternativeRecord).where(
                AlternativeRecord.id == record_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_source_component(
        session: AsyncSession,
        source_component_id: int,
    ) -> list[AlternativeRecord]:
        result = await session.execute(
            select(AlternativeRecord)
            .where(
                AlternativeRecord.source_component_id
                == source_component_id
            )
            .order_by(
                AlternativeRecord.id
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        source_component_id: int,
        alternative_component_id: int,
        compatibility_score: float,
        category_match: bool,
        package_match: bool,
        manufacturer_match: bool,
        lifecycle_score: float,
        availability_score: float,
        reasons: list[str] | None = None,
    ) -> AlternativeRecord:

        reasons_json = (
            json.dumps(reasons)
            if reasons is not None
            else None
        )

        record = AlternativeRecord(
            source_component_id=source_component_id,
            alternative_component_id=alternative_component_id,
            compatibility_score=compatibility_score,
            category_match=category_match,
            package_match=package_match,
            manufacturer_match=manufacturer_match,
            lifecycle_score=lifecycle_score,
            availability_score=availability_score,
            reasons=reasons_json,
        )

        session.add(record)
        await session.flush()

        return record