from backend.app.intelligence.enrichment.arrow import (
    ArrowProvider,
)
from backend.app.intelligence.enrichment.digikey import (
    DigiKeyProvider,
)
from backend.app.intelligence.enrichment.mouser import (
    MouserProvider,
)
from backend.app.intelligence.enrichment.orchestrator import (
    EnrichmentOrchestrator,
)
from backend.app.intelligence.enrichment.registry import (
    EnrichmentProviderRegistry,
)


def create_default_registry() -> EnrichmentProviderRegistry:
    """
    Create the default distributor provider registry.

    Provider priority:
        1. Mouser
        2. Arrow
        3. Digi-Key
    """

    registry = EnrichmentProviderRegistry()

    registry.register(MouserProvider())
    registry.register(ArrowProvider())
    registry.register(DigiKeyProvider())

    return registry


def create_default_orchestrator() -> EnrichmentOrchestrator:
    """
    Create the default enrichment orchestrator using
    the configured distributor priority.
    """

    registry = create_default_registry()

    return EnrichmentOrchestrator(
        [
            registry.get("mouser"),
            registry.get("arrow"),
            registry.get("digikey"),
        ]
    )