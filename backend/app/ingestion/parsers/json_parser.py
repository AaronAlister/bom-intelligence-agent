import json
from pathlib import Path
from typing import Any

from .base import BaseBOMParser


class JSONBOMParser(BaseBOMParser):

    supported_extensions = {
        ".json",
    }

    def parse(
        self,
        file_path: Path
    ) -> list[dict[str, Any]]:

        with file_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return [
                {
                    str(key): value
                    for key, value in record.items()
                }
                for record in data
                if isinstance(record, dict)
            ]

        if isinstance(data, dict):

            for key in (
                "components",
                "items",
                "bom",
                "parts",
                "data",
            ):

                value = data.get(key)

                if isinstance(value, list):

                    return [
                        {
                            str(k): v
                            for k, v in record.items()
                        }
                        for record in value
                        if isinstance(record, dict)
                    ]

            return [
                {
                    str(key): value
                    for key, value in data.items()
                }
            ]

        raise ValueError(
            "Unsupported JSON BOM structure"
        )