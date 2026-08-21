from backend.app.intelligence.alternatives.models import (
    AlternativeAnalysis,
    AlternativeCandidate,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


class AlternativeMatcher:
    """
    Rank potential replacement components.

    Candidates are classified as:

    RECOMMENDED:
        Strong compatibility signals.

    REVIEW:
        Potentially relevant replacement requiring engineering
        validation before substitution.

    Candidates with insufficient relevance are discarded.
    """

    CATEGORY_WEIGHT = 35.0
    PACKAGE_WEIGHT = 30.0
    MANUFACTURER_WEIGHT = 10.0
    LIFECYCLE_WEIGHT = 15.0
    AVAILABILITY_WEIGHT = 10.0

    REVIEW_THRESHOLD = 30.0
    RECOMMENDED_THRESHOLD = 80.0

    @classmethod
    def analyze(
        cls,
        *,
        source: ComponentEnrichmentResult,
        candidates: list[ComponentEnrichmentResult],
    ) -> AlternativeAnalysis:
        """
        Rank candidate components against a source component.
        """

        scored: list[AlternativeCandidate] = []

        for candidate in candidates:
            if candidate.mpn == source.mpn:
                continue

            result = cls._score_candidate(
                source=source,
                candidate=candidate,
            )

            if result is not None:
                scored.append(result)

        scored.sort(
            key=lambda candidate: (
                candidate.compatibility_score
            ),
            reverse=True,
        )

        return AlternativeAnalysis(
            source_mpn=source.mpn or "",
            candidates=scored,
            best_candidate=(
                scored[0]
                if scored
                else None
            ),
        )

    @classmethod
    def _score_candidate(
        cls,
        *,
        source: ComponentEnrichmentResult,
        candidate: ComponentEnrichmentResult,
    ) -> AlternativeCandidate | None:
        """
        Calculate compatibility for one candidate.
        """

        category_match = cls._matches(
            source.category,
            candidate.category,
        )

        category_family_match = cls._category_family_match(
            source.category,
            candidate.category,
        )

        package_match = cls._matches(
            source.package,
            candidate.package,
        )

        manufacturer_match = cls._matches(
            source.manufacturer,
            candidate.manufacturer,
        )

        # ----------------------------------------------------------
        # Compatibility gates
        # ----------------------------------------------------------

        # Completely unrelated categories are rejected.
        if not category_match and not category_family_match:
            return None

        # Exact category with a different package is not considered
        # a valid alternative. This prevents ordinary components
        # with the same category but incompatible packages from
        # being surfaced as alternatives.
        #
        # A family-level category match with a different package is
        # intentionally allowed as REVIEW because it may represent
        # a legitimate cross-category catalog normalization case.
        if category_match and not package_match:
            return None

        # Family-level compatibility with a different package is
        # only useful when the manufacturer also matches.
        #
        # This is the intended REVIEW path for cases such as:
        #
        # ARM Microcontrollers - MCU / LQFP-100
        #                 ->
        # MCU / LQFP-48
        if (
            category_family_match
            and not package_match
            and not manufacturer_match
        ):
            return None

        lifecycle_score = cls._lifecycle_score(
            candidate.lifecycle_status
        )

        availability_score = cls._availability_score(
            candidate.availability
        )

        score = 0.0

        if category_match:
            score += cls.CATEGORY_WEIGHT
        elif category_family_match:
            score += cls.CATEGORY_WEIGHT * 0.75

        if package_match:
            score += cls.PACKAGE_WEIGHT

        if manufacturer_match:
            score += cls.MANUFACTURER_WEIGHT

        score += lifecycle_score
        score += availability_score

        score = round(
            min(score, 100.0),
            2,
        )

        if score < cls.REVIEW_THRESHOLD:
            return None

        compatibility_status = (
            "RECOMMENDED"
            if score >= cls.RECOMMENDED_THRESHOLD
            else "REVIEW"
        )

        reasons = cls._build_reasons(
            category_match=category_match,
            category_family_match=category_family_match,
            package_match=package_match,
            manufacturer_match=manufacturer_match,
            lifecycle_score=lifecycle_score,
            availability_score=availability_score,
            compatibility_status=compatibility_status,
        )

        return AlternativeCandidate(
            component=candidate,
            compatibility_score=score,
            compatibility_status=compatibility_status,
            category_match=category_match,
            package_match=package_match,
            manufacturer_match=manufacturer_match,
            lifecycle_score=lifecycle_score,
            availability_score=availability_score,
            reasons=reasons,
        )

    @classmethod
    def _category_family_match(
        cls,
        source_category: str | None,
        candidate_category: str | None,
    ) -> bool:
        """
        Detect broad component-category family compatibility.

        Examples:

            ARM Microcontrollers - MCU
            8-bit Microcontrollers - MCU
            MCU
            Wireless MCU

        can belong to the same MCU family.
        """

        if not source_category or not candidate_category:
            return False

        source = source_category.strip().lower()
        candidate = candidate_category.strip().lower()

        if source == candidate:
            return False

        families = (
            (
                "microcontroller",
                "microcontrollers",
                "mcu",
            ),
            (
                "memory",
                "flash",
                "nor flash",
                "nand flash",
                "dram",
                "sram",
            ),
            (
                "resistor",
                "resistors",
            ),
            (
                "capacitor",
                "capacitors",
            ),
            (
                "diode",
                "diodes",
            ),
            (
                "mosfet",
                "mosfets",
            ),
            (
                "connector",
                "connectors",
            ),
        )

        for family in families:
            source_matches = any(
                token in source
                for token in family
            )

            candidate_matches = any(
                token in candidate
                for token in family
            )

            if source_matches and candidate_matches:
                return True

        return False

    @classmethod
    def _build_reasons(
        cls,
        *,
        category_match: bool,
        category_family_match: bool,
        package_match: bool,
        manufacturer_match: bool,
        lifecycle_score: float,
        availability_score: float,
        compatibility_status: str,
    ) -> list[str]:
        """
        Build human-readable explanations for the score.
        """

        reasons: list[str] = []

        if category_match:
            reasons.append(
                "Component category matches the source."
            )
        elif category_family_match:
            reasons.append(
                "Component belongs to the same category family "
                "as the source."
            )
        else:
            reasons.append(
                "Component category differs from the source."
            )

        if package_match:
            reasons.append(
                "Package matches the source component."
            )
        else:
            reasons.append(
                "Package differs from the source component."
            )

        if manufacturer_match:
            reasons.append(
                "Manufacturer matches the source component."
            )
        else:
            reasons.append(
                "Manufacturer differs from the source component."
            )

        if lifecycle_score > 0:
            reasons.append(
                "Candidate has a usable lifecycle status."
            )
        else:
            reasons.append(
                "Candidate lifecycle status is unknown "
                "or unsuitable."
            )

        if availability_score > 0:
            reasons.append(
                "Candidate has reported distributor availability."
            )
        else:
            reasons.append(
                "Candidate has no reported distributor availability."
            )

        if compatibility_status == "RECOMMENDED":
            reasons.append(
                "Candidate meets the recommended compatibility "
                "threshold."
            )
        else:
            reasons.append(
                "Engineering review is required before substitution."
            )

        return reasons

    # --- NEW METHOD ---
    @classmethod
    def is_compatible(
        cls,
        *,
        source: ComponentEnrichmentResult,
        candidate: ComponentEnrichmentResult,
    ) -> bool:
        """
        Return whether a candidate can pass the structural
        compatibility gates without lifecycle or availability data.
        """

        category_match = cls._matches(
            source.category,
            candidate.category,
        )

        category_family_match = cls._category_family_match(
            source.category,
            candidate.category,
        )

        package_match = cls._matches(
            source.package,
            candidate.package,
        )

        manufacturer_match = cls._matches(
            source.manufacturer,
            candidate.manufacturer,
        )

        if not category_match and not category_family_match:
            return False

        if category_match and not package_match:
            return False

        if (
            category_family_match
            and not package_match
            and not manufacturer_match
        ):
            return False

        return True

    @staticmethod
    def _matches(
        source_value: str | None,
        candidate_value: str | None,
    ) -> bool:
        """
        Perform case-insensitive exact matching.
        """

        if not source_value or not candidate_value:
            return False

        return (
            source_value.strip().lower()
            == candidate_value.strip().lower()
        )

    @staticmethod
    def _lifecycle_score(
        lifecycle_status: str | None,
    ) -> float:
        """
        Convert lifecycle status into a score.
        """

        if not lifecycle_status:
            return 0.0

        status = lifecycle_status.strip().upper()

        if status == "ACTIVE":
            return 15.0

        if status == "NRND":
            return 5.0

        return 0.0

    @staticmethod
    def _availability_score(
        availability: int | None,
    ) -> float:
        """
        Convert distributor availability into a score.
        """

        if availability is None:
            return 0.0

        if availability >= 1000:
            return 10.0

        if availability > 0:
            return 5.0

        return 0.0