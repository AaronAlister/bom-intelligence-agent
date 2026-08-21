import logging
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.bom_schemas import (
    BOMRiskComponentResponse,
    BOMRiskDriverResponse,
    BOMRiskHistoryResponse,
    BOMRiskHistorySnapshotResponse,
    BOMRiskRecommendationResponse,
    BOMRiskResponse,
    BOMRiskTrendResponse,
)
from backend.app.core.config import settings
from backend.app.db.repositories import (
    BOMRepository,
    BOMRiskRepository,
)
from backend.app.db.session import get_db
from backend.app.ingestion.parsers import get_parser
from backend.app.ingestion.schemas import (
    BOMComponent,
    BOMMetadata,
    IngestionResult,
)
from backend.app.intelligence.risk.bom_explainer import (
    BOMRiskExplainer,
)
from backend.app.intelligence.risk.bom_trend_analyzer import (
    BOMRiskTrendAnalyzer,
)
from backend.app.intelligence.risk.models import RiskSeverity
from backend.app.services.bom_component_risk import (
    BOMComponentRiskService,
)
from backend.app.services.bom_ingestion_service import (
    BOMIngestionService,
)
from backend.app.services.bom_risk import (
    BOMRiskService,
)
from backend.app.services.bom_risk_workflow import (
    BOMRiskWorkflowService,
)

# ---- NEW IMPORTS ----
from backend.app.reports.models import BOMReport
from backend.app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/boms",
    tags=["BOM"],
)


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".xml",
    ".json",
}


MAX_BOM_FILE_SIZE_BYTES = (
    settings.max_bom_file_size_mb * 1024 * 1024
)


