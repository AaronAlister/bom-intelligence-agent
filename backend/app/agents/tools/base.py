from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from typing import Any

from backend.app.agents.state import ToolResult


def serialize_result(result: Any) -> dict[str, Any]:
    """
    Serialize an intelligence result into a JSON-compatible
    dictionary without coupling the agent layer to a specific
    result model implementation.
    """

    if isinstance(result, dict):
        return result

    model_dump = getattr(result, "model_dump", None)

    if callable(model_dump):
        dumped = model_dump(mode="json")

        if isinstance(dumped, dict):
            return dumped

        raise TypeError(
            "model_dump() must return a dictionary"
        )

    legacy_dict = getattr(result, "dict", None)

    if callable(legacy_dict):
        dumped = legacy_dict()

        if isinstance(dumped, dict):
            return dumped

        raise TypeError(
            "dict() must return a dictionary"
        )

    if is_dataclass(result):
        if isinstance(result, type):
            raise TypeError(
                "Dataclass classes are not supported; "
                "an instance is required."
            )

        dumped = asdict(result)

        if isinstance(dumped, dict):
            return dumped

        raise TypeError(
            "asdict() must return a dictionary"
        )

    raise TypeError(
        f"Unsupported result type: {type(result).__name__}"
    )


class AgentTool(ABC):
    """
    Base interface for deterministic capabilities exposed
    to the BOM agent.
    """

    name: str

    description: str

    dependencies: tuple[str, ...] = ()

    @abstractmethod
    async def execute(
        self,
        *,
        bom_id: str,
        component_ids: list[str],
        context: dict[str, Any],
    ) -> ToolResult:
        """
        Execute the capability.

        Implementations should delegate to existing
        intelligence services rather than duplicating
        business logic.
        """
        raise NotImplementedError
    