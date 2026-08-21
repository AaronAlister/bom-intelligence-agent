from dataclasses import dataclass

from backend.app.agents.tools.base import AgentTool


@dataclass(frozen=True)
class ToolMetadata:
    """Static metadata describing an agent tool."""

    name: str
    description: str
    dependencies: tuple[str, ...]


class AgentToolRegistry:
    """
    Registry of tools available to the BOM agent.

    The registry owns tool discovery and metadata lookup.
    It does not execute tools.
    """

    def __init__(
        self,
        tools: list[AgentTool] | None = None,
    ) -> None:
        self._tools: dict[str, AgentTool] = {}

        if tools is not None:
            for tool in tools:
                self.register(tool)

    def register(
        self,
        tool: AgentTool,
    ) -> None:
        """
        Register a tool by its unique name.

        Raises:
            ValueError: If another tool is already registered
                with the same name.
        """

        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self._tools[tool.name] = tool

    def get(
        self,
        name: str,
    ) -> AgentTool:
        """
        Return a registered tool.

        Raises:
            KeyError: If the requested tool is not registered.
        """

        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(
                f"Tool '{name}' is not registered."
            ) from exc

    def contains(
        self,
        name: str,
    ) -> bool:
        """Return whether a tool is registered."""

        return name in self._tools

    def names(self) -> tuple[str, ...]:
        """Return registered tool names in registration order."""

        return tuple(self._tools.keys())

    def metadata(
        self,
        name: str,
    ) -> ToolMetadata:
        """Return metadata for a registered tool."""

        tool = self.get(name)

        return ToolMetadata(
            name=tool.name,
            description=tool.description,
            dependencies=tool.dependencies,
        )

    def all_metadata(self) -> tuple[ToolMetadata, ...]:
        """Return metadata for all registered tools."""

        return tuple(
            self.metadata(name)
            for name in self._tools
        )