@router.post(
    "/upload",
    response_model=IngestionResult,
)
async def upload_bom(
    file: UploadFile = File(...),
    product: str | None = Form(default=None),
    revision: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
) -> IngestionResult:
    """
    Upload, validate, ingest, and persist a BOM.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A BOM file is required.",
        )

    safe_filename = Path(file.filename).name

    if not safe_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid BOM filename.",
        )

    extension = Path(
        safe_filename
    ).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported BOM format: {extension}. "
                "Supported formats are: "
                f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    try:
        get_parser(extension)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = (
                Path(temp_dir)
                / safe_filename
            )

            file_size = 0

            with temp_file.open("wb") as destination:
                while chunk := file.file.read(
                    1024 * 1024
                ):
                    file_size += len(chunk)

                    if (
                        file_size
                        > MAX_BOM_FILE_SIZE_BYTES
                    ):
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "BOM file exceeds the "
                                "maximum allowed size "
                                f"of {settings.max_bom_file_size_mb} MB."
                            ),
                        )

                    destination.write(chunk)

            if file_size == 0:
                raise HTTPException(
                    status_code=422,
                    detail="The uploaded BOM file is empty.",
                )

            result = (
                await BOMIngestionService.ingest_and_persist(
                    session=session,
                    file_path=temp_file,
                    product=product,
                    revision=revision,
                )
            )

            if result.total_rows == 0:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "The uploaded file contains "
                        "no BOM records."
                    ),
                )

            if result.invalid_rows > 0:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": (
                            "The BOM contains structurally "
                            "invalid rows."
                        ),
                        "invalid_rows": result.invalid_rows,
                        "total_rows": result.total_rows,
                        "validation_issues": [
                            issue.model_dump()
                            for issue in result.validation_issues
                        ],
                    },
                )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "BOM ingestion failed"
        )

        raise HTTPException(
            status_code=500,
            detail="BOM ingestion failed.",
        ) from exc


@router.get(
    "/latest",
    response_model=IngestionResult,
)
async def get_latest_bom(
    session: AsyncSession = Depends(get_db),
) -> IngestionResult:
    """
    Return the most recently ingested BOM with all its
    components and ingestion metadata.
    """

    bom = await BOMRepository.get_latest(
        session
    )

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail="No BOM has been ingested yet.",
        )

    if not bom.ingestion_records:
        raise HTTPException(
            status_code=500,
            detail="Latest BOM has no ingestion record.",
        )

    ingestion_record = max(
        bom.ingestion_records,
        key=lambda record: (
            record.created_at,
            record.id,
        ),
    )

    if ingestion_record.status != "success":
        raise HTTPException(
            status_code=500,
            detail="Latest BOM ingestion was not successful.",
        )

    components = [
        BOMComponent(
            mpn=bom_component.component.mpn,
            manufacturer=(
                bom_component.component.manufacturer
            ),
            description=(
                bom_component.component.description
            ),
            category=(
                bom_component.component.category
            ),
            package=(
                bom_component.component.package
            ),
            quantity=bom_component.quantity,
            reference_designators=[
                reference.strip()
                for reference in (
                    bom_component.reference_designators
                    or ""
                ).split(",")
                if reference.strip()
            ],
        )
        for bom_component in bom.components
    ]

    metadata = BOMMetadata(
        bom_id=bom.bom_id,
        bom_database_id=bom.id,
        product=bom.product,
        revision=bom.revision,
        source_file=(
            bom.source_file
            or ingestion_record.source_file
        ),
        source_format=ingestion_record.source_format,
        ingested_at=ingestion_record.created_at,
    )

    total_rows = ingestion_record.row_count
    invalid_rows = ingestion_record.error_count
    valid_rows = total_rows - invalid_rows

    return IngestionResult(
        bom_id=bom.bom_id,
        bom_database_id=bom.id,
        source_file=(
            bom.source_file
            or ingestion_record.source_file
        ),
        source_format=ingestion_record.source_format,
        metadata=metadata,
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        components=components,
        validation_issues=[],
    )


# ---- NEW REPORT ENDPOINT ----
@router.get(
    "/{bom_id}/report",
    response_model=BOMReport,
)
async def get_bom_report(
    bom_id: int,
    session: AsyncSession = Depends(get_db),
) -> BOMReport:
    """
    Generate a complete intelligence report for a BOM.

    The report is assembled from persisted BOM, lifecycle,
    availability, and risk intelligence. This endpoint does
    not execute a new analysis or modify the database.
    """

    try:
        return await ReportService.generate(
            session=session,
            bom_id=bom_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Failed to generate BOM report for BOM %s",
            bom_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to generate BOM report.",
        ) from exc


@router.get(
    "/{bom_id}/risk/history",
    response_model=BOMRiskHistoryResponse,
)
async def get_bom_risk_history(
    bom_id: int,
    session: AsyncSession = Depends(get_db),
) -> BOMRiskHistoryResponse:
    """
    Return historical BOM risk snapshots and the
    calculated risk trend.

    The endpoint is read-only.
    """

    bom = await BOMRepository.get_by_id(
        session,
        bom_id,
    )

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail=f"BOM {bom_id} not found.",
        )

    try:
        records = await BOMRiskRepository.list_for_bom(
            session,
            bom_id,
        )

        trend = BOMRiskTrendAnalyzer.analyze(
            records
        )

        return BOMRiskHistoryResponse(
            bom_id=bom_id,
            snapshot_count=len(records),
            trend=BOMRiskTrendResponse(
                trend=trend.trend,
                snapshot_count=trend.snapshot_count,
                previous_score=trend.previous_score,
                current_score=trend.current_score,
                score_change=trend.score_change,
                previous_severity=(
                    trend.previous_severity
                ),
                current_severity=(
                    trend.current_severity
                ),
                previous_high_risk_count=(
                    trend.previous_high_risk_count
                ),
                current_high_risk_count=(
                    trend.current_high_risk_count
                ),
                high_risk_count_change=(
                    trend.high_risk_count_change
                ),
                previous_critical_count=(
                    trend.previous_critical_count
                ),
                current_critical_count=(
                    trend.current_critical_count
                ),
                critical_count_change=(
                    trend.critical_count_change
                ),
                previous_lifecycle_risk_count=(
                    trend.previous_lifecycle_risk_count
                ),
                current_lifecycle_risk_count=(
                    trend.current_lifecycle_risk_count
                ),
                lifecycle_risk_count_change=(
                    trend.lifecycle_risk_count_change
                ),
                previous_availability_risk_count=(
                    trend.previous_availability_risk_count
                ),
                current_availability_risk_count=(
                    trend.current_availability_risk_count
                ),
                availability_risk_count_change=(
                    trend.availability_risk_count_change
                ),
            ),
            history=[
                BOMRiskHistorySnapshotResponse(
                    id=record.id,
                    overall_score=record.overall_score,
                    severity=RiskSeverity(
                        record.severity
                    ),
                    component_count=(
                        record.component_count
                    ),
                    high_risk_count=(
                        record.high_risk_count
                    ),
                    critical_count=(
                        record.critical_count
                    ),
                    lifecycle_risk_count=(
                        record.lifecycle_risk_count
                    ),
                    availability_risk_count=(
                        record.availability_risk_count
                    ),
                    created_at=record.created_at,
                )
                for record in records
            ],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "BOM risk history contains "
                "invalid data."
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "BOM risk history analysis failed."
            ),
        ) from exc


# =============================================================
# COMPONENT-LEVEL BOM RISK ANALYSIS
# =============================================================

@router.post(
    "/{bom_id}/components/risk",
    response_model=BOMRiskResponse,
)
async def analyze_bom_component_risk(
    bom_id: int,
    session: AsyncSession = Depends(get_db),
) -> BOMRiskResponse:
    """
    Run component-level risk analysis for every component
    belonging to the BOM.

    The resulting component risk records are then aggregated
    into a BOM-level risk assessment.
    """

    bom = await BOMRepository.get_by_id(
        session,
        bom_id,
    )

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail=f"BOM {bom_id} not found.",
        )

    try:
        await BOMComponentRiskService.analyze_bom_components(
            session=session,
            bom_id=bom_id,
        )

        (
            assessment,
            explanation,
            _risk_record,
        ) = await BOMRiskWorkflowService.analyze_and_persist(
            session=session,
            bom_id=bom_id,
        )

        await session.commit()

        return BOMRiskResponse(
            bom_id=bom_id,
            overall_score=assessment.overall_score,
            severity=assessment.severity,
            component_count=assessment.component_count,
            high_risk_count=assessment.high_risk_count,
            critical_count=assessment.critical_count,
            lifecycle_risk_count=(
                assessment.lifecycle_risk_count
            ),
            availability_risk_count=(
                assessment.availability_risk_count
            ),
            top_risk_components=[
                BOMRiskComponentResponse(
                    component_id=component.component_id,
                    mpn=component.mpn,
                    quantity=component.quantity,
                    score=component.score,
                    severity=component.severity,
                    lifecycle_risk=(
                        component.lifecycle_risk
                    ),
                    availability_risk=(
                        component.availability_risk
                    ),
                )
                for component
                in assessment.top_risk_components
            ],
            summary=explanation.summary,
            risk_drivers=[
                BOMRiskDriverResponse(
                    component_id=driver.component_id,
                    mpn=driver.mpn,
                    score=driver.score,
                    severity=driver.severity,
                    reason=driver.reason,
                )
                for driver in explanation.risk_drivers
            ],
            recommendations=[
                BOMRiskRecommendationResponse(
                    priority=recommendation.priority,
                    component_id=(
                        recommendation.component_id
                    ),
                    mpn=recommendation.mpn,
                    action=recommendation.action,
                    reason=recommendation.reason,
                )
                for recommendation
                in explanation.recommendations
            ],
        )

    except ValueError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await session.rollback()

        logger.exception(
            "BOM component risk analysis failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "BOM component risk analysis failed."
            ),
        ) from exc


# =============================================================
# COMPLETE BOM RISK ANALYSIS
# =============================================================

@router.post(
    "/{bom_id}/risk",
    response_model=BOMRiskResponse,
)
async def analyze_bom_risk(
    bom_id: int,
    session: AsyncSession = Depends(get_db),
) -> BOMRiskResponse:
    """
    Run the complete BOM risk workflow.

    The workflow:

        1. Analyze every component in the BOM.
        2. Persist component-level risk records.
        3. Aggregate component risks into a BOM-level
           assessment.
        4. Persist the BOM risk snapshot.
        5. Return the resulting BOM risk intelligence.
    """

    bom = await BOMRepository.get_by_id(
        session,
        bom_id,
    )

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail=f"BOM {bom_id} not found.",
        )

    try:
        # -----------------------------------------------------
        # 1. Analyze all components and persist their risks.
        #
        # BOMComponentRiskService already owns:
        #
        #     enrichment
        #     lifecycle assessment
        #     availability assessment
        #     component risk assessment
        #     risk persistence
        #
        # Therefore we deliberately do not duplicate that
        # provider/orchestrator logic in this route.
        # -----------------------------------------------------

        await BOMComponentRiskService.analyze_bom_components(
            session=session,
            bom_id=bom_id,
        )

        # -----------------------------------------------------
        # 2. Aggregate component risks into BOM-level risk.
        # -----------------------------------------------------

        (
            assessment,
            explanation,
            _risk_record,
        ) = await BOMRiskWorkflowService.analyze_and_persist(
            session=session,
            bom_id=bom_id,
        )

        # -----------------------------------------------------
        # 3. Persist the complete workflow.
        # -----------------------------------------------------

        await session.commit()

        # -----------------------------------------------------
        # 4. Return BOM risk intelligence.
        # -----------------------------------------------------

        return BOMRiskResponse(
            bom_id=bom_id,
            overall_score=assessment.overall_score,
            severity=assessment.severity,
            component_count=assessment.component_count,
            high_risk_count=assessment.high_risk_count,
            critical_count=assessment.critical_count,
            lifecycle_risk_count=(
                assessment.lifecycle_risk_count
            ),
            availability_risk_count=(
                assessment.availability_risk_count
            ),
            top_risk_components=[
                BOMRiskComponentResponse(
                    component_id=component.component_id,
                    mpn=component.mpn,
                    quantity=component.quantity,
                    score=component.score,
                    severity=component.severity,
                    lifecycle_risk=(
                        component.lifecycle_risk
                    ),
                    availability_risk=(
                        component.availability_risk
                    ),
                )
                for component
                in assessment.top_risk_components
            ],
            summary=explanation.summary,
            risk_drivers=[
                BOMRiskDriverResponse(
                    component_id=driver.component_id,
                    mpn=driver.mpn,
                    score=driver.score,
                    severity=driver.severity,
                    reason=driver.reason,
                )
                for driver in explanation.risk_drivers
            ],
            recommendations=[
                BOMRiskRecommendationResponse(
                    priority=recommendation.priority,
                    component_id=(
                        recommendation.component_id
                    ),
                    mpn=recommendation.mpn,
                    action=recommendation.action,
                    reason=recommendation.reason,
                )
                for recommendation
                in explanation.recommendations
            ],
        )

    except ValueError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        await session.rollback()

        logger.exception(
            "BOM risk analysis failed"
        )

        raise HTTPException(
            status_code=500,
            detail="BOM risk analysis failed.",
        ) from exc


# =============================================================
# READ CURRENT BOM RISK
# =============================================================

@router.get(
    "/{bom_id}/risk",
    response_model=BOMRiskResponse,
)
async def get_bom_risk(
    bom_id: int,
    session: AsyncSession = Depends(get_db),
) -> BOMRiskResponse:
    """
    Return the current risk intelligence for a BOM.

    This endpoint is read-only.
    """

    bom = await BOMRepository.get_by_id(
        session,
        bom_id,
    )

    if bom is None:
        raise HTTPException(
            status_code=404,
            detail=f"BOM {bom_id} not found.",
        )

    try:
        assessment = await BOMRiskService.assess_bom(
            session,
            bom_id,
        )

        explanation = BOMRiskExplainer.explain(
            assessment
        )

        return BOMRiskResponse(
            bom_id=bom_id,
            overall_score=assessment.overall_score,
            severity=assessment.severity,
            component_count=assessment.component_count,
            high_risk_count=assessment.high_risk_count,
            critical_count=assessment.critical_count,
            lifecycle_risk_count=(
                assessment.lifecycle_risk_count
            ),
            availability_risk_count=(
                assessment.availability_risk_count
            ),
            top_risk_components=[
                BOMRiskComponentResponse(
                    component_id=component.component_id,
                    mpn=component.mpn,
                    quantity=component.quantity,
                    score=component.score,
                    severity=component.severity,
                    lifecycle_risk=(
                        component.lifecycle_risk
                    ),
                    availability_risk=(
                        component.availability_risk
                    ),
                )
                for component
                in assessment.top_risk_components
            ],
            summary=explanation.summary,
            risk_drivers=[
                BOMRiskDriverResponse(
                    component_id=driver.component_id,
                    mpn=driver.mpn,
                    score=driver.score,
                    severity=driver.severity,
                    reason=driver.reason,
                )
                for driver in explanation.risk_drivers
            ],
            recommendations=[
                BOMRiskRecommendationResponse(
                    priority=recommendation.priority,
                    component_id=(
                        recommendation.component_id
                    ),
                    mpn=recommendation.mpn,
                    action=recommendation.action,
                    reason=recommendation.reason,
                )
                for recommendation
                in explanation.recommendations
            ],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail="BOM risk data contains invalid values.",
        ) from exc

    except Exception as exc:
        logger.exception(
            "BOM risk retrieval failed"
        )

        raise HTTPException(
            status_code=500,
            detail="BOM risk analysis failed.",
        ) from exc