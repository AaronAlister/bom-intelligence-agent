from collections.abc import Iterable
from datetime import date

from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.lifecycle.models import (
    LifecycleAssessment,
    LifecycleRisk,
    LifecycleStatus,
)


class LifecycleAssessor:
    """
    Converts distributor lifecycle information into a
    normalized lifecycle assessment.
    """

    _STATUS_MAP = {
        "ACTIVE": LifecycleStatus.ACTIVE,
        "PRODUCTION": LifecycleStatus.ACTIVE,
        "NRND": LifecycleStatus.NRND,
        "NOT RECOMMENDED FOR NEW DESIGNS": (
            LifecycleStatus.NRND
        ),
        "EOL": LifecycleStatus.EOL,
        "END OF LIFE": LifecycleStatus.EOL,
        "OBSOLETE": LifecycleStatus.OBSOLETE,
        "DISCONTINUED": LifecycleStatus.OBSOLETE,
    }

    @classmethod
    def assess(
        cls,
        results: Iterable[ComponentEnrichmentResult],
    ) -> LifecycleAssessment:
        """
        Assess lifecycle status from distributor results.

        The first recognized lifecycle status in provider
        priority order is used.
        """

        for result in results:
            normalized_status = cls._normalize_status(
                result.lifecycle_status
            )

            if normalized_status is None:
                continue

            return LifecycleAssessment(
                status=normalized_status,
                eol_date=None,
                last_buy_date=None,
                risk=cls._get_risk(
                    normalized_status
                ),
                source=result.source,
            )

        return LifecycleAssessment(
            status=LifecycleStatus.UNKNOWN,
            eol_date=None,
            last_buy_date=None,
            risk=LifecycleRisk.UNKNOWN,
            source=None,
        )

    @classmethod
    def _normalize_status(
        cls,
        status: str | None,
    ) -> LifecycleStatus | None:
        if status is None:
            return None

        normalized = (
            status.strip()
            .upper()
        )

        if not normalized:
            return None

        return cls._STATUS_MAP.get(
            normalized
        )

    @staticmethod
    def _get_risk(
        status: LifecycleStatus,
    ) -> LifecycleRisk:
        if status == LifecycleStatus.ACTIVE:
            return LifecycleRisk.LOW

        if status == LifecycleStatus.NRND:
            return LifecycleRisk.MEDIUM

        if status == LifecycleStatus.EOL:
            return LifecycleRisk.HIGH

        if status == LifecycleStatus.OBSOLETE:
            return LifecycleRisk.CRITICAL

        return LifecycleRisk.UNKNOWN