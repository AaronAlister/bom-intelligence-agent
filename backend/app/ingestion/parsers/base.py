from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseBOMParser(ABC):
    """
    Base interface for BOM file parsers.

    Parsers are responsible only for reading the source
    file and converting it into raw records.

    They should NOT perform:
    - column detection
    - normalization
    - validation
    - deduplication
    """

    supported_extensions: set[str] = set()

    @abstractmethod
    def parse(
        self,
        file_path: Path
    ) -> list[dict[str, Any]]:
        """
        Parse a BOM file into raw row dictionaries.
        """
        raise NotImplementedError

    def supports(
        self,
        extension: str
    ) -> bool:
        return extension.lower() in self.supported_extensions