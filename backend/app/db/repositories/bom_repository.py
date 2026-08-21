from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent


class BOMRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        bom_id: int,
    ) -> BOM | None:
        result = await session.execute(
            select(BOM).where(
                BOM.id == bom_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_bom_id(
        session: AsyncSession,
        bom_id: str,
    ) -> BOM | None:
        result = await session.execute(
            select(BOM).where(
                BOM.bom_id == bom_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        bom_id: str,
        product: str | None = None,
        revision: str | None = None,
        source_file: str | None = None,
    ) -> BOM:
        bom = BOM(
            bom_id=bom_id,
            product=product,
            revision=revision,
            source_file=source_file,
        )

        session.add(bom)
        await session.flush()

        return bom

    @staticmethod
    async def list_all(
        session: AsyncSession,
    ) -> list[BOM]:
        result = await session.execute(
            select(BOM).order_by(BOM.id)
        )

        return list(
            result.scalars().all()
        )

    @staticmethod
    async def get_latest(
        session: AsyncSession,
    ) -> BOM | None:
        result = await session.execute(
            select(BOM)
            .options(
                selectinload(
                    BOM.components
                ).selectinload(
                    BOMComponent.component
                ),
                selectinload(
                    BOM.ingestion_records
                ),
            )
            .order_by(
                BOM.created_at.desc(),
                BOM.id.desc(),
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def list_components_for_bom(
        session: AsyncSession,
        bom_id: int,
    ) -> list[BOMComponent]:
        """
        Return all BOM-component associations for a BOM,
        with their component records eagerly loaded.
        """

        result = await session.execute(
            select(BOMComponent)
            .where(
                BOMComponent.bom_id == bom_id
            )
            .options(
                selectinload(
                    BOMComponent.component
                )
            )
            .order_by(
                BOMComponent.id
            )
        )

        return list(
            result.scalars().all()
        )