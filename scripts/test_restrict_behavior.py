import asyncio
import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.session import AsyncSessionLocal, engine
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component


async def main():
    suffix = uuid.uuid4().hex[:8]

    bom_id = f"RESTRICT-BOM-{suffix}"
    mpn = f"RESTRICT-COMP-{suffix}"

    print(f"BOM ID: {bom_id}")
    print(f"MPN:    {mpn}")

    async with AsyncSessionLocal() as session:
        bom = BOM(
            bom_id=bom_id,
            product="Restrict Diagnostic",
            revision="1.0",
            source_file="diagnostic.csv",
        )

        component = Component(
            mpn=mpn,
            manufacturer="Diagnostic Manufacturer",
        )

        session.add_all([bom, component])
        await session.flush()

        association = BOMComponent(
            bom_id=bom.id,
            component_id=component.id,
            quantity=1,
            reference_designators="U1",
        )

        session.add(association)
        await session.commit()

        component_id = component.id
        bom_db_id = bom.id

        print(f"Component DB ID: {component_id}")
        print(f"BOM DB ID:       {bom_db_id}")

    # Attempt the restricted delete in a completely new transaction.
    async with AsyncSessionLocal() as session:
        print("\nAttempting component DELETE...")

        try:
            await session.execute(
                delete(Component).where(
                    Component.id == component_id
                )
            )

            await session.commit()

            print("ERROR: Component deletion unexpectedly succeeded.")

        except IntegrityError as exc:
            print("SUCCESS: PostgreSQL rejected the component deletion.")
            print(f"IntegrityError: {type(exc).__name__}")

            await session.rollback()

    # Verify using another completely fresh connection/session.
    async with AsyncSessionLocal() as session:
        component_exists = await session.scalar(
            select(Component.id).where(
                Component.id == component_id
            )
        )

        association_exists = await session.scalar(
            select(BOMComponent.id).where(
                BOMComponent.bom_id == bom_db_id,
                BOMComponent.component_id == component_id,
            )
        )

        print("\nDatabase state after rejected DELETE:")
        print(f"Component exists:    {component_exists is not None}")
        print(f"BOMComponent exists: {association_exists is not None}")

        # Cleanup.
        await session.execute(
            delete(BOM).where(BOM.id == bom_db_id)
        )
        await session.commit()

        print("\nCleanup complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())