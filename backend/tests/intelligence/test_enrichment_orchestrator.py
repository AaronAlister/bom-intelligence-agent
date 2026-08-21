import pytest

from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)
from backend.app.intelligence.enrichment.models import (
    ComponentEnrichmentResult,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)


class SuccessfulProvider(ComponentEnrichmentProvider):
    def __init__(
        self,
        name: str,
        result: ComponentEnrichmentResult | None,
    ) -> None:
        self._name = name
        self._result = result
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1
        return self._result


class FailingProvider(ComponentEnrichmentProvider):
    def __init__(self, name: str) -> None:
        self._name = name
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    async def enrich(
        self,
        *,
        mpn: str,
        manufacturer: str | None = None,
    ) -> ComponentEnrichmentResult | None:
        self.calls += 1
        raise RuntimeError("Provider failure")


@pytest.mark.asyncio
async def test_first_successful_provider_wins():
    first = SuccessfulProvider(
        "first",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="first",
        ),
    )

    second = SuccessfulProvider(
        "second",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="second",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    outcome = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert outcome.result is not None
    assert outcome.result.source == "first"
    assert outcome.found is True
    assert outcome.provider_failed is False

    assert first.calls == 1
    assert second.calls == 0


@pytest.mark.asyncio
async def test_not_found_falls_back_to_next_provider():
    first = SuccessfulProvider(
        "first",
        None,
    )

    second = SuccessfulProvider(
        "second",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="second",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    outcome = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert outcome.result is not None
    assert outcome.result.source == "second"
    assert outcome.attempts[0].status == "NOT_FOUND"
    assert outcome.attempts[1].status == "ENRICHED"

    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_provider_failure_falls_back_to_next_provider():
    first = FailingProvider("first")

    second = SuccessfulProvider(
        "second",
        ComponentEnrichmentResult(
            mpn="LM358DR",
            manufacturer="Texas Instruments",
            source="second",
        ),
    )

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    outcome = await orchestrator.enrich(
        mpn="LM358DR",
        manufacturer="Texas Instruments",
    )

    assert outcome.result is not None
    assert outcome.result.source == "second"
    assert outcome.attempts[0].status == "FAILED"
    assert outcome.attempts[1].status == "ENRICHED"

    assert outcome.provider_failed is True
    assert outcome.all_providers_failed is False

    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_all_providers_not_found_returns_empty_outcome():
    first = SuccessfulProvider(
        "first",
        None,
    )

    second = SuccessfulProvider(
        "second",
        None,
    )

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    outcome = await orchestrator.enrich(
        mpn="UNKNOWN",
        manufacturer="Unknown",
    )

    assert outcome.result is None
    assert outcome.found is False
    assert outcome.provider_failed is False
    assert outcome.all_providers_failed is False

    assert [attempt.status for attempt in outcome.attempts] == [
        "NOT_FOUND",
        "NOT_FOUND",
    ]

    assert first.calls == 1
    assert second.calls == 1


@pytest.mark.asyncio
async def test_all_provider_failures_returns_failed_outcome():
    first = FailingProvider("first")
    second = FailingProvider("second")

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    outcome = await orchestrator.enrich(
        mpn="UNKNOWN",
        manufacturer="Unknown",
    )

    assert outcome.result is None
    assert outcome.found is False
    assert outcome.provider_failed is True
    assert outcome.all_providers_failed is True

    assert [attempt.status for attempt in outcome.attempts] == [
        "FAILED",
        "FAILED",
    ]

    assert first.calls == 1
    assert second.calls == 1


def test_orchestrator_requires_provider():
    with pytest.raises(ValueError):
        EnrichmentOrchestrator([])


def test_providers_preserve_priority_order():
    first = SuccessfulProvider("first", None)
    second = SuccessfulProvider("second", None)

    orchestrator = EnrichmentOrchestrator(
        [first, second]
    )

    assert orchestrator.providers == (
        first,
        second,
    )