import uuid
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.app.db.session import AsyncSessionLocal
from backend.app.main import app
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.component import Component
from backend.app.models.ingestion import IngestionRecord


client = TestClient(app)


def test_bom_upload_persists_complete_graph():
    suffix = uuid.uuid4().hex[:8]

    filename = f"e2e_test_{suffix}.csv"

    mpn_1 = f"LM358DR-{suffix}"
    mpn_2 = f"STM32F401-{suffix}"

    response = client.post(
        "/api/v1/boms/upload",
        files={
            "file": (
                filename,
                BytesIO(
                    (
                        "MPN,Manufacturer,Description,Category,"
                        "Package,Quantity,Reference Designators\n"
                        f"{mpn_1},Texas Instruments,"
                        "Dual operational amplifier,Analog IC,"
                        'SOIC-8,2,"U1,U2"\n'
                        f"{mpn_2},STMicroelectronics,"
                        "ARM Cortex-M4 microcontroller,MCU,"
                        "LQFP-48,1,U3\n"
                    ).encode("utf-8")
                ),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["source_file"] == filename
    assert data["source_format"] == "csv"
    assert data["total_rows"] == 2
    assert data["valid_rows"] == 2
    assert data["invalid_rows"] == 0
    assert len(data["components"]) == 2

    bom_identifier = data["bom_id"]

    async def verify_database():
        async with AsyncSessionLocal() as session:

            stored_bom = await session.scalar(
                select(BOM).where(
                    BOM.bom_id == bom_identifier
                )
            )

            assert stored_bom is not None
            assert stored_bom.source_file == filename

            stored_components = await session.scalars(
                select(Component).where(
                    Component.mpn.in_(
                        [
                            mpn_1,
                            mpn_2,
                        ]
                    )
                )
            )

            components = list(
                stored_components
            )

            assert len(components) == 2

            mappings = await session.scalars(
                select(BOMComponent).where(
                    BOMComponent.bom_id
                    == stored_bom.id
                )
            )

            mappings = list(mappings)

            assert len(mappings) == 2

            stored_ingestion = await session.scalar(
                select(IngestionRecord).where(
                    IngestionRecord.bom_id
                    == stored_bom.id
                )
            )

            assert stored_ingestion is not None
            assert stored_ingestion.status == "success"
            assert stored_ingestion.row_count == 2
            assert stored_ingestion.error_count == 0

            await session.execute(
                delete(BOM).where(
                    BOM.id == stored_bom.id
                )
            )

            await session.commit()

    import asyncio

    asyncio.run(verify_database())