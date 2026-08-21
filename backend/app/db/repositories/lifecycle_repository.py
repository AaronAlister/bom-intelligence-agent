from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lifecycle import LifecycleRecord


class LifecycleRepository:
    """Database operations for component lifecycle records."""

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        lifecycle_id: int,
    ) -> LifecycleRecord | None:
        result = await session.execute(
            select(LifecycleRecord).where(
                LifecycleRecord.id == lifecycle_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_component(
        session: AsyncSession,
        component_id: int,
    ) -> list[LifecycleRecord]:
        result = await session.execute(
            select(LifecycleRecord)
            .where(
                LifecycleRecord.component_id == component_id
            )
            .order_by(LifecycleRecord.id)
        )

        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        component_id: int,
        status: str,
        eol_date: date | None = None,
        last_buy_date: date | None = None,
    ) -> LifecycleRecord:
        record = LifecycleRecord(
            component_id=component_id,
            status=status,
            eol_date=eol_date,
            last_buy_date=last_buy_date,
        )

        session.add(record)
        await session.flush()

        return record