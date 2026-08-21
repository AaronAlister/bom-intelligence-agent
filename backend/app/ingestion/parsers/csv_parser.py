import csv
from pathlib import Path
from typing import Any

from .base import BaseBOMParser


class CSVBOMParser(BaseBOMParser):

    supported_extensions = {
        ".csv",
        ".tsv",
    }

    def parse(
        self,
        file_path: Path
    ) -> list[dict[str, Any]]:

        delimiter = (
            "\t"
            if file_path.suffix.lower() == ".tsv"
            else ","
        )

        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(
                file,
                delimiter=delimiter
            )

            records = []

            for row in reader:

                cleaned_row = {
                    str(key).strip():
                    value.strip()
                    if isinstance(value, str)
                    else value

                    for key, value in row.items()
                }

                records.append(cleaned_row)

            return records