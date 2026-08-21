from dataclasses import dataclass

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)


@dataclass(slots=True)
class EnrichmentAttempt:
    """Record the outcome of one provider attempt."""

    provider: str
    status: str
    error: str | None = None


@dataclass(slots=True)
class EnrichmentOutcome:
    """Complete outcome of the distributor enrichment chain."""

    result: ComponentEnrichmentResult | None
    attempts: list[EnrichmentAttempt]

    @property
    def found(self) -> bool:
        """Return whether a provider successfully enriched the component."""

        return self.result is not None

    @property
    def provider_failed(self) -> bool:
        """Return whether at least one provider failed."""

        return any(
            attempt.status == "FAILED"
            for attempt in self.attempts
        )

    @property
    def all_providers_failed(self) -> bool:
        """Return whether every provider failed."""

        return bool(self.attempts) and all(
            attempt.status == "FAILED"
            for attempt in self.attempts
        )


class EnrichmentOrchestrator:
    """Coordinates multiple component enrichment providers."""

    def __init__(
        self,
        providers: list[ComponentEnrichmentProvider],
    ) -> None:
        if not providers:
            raise ValueError(
                "At least one enrichment provider is required"
            )

        self._providers = providers

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> EnrichmentOutcome:
        """
        Try providers in priority order.

        Provider outcomes are tracked separately so that
        NOT_FOUND and provider failures are not conflated.

        The first successful enrichment result is returned.
        """

        attempts: list[EnrichmentAttempt] = []

        for provider in self._providers:
            try:
                result = await provider.enrich(
                    mpn=mpn,
                    manufacturer=manufacturer,
                )

            except Exception as exc:
                attempts.append(
                    EnrichmentAttempt(
                        provider=provider.name,
                        status="FAILED",
                        error=str(exc),
                    )
                )
                continue

            if result is None:
                attempts.append(
                    EnrichmentAttempt(
                        provider=provider.name,
                        status="NOT_FOUND",
                    )
                )
                continue

            attempts.append(
                EnrichmentAttempt(
                    provider=provider.name,
                    status="ENRICHED",
                )
            )

            return EnrichmentOutcome(
                result=result,
                attempts=attempts,
            )

        return EnrichmentOutcome(
            result=None,
            attempts=attempts,
        )

    @property
    def providers(
        self,
    ) -> tuple[ComponentEnrichmentProvider, ...]:
        """Return providers in priority order."""

        return tuple(self._providers)