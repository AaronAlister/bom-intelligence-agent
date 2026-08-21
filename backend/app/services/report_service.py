import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories import (
    BOMRepository,
    BOMRiskRepository,
    LifecycleRepository,
    RiskRepository,
)
from backend.app.intelligence.risk.models import (
    RiskSeverity,
)
from backend.app.reports.models import (
    BOMReport,
    ReportAvailabilitySummary,
    ReportComponentRisk,
    ReportLifecycleSummary,
    ReportRecommendation,
    ReportRiskDriver,
)


class ReportService:
    """
    Builds a read-only report from persisted BOM intelligence.

    This service does not perform external enrichment,
    risk assessment, or database writes.
    """

    @staticmethod
    async def generate(
        session: AsyncSession,
        *,
        bom_id: int,
    ) -> BOMReport:
        """
        Generate a complete report for a persisted BOM.

        All intelligence is read from persisted records.
        """

        bom = await BOMRepository.get_by_id(
            session,
            bom_id,
        )

        if bom is None:
            raise ValueError(
                f"BOM {bom_id} not found."
            )

        bom_components = (
            await BOMRepository
            .list_components_for_bom(
                session,
                bom_id,
            )
        )

        risk_snapshot = (
            await BOMRiskRepository
            .get_latest_for_bom(
                session,
                bom_id,
            )
        )

        risk_records = {
            bom_component.component.id: (
                await RiskRepository
                .list_for_component(
                    session,
                    bom_component.component.id,
                )
            )
            for bom_component in bom_components
        }

        lifecycle_records = {
            bom_component.component.id: (
                await LifecycleRepository
                .list_for_component(
                    session,
                    bom_component.component.id,
                )
            )
            for bom_component in bom_components
        }

        return ReportService._build_report(
            bom=bom,
            bom_components=bom_components,
            risk_snapshot=risk_snapshot,
            risk_records=risk_records,
            lifecycle_records=lifecycle_records,
        )

    @staticmethod
    def _build_report(
        *,
        bom: Any,
        bom_components: list[Any],
        risk_snapshot: Any,
        risk_records: dict[int, list[Any]],
        lifecycle_records: dict[int, list[Any]],
    ) -> BOMReport:
        """Build the report from persisted records."""

        component_reports: list[
            ReportComponentRisk
        ] = []

        lifecycle_counts = {
            "ACTIVE": 0,
            "NRND": 0,
            "EOL": 0,
            "OBSOLETE": 0,
            "UNKNOWN": 0,
        }

        components_with_availability = 0
        components_without_availability = 0

        for bom_component in bom_components:
            component = bom_component.component

            component_risks = risk_records.get(
                component.id,
                [],
            )

            latest_risk = (
                component_risks[-1]
                if component_risks
                else None
            )

            lifecycle_history = (
                lifecycle_records.get(
                    component.id,
                    [],
                )
            )

            latest_lifecycle = (
                lifecycle_history[-1]
                if lifecycle_history
                else None
            )

            lifecycle_status = (
                latest_lifecycle.status.upper()
                if latest_lifecycle is not None
                else "UNKNOWN"
            )

            if lifecycle_status not in lifecycle_counts:
                lifecycle_status = "UNKNOWN"

            lifecycle_counts[
                lifecycle_status
            ] += 1

            lifecycle_risk = False
            availability_risk = False

            if latest_risk is not None:
                details = (
                    ReportService._parse_details(
                        latest_risk.details
                    )
                )

                lifecycle_score = (
                    ReportService._safe_float(
                        details.get(
                            "lifecycle_score"
                        )
                    )
                )

                availability_score = (
                    ReportService._safe_float(
                        details.get(
                            "availability_score"
                        )
                    )
                )

                lifecycle_risk = (
                    lifecycle_score > 0.0
                )

                availability_risk = (
                    availability_score > 0.0
                )

                if availability_score >= 50.0:
                    (
                        components_without_availability
                    ) += 1
                else:
                    (
                        components_with_availability
                    ) += 1

                component_reports.append(
                    ReportComponentRisk(
                        component_id=component.id,
                        mpn=component.mpn,
                        manufacturer=(
                            component.manufacturer
                        ),
                        quantity=(
                            bom_component.quantity
                        ),
                        score=latest_risk.score,
                        severity=latest_risk.severity,
                        lifecycle_risk=(
                            lifecycle_risk
                        ),
                        availability_risk=(
                            availability_risk
                        ),
                    )
                )

            else:
                components_with_availability += 1

                component_reports.append(
                    ReportComponentRisk(
                        component_id=component.id,
                        mpn=component.mpn,
                        manufacturer=(
                            component.manufacturer
                        ),
                        quantity=(
                            bom_component.quantity
                        ),
                        score=0.0,
                        severity=(
                            RiskSeverity.UNKNOWN.value
                        ),
                        lifecycle_risk=False,
                        availability_risk=False,
                    )
                )

        component_reports.sort(
            key=lambda item: (
                -item.score,
                item.component_id,
            )
        )

        top_risk_components = (
            component_reports[:10]
        )

        if risk_snapshot is None:
            overall_score = 0.0
            severity = (
                RiskSeverity.UNKNOWN.value
            )
            high_risk_count = 0
            critical_count = 0

            lifecycle_risk_count = sum(
                item.lifecycle_risk
                for item in component_reports
            )

            availability_risk_count = sum(
                item.availability_risk
                for item in component_reports
            )

            summary = (
                "No persisted BOM risk "
                "assessment is available."
            )

            risk_drivers: list[
                ReportRiskDriver
            ] = []

            recommendations: list[
                ReportRecommendation
            ] = []

        else:
            overall_score = (
                risk_snapshot.overall_score
            )

            severity = (
                risk_snapshot.severity
            )

            high_risk_count = (
                risk_snapshot.high_risk_count
            )

            critical_count = (
                risk_snapshot.critical_count
            )

            lifecycle_risk_count = (
                risk_snapshot.lifecycle_risk_count
            )

            availability_risk_count = (
                risk_snapshot
                .availability_risk_count
            )

            (
                summary,
                risk_drivers,
                recommendations,
            ) = (
                ReportService
                ._extract_bom_explanation(
                    risk_snapshot.details
                )
            )

        total_quantity = sum(
            bom_component.quantity
            for bom_component in bom_components
        )

        return BOMReport(
            bom_id=bom.id,
            generated_at=datetime.now(
                timezone.utc
            ),
            product=bom.product,
            revision=bom.revision,
            source_file=bom.source_file,
            source_format=(
                ReportService
                ._infer_source_format(
                    bom.source_file
                )
            ),
            component_count=len(
                bom_components
            ),
            total_quantity=total_quantity,
            overall_score=overall_score,
            severity=severity,
            high_risk_count=high_risk_count,
            critical_count=critical_count,
            lifecycle_risk_count=(
                lifecycle_risk_count
            ),
            availability_risk_count=(
                availability_risk_count
            ),
            summary=summary,
            lifecycle=(
                ReportLifecycleSummary(
                    active_count=(
                        lifecycle_counts[
                            "ACTIVE"
                        ]
                    ),
                    nrnd_count=(
                        lifecycle_counts[
                            "NRND"
                        ]
                    ),
                    eol_count=(
                        lifecycle_counts[
                            "EOL"
                        ]
                    ),
                    obsolete_count=(
                        lifecycle_counts[
                            "OBSOLETE"
                        ]
                    ),
                    unknown_count=(
                        lifecycle_counts[
                            "UNKNOWN"
                        ]
                    ),
                    lifecycle_risk_count=(
                        lifecycle_risk_count
                    ),
                )
            ),
            availability=(
                ReportAvailabilitySummary(
                    availability_risk_count=(
                        availability_risk_count
                    ),
                    components_with_availability=(
                        components_with_availability
                    ),
                    components_without_availability=(
                        components_without_availability
                    ),
                )
            ),
            top_risk_components=(
                top_risk_components
            ),
            risk_drivers=risk_drivers,
            recommendations=recommendations,
        )

    @staticmethod
    def _parse_details(
        details: str | None,
    ) -> dict[str, Any]:
        """Safely decode persisted JSON details."""

        if not details:
            return {}

        try:
            parsed = json.loads(details)
        except (
            TypeError,
            ValueError,
        ):
            return {}

        if not isinstance(parsed, dict):
            return {}

        return parsed

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float:
        """Convert a value to float without raising."""

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

    @staticmethod
    def _extract_bom_explanation(
        details: str | None,
    ) -> tuple[
        str,
        list[ReportRiskDriver],
        list[ReportRecommendation],
    ]:
        """Extract persisted BOM explanation data."""

        payload = (
            ReportService._parse_details(
                details
            )
        )

        summary = str(
            payload.get(
                "summary",
                "BOM risk assessment is available.",
            )
        )

        drivers: list[
            ReportRiskDriver
        ] = []

        raw_drivers = payload.get(
            "risk_drivers",
            [],
        )

        if isinstance(raw_drivers, list):
            for item in raw_drivers:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                try:
                    drivers.append(
                        ReportRiskDriver(
                            component_id=int(
                                item[
                                    "component_id"
                                ]
                            ),
                            mpn=str(
                                item["mpn"]
                            ),
                            score=float(
                                item["score"]
                            ),
                            severity=str(
                                item[
                                    "severity"
                                ]
                            ),
                            reason=str(
                                item["reason"]
                            ),
                        )
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

        recommendations: list[
            ReportRecommendation
        ] = []

        raw_recommendations = (
            payload.get(
                "recommendations",
                [],
            )
        )

        if isinstance(
            raw_recommendations,
            list,
        ):
            for item in raw_recommendations:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                try:
                    component_id = (
                        item.get(
                            "component_id"
                        )
                    )

                    recommendations.append(
                        ReportRecommendation(
                            priority=str(
                                item[
                                    "priority"
                                ]
                            ),
                            component_id=(
                                int(
                                    component_id
                                )
                                if component_id
                                is not None
                                else None
                            ),
                            mpn=(
                                str(
                                    item["mpn"]
                                )
                                if item.get(
                                    "mpn"
                                )
                                is not None
                                else None
                            ),
                            action=str(
                                item["action"]
                            ),
                            reason=str(
                                item["reason"]
                            ),
                        )
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

        return (
            summary,
            drivers,
            recommendations,
        )

    @staticmethod
    def _infer_source_format(
        source_file: str | None,
    ) -> str | None:
        """Infer source format from the BOM filename."""

        if not source_file:
            return None

        suffix = Path(
            source_file
        ).suffix.lower()

        if not suffix:
            return None

        return suffix.lstrip(".")