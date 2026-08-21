from backend.app.intelligence.enrichment.base import (
    ComponentEnrichmentProvider,
)


class EnrichmentProviderRegistry:
    """Registry of component enrichment providers."""

    def __init__(self) -> None:
        self._providers: dict[
            str,
            ComponentEnrichmentProvider,
        ] = {}

    def register(
        self,
        provider: ComponentEnrichmentProvider,
    ) -> None:
        """Register an enrichment provider."""

        name = provider.name.strip().lower()

        if not name:
            raise ValueError(
                "Provider name cannot be empty"
            )

        if name in self._providers:
            raise ValueError(
                f"Provider already registered: {name}"
            )

        self._providers[name] = provider

    def get(
        self,
        name: str,
    ) -> ComponentEnrichmentProvider:
        """Retrieve a registered provider."""

        normalized_name = name.strip().lower()

        try:
            return self._providers[normalized_name]
        except KeyError:
            raise KeyError(
                f"Unknown enrichment provider: "
                f"{normalized_name}"
            ) from None

    def list_names(self) -> list[str]:
        """Return registered provider names."""

        return list(self._providers.keys())