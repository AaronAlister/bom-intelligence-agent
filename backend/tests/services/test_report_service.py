import uuid

import pytest
from sqlalchemy import delete

from backend.app.db.repositories import (
    BOMRepository,
    BOMRiskRepository,
    ComponentRepository,
    LifecycleRepository,
    RiskRepository,
)
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.bom import BOM
from backend.app.models.bom_component import BOMComponent
from backend.app.models.bom_risk import BOMRiskRecord
from backend.app.services.report_service import (
    ReportService,
)


@pytest.mark.asyncio
async def test_report_generates_for_analyzed_bom() -> None:
    suffix = uuid.uuid4().hex[:8]

    bom_database_id: int | None = None
    component_ids: list[int] = []

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=f"REPORT-ANALYZED-{suffix}",
            product="Report Test Controller",
            revision="REV-A",
            source_file="report_test.xlsx",
        )

        component_one = await ComponentRepository.create(
            session,
            mpn=f"REPORT-COMP-ONE-{suffix}",
            manufacturer="Texas Instruments",
            category="Power IC",
            package="QFN-16",
        )

        component_two = await ComponentRepository.create(
            session,
            mpn=f"REPORT-COMP-TWO-{suffix}",
            manufacturer="STMicroelectronics",
            category="Microcontroller",
            package="LQFP-64",
        )

        await session.flush()

        bom_component_one = BOMComponent(
            bom_id=bom.id,
            component_id=component_one.id,
            quantity=2,
            reference_designators="U1",
        )

        bom_component_two = BOMComponent(
            bom_id=bom.id,
            component_id=component_two.id,
            quantity=5,
            reference_designators="U2",
        )

        session.add_all(
            [
                bom_component_one,
                bom_component_two,
            ]
        )

        await session.flush()

        lifecycle_one = await LifecycleRepository.create(
            session,
            component_id=component_one.id,
            status="ACTIVE",
        )

        lifecycle_two = await LifecycleRepository.create(
            session,
            component_id=component_two.id,
            status="NRND",
        )

        assert lifecycle_one.component_id == component_one.id
        assert lifecycle_two.component_id == component_two.id

        risk_details_one = {
            "lifecycle_score": 0.0,
            "availability_score": 0.0,
            "reasons": [
                "Component lifecycle is ACTIVE.",
                "Component is available from 2 distributors.",
            ],
        }

        risk_details_two = {
            "lifecycle_score": 50.0,
            "availability_score": 50.0,
            "reasons": [
                "Component is NRND.",
                "Component is available from only one distributor.",
            ],
        }

        risk_one = await RiskRepository.create(
            session,
            component_id=component_one.id,
            risk_type="COMPONENT",
            score=0.0,
            severity="LOW",
            details=risk_details_one,
        )

        risk_two = await RiskRepository.create(
            session,
            component_id=component_two.id,
            risk_type="COMPONENT",
            score=50.0,
            severity="HIGH",
            details=risk_details_two,
        )

        assert risk_one.component_id == component_one.id
        assert risk_two.component_id == component_two.id

        bom_risk_details = {
            "summary": (
                "BOM risk is HIGH because the second "
                "component has lifecycle and availability exposure."
            ),
            "risk_drivers": [
                {
                    "component_id": component_two.id,
                    "mpn": component_two.mpn,
                    "score": 50.0,
                    "severity": "HIGH",
                    "reason": (
                        "NRND lifecycle and limited "
                        "distributor availability."
                    ),
                }
            ],
            "recommendations": [
                {
                    "priority": "HIGH",
                    "component_id": component_two.id,
                    "mpn": component_two.mpn,
                    "action": (
                        "Evaluate an alternative component."
                    ),
                    "reason": (
                        "Reduce lifecycle and "
                        "availability exposure."
                    ),
                }
            ],
        }

        risk_snapshot = await BOMRiskRepository.create(
            session,
            bom_id=bom.id,
            overall_score=25.0,
            severity="MEDIUM",
            component_count=2,
            high_risk_count=1,
            critical_count=0,
            lifecycle_risk_count=1,
            availability_risk_count=1,
            details=bom_risk_details,
        )

        await session.commit()

        bom_database_id = bom.id
        component_ids = [
            component_one.id,
            component_two.id,
        ]

    assert bom_database_id is not None

    async with AsyncSessionLocal() as session:
        report = await ReportService.generate(
            session,
            bom_id=bom_database_id,
        )

        assert report.bom_id == bom_database_id

        assert report.product == (
            "Report Test Controller"
        )

        assert report.revision == "REV-A"

        assert report.source_file == (
            "report_test.xlsx"
        )

        assert report.source_format == "xlsx"

        assert report.component_count == 2

        assert report.total_quantity == 7

        assert report.overall_score == (
            risk_snapshot.overall_score
        )

        assert report.severity == (
            risk_snapshot.severity
        )

        assert report.high_risk_count == (
            risk_snapshot.high_risk_count
        )

        assert report.critical_count == (
            risk_snapshot.critical_count
        )

        assert report.lifecycle_risk_count == (
            risk_snapshot.lifecycle_risk_count
        )

        assert report.availability_risk_count == (
            risk_snapshot.availability_risk_count
        )

        assert report.summary == (
            "BOM risk is HIGH because the second "
            "component has lifecycle and availability exposure."
        )

        assert report.lifecycle.active_count == 1
        assert report.lifecycle.nrnd_count == 1
        assert report.lifecycle.eol_count == 0
        assert report.lifecycle.obsolete_count == 0
        assert report.lifecycle.unknown_count == 0
        assert report.lifecycle.lifecycle_risk_count == 1

        assert (
            report.availability
            .availability_risk_count
            == 1
        )

        assert (
            report.availability
            .components_with_availability
            == 1
        )

        assert (
            report.availability
            .components_without_availability
            == 1
        )

        assert len(
            report.top_risk_components
        ) == 2

        assert (
            report.top_risk_components[0].mpn
            == f"REPORT-COMP-TWO-{suffix}"
        )

        assert (
            report.top_risk_components[0].score
            == 50.0
        )

        assert (
            report.top_risk_components[0].severity
            == "HIGH"
        )

        assert (
            report.top_risk_components[0]
            .lifecycle_risk
            is True
        )

        assert (
            report.top_risk_components[0]
            .availability_risk
            is True
        )

        assert (
            report.top_risk_components[1].mpn
            == f"REPORT-COMP-ONE-{suffix}"
        )

        assert (
            report.top_risk_components[1].score
            == 0.0
        )

        assert (
            report.top_risk_components[1]
            .lifecycle_risk
            is False
        )

        assert (
            report.top_risk_components[1]
            .availability_risk
            is False
        )

        assert len(report.risk_drivers) == 1

        assert (
            report.risk_drivers[0].component_id
            == component_ids[1]
        )

        assert (
            report.risk_drivers[0].score
            == 50.0
        )

        assert (
            report.risk_drivers[0].severity
            == "HIGH"
        )

        assert len(report.recommendations) == 1

        assert (
            report.recommendations[0].component_id
            == component_ids[1]
        )

        assert (
            report.recommendations[0].priority
            == "HIGH"
        )


