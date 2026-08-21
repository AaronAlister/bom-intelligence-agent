from backend.app.intelligence.enrichment.arrow import (
    ArrowProvider,
)
from backend.app.intelligence.enrichment.digikey import (
    DigiKeyProvider,
)
from backend.app.intelligence.enrichment.factory import (
    create_default_orchestrator,
    create_default_registry,
)
from backend.app.intelligence.enrichment.mouser import (
    MouserProvider,
)


def test_default_registry_contains_all_distributors():
    registry = create_default_registry()

    assert registry.list_names() == [
        "mouser",
        "arrow",
        "digikey",
    ]


def test_default_registry_returns_correct_providers():
    registry = create_default_registry()

    assert isinstance(
        registry.get("mouser"),
        MouserProvider,
    )

    assert isinstance(
        registry.get("arrow"),
        ArrowProvider,
    )

    assert isinstance(
        registry.get("digikey"),
        DigiKeyProvider,
    )


def test_default_orchestrator_preserves_priority():
    orchestrator = create_default_orchestrator()

    providers = orchestrator.providers

    assert len(providers) == 3

    assert isinstance(
        providers[0],
        MouserProvider,
    )

    assert isinstance(
        providers[1],
        ArrowProvider,
    )

    assert isinstance(
        providers[2],
        DigiKeyProvider,
    )