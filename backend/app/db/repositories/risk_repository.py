import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.risk import RiskRecord


class RiskRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        risk_id: int,
    ) -> RiskRecord | None:
        result = await session.execute(
            select(RiskRecord).where(
                RiskRecord.id == risk_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_component(
        session: AsyncSession,
        component_id: int,
    ) -> list[RiskRecord]:
        result = await session.execute(
            select(RiskRecord)
            .where(
                RiskRecord.component_id == component_id
            )
            .order_by(RiskRecord.id)
        )

        return list(result.scalars().all())

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        component_id: int,
        risk_type: str,
        score: float,
        severity: str,
        details: dict | None = None,
    ) -> RiskRecord:

        details_json = (
            json.dumps(details)
            if details is not None
            else None
        )

        record = RiskRecord(
            component_id=component_id,
            risk_type=risk_type,
            score=score,
            severity=severity,
            details=details_json,
        )

        session.add(record)
        await session.flush()

        return record