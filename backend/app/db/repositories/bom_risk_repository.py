import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.bom_risk import BOMRiskRecord


class BOMRiskRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        risk_id: int,
    ) -> BOMRiskRecord | None:
        result = await session.execute(
            select(BOMRiskRecord).where(
                BOMRiskRecord.id == risk_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_bom(
        session: AsyncSession,
        bom_id: int,
    ) -> list[BOMRiskRecord]:
        result = await session.execute(
            select(BOMRiskRecord)
            .where(
                BOMRiskRecord.bom_id == bom_id
            )
            .order_by(BOMRiskRecord.id)
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_latest_for_bom(
        session: AsyncSession,
        bom_id: int,
    ) -> BOMRiskRecord | None:
        """
        Return the most recent risk snapshot for a BOM.
        """

        result = await session.execute(
            select(BOMRiskRecord)
            .where(
                BOMRiskRecord.bom_id == bom_id
            )
            .order_by(
                BOMRiskRecord.created_at.desc(),
                BOMRiskRecord.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        bom_id: int,
        overall_score: float,
        severity: str,
        component_count: int,
        high_risk_count: int,
        critical_count: int,
        lifecycle_risk_count: int,
        availability_risk_count: int,
        details: dict | None = None,
    ) -> BOMRiskRecord:

        details_json = (
            json.dumps(details)
            if details is not None
            else None
        )

        record = BOMRiskRecord(
            bom_id=bom_id,
            overall_score=overall_score,
            severity=severity,
            component_count=component_count,
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            lifecycle_risk_count=lifecycle_risk_count,
            availability_risk_count=availability_risk_count,
            details=details_json,
        )

        session.add(record)
        await session.flush()

        return record