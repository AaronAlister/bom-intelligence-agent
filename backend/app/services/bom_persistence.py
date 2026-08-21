from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import (
    BOMRepository,
    ComponentRepository,
    IngestionRepository,
)
from backend.app.models.bom_component import BOMComponent


class BOMPersistenceService:

    @staticmethod
    async def persist_bom(
        session: AsyncSession,
        *,
        bom_id: str,
        product: str | None,
        revision: str | None,
        source_file: str,
        source_format: str,
        components: list[dict],
    ):
        # 1. Create BOM
        bom = await BOMRepository.create(
            session,
            bom_id=bom_id,
            product=product,
            revision=revision,
            source_file=source_file,
        )

        # 2. Process components
        for component_data in components:
            mpn = component_data["mpn"]

            component = await ComponentRepository.get_by_mpn(
                session,
                mpn,
            )

            if component is None:
                component = await ComponentRepository.create(
                    session,
                    mpn=mpn,
                    manufacturer=component_data.get("manufacturer"),
                    description=component_data.get("description"),
                    category=component_data.get("category"),
                    package=component_data.get("package"),
                )

            # 3. Create BOM ↔ Component mapping
            association = BOMComponent(
                bom_id=bom.id,
                component_id=component.id,
                quantity=component_data.get("quantity", 1),
                reference_designators=(
                    ",".join(
                        component_data.get(
                            "reference_designators",
                            [],
                        )
                    ) or None
                ),
            )

            session.add(association)

        # 4. Record ingestion
        ingestion = await IngestionRepository.create(
            session,
            bom_id=bom.id,
            source_file=source_file,
            source_format=source_format,
            status="success",
            row_count=len(components),
            error_count=0,
        )

        await session.flush()

        return bom, ingestion