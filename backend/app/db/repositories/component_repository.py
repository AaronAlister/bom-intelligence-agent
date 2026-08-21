from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component


class ComponentRepository:

    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        component_id: int,
    ) -> Component | None:
        result = await session.execute(
            select(Component).where(
                Component.id == component_id
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_mpn(
        session: AsyncSession,
        mpn: str,
    ) -> Component | None:
        result = await session.execute(
            select(Component).where(
                Component.mpn == mpn
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_normalized_mpn(
        session: AsyncSession,
        normalized_mpn: str,
    ) -> Component | None:
        result = await session.execute(
            select(Component).where(
                Component.normalized_mpn == normalized_mpn
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        *,
        mpn: str,
        manufacturer: str | None = None,
        description: str | None = None,
        category: str | None = None,
        package: str | None = None,
    ) -> Component:
        component = Component(
            mpn=mpn,
            manufacturer=manufacturer,
            description=description,
            category=category,
            package=package,
        )

        session.add(component)
        await session.flush()

        return component

    @staticmethod
    async def list_all(
        session: AsyncSession,
    ) -> list[Component]:
        result = await session.execute(
            select(Component).order_by(
                Component.id
            )
        )

        return list(result.scalars().all())

    @staticmethod
    async def search(
        session: AsyncSession,
        *,
        bom_id: str | None = None,
        search: str | None = None,
        enrichment_status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Component], int]:
        """
        Return paginated components with optional BOM,
        search, and enrichment-status filtering.

        When bom_id is supplied, only components belonging
        to that BOM are returned.
        """

        filters = []

        if bom_id is not None:
            bom_id_query = (
                select(BOM.id)
                .where(
                    BOM.bom_id == bom_id
                )
            )

            filters.append(
                Component.id.in_(
                    select(
                        BOMComponent.component_id
                    ).where(
                        BOMComponent.bom_id.in_(
                            bom_id_query
                        )
                    )
                )
            )

        if search:
            search_term = (
                f"%{search.strip()}%"
            )

            filters.append(
                or_(
                    Component.mpn.ilike(
                        search_term
                    ),
                    Component.manufacturer.ilike(
                        search_term
                    ),
                    Component.description.ilike(
                        search_term
                    ),
                )
            )

        if enrichment_status:
            filters.append(
                Component.enrichment_status
                == enrichment_status.upper()
            )

        count_query = select(
            func.count(Component.id)
        )

        if filters:
            count_query = count_query.where(
                *filters
            )

        count_result = await session.execute(
            count_query
        )

        total = count_result.scalar_one()

        offset = (
            (page - 1) * page_size
        )

        query = (
            select(Component)
            .order_by(Component.id)
            .offset(offset)
            .limit(page_size)
        )

        if filters:
            query = query.where(
                *filters
            )

        result = await session.execute(
            query
        )

        components = list(
            result.scalars().all()
        )

        return components, total

    @staticmethod
    async def list_alternative_candidates(
        session: AsyncSession,
        *,
        category: str | None,
        package: str | None,
        manufacturer: str | None,
        exclude_component_id: int,
    ) -> list[Component]:
        """
        Return components that are potential
        alternative candidates.

        Candidate discovery intentionally uses broader
        filters than final compatibility validation.

        Category, package, and manufacturer are treated
        as discovery signals using OR logic.

        Final compatibility decisions remain the
        responsibility of AlternativeMatcher.
        """

        query = (
            select(Component)
            .where(
                Component.id != exclude_component_id,
            )
            .order_by(
                Component.id
            )
        )

        discovery_filters = []

        if category:
            discovery_filters.append(
                Component.category == category
            )

        if package:
            discovery_filters.append(
                Component.package == package
            )

        if manufacturer:
            discovery_filters.append(
                Component.manufacturer == manufacturer
            )

        if discovery_filters:
            query = query.where(
                or_(
                    *discovery_filters
                )
            )

        result = await session.execute(
            query
        )

        return list(
            result.scalars().all()
        )