@pytest.mark.asyncio
async def test_report_returns_unknown_risk_without_snapshot() -> None:
    bom_id: int | None = None

    async with AsyncSessionLocal() as session:
        bom = await BOMRepository.create(
            session,
            bom_id=(
                "REPORT-NO-RISK-"
                f"{uuid.uuid4().hex[:8]}"
            ),
            product="Report Test BOM",
            source_file="report_test.xlsx",
        )

        await session.commit()

        bom_id = bom.id

    assert bom_id is not None

    async with AsyncSessionLocal() as session:
        report = await ReportService.generate(
            session,
            bom_id=bom_id,
        )

        assert report.bom_id == bom_id

        assert report.overall_score == 0.0

        assert report.severity == "UNKNOWN"

        assert report.summary == (
            "No persisted BOM risk "
            "assessment is available."
        )

        assert report.risk_drivers == []

        assert report.recommendations == []

        assert report.component_count == 0

        assert report.total_quantity == 0

    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(BOMRiskRecord).where(
                BOMRiskRecord.bom_id == bom_id
            )
        )

        await session.execute(
            delete(BOMComponent).where(
                BOMComponent.bom_id == bom_id
            )
        )

        # Clean deletion using the imported BOM model
        await session.execute(
            delete(BOM).where(
                BOM.id == bom_id
            )
        )

        await session.commit()


@pytest.mark.asyncio
async def test_report_raises_for_unknown_bom() -> None:
    async with AsyncSessionLocal() as session:
        with pytest.raises(
            ValueError,
            match="BOM 999999 not found",
        ):
            await ReportService.generate(
                session,
                bom_id=999999,
